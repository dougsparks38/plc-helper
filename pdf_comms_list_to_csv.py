#!/usr/bin/env python3
"""
pdf_comms_list_to_csv.py -- PLCHelper TASK_014, script 1 of 2.

Reads one or more vendor "data communication list" PDFs (tables that name each
comms point and give its address in the vendor PLC) and writes ONE reviewable
CSV, one row per point, plus an issues report beside it.

Why words, not pdfplumber's table cells
---------------------------------------
Vendor lists exported from a spreadsheet often come out of pdfplumber with
merged cells: a whole column of tag names in one cell, all descriptions in
another, addresses and units run together in a third, matched only by order.
Matching by order is exactly the guess this tool must never make. So each
point is rebuilt from the words on the page by their position: words on the
same text line belong to the same row, and a row is a point only when it holds
a data-type word immediately followed by an address word (the "anchor").
The table cells are still read, but only as an independent cross-check: the
tag names (and the addresses of named rows) found in the table cells must
appear in the same order as in the word-position parse, or the section stops.

Safety rules (from the approved plan)
-------------------------------------
* Per section (page + section title), names, addresses, types and
  descriptions are counted. If the named rows do not all have an address and
  a type on the same line, the whole section is stopped: an ERROR naming the
  PDF, page and section goes to the issues report and nothing from that
  section is written to the CSV.
* A named row with a blank description or no units is still a certain row
  (its fields came from one text line); the gap is written in `notes`.
* Rows with an address but no tag name (spares, container words), malformed
  addresses, hardwired-signal sections, and any text that fits no rule go to
  the issues report, never into the CSV.
* The Ignition path is filled only from an EXACT tag-name match in the
  optional Ignition export. No match -> blank path plus a note (with a
  "possible match" hint when names differ only in punctuation / suffix).

Usage
-----
python pdf_comms_list_to_csv.py ^
    --input "<list A.pdf>" "[Device A]" ^
    --input "<list B.pdf>" "[Device B]" ^
    --vendor <VendorWord> ^
    [--ignition-export "<tags export.json>"] ^
    --out "<tag map.csv>"

--input takes the PDF path AND the Ignition OPC device name (in brackets) for
that PDF. There is no default device name: a missing one is an error.
--vendor is the word the PDFs use for the vendor PLC in their "From: X To: Y"
page headers; it decides `direction` (From vendor = read, To vendor = write).

Exit code: 0 = clean, 1 = bad arguments / unreadable input,
2 = finished but at least one section was stopped (see issues report).
"""

import argparse
import collections
import csv
import json
import os
import re
import sys

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    sys.exit("pdfplumber is required: pip install pdfplumber")

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Data-type words as they appear in vendor lists (case-insensitive) and the
# Ignition tag dataType each one maps to. Logix DINT = 32-bit -> Int4,
# INT = 16-bit -> Int2, SINT = 8-bit -> Int1, REAL = 32-bit float -> Float4,
# BOOL -> Boolean (Ignition 8.x tag data types).
TYPE_MAP = {
    "bool": "Boolean",
    "real": "Float4",
    "dint": "Int4",
    "int": "Int2",
    "sint": "Int1",
    "lint": "Int8",
    "lreal": "Float8",
}

# A Logix address: name, one or more [index], optional .member/.bit parts.
ADDRESS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[\d+\])+(\.[A-Za-z0-9_]+)*$")
BIT_ADDRESS_RE = re.compile(r"^(?P<base>.*\])\.(?P<bit>\d+)$")
START_VALUE_RE = re.compile(r"^(TRUE|FALSE|-?\d+(\.\d+)?%?)$", re.IGNORECASE)
SECTION_LAST_WORDS = {"array", "signals", "values"}

ROW_TOLERANCE = 4.0      # words whose tops differ by <= this share a row
CELL_GAP = 12.0          # gap (pt) that splits right-hand words into cells
CONTINUATION_GAP = 16.0  # max vertical gap for a remarks continuation line

