#!/usr/bin/env python3
"""
Tests for PLCHelper TASK_014 (pdf_comms_list_to_csv.py and
csv_to_ignition_opc_tags.py). All fixtures are synthetic and built in code;
no real vendor list or Ignition export is read.

Run:  python test_task014.py
Scratch files go to ./_test_tmp_task014/ (git-ignored).
"""

import csv
import json
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pdf_comms_list_to_csv as s1  # noqa: E402
import csv_to_ignition_opc_tags as s2  # noqa: E402

TMP = os.path.join(HERE, "_test_tmp_task014")


# ---------------------------------------------------------------------------
# A fake pdfplumber page built from (top, x0, text) triples
# ---------------------------------------------------------------------------

def W(top, x0, text):
    return {"top": float(top), "x0": float(x0), "x1": float(x0) + 5.5 * len(text), "text": text}


class FakePage:
    def __init__(self, lines, tables=None):
        self.words = []
        for top, items in lines:
            for x0, text in items:
                self.words.append(W(top, x0, text))
        self.tables = tables or []

    def extract_words(self, **_):
        return list(self.words)

    def extract_tables(self):
        return self.tables


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def header(top=10):
    return [
        (top, [(70, "From:"), (100, "VEND"), (210, "To:"), (230, "Client")]),
        (top + 20, [(70, "Ethernet/IP"), (140, "signals:")]),
        (top + 30, [(130, "TAG"), (330, "Description"), (540, "Type"), (640, "Address")]),
    ]


def good_page():
    """Merged-cell style: names, descriptions and addresses only line up by y."""
    lines = header() + [
        (50, [(70, "Unit"), (100, "array")]),
        (62, [(70, "TAG_A"), (511, "Real"), (605, "ArrA[0]"), (760, "0.0"), (840, "degF")]),
        (63, [(211, "First"), (250, "value")]),
        (75, [(70, "Two"), (95, "Words"), (211, "Second"), (260, "value"),
              (511, "Bool"), (605, "Word[1].3"), (886, "1"), (894, "="), (902, "On")]),
        (88, [(70, "TAG_C"), (211, "Third"), (511, "DINT"), (605, "ArrB[2]"), (886, "0"), (894, "="), (902, "Off")]),
        (100, [(886, "1"), (894, "="), (902, "Run")]),
        (113, [(511, "Real"), (605, "ArrA[9]")]),   # spare: no tag name
    ]
    tables = [[["Ethernet/IP signals:", None, None]],
              [["TAG_A\nTwo Words\nTAG_C", "First value Real",
                "ArrA[0] 0.0 degF\nWord[1].3 1 = On\nArrB[2] 0 = Off\nArrA[9]"]]]
    return FakePage(lines, tables)


def bad_page():
    """A named row whose address is missing -> section must stop."""
    lines = header() + [
        (50, [(70, "Bad"), (100, "array")]),
        (62, [(70, "TAG_X"), (211, "Has"), (240, "address"), (511, "Real"), (605, "ArrC[0]")]),
        (75, [(70, "TAG_Y")]),
    ]
    return FakePage(lines)


def order_mismatch_page():
    """Table cells list the names in a different order than the text lines."""
    lines = header() + [
        (50, [(70, "Swap"), (100, "array")]),
        (62, [(70, "TAG_P"), (211, "Desc"), (240, "one"), (511, "Real"), (605, "ArrD[0]")]),
        (75, [(70, "TAG_Q"), (211, "Desc"), (240, "two"), (511, "Real"), (605, "ArrD[1]")]),
    ]
    tables = [[["TAG_Q\nTAG_P", "x", "ArrD[1]\nArrD[0]"]]]
    return FakePage(lines, tables)


