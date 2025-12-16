# ELF NID Renamer

This tool rewrites function symbol names in an ELF file into **PlayStation-style NIDs**, using the **exact same algorithm as IDA Pro**.

It is intended for working with **PS4/PS5 SPRX / PRX-like ELFs**, reverse-engineering workflows, and loader experiments where functions are identified by NID rather than by human-readable names.

---

## What this does

Given an ELF file containing functions named like:

```
nid_sceKernelFoo
nid_sceKernelBar
nid_sceKernelBaz
```

The tool:

1. Finds **defined function symbols** whose names start with a configurable prefix (`nid_` by default)
2. Strips the prefix (e.g. `sceKernelFoo`)
3. Computes a **PlayStation NID** from the stripped name using:

   * SHA-1
   * Sony’s fixed NID suffix
   * little-endian u64 truncation
   * Sony’s custom base64 alphabet
   * 11-character output (exact IDA behavior)
4. Renames the ELF symbol using `objcopy --redefine-sym`

Example result:

```
nid_sceKernelFoo  →  W0Aa+HAwN6U
```

The output ELF is otherwise unchanged.

---

## What this does *not* do

* It does **not** add or remove symbols
* It does **not** change relocation entries or code
* It does **not** modify import tables
* It does **not** guess exports — only symbols already present are renamed
* It does **not** attempt to make the ELF valid for any particular firmware

This is a **surgical symbol-renaming tool**, nothing more.

---

## Requirements

* Python 3.10+
* GNU binutils:

  * `readelf`
  * `objcopy`
* Works with:

  * executables
  * shared objects
  * SPRX / PRX-like ELFs (as long as GNU tools can parse them)

---

## Installation

No packaging required.

Clone the repository and run directly:

```bash
git clone <repo>
cd elf-nid-renamer
```

If you use `uv` (recommended):

```bash
uv run nid_rename rename input.elf output.elf
```

Otherwise:

```bash
python3 nid_rename rename input.elf output.elf
```

---

## Usage

### Basic usage

Rename all functions prefixed with `nid_`:

```bash
uv run nid_rename rename input.elf output.elf
```

### Dry run (no output written)

```bash
uv run nid_rename rename input.elf output.elf --dry-run
```

### Custom prefix

```bash
uv run nid_rename rename input.elf output.elf --prefix my_nid_
```

Only functions whose names start with the prefix are processed.

---

## Symbol selection rules

A symbol is renamed if:

* `Type == FUNC`
* `Ndx != UND` (defined in the file)
* `name.startswith(prefix)`

Binding and visibility do **not** matter:

* `LOCAL`, `GLOBAL`, `HIDDEN` are all supported

This matches real-world SPRX layouts where most NID-named functions are `LOCAL | HIDDEN`.

---

## NID computation details

The NID generation is **byte-for-byte identical to IDA Pro’s implementation**:

```text
SHA1( name_without_prefix + NID_SUFFIX )
↓
first 8 bytes
↓
little-endian uint64
↓
custom base64 encoding (A–Z a–z 0–9 + -)
↓
left-padded to 11 characters with 'A'
```

No additional salt is applied.
The prefix (`nid_`) is **not included** in the hash input.

---

## Output

* The input file is copied to the output path
* All renames are applied in a **single `objcopy` invocation**
* A Rich table shows the mapping:

| Original symbol  | Logical name | NID         |
| ---------------- | ------------ | ----------- |
| nid_sceKernelFoo | sceKernelFoo | W0Aa+HAwN6U |

---

## Typical use cases

* Preparing `.sprx` files for PS4/PS5 loaders
* Matching IDA-generated NIDs exactly
* Verifying symbol → NID mappings
* Rebuilding stripped or obfuscated modules
* ELF surgery during reverse-engineering

---

## Notes

* `objcopy --redefine-sym` works on local symbols, but behavior may vary on very exotic ELF formats
* If your toolchain rejects the file, you may need platform-specific binutils
* The script assumes ASCII symbol names

---

## License

Use at your own risk.
This tool performs low-level binary modification and is intended for reverse-engineering and research purposes.

---

Here’s a clean, explicit disclaimer section you can **append near the end of the README** (usually right before or inside the License section). It’s factual, unambiguous, and doesn’t sound defensive or goofy.

---

## Disclaimer (AI-Generated Code)

This project — including **all source code, scripts, and documentation (this README included)** — was generated using **generative AI**, with **minimal human intervention**.

Human involvement was limited to:

* defining requirements,
* validating behavior,
* and iterating on specifications.

No claim is made that the code follows best practices, is production-ready, or is free of errors.
Review, audit, and test the code yourself before using it in any context where correctness or safety matters.

Use at your own risk.