CSV_COLUMNS = [
    "device", "ignition_folder", "tag_name", "description", "data_type",
    "ignition_data_type", "units", "start_value", "remarks", "address",
    "direction", "source_pdf", "page", "section", "ignition_path", "notes",
    "raw_after_address",
]
ISSUE_COLUMNS = ["severity", "source_pdf", "page", "section", "item", "detail"]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def norm(text):
    """Lower-case and drop everything but letters and digits."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def cluster_rows(words):
    """Group words into text rows by their top coordinate."""
    rows = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and w["top"] - rows[-1]["top"] <= ROW_TOLERANCE:
            rows[-1]["words"].append(w)
        else:
            rows.append({"top": w["top"], "words": [w]})
    for r in rows:
        r["words"].sort(key=lambda w: w["x0"])
        r["text"] = " ".join(w["text"] for w in r["words"])
    return rows


def find_anchor(row_words):
    """Index of a type word directly followed by an address word, else None."""
    for i in range(len(row_words) - 1):
        if row_words[i]["text"].lower() in TYPE_MAP and \
                ADDRESS_RE.match(row_words[i + 1]["text"]):
            return i
    return None


def find_address_only(row_words):
    """Index of the first address-looking word (no type word before it)."""
    for i, w in enumerate(row_words):
        if ADDRESS_RE.match(w["text"]):
            return i
    return None


def looks_like_broken_address(text):
    return "[" in text and not ADDRESS_RE.match(text)


def split_cells(words):
    """Split a run of words into cells wherever the horizontal gap is large."""
    cells = []
    for w in words:
        if cells and w["x0"] - cells[-1][-1]["x1"] <= CELL_GAP:
            cells[-1].append(w)
        else:
            cells.append([w])
    return [" ".join(w["text"] for w in c) for c in cells]


def is_units_cell(text):
    """Conservative: at most two short tokens, no '=' and no digits.
    Anything else stays in `remarks`; the untouched text is always kept in
    `raw_after_address` for review."""
    toks = text.split()
    return (0 < len(toks) <= 2 and "=" not in text
            and not re.search(r"\d", text)
            and all(len(t) <= 10 for t in toks))


def classify_trailing(cells):
    """start value / units / remarks from the cells right of the address."""
    start = units = ""
    rest = list(cells)
    if rest and START_VALUE_RE.match(rest[0]):
        start = rest.pop(0)
    if rest and is_units_cell(rest[0]):
        units = rest.pop(0)
    return start, units, " ".join(rest)


def page_direction(row_texts, vendor):
    """'read' / 'write' / '' from a 'From: X To: Y' page header line."""
    v = vendor.lower()
    for t in row_texts:
        m = re.search(r"From:\s*(.*?)\s+To:\s*(.*)", t)
        if m:
            src, dst = m.group(1).lower(), m.group(2).lower()
            if src.startswith(v) and not dst.startswith(v):
                return "read", t
            if dst.startswith(v) and not src.startswith(v):
                return "write", t
            return "", t
    return None, None


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------

def description_column_x(rows):
    """Left edge of the description column, from this page's anchored rows.

    In each anchored row with two or more words before the type word, the
    description starts after the widest horizontal gap (tag names may hold
    spaces, but the column gap is wider than a word space). The most common
    such x position on the page is the column edge.
    """
    candidates = []
    for r in rows:
        a = find_anchor(r["words"])
        if a is None or a < 2:
            continue
        left = r["words"][:a]
        gaps = [(left[i + 1]["x0"] - left[i]["x1"], i + 1) for i in range(len(left) - 1)]
        gap, idx = max(gaps)
        if gap > CELL_GAP:
            candidates.append(round(left[idx]["x0"]))
    if not candidates:
        return None
    return collections.Counter(candidates).most_common(1)[0][0]


def parse_page(page, pdf_name, page_no, vendor, state, issues):
    """Parse one page. Returns a list of section dicts (see new_section)."""
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    rows = cluster_rows(words)
    row_texts = [r["text"] for r in rows]

    direction, from_line = page_direction(row_texts, vendor)
    if direction is not None:
        state["direction"] = direction
        state["from_line"] = from_line
        if direction == "":
            issues.append(["WARNING", pdf_name, page_no, "",
                           "direction", f"page header not understood: {from_line!r}"])

    desc_x = description_column_x(rows)
    if desc_x is not None:
        state["desc_x"] = desc_x

    sections = []
    seen_marker = False
    section = None
    last_point = None

    def new_section(title, kind):
        s = {"title": title, "kind": kind, "page": page_no, "points": [],
             "named_without_address": [], "direction": state.get("direction", ""),
             "from_line": state.get("from_line", "")}
        sections.append(s)
        return s

    # A page with no section marker of its own continues the previous page's
    # section (vendor lists split long arrays across pages).
    has_marker = any("hardwired signals" in t.lower() or "ethernet/ip signals" in t.lower()
                     for t in row_texts)
    if not has_marker and state.get("kind"):
        seen_marker = True
        section = new_section(state.get("title", "(continued)"), state["kind"])

    for r in rows:
        t = r["text"]
        tl = t.lower()
        ws = r["words"]

        if "hardwired signals" in tl:
            seen_marker = True
            state["kind"] = "hardwired"
            state["title"] = "Hardwired signals"
            section = new_section("Hardwired signals", "hardwired")
            last_point = None
            continue
        if "ethernet/ip signals" in tl:
            seen_marker = True
            state["kind"] = "comms"
            state["title"] = "(untitled)"
            section = new_section("(untitled)", "comms")
            last_point = None
            continue
        if not seen_marker and section is None:
            continue  # page title block (project, list name, From/To line)
        if tl.startswith("tag ") and "description" in tl:
            continue  # column header row
        if t.startswith("*"):
            issues.append(["INFO", pdf_name, page_no, section["title"] if section else "",
                           "footnote", t])
            continue

        anchor = find_anchor(ws)
        dx = state.get("desc_x")

        if anchor is None:
            addr_i = find_address_only(ws)
            broken = [w["text"] for w in ws if looks_like_broken_address(w["text"])]
            # Section title: everything in the tag column, ends in array/signals/values
            if (addr_i is None and not broken and ws[-1]["text"].lower() in SECTION_LAST_WORDS
                    and (dx is None or all(w["x0"] < dx - 2 for w in ws))):
                # A title inside a hardwired block stays hardwired.
                kind = section["kind"] if section else "comms"
                state["title"] = t
                section = new_section(t, kind)
                last_point = None
                continue
            if section is None:
                issues.append(["INFO", pdf_name, page_no, "", "unplaced text", t])
                continue
            if addr_i is not None or broken:
                issues.append(["WARNING", pdf_name, page_no, section["title"],
                               "address without data type",
                               f"{t!r} -- not written to CSV"])
                continue
            # Remarks continuation (e.g. a multi-line value list)
            if (last_point is not None and r["top"] - last_point["_bottom"] <= CONTINUATION_GAP
                    and all(w["x0"] > last_point["_addr_x"] for w in ws)):
                last_point["remarks"] = (last_point["remarks"] + "; " + t).strip("; ")
                last_point["raw_after_address"] += " | " + t
                last_point["_bottom"] = r["top"]
                last_point["_cont"] += 1
                continue
            # Words only in the tag column: a named row with no address
            if dx is not None and all(w["x0"] < dx - 2 for w in ws):
                section["named_without_address"].append(t)
                continue
            issues.append(["INFO", pdf_name, page_no, section["title"], "unparsed text", t])
            continue

        # Anchored row: <tag words> <description words> TYPE ADDRESS <trailing>
        left = ws[:anchor]
        if dx is None:
            tag_words, desc_words = left[:1], left[1:]
        else:
            tag_words = [w for w in left if w["x0"] < dx - 5]
            desc_words = [w for w in left if w["x0"] >= dx - 5]
        tag = " ".join(w["text"] for w in tag_words)
        desc = " ".join(w["text"] for w in desc_words)
        dtype = ws[anchor]["text"]
        addr_w = ws[anchor + 1]
        trailing = ws[anchor + 2:]
        start, units, remarks = classify_trailing(split_cells(trailing))

        if section is None:
            section = new_section("(untitled)", "comms")
        point = {
            "tag_name": tag, "description": desc, "data_type": dtype,
            "ignition_data_type": TYPE_MAP[dtype.lower()],
            "units": units, "start_value": start, "remarks": remarks,
            "raw_after_address": " ".join(w["text"] for w in trailing),
            "address": addr_w["text"], "page": page_no,
            "section": section["title"], "notes": [],
            "_addr_x": addr_w["x0"], "_bottom": r["top"], "_cont": 0,
        }
        section["points"].append(point)
        last_point = point
    return sections


# ---------------------------------------------------------------------------
# Table-cell cross-check
# ---------------------------------------------------------------------------

def table_sequences(page):
    """Tag-like lines and address-first lines, in table reading order."""
    lines = []
    for table in page.extract_tables():
        for row in table:
            for cell in row:
                if cell:
                    lines.extend(l.strip() for l in cell.split("\n") if l.strip())
    addrs = []
    for l in lines:
        first = l.split()[0]
        if ADDRESS_RE.match(first):
            addrs.append(first)
    return lines, addrs


def is_subsequence(needle, hay):
    it = iter(hay)
    return all(any(x == y for y in it) for x in needle)


def cross_check_page(page, sections):
    """Return an error string, or '' when the table cells agree."""
    lines, t_addrs = table_sequences(page)
    named = [p for s in sections for p in s["points"] if p["tag_name"]]
    if not named:
        return ""
    names = [p["tag_name"] for p in named]
    name_set = set(names)
    t_names = [l for l in lines if l in name_set]
    if not t_names:
        return ""  # table extraction found no tag cells at all; nothing to compare
    # Every named row must appear in the table's tag cells in the same order.
    if not is_subsequence(names, t_names):
        return ("tag order in table cells differs from the word-position parse "
                f"(table: {len(t_names)} names, parse: {len(names)} names)")
    if t_addrs and not is_subsequence([p["address"] for p in named], t_addrs):
        return "addresses of named rows are not in the same order in the table cells"
    return ""


# ---------------------------------------------------------------------------
# Ignition export cross-reference
# ---------------------------------------------------------------------------

def export_roots(data):
    """Top-level nodes of an Ignition export: a folder object, a bare
    {"tags": [...]} wrapper, or a list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "tagType" not in data and "tags" in data:
        return data["tags"]
    return [data]


