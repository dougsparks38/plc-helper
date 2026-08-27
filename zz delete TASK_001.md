# TASK_001 — Document data structures for SCADA designer

## Your job

Read every `.L5X` file provided and produce or update the unified
reference document that the SCADA/Ignition designer uses to build
their tag structure.

---

## Step 1 — Identify the current reference file

Find the most recent version of the reference file:

```bash
ls PLCHelper_Reference_v*.md | sort | tail -1
```

Note the current version number. The output file will be bumped by 0.1
(e.g. v1.3 → v1.4).

---

## Step 2 — Locate L5X files to process

```bash
find . -name "*.L5X" | sort
```

Process all L5X files found. Determine each file's type by inspecting
the XML:
- If it contains `AddOnInstructionDefinition Use="Target"` → AOI file
- If it contains `DataType Use="Target"` → UDT file

---

## Step 3 — Parse each file

**AOI files** — extract from `<Parameters>`:
- `Name` attribute → `.Name` in output
- `<Description>` text → description in output
- Exclude nothing — include all parameters

**UDT files** — extract from `<Members>`:
- `Name` attribute → `.Name` in output
- `<Description>` text → description in output
- Skip members where `Hidden="true"`
- Skip members whose name starts with `ZZZZZZZZZZ`

**Critical**: Copy every name exactly as it appears in the XML —
character for character, no capitalization changes of any kind.
These names are used directly in PLC and Ignition code; any change
will break the program.

If a parameter or member has no `<Description>`, write a short
plain-English description inferred from the name using the naming
convention table in `CLAUDE.md`.

---

## Step 4 — Merge and sort

Combine all parsed sections (AOIs and UDTs) into a single list sorted
alphabetically by section name.

---

## Step 5 — Write the output file

Use this format for every section:

```
## SECTION_NAME

.MemberName - Description
.MemberName - Description
```

- Do not include local tags
- Do not include dependent AOI information
- Preserve any existing `[exclude]` markers if updating an existing file
- Do not add or remove `[exclude]` markers

Save as the next version (e.g. `PLCHelper_Reference_v1.1.md`). Do not
delete or overwrite the previous version. Update the version number
in the file header.

---

## Step 6 — Confirm

- Print a summary of all sections documented
- Flag any files that were missing or could not be parsed
- Confirm no section is empty or missing