def hardwired_page():
    lines = [
        (10, [(70, "From:"), (100, "Client"), (210, "To:"), (230, "VEND")]),
        (30, [(70, "Hardwired"), (135, "signals:")]),
        (40, [(130, "TAG"), (330, "Description"), (540, "Type")]),
        (60, [(70, "Ethernet/IP"), (140, "signals:")]),
        (70, [(130, "TAG"), (330, "Description"), (540, "Type")]),
        (80, [(70, "Boolean"), (120, "signals")]),
        (92, [(70, "CMD_1"), (211, "Command"), (260, "one"), (511, "Bool"), (605, "ToVend[0].2")]),
        (104, [(70, "CMD_2"), (211, "Wrong"), (260, "way"), (511, "Bool"), (605, "VEND_to_Client[0].1")]),
    ]
    return FakePage(lines)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Script1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)
        os.makedirs(TMP)

    def run_s1(self, pages, export=None, device="[Device A]"):
        pdf_path = os.path.join(TMP, "list.pdf")
        open(pdf_path, "wb").close()
        out = os.path.join(TMP, "map.csv")
        args = ["--input", pdf_path, device, "--vendor", "VEND", "--out", out]
        if export is not None:
            exp = os.path.join(TMP, "export.json")
            write_json(exp, export)
            args += ["--ignition-export", exp]
        orig = s1.pdfplumber.open
        s1.pdfplumber.open = lambda p: FakePdf(pages)
        try:
            code = s1.run(args)
        finally:
            s1.pdfplumber.open = orig
        return code, read_csv(out), read_csv(os.path.join(TMP, "map - issues.csv"))

    def test_row_alignment_by_position(self):
        code, rows, issues = self.run_s1([good_page()])
        self.assertEqual(code, 0)
        by = {r["tag_name"]: r for r in rows}
        self.assertEqual(sorted(by), ["TAG_A", "TAG_C", "Two Words"])
        self.assertEqual(by["TAG_A"]["description"], "First value")
        self.assertEqual(by["TAG_A"]["address"], "ArrA[0]")
        self.assertEqual(by["TAG_A"]["units"], "degF")
        self.assertEqual(by["TAG_A"]["start_value"], "0.0")
        self.assertEqual(by["TAG_A"]["ignition_data_type"], "Float4")
        self.assertEqual(by["Two Words"]["address"], "Word[1].3")
        self.assertEqual(by["Two Words"]["ignition_data_type"], "Boolean")
        self.assertEqual(by["TAG_C"]["remarks"], "0 = Off; 1 = Run")
        self.assertEqual(by["TAG_A"]["direction"], "read")
        self.assertEqual(by["TAG_A"]["device"], "[Device A]")
        self.assertTrue(any(i["item"] == "ArrA[9]" for i in issues), "spare row reported")
        self.assertNotIn("", by)

    def test_count_mismatch_stops_section(self):
        code, rows, issues = self.run_s1([bad_page()])
        self.assertEqual(code, 2)
        self.assertEqual(rows, [])
        err = [i for i in issues if i["severity"] == "ERROR"]
        self.assertEqual(len(err), 1)
        self.assertEqual(err[0]["page"], "1")
        self.assertEqual(err[0]["section"], "Bad array")
        self.assertIn("list.pdf", err[0]["source_pdf"])

    def test_table_order_cross_check_stops_section(self):
        code, rows, issues = self.run_s1([order_mismatch_page()])
        self.assertEqual(code, 2)
        self.assertEqual(rows, [])
        self.assertTrue(any("cross-check" in i["detail"] for i in issues))

    def test_write_direction_and_conflict(self):
        code, rows, issues = self.run_s1([hardwired_page()])
        by = {r["tag_name"]: r for r in rows}
        self.assertEqual(by["CMD_1"]["direction"], "write")
        self.assertEqual(by["CMD_2"]["direction"], "")
        self.assertIn("conflict", by["CMD_2"]["notes"])

    def test_ignition_cross_reference(self):
        export = {"name": "Root", "tagType": "Folder", "tags": [
            {"name": "Unit", "tagType": "Folder", "tags": [
                {"name": "TAG_A", "tagType": "AtomicTag", "dataType": "Float4", "valueSource": "memory"},
                {"name": "Two_Words", "tagType": "AtomicTag", "dataType": "Boolean", "valueSource": "memory"},
            ]}]}
        code, rows, issues = self.run_s1([good_page()], export=export)
        by = {r["tag_name"]: r for r in rows}
        self.assertEqual(by["TAG_A"]["ignition_path"], "Root/Unit/TAG_A")
        self.assertEqual(by["TAG_A"]["ignition_folder"], "Root/Unit")
        self.assertEqual(by["Two Words"]["ignition_path"], "")
        self.assertIn("possible: Two_Words", by["Two Words"]["notes"])
        self.assertEqual(by["TAG_C"]["ignition_path"], "")

    def test_device_must_be_given_in_brackets(self):
        with self.assertRaises(SystemExit):
            self.run_s1([good_page()], device="Device A")

    def test_device_argument_required(self):
        pdf_path = os.path.join(TMP, "list.pdf")
        open(pdf_path, "wb").close()
        with self.assertRaises(SystemExit):
            s1.parse_args(["--input", pdf_path, "--vendor", "VEND", "--out", "x.csv"])


