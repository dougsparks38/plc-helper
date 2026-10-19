# pdf_comms_list_to_csv.py — quick help (TASK_014, script 1 of 2)

Reads vendor "data communication list" PDFs and writes one reviewable tag-map
CSV (one row per comms point) plus an issues report. Full write-up:
`PLCHelper_Tasks.md`, TASK_014.

## Run

```
python pdf_comms_list_to_csv.py --input "<list A.pdf>" "[Device A]" --input "<list B.pdf>" "[Device B]" --vendor <VendorWord> --ignition-export "<tags export.json>" --out "<tag map.csv>"
```

- `--input PDF DEVICE` — repeat once per PDF. DEVICE is the Ignition OPC
  device name **in brackets**. There is no default; leaving it out is an error.
- `--vendor` — the word the PDFs use for the vendor PLC in their
  "From: X To: Y" page headers. From vendor = `read`, to vendor = `write`.
- `--ignition-export` — optional. Fills `ignition_path` / `ignition_folder`
  from an **exact** tag-name match only.
- `--out` — the CSV. The issues report goes beside it as
  `<out> - issues.csv` unless `--issues` names another path.

Exit code 0 = clean, 2 = at least one section stopped (see ERROR lines).

## CSV columns

`device, ignition_folder, tag_name, description, data_type,
ignition_data_type, units, start_value, remarks, address, direction,
source_pdf, page, section, ignition_path, notes, raw_after_address`

- `data_type` is verbatim; `ignition_data_type` maps it (BOOL → Boolean,
  REAL → Float4, DINT → Int4, INT → Int2, SINT → Int1).
- `units` / `start_value` / `remarks` are split from the text right of the
  address by gap and content rules; the untouched text is in
  `raw_after_address`. Check it when units matter.
- `notes` carries every flag: no exact Ignition match (with a "possible:"
  hint), duplicate tag names, duplicate addresses, a word used both for bits
  and a value, blank description, direction conflicts.

## What goes to the issues report, not the CSV

Addresses with no tag name (spares, the DINT word itself), rows with an
address but no data type, malformed addresses, hardwired-signal sections,
footnotes and side notes, arrays listed with more than one data type, and
Ignition tags no CSV row matched.

## When a section is stopped

Names, addresses, types and descriptions are counted per section (page +
section title). A named row without an address and type on the same text
line, or table cells that list the names/addresses in a different order than
the text lines, stops the whole section: nothing from it is written and an
ERROR names the PDF, page and section.
