#!/usr/bin/env python3
"""
match_plc_tags_to_ignition_json.py -- match a list of PLC tag names to the
atomic tags in an Ignition tag export, and write a tag-map CSV that
csv_to_ignition_opc_tags.py can bind.

Inputs (all read only; none is ever overwritten):
  --input   the PLC tag list: an .xlsx (first sheet, or --sheet) or a .csv.
            Needs a header row with a NAME column; a DESCRIPTION column is
            copied through when present. Other columns are ignored.
  --json    the Ignition tag export to match against (folder/tag tree).
Output:
  --out     a NEW tag-map CSV with the columns csv_to_ignition_opc_tags.py
            reads -- device, address, ignition_path, ignition_data_type,
            tag_name -- then description, status, source_row for review.
            Only rows that matched cleanly are in it, so it can be bound as
            it is.
  A review report CSV is written beside it ("<out> - review report.csv")
  listing every row that is NOT in the tag map, and why.

Matching rules:
  * Key: the NAME with --strip-prefix removed from the front (exact,
    case-sensitive). The remainder must equal an atomic tag's name exactly.
    A NAME that does not start with the prefix is reported, not matched.
  * --skip-name NAME (repeatable): that row is left out on purpose and
    reported as SKIPPED.
  * --exclude-folder PATH (repeatable): atomic tags at or below this folder
    path in the export (full path from the export root, e.g.
    "Root/Area/OldFolder") are never matched. A same-named tag found there is
    reported as LEFT ALONE. A PATH that names no folder in the export stops
    the run (exit 1) so a typo cannot silently do nothing.
  * After exclusions, the name must match exactly one atomic tag. None ->
    NOT FOUND; more than one -> DUPLICATE (every path listed). Never guessed.
  * --expect-data-type TYPE (optional): a match whose dataType differs is
    reported as TYPE MISMATCH and left out of the tag map.
  * The same NAME twice in the input -> every copy reported, none matched.
  * device column = "[<--device>]"; address column = the NAME exactly as
    written in the input; ignition_data_type = the export tag's dataType.

Exit code: 0 = every row that was not skipped matched, 1 = bad arguments or
unreadable input, 2 = finished but some rows have problems (see report).
"""

import argparse
import csv
import os
import sys

from csv_to_ignition_opc_tags import export_roots, index_atomic, load_json

MAP_COLUMNS = ["device", "address", "ignition_path", "ignition_data_type", "tag_name",
               "description", "status", "source_row"]
REPORT_COLUMNS = ["status", "tag_name", "description", "ignition_path", "data_type",
                  "source_row", "detail"]
# Statuses that are expected outcomes, not problems.
NOT_PROBLEMS = {"SKIPPED", "LEFT ALONE", "NOTE"}


