# csv_to_ignition_opc_tags.py — quick help (TASK_014, script 2 of 2)

Turns the reviewed tag-map CSV into an Ignition tag import JSON that binds
existing memory tags to PLC addresses as plain OPC atomic tags. Full
write-up: `PLCHelper_Tasks.md`, TASK_014.

## Run

```
python csv_to_ignition_opc_tags.py --csv "<tag map.csv>" --base "<tags export.json>" --sample "<one bound tag.json>" --out "<tags import.json>"
```

- `--csv` — the reviewed CSV from `pdf_comms_list_to_csv.py`.
- `--base` — the existing tag export; its folders, names, tooltips, engUnits
  and other properties are kept.
- `--sample` — **required**: one atomic tag bound by hand in Designer (drag
  one element in from the OPC browser) and exported. It supplies the OPC
  server name, `valueSource`, and the path format `<prefix>[<device>]<address>`.
- `--out` — a new file. The script refuses to write over any input, and
  refuses an existing output unless `--replace-output` is given.

A build report goes beside the output as `<out> - build report.csv`
(BOUND / NOT BUILT per CSV row). Exit code 2 = some rows were not built.

## What it changes on each bound tag

`valueSource`, `opcServer` (and any other non-per-tag property the sample
carries) and `opcItemPath` = sample prefix + CSV device + CSV address,
exactly as written (bit addresses like `Word[0].3` included). Nothing else.
Keys the base tag already has (for example a memory tag's `value`) stay; the
report notes them.

## Not built (reported, never guessed)

Blank `ignition_path`; path not in the base export; two CSV rows for one
tag; device not in brackets; no address; base `dataType` differs from the
CSV's `ignition_data_type`.

## Before relying on it

The output is **not validated** until a small trial import in Ignition
(a copy of one folder, or a test provider) shows good quality on the bound
tags. Changing/adding properties is a `MergeOverwrite`-safe import; see the
Ignition notes in TRUSTED_SOURCES.md.
