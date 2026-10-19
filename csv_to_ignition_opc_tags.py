#!/usr/bin/env python3
"""
csv_to_ignition_opc_tags.py -- PLCHelper TASK_014, script 2 of 2.

Turns the reviewed tag-map CSV (from pdf_comms_list_to_csv.py) into an
Ignition tag import JSON that binds existing memory tags to PLC addresses.

Inputs (all read only; none is ever overwritten):
  --csv     the reviewed tag-map CSV. Uses: device, address, ignition_path,
            ignition_data_type (and tag_name for messages).
  --base    the existing Ignition tag export (the folder/tag tree to keep).
  --sample  ONE atomic tag exported from Ignition after binding it by hand
            (e.g. dragged in from the OPC browser). It is the template for the
            OPC server name, the valueSource value, any other tag-level
            properties it carries, and the OPC item path format
            "<prefix>[<device>]<address>".
Output:
  --out     a NEW JSON file: the base tree, unchanged except that every tag
            the CSV binds gets valueSource / opcServer / opcItemPath (and any
            other non-per-tag property the sample carries). Name, folder,
            tooltip, engUnit and everything else already on the base tag are
            kept as they are. Plain atomic tags only -- no UDTs.
  A build report CSV is written beside it ("<out> - build report.csv").

Rules:
  * A CSV row is bound only when its ignition_path names exactly one atomic
    tag in the base export. Blank path, path not found, or two CSV rows for
    the same path -> reported, not built.
  * Data type: if the base tag's dataType and the CSV's ignition_data_type
    differ, the tag is reported and NOT bound (no choosing). A blank CSV type
    keeps the base type.
  * The address is used exactly as the CSV gives it (bit addresses such as
    Word[0].3 included); the device name's brackets come from the CSV.
  * Properties the sample does not have are never added; properties the base
    tag already has are kept.

Exit code: 0 = every CSV row with a path was bound, 1 = bad arguments,
2 = finished but some rows were not built (see build report).
"""

import argparse
import copy
import csv
import json
import os
import re
import sys

# Keys that belong to each tag individually; never copied from the sample.
PER_TAG_KEYS = {"name", "tagType", "dataType", "opcItemPath", "tooltip",
                "engUnit", "documentation", "value", "tags", "path", "fullPath"}