class Script2Tests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        os.makedirs(TMP)
        self.base = os.path.join(TMP, "base.json")
        self.sample = os.path.join(TMP, "sample.json")
        self.csv = os.path.join(TMP, "map.csv")
        self.out = os.path.join(TMP, "out.json")
        write_json(self.base, {"name": "Root", "tagType": "Folder", "tags": [
            {"name": "Unit", "tagType": "Folder", "tags": [
                {"name": "T_REAL", "tagType": "AtomicTag", "dataType": "Float4", "engUnit": "degF",
                 "tooltip": "A real", "valueSource": "memory"},
                {"name": "T_BIT", "tagType": "AtomicTag", "dataType": "Boolean",
                 "tooltip": "A bit", "valueSource": "memory", "value": False, "defaultValue": False},
                {"name": "T_CONFLICT", "tagType": "AtomicTag", "dataType": "Float4",
                 "tooltip": "Wrong type", "valueSource": "memory"},
                {"name": "T_UNTOUCHED", "tagType": "AtomicTag", "dataType": "Int4",
                 "tooltip": "Not in CSV", "valueSource": "memory"},
            ]}]})
        # Same shape as a real single-tag export after an OPC-browser drag.
        write_json(self.sample, {"dataType": "Float4", "name": "Arr_100_",
                                 "opcItemPath": "ns=1;s=[Some Device]Arr[100]",
                                 "opcServer": "Example OPC UA Server",
                                 "tagType": "AtomicTag", "valueSource": "opc"})
        rows = [
            {"device": "[Device A]", "tag_name": "T_REAL", "address": "ArrA[0]",
             "ignition_path": "Root/Unit/T_REAL", "ignition_data_type": "Float4"},
            {"device": "[Device A]", "tag_name": "T_BIT", "address": "Word[1].3",
             "ignition_path": "Root/Unit/T_BIT", "ignition_data_type": "Boolean"},
            {"device": "[Device A]", "tag_name": "T_CONFLICT", "address": "ArrB[2]",
             "ignition_path": "Root/Unit/T_CONFLICT", "ignition_data_type": "Int4"},
            {"device": "[Device A]", "tag_name": "NO_PATH", "address": "ArrA[5]",
             "ignition_path": "", "ignition_data_type": "Float4"},
            {"device": "[Device A]", "tag_name": "MISSING", "address": "ArrA[6]",
             "ignition_path": "Root/Unit/NOPE", "ignition_data_type": "Float4"},
        ]
        with open(self.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    def build(self, extra=None):
        args = ["--csv", self.csv, "--base", self.base, "--sample", self.sample, "--out", self.out]
        return s2.run(args + (extra or []))

    def tags(self):
        with open(self.out, encoding="utf-8") as f:
            data = json.load(f)
        return {t["name"]: t for t in data["tags"][0]["tags"]}

    def test_binding(self):
        with open(self.base, encoding="utf-8") as f:
            before = f.read()
        code = self.build()
        self.assertEqual(code, 2)  # conflict + no path + missing are reported
        t = self.tags()
        self.assertEqual(t["T_REAL"], {
            "name": "T_REAL", "tagType": "AtomicTag", "dataType": "Float4", "engUnit": "degF",
            "tooltip": "A real", "valueSource": "opc", "opcServer": "Example OPC UA Server",
            "opcItemPath": "ns=1;s=[Device A]ArrA[0]"})
        self.assertEqual(t["T_BIT"]["opcItemPath"], "ns=1;s=[Device A]Word[1].3")
        self.assertEqual(t["T_BIT"]["dataType"], "Boolean")
        self.assertEqual(t["T_CONFLICT"]["valueSource"], "memory")  # not bound
        self.assertNotIn("opcItemPath", t["T_CONFLICT"])
        self.assertEqual(t["T_UNTOUCHED"]["valueSource"], "memory")
        with open(self.base, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)  # input untouched
        rep = read_csv(os.path.join(TMP, "out - build report.csv"))
        status = {r["tag_name"]: (r["status"], r["detail"]) for r in rep}
        self.assertEqual(status["T_CONFLICT"][0], "NOT BUILT")
        self.assertIn("data type conflict", status["T_CONFLICT"][1])
        self.assertEqual(status["NO_PATH"][0], "NOT BUILT")
        self.assertEqual(status["MISSING"][0], "NOT BUILT")
        self.assertEqual(status["T_REAL"][0], "BOUND")

    def test_never_overwrites_inputs(self):
        with self.assertRaises(SystemExit):
            s2.run(["--csv", self.csv, "--base", self.base, "--sample", self.sample, "--out", self.base])

    def test_refuses_existing_output(self):
        self.build()
        with self.assertRaises(SystemExit):
            self.build()
        self.assertEqual(self.build(["--replace-output"]), 2)

    def test_duplicate_rows_for_one_path_not_built(self):
        with open(self.csv, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["[Device A]", "T_REAL", "ArrA[7]", "Root/Unit/T_REAL", "Float4"])
        self.build()
        self.assertEqual(self.tags()["T_REAL"]["valueSource"], "memory")

    def test_bad_sample_rejected(self):
        write_json(self.sample, {"name": "x", "tagType": "AtomicTag", "valueSource": "memory"})
        self.assertEqual(self.build(), 1)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
