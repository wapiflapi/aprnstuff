#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# ──────────────────────────────────────────────────────────────
# IDA-EXACT NID LOGIC
# ──────────────────────────────────────────────────────────────

ENCODING_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-"
NID_SUFFIX = bytes.fromhex("518D64A635DED8C1E6B039B1C3E55230")
NID_LEN = 11


def nid_from_name(name: str) -> str:
    """
    Exact match of IDA logic:
      sha1(name + suffix)[:8] → little-endian u64 → custom base64 → pad to 11
    """
    digest = hashlib.sha1(name.encode("ascii") + NID_SUFFIX).digest()[:8]
    (value,) = struct.unpack("<Q", digest)

    # encode
    out = ENCODING_CHARSET[((value & 0xF) << 2)]
    value >>= 4
    while value:
        out += ENCODING_CHARSET[value & 0x3F]
        value >>= 6

    out = out[::-1]
    if len(out) < NID_LEN:
        out = ("A" * (NID_LEN - len(out))) + out
    return out


# ──────────────────────────────────────────────────────────────
# ELF SYMBOL PARSING
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Sym:
    num: int
    value: int
    size: int
    stype: str
    bind: str
    vis: str
    ndx: str
    name: str


SYM_RE = re.compile(
    r"^\s*(\d+):\s+([0-9a-fA-F]+)\s+(\d+)\s+"
    r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$"
)


def read_symbols(path: Path) -> list[Sym]:
    p = subprocess.run(
        ["readelf", "-Ws", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        raise typer.BadParameter(p.stdout)

    syms: list[Sym] = []
    for line in p.stdout.splitlines():
        m = SYM_RE.match(line)
        if not m:
            continue
        num, value, size, stype, bind, vis, ndx, name = m.groups()
        syms.append(
            Sym(
                num=int(num),
                value=int(value, 16),
                size=int(size),
                stype=stype,
                bind=bind,
                vis=vis,
                ndx=ndx,
                name=name.strip(),
            )
        )
    return syms


def is_defined_func(sym: Sym) -> bool:
    return (
        sym.stype == "FUNC"
        and sym.ndx != "UND"
    )


# ──────────────────────────────────────────────────────────────
# RENAME LOGIC
# ──────────────────────────────────────────────────────────────

def build_mapping(
    syms: Iterable[Sym],
    *,
    prefix: str,
) -> list[tuple[Sym, str]]:
    out: list[tuple[Sym, str]] = []

    for s in syms:
        if not is_defined_func(s):
            continue
        if not s.name.startswith(prefix):
            continue

        logical_name = s.name[len(prefix):]  # strip nid_
        new_name = nid_from_name(logical_name)
        out.append((s, new_name))

    return out


def run_objcopy(
    input_elf: Path,
    output_elf: Path,
    mapping: list[tuple[Sym, str]],
) -> None:
    shutil.copy2(input_elf, output_elf)

    cmd = ["objcopy"]
    for old, new in mapping:
        cmd += ["--redefine-sym", f"{old.name}={new}"]
    cmd.append(str(output_elf))

    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise typer.BadParameter(p.stdout)


# ──────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False)
console = Console()


def render_table(mapping: list[tuple[Sym, str]]) -> None:
    t = Table(title=f"Renaming {len(mapping)} symbol(s)")
    t.add_column("Original", style="bold")
    t.add_column("Logical name")
    t.add_column("NID")
    t.add_column("Bind")
    t.add_column("Vis")
    t.add_column("Ndx")

    for s, nid in mapping:
        t.add_row(
            s.name,
            s.name.split("_", 1)[1],
            nid,
            s.bind,
            s.vis,
            s.ndx,
        )
    console.print(t)


@app.command()
def rename(
    input_elf: Path = typer.Argument(..., exists=True, readable=True),
    output_elf: Path = typer.Argument(...),
    prefix: str = typer.Option("__nid__", help="Prefix marking symbols to remap"),
    dry_run: bool = typer.Option(False, help="Do not write output file"),
):
    console.print(
        Panel.fit(
            f"[bold]Input:[/bold] {input_elf}\n"
            f"[bold]Output:[/bold] {output_elf}\n"
            f"[bold]Prefix:[/bold] {prefix}",
            title="ELF NID Renamer",
        )
    )

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t1 = p.add_task("Reading symbols…")
        syms = read_symbols(input_elf)
        p.update(t1, completed=1)

        t2 = p.add_task("Building mapping…")
        mapping = build_mapping(syms, prefix=prefix)
        p.update(t2, completed=1)

    if not mapping:
        console.print(f"[yellow]No matching functions found for prefix '{prefix}'.[/yellow]")
        raise typer.Exit(0)

    render_table(mapping)

    if dry_run:
        console.print("[cyan]Dry-run: not writing output[/cyan]")
        raise typer.Exit(0)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t3 = p.add_task("Running objcopy…")
        run_objcopy(input_elf, output_elf, mapping)
        p.update(t3, completed=1)

    console.print(f"[green]Done.[/green] Wrote {output_elf}")


if __name__ == "__main__":
    app()
