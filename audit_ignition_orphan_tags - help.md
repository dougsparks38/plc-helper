# audit_ignition_orphan_tags.py — quick help (TASK_006)

Lists every Ignition tag that has no matching tag in the current PLC
program. Read only: it never deletes or edits anything. Full write-up:
`PLCHelper_Tasks.md`, TASK_006.

## Run

```
python audit_ignition_orphan_tags.py --json "<tag export.json>" --l5x "<program.L5X>" --map CONSPD4_AOI=CONSPD2_AOI --output "<report.csv>"
```

- `--json` — an Ignition tag export (Tag Browser > More Options > Export).
- `--l5x` — a fresh full-program L5X export.
- `--map PLC_TYPE=IGNITION_UDT` — repeat once per Ignition UDT whose name
  differs from its PLC type (the known pairs are in TASK_005's table).
  Without one, a UDT name means the PLC type of the same name.
- `--output` — a new CSV; must not be one of the inputs.

## Report

Columns `status, ignition_path, ignition_type, reason`.

- **ORPHAN** — no PLC tag (or no such member) for this Ignition tag.
- **REVIEW** — needs Doug's decision: the PLC tag exists but with a
  different type, exists only in program scope, the tag is not PLC-bound,
  or its OPC path cannot be read.

Matched tags are only counted. Instance members are not compared with AOI
parameters. Exit code 2 = something was flagged.
