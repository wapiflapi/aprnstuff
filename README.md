# ELF NID Symbol Renamer

This repository contains a small utility script, `nid_rename.py`, that rewrites function symbol names in an ELF file into **deterministic identifier strings (NIDs)** derived from their original names.

The tool is intended for reverse-engineering and binary analysis workflows where:

* functions are initially named descriptively,
* then later need to be converted into compact, opaque identifiers,
* while keeping the ELF otherwise unchanged.

---

## What this tool does

Given an ELF file containing function symbols like:

```
__nid__exampleFunction
__nid__doSomethingImportant
```

The script:

1. Scans the ELF symbol table
2. Selects **defined function symbols** whose names start with a configurable prefix
   (default: `__nid__`)
3. Strips that prefix to recover the *logical* function name
   (`exampleFunction`, `doSomethingImportant`)
4. Computes a deterministic identifier string (NID) from that logical name using a
   fixed hashing + encoding scheme
5. Renames the ELF symbol using `objcopy --redefine-sym`

Example transformation:

```
__nid__exampleFunction  →  W0Aa+HAwN6U
```

The output ELF is otherwise identical to the input.

---

## What this tool does *not* do

* It does **not** change code, relocations, or data
* It does **not** add or remove symbols
* It does **not** guess which symbols “should” be renamed
* It does **not** validate the resulting ELF for any specific loader or runtime

This is a **symbol renaming utility**, not a full binary rewriter.

---

## Requirements

* Python 3.10+
* GNU binutils available in `PATH`:

  * `readelf`
  * `objcopy`

The script works on any ELF file that GNU binutils can parse, including executables,
shared objects, and non-standard ELF variants.

---

## Installation

No installation step is required.

Clone the repository and run the script directly:

```bash
git clone https://github.com/wapiflapi/aprnstuff
cd aprnstuff
```

---

## Usage

### Basic usage

Rename all functions prefixed with `__nid__`:

```bash
python3 nid_rename.py rename input.elf output.elf
```

### Dry run (no output written)

```bash
python3 nid_rename.py rename input.elf output.elf --dry-run
```

### Custom prefix

```bash
python3 nid_rename.py rename input.elf output.elf --prefix myprefix__
```

Only function symbols whose names start with the prefix are processed.

---

## Symbol selection rules

A symbol is renamed if **all** of the following are true:

* `Type == FUNC`
* `Ndx != UND` (the symbol is defined in the ELF)
* `name.startswith(prefix)`

Binding and visibility are intentionally ignored:

* `LOCAL`, `GLOBAL`, and `HIDDEN` symbols are all supported

This matches real-world ELF layouts where many internal functions are local or hidden.

---

## Identifier (NID) computation

The identifier generation logic is a **direct translation of existing prior work**
used in the reverse-engineering community.

High-level process:

1. Take the function name **without the prefix**
2. Append a fixed byte suffix
3. Compute SHA-1
4. Take the first 8 bytes as a little-endian 64-bit value
5. Encode that value using a custom 64-character alphabet
6. Left-pad the result to 11 characters

The output is:

* deterministic
* stable
* purely name-derived

---

## Output

* The input ELF is copied to the output path
* All renames are applied in a **single `objcopy` invocation**
* A Rich table is printed showing the mapping:

| Original symbol          | Logical name      | New name      |
| ------------------------ | ----------------- | ------------- |
| `__nid__exampleFunction` | `exampleFunction` | `W0Aa+HAwN6U` |

---

## Inspiration and prior work

This project does **not** introduce new algorithms or original techniques.

It is a Python translation and automation of ideas and logic that already exist in
prior public work, most notably tools and plugins developed by others in the reverse-engineering community.

In particular, the identifier computation and general workflow are inspired by:

* [https://github.com/flatz/ida_ps5_elf_plugin](https://github.com/flatz/ida_ps5_elf_plugin)

This repository merely packages those ideas into a standalone, scriptable ELF utility.

---

## Disclaimer (AI-Generated Code)

This project — including **all source code and documentation (this README included)** —
was generated using **generative AI**, with **minimal human intervention**.

Human involvement was limited to:

* defining requirements,
* validating behavior,
* and translating existing public work into a standalone script.

No claim of originality is made for the underlying techniques or algorithms.

Review, audit, and test the code yourself before using it in any context where
correctness, safety, or reversibility matters.

Use at your own risk.

---