def load_ignition_index(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    index = collections.defaultdict(list)

    def walk(node, parents):
        here = parents + [node.get("name", "")]
        if node.get("tagType") == "AtomicTag":
            index[node["name"]].append("/".join(here))
        for child in node.get("tags", []) or []:
            walk(child, here)

    for root in export_roots(data):
        walk(root, [])
    return index


def possible_matches(name, index):
    n = norm(name)
    hits = [k for k in index if norm(k) == n]
    if not hits:
        hits = [k for k in index if norm(k).startswith(n) and len(norm(k)) - len(n) <= 4]
    return sorted(hits)


def attach_ignition_paths(points, index):
    for p in points:
        paths = index.get(p["tag_name"], [])
        if len(paths) == 1:
            p["ignition_path"] = paths[0]
        elif len(paths) > 1:
            sec = norm(re.sub(r"\b(array|signals|values)\b", "", p["section"], flags=re.I))
            pick = [x for x in paths if norm(x.split("/")[-2]) == sec] if sec else []
            if len(pick) == 1:
                p["ignition_path"] = pick[0]
                p["notes"].append(f"name is in {len(paths)} Ignition folders; "
                                  f"picked the folder whose name equals the section title")
            else:
                p["ignition_path"] = ""
                p["notes"].append("name is in several Ignition folders, not resolved: "
                                  + ", ".join(paths))
        else:
            p["ignition_path"] = ""
            hint = possible_matches(p["tag_name"], index)
            p["notes"].append("no exact name match in Ignition export"
                              + (f" (possible: {', '.join(hint)})" if hint else ""))
        p["ignition_folder"] = p["ignition_path"].rsplit("/", 1)[0] if p["ignition_path"] else ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", nargs=2, action="append", metavar=("PDF", "DEVICE"),
                    required=True,
                    help='PDF path and its Ignition OPC device name in brackets, e.g. "[Device A]"')
    ap.add_argument("--vendor", required=True,
                    help='word the PDFs use for the vendor PLC in "From: X To: Y" headers')
    ap.add_argument("--ignition-export", help="existing Ignition tag export JSON (read only)")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--issues", help="issues report path (default: '<out> - issues.csv')")
    a = ap.parse_args(argv)
    for pdf, dev in a.input:
        if not (dev.startswith("[") and dev.endswith("]") and len(dev) > 2):
            ap.error(f"device name for {pdf!r} must be given in brackets, e.g. \"[Device A]\"; got {dev!r}")
        if not os.path.isfile(pdf):
            ap.error(f"PDF not found: {pdf}")
    if not a.issues:
        stem = a.out[:-4] if a.out.lower().endswith(".csv") else a.out
        a.issues = stem + " - issues.csv"
    inputs = {os.path.abspath(p) for p, _ in a.input}
    if a.ignition_export:
        inputs.add(os.path.abspath(a.ignition_export))
    for o in (a.out, a.issues):
        if os.path.abspath(o) in inputs:
            ap.error(f"output path is one of the inputs: {o}")
    return a