def read_input_rows(path, sheet=None):
    """Return [(source_row, name, description)] from an .xlsx or .csv."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb[sheet] if sheet else wb.worksheets[0]
        except KeyError:
            raise ValueError(f"sheet not found: {sheet!r} (sheets: {wb.sheetnames})")
        table = [list(r) for r in ws.iter_rows(values_only=True)]
        wb.close()
    else:
        if sheet:
            raise ValueError("--sheet only applies to an Excel input")
        with open(path, newline="", encoding="utf-8-sig") as f:
            table = list(csv.reader(f))
    if not table:
        raise ValueError("input is empty")
    header = [("" if h is None else str(h)).strip() for h in table[0]]
    if "NAME" not in header:
        raise ValueError(f"input has no NAME column (header: {header})")
    ni = header.index("NAME")
    di = header.index("DESCRIPTION") if "DESCRIPTION" in header else None
    rows = []
    for n, r in enumerate(table[1:], start=2):
        name = r[ni] if ni < len(r) else None
        name = "" if name is None else str(name).strip()
        if not name:
            continue
        desc = r[di] if di is not None and di < len(r) else None
        rows.append((n, name, "" if desc is None else str(desc).strip()))
    return rows


def folder_paths(data):
    """Every folder path in the export, in the same form index_atomic uses."""
    found = set()

    def walk(node, parents):
        here = parents + [node.get("name", "")]
        if node.get("tagType") in ("Folder", "Provider"):
            found.add("/".join(here))
        for child in node.get("tags", []) or []:
            walk(child, here)

    for root in export_roots(data):
        walk(root, [])
    return found


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", required=True, help="PLC tag list, .xlsx or .csv (read only)")
    ap.add_argument("--sheet", help="Excel sheet name (default: first sheet)")
    ap.add_argument("--json", required=True, help="Ignition tag export JSON (read only)")
    ap.add_argument("--strip-prefix", required=True,
                    help="prefix removed from the front of each NAME to get the Ignition tag name "
                         "(pass \"\" for none)")
    ap.add_argument("--device", required=True,
                    help="OPC device name, without brackets; written as [<device>]")
    ap.add_argument("--skip-name", action="append", default=[],
                    help="input NAME to leave out on purpose (repeatable)")
    ap.add_argument("--exclude-folder", action="append", default=[],
                    help="export folder path whose tags are never matched (repeatable)")
    ap.add_argument("--expect-data-type",
                    help="Ignition dataType every match must have (e.g. Float4); others reported")
    ap.add_argument("--out", required=True, help="new tag-map CSV path")
    ap.add_argument("--report", help="review report path (default: '<out> - review report.csv')")
    ap.add_argument("--replace-output", action="store_true",
                    help="allow replacing an existing OUTPUT file (inputs are never replaceable)")
    a = ap.parse_args(argv)
    if not a.report:
        stem = a.out[:-4] if a.out.lower().endswith(".csv") else a.out
        a.report = stem + " - review report.csv"
    dev = a.device.strip()
    if not dev or "[" in dev or "]" in dev:
        ap.error(f"--device must be the bare device name, no brackets: {a.device!r}")
    a.device = dev
    a.exclude_folder = [p.strip().strip("/") for p in a.exclude_folder]
    if any(not p for p in a.exclude_folder):
        ap.error("--exclude-folder given an empty path")
    for p in (a.input, a.json):
        if not os.path.isfile(p):
            ap.error(f"input not found: {p}")
    inputs = {os.path.abspath(p) for p in (a.input, a.json)}
    if os.path.abspath(a.out) == os.path.abspath(a.report):
        ap.error("--out and --report are the same file")
    for o in (a.out, a.report):
        if os.path.abspath(o) in inputs:
            ap.error(f"refusing to write over an input file: {o}")
        if os.path.exists(o) and not a.replace_output:
            ap.error(f"output already exists (use --replace-output to replace it): {o}")
    return a


def is_under(path, folder):
    return path.startswith(folder + "/")


def run(argv=None):
    a = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        rows = read_input_rows(a.input, a.sheet)
        data = load_json(a.json)
    except (ValueError, OSError) as e:
        print(f"Input problem: {e}", file=sys.stderr)
        return 1

    folders = folder_paths(data)
    bad = [p for p in a.exclude_folder if p not in folders]
    if bad:
        print(f"--exclude-folder names no folder in the export: {bad}", file=sys.stderr)
        return 1

    # Ignition tag name -> list of (path, tag) across the whole export.
    by_name = {}
    for path, tags in index_atomic(data).items():
        for t in tags:
            by_name.setdefault(t.get("name", ""), []).append((path, t))

    counts = {}
    for _, name, _ in rows:
        counts[name] = counts.get(name, 0) + 1

    tag_map, report = [], []
    skip = set(a.skip_name)
    used_skips = set()
    for src, name, desc in rows:
        if name in skip:
            used_skips.add(name)
            report.append(["SKIPPED", name, desc, "", "", src, "left out by --skip-name"])
            continue
        if counts[name] > 1:
            report.append(["DUPLICATE INPUT", name, desc, "", "", src,
                           f"NAME appears {counts[name]} times in the input; none matched"])
            continue
        if not name.startswith(a.strip_prefix):
            report.append(["NO PREFIX", name, desc, "", "", src,
                           f"NAME does not start with {a.strip_prefix!r}"])
            continue
        key = name[len(a.strip_prefix):]
        found = by_name.get(key, [])
        kept = []
        for path, t in found:
            hit = next((f for f in a.exclude_folder if is_under(path, f)), None)
            if hit:
                report.append(["LEFT ALONE", name, desc, path, t.get("dataType", ""), src,
                               f"in excluded folder {hit}; not bound, not changed"])
            else:
                kept.append((path, t))
        if not kept:
            report.append(["NOT FOUND", name, desc, "", "", src,
                           f"no atomic tag named {key!r}"
                           + (" outside the excluded folders" if found else "")])
            continue
        if len(kept) > 1:
            report.append(["DUPLICATE", name, desc, "; ".join(p for p, _ in kept), "", src,
                           f"{len(kept)} atomic tags named {key!r}; not chosen"])
            continue
        path, t = kept[0]
        dtype = t.get("dataType", "")
        if a.expect_data_type and dtype != a.expect_data_type:
            report.append(["TYPE MISMATCH", name, desc, path, dtype, src,
                           f"export dataType {dtype or '(none)'}, expected {a.expect_data_type}"])
            continue
        tag_map.append({"device": f"[{a.device}]", "address": name, "ignition_path": path,
                        "ignition_data_type": dtype, "tag_name": name, "description": desc,
                        "status": "MATCHED", "source_row": src})
    for s in sorted(skip - used_skips):
        report.append(["NOTE", s, "", "", "", "", "--skip-name not found in the input"])

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=MAP_COLUMNS)
        w.writeheader()
        w.writerows(tag_map)
    with open(a.report, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(REPORT_COLUMNS)
        w.writerows(report)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    tally = {}
    for r in report:
        tally[r[0]] = tally.get(r[0], 0) + 1
    problems = sum(n for s, n in tally.items() if s not in NOT_PROBLEMS)
    print(f"Input rows: {len(rows)}; matched: {len(tag_map)}; "
          + "; ".join(f"{s.lower()}: {n}" for s, n in sorted(tally.items())))
    print(f"Tag map: {a.out}")
    print(f"Report:  {a.report}")
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(run())