ITEM_PATH_RE = re.compile(r"^(?P<prefix>.*?)\[(?P<device>[^\]]+)\](?P<address>.+)$")
REPORT_COLUMNS = ["status", "tag_name", "ignition_path", "address", "detail"]


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def export_roots(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "tagType" not in data and "tags" in data:
        return data["tags"]
    return [data]


def index_atomic(data):
    """Map 'Folder/Sub/Name' -> list of atomic tag dicts (live references)."""
    idx = {}

    def walk(node, parents):
        here = parents + [node.get("name", "")]
        if node.get("tagType") == "AtomicTag":
            idx.setdefault("/".join(here), []).append(node)
        for child in node.get("tags", []) or []:
            walk(child, here)

    for root in export_roots(data):
        walk(root, [])
    return idx


def read_sample(path):
    s = load_json(path)
    if isinstance(s, dict) and "tags" in s and "tagType" not in s:
        if len(s["tags"]) != 1:
            raise ValueError("sample must contain exactly one tag")
        s = s["tags"][0]
    if s.get("tagType") != "AtomicTag":
        raise ValueError("sample is not an AtomicTag")
    for k in ("valueSource", "opcServer", "opcItemPath"):
        if not s.get(k):
            raise ValueError(f"sample has no {k!r}")
    m = ITEM_PATH_RE.match(s["opcItemPath"])
    if not m:
        raise ValueError(f"sample opcItemPath not in '<prefix>[<device>]<address>' form: "
                         f"{s['opcItemPath']!r}")
    copy_props = {k: v for k, v in s.items() if k not in PER_TAG_KEYS}
    return s, m.group("prefix"), copy_props


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", required=True, help="reviewed tag-map CSV")
    ap.add_argument("--base", required=True, help="existing Ignition tag export JSON (read only)")
    ap.add_argument("--sample", required=True,
                    help="one hand-bound atomic tag exported from Ignition (read only)")
    ap.add_argument("--out", required=True, help="new output JSON path")
    ap.add_argument("--report", help="build report path (default: '<out> - build report.csv')")
    ap.add_argument("--replace-output", action="store_true",
                    help="allow replacing an existing OUTPUT file (inputs are never replaceable)")
    a = ap.parse_args(argv)
    if not a.report:
        stem = a.out[:-5] if a.out.lower().endswith(".json") else a.out
        a.report = stem + " - build report.csv"
    inputs = {os.path.abspath(p) for p in (a.csv, a.base, a.sample)}
    for o in (a.out, a.report):
        if os.path.abspath(o) in inputs:
            ap.error(f"refusing to write over an input file: {o}")
        if os.path.exists(o) and not a.replace_output:
            ap.error(f"output already exists (use --replace-output to replace it): {o}")
    for p in (a.csv, a.base, a.sample):
        if not os.path.isfile(p):
            ap.error(f"input not found: {p}")
    return a


def run(argv=None):
    a = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        sample, prefix, copy_props = read_sample(a.sample)
    except ValueError as e:
        print(f"Sample problem: {e}", file=sys.stderr)
        return 1

    base = load_json(a.base)
    out = copy.deepcopy(base)
    idx = index_atomic(out)

    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    need = {"device", "address", "ignition_path", "ignition_data_type", "tag_name"}
    missing = need - set(rows[0].keys() if rows else need)
    if missing:
        print(f"CSV is missing columns: {sorted(missing)}", file=sys.stderr)
        return 1

    report = []
    by_path = {}
    for r in rows:
        p = (r.get("ignition_path") or "").strip()
        if not p:
            report.append(["NOT BUILT", r["tag_name"], "", r["address"],
                           "no ignition_path in CSV"])
            continue
        by_path.setdefault(p, []).append(r)

    bound = 0
    for path, rs in by_path.items():
        r = rs[0]
        if len(rs) > 1:
            for x in rs:
                report.append(["NOT BUILT", x["tag_name"], path, x["address"],
                               f"{len(rs)} CSV rows point at this Ignition tag"])
            continue
        tags = idx.get(path, [])
        if len(tags) != 1:
            report.append(["NOT BUILT", r["tag_name"], path, r["address"],
                           "Ignition path not found in base export" if not tags
                           else "Ignition path is not unique in base export"])
            continue
        tag = tags[0]
        dev = (r.get("device") or "").strip()
        addr = (r.get("address") or "").strip()
        if not (dev.startswith("[") and dev.endswith("]") and len(dev) > 2):
            report.append(["NOT BUILT", r["tag_name"], path, addr,
                           f"device not in brackets: {dev!r}"])
            continue
        if not addr:
            report.append(["NOT BUILT", r["tag_name"], path, addr, "no address"])
            continue
        csv_type = (r.get("ignition_data_type") or "").strip()
        base_type = tag.get("dataType", "")
        if csv_type and base_type and csv_type != base_type:
            report.append(["NOT BUILT", r["tag_name"], path, addr,
                           f"data type conflict: base export {base_type}, CSV {csv_type}"])
            continue
        notes = []
        if csv_type and not base_type:
            # The base tag sits at Ignition's default type; the CSV is certain.
            tag["dataType"] = csv_type
            notes.append(f"dataType set to {csv_type} (base tag had none)")
        if tag.get("valueSource") not in (None, "memory"):
            notes.append(f"base valueSource was {tag.get('valueSource')!r}")
        for k, v in copy_props.items():
            tag[k] = v
        tag["opcItemPath"] = f"{prefix}{dev}{addr}"
        for k in ("value",):
            if k in tag:
                notes.append(f"base tag keeps its '{k}' key")
        bound += 1
        report.append(["BOUND", r["tag_name"], path, addr,
                       tag["opcItemPath"] + ("; " + "; ".join(notes) if notes else "")])

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(a.report, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(REPORT_COLUMNS)
        w.writerows(report)

    not_built = sum(1 for x in report if x[0] != "BOUND")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"Sample: opcServer={sample['opcServer']!r}, path prefix={prefix!r}, "
          f"copied properties={sorted(copy_props)}")
    print(f"CSV rows: {len(rows)}; bound: {bound}; not built: {not_built}")
    print(f"Output: {a.out}")
    print(f"Report: {a.report}")
    print("NOT validated in Ignition -- do a small trial import first.")
    return 2 if not_built else 0


if __name__ == "__main__":
    sys.exit(run())