def run(argv=None):
    a = parse_args(argv if argv is not None else sys.argv[1:])
    issues = []
    out_rows = []
    summary = []
    stopped = 0

    for pdf_path, device in a.input:
        pdf_name = os.path.basename(pdf_path)
        state = {}
        with pdfplumber.open(pdf_path) as pdf:
            for page_no, page in enumerate(pdf.pages, 1):
                sections = parse_page(page, pdf_name, page_no, a.vendor, state, issues)
                if not sections:
                    issues.append(["INFO", pdf_name, page_no, "", "page",
                                   "no signal sections on this page (cover / revision page?)"])
                    continue
                xerr = cross_check_page(page, sections)
                for s in sections:
                    named = [p for p in s["points"] if p["tag_name"]]
                    unnamed = [p for p in s["points"] if not p["tag_name"]]
                    n_desc = sum(1 for p in named if p["description"])
                    n_units = sum(1 for p in named if p["units"])
                    counts = (f"names={len(named) + len(s['named_without_address'])}, "
                              f"addresses={len(named)}, types={len(named)}, "
                              f"descriptions={n_desc}, units={n_units}")
                    if s["kind"] == "hardwired":
                        for p in s["points"]:
                            issues.append(["SKIPPED", pdf_name, page_no, s["title"],
                                           p["tag_name"] or p["address"],
                                           "hardwired signal -- not a comms point"])
                        if s["points"]:
                            summary.append((pdf_name, device, page_no, s["title"], 0, "hardwired, skipped"))
                        continue
                    if not s["points"] and not s["named_without_address"]:
                        continue
                    for u in unnamed:
                        issues.append(["WARNING", pdf_name, page_no, s["title"], u["address"],
                                       f"address with no tag name ({u['data_type']}"
                                       f"{', ' + u['remarks'] if u['remarks'] else ''}) -- not written"])
                    err = ""
                    if s["named_without_address"]:
                        err = ("count mismatch -- named rows without address/type on the same line: "
                               + " | ".join(s["named_without_address"]))
                    elif xerr:
                        err = "table-cell cross-check failed: " + xerr
                    if err:
                        stopped += 1
                        issues.append(["ERROR", pdf_name, page_no, s["title"], "section stopped",
                                       f"{err} ({counts}); nothing written for this section"])
                        summary.append((pdf_name, device, page_no, s["title"], 0, "STOPPED: " + counts))
                        continue
                    for p in named:
                        p["device"] = device
                        p["source_pdf"] = pdf_name
                        p["direction"] = s["direction"]
                        if not s["direction"]:
                            p["notes"].append("direction unknown (page header not understood)")
                        if not p["description"]:
                            p["notes"].append("description blank in PDF")
                        if p["_cont"]:
                            p["notes"].append(f"remarks continue over {p['_cont']} more line(s) in PDF")
                        vend = a.vendor.lower() + "_to_"
                        if s["direction"] == "write" and vend in p["address"].lower():
                            p["direction"] = ""
                            p["notes"].append(f"direction left blank -- conflict: page header says write "
                                              f"({s['from_line']!r}) but the address array name "
                                              f"reads as vendor-to-client")
                        out_rows.append(p)
                    summary.append((pdf_name, device, page_no, s["title"], len(named), counts))

    # Cross-checks over everything parsed
    by_name = collections.defaultdict(list)
    by_addr = collections.defaultdict(list)
    arr_types = collections.defaultdict(set)
    for p in out_rows:
        by_name[(p["device"], p["tag_name"])].append(p)
        by_addr[(p["device"], p["address"])].append(p)
        m = BIT_ADDRESS_RE.match(p["address"])
        base = p["address"].split("[")[0]
        arr_types[(p["device"], base)].add("bit of word" if m else p["data_type"].upper())
    for (dev, name), ps in by_name.items():
        if len(ps) > 1:
            where = ", ".join(f"p{q['page']} {q['section']}" for q in ps)
            for q in ps:
                q["notes"].append(f"tag name appears {len(ps)} times for this device ({where})")
    for (dev, addr), ps in by_addr.items():
        if len(ps) > 1:
            names = ", ".join(q["tag_name"] for q in ps)
            for q in ps:
                q["notes"].append(f"address used by {len(ps)} rows for this device ({names})")
    bit_words = collections.defaultdict(list)
    for p in out_rows:
        m = BIT_ADDRESS_RE.match(p["address"])
        if m:
            bit_words[(p["device"], m.group("base"))].append(p["tag_name"])
    for p in out_rows:
        users = bit_words.get((p["device"], p["address"]))
        if users:
            p["notes"].append(f"this element is also listed as a bit-word for: {', '.join(users)}")
    for (dev, base), types in arr_types.items():
        if len(types) > 1:
            issues.append(["WARNING", "", "", "", f"{dev} {base}",
                           "array listed with more than one data type: " + ", ".join(sorted(types))
                           + " -- a Logix array has one type; confirm in the PLC"])

    if a.ignition_export:
        index = load_ignition_index(a.ignition_export)
        attach_ignition_paths(out_rows, index)
        used = {p["ignition_path"] for p in out_rows if p["ignition_path"]}
        for name, paths in sorted(index.items()):
            for path in paths:
                if path not in used:
                    issues.append(["INFO", os.path.basename(a.ignition_export), "", "",
                                   path, "Ignition tag not matched by any CSV row"])
    else:
        for p in out_rows:
            p["ignition_path"] = p["ignition_folder"] = ""

    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for p in out_rows:
            row = dict(p)
            row["notes"] = "; ".join(p["notes"])
            w.writerow([row.get(c, "") for c in CSV_COLUMNS])
    with open(a.issues, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(ISSUE_COLUMNS)
        w.writerows(issues)

    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Sections:")
    for pdf_name, dev, page_no, title, n, counts in summary:
        print(f"  {pdf_name} | {dev} | p{page_no} | {title} | rows written: {n} | {counts}")
    sev = collections.Counter(i[0] for i in issues)
    print(f"CSV rows: {len(out_rows)} -> {a.out}")
    print(f"Issues: {dict(sev)} -> {a.issues}")
    if stopped:
        print(f"{stopped} section(s) STOPPED -- see ERROR lines in the issues report.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(run())
