#!/usr/bin/env python3
"""
Tests for match_plc_tags_to_ignition_json.py. All fixtures are synthetic and
built in code; no real tag list or Ignition export is read.

Run:  python test_match_plc_tags.py
Scratch files go to ./_test_tmp_match/ (git-ignored).
"""

import csv
import json
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import match_plc_tags_to_ignition_json as m  # noqa: E402
import csv_to_ignition_opc_tags as s2  # noqa: E402

TMP = os.path.join(HERE, "_test_tmp_match")


def atom(name, dtype="Float4", **kw):
    t = {"name": name, "tagType": "AtomicTag", "dataType": dtype, "valueSource": "memory"}
    t.update(kw)
    return t


EXPORT = {"name": "Root", "tagType": "Folder", "tags": [
    {"name": "Area", "tagType": "Folder", "tags": [
        {"name": "LineA", "tagType": "Folder", "tags": [atom("AA01"), atom("AA02")]},
        {"name": "OldCopies", "tagType": "Folder", "tags": [
            atom("AA01", value=1.0, defaultValue=1.0), atom("AA02")]},
        {"name": "Unit1", "tagType": "Folder", "tags": [
            atom("BB10", tooltip="Unit 1 value"), atom("CC10", "Int4"), atom("DD10")]},
        {"name": "Unit2", "tagType": "Folder", "tags": [atom("DD10")]},
        {"name": "Empty", "tagType": "Folder"},
    ]}]}

ROWS = [
    ("TAG", "PX_AA01", "Line A value one"),
    ("TAG", "PX_AA02", "Line A value two"),
    ("TAG", "PX_BB10", "Unit 1 value"),
    ("TAG", "PX_CC10", "Wrong type"),
    ("TAG", "PX_DD10", "In two units"),
    ("TAG", "PX_ZZ99", "Not in export"),
    ("TAG", "OTHER_BB10", "No prefix"),
    ("TAG", "PX_Heartbeat", "Skip me"),
]


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["TYPE", "NAME", "DESCRIPTION"])
        w.writerows(rows)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def statuses(path, drop_notes=True):
    return [r["status"] for r in read_csv(path) if not (drop_notes and r["status"] == "NOTE")]


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class MatchTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        os.makedirs(TMP, exist_ok=True)  # OneDrive can hold the folder briefly
        for f in os.listdir(TMP):
            os.remove(os.path.join(TMP, f))
        self.json = os.path.join(TMP, "export.json")
        self.inp = os.path.join(TMP, "list.csv")
        self.out = os.path.join(TMP, "map.csv")
        self.rep = os.path.join(TMP, "map - review report.csv")
        write_json(self.json, EXPORT)
        write_csv(self.inp, ROWS)

    def args(self, extra=None, inp=None):
        return ["--input", inp or self.inp, "--json", self.json, "--strip-prefix", "PX_",
                "--device", "Dev 1", "--skip-name", "PX_Heartbeat",
                "--exclude-folder", "Root/Area/OldCopies", "--expect-data-type", "Float4",
                "--out", self.out] + (extra or [])

    def test_matching_and_report(self):
        before = read_text(self.json)
        code = m.run(self.args())
        self.assertEqual(code, 2)  # type mismatch, duplicate, not found, no prefix
        rows = read_csv(self.out)
        self.assertEqual(list(rows[0])[:5], ["device", "address", "ignition_path",
                                             "ignition_data_type", "tag_name"])
        by = {r["tag_name"]: r for r in rows}
        self.assertEqual(sorted(by), ["PX_AA01", "PX_AA02", "PX_BB10"])
        self.assertEqual(by["PX_AA01"]["ignition_path"], "Root/Area/LineA/AA01")
        self.assertEqual(by["PX_AA01"]["device"], "[Dev 1]")
        self.assertEqual(by["PX_AA01"]["address"], "PX_AA01")
        self.assertEqual(by["PX_AA01"]["ignition_data_type"], "Float4")
        self.assertEqual(by["PX_BB10"]["description"], "Unit 1 value")
        rep = read_csv(self.rep)
        st = {}
        for r in rep:
            st.setdefault(r["tag_name"], []).append(r)
        self.assertEqual([r["status"] for r in st["PX_Heartbeat"]], ["SKIPPED"])
        left = [r for r in rep if r["status"] == "LEFT ALONE"]
        self.assertEqual(sorted(r["ignition_path"] for r in left),
                         ["Root/Area/OldCopies/AA01", "Root/Area/OldCopies/AA02"])
        self.assertEqual(st["PX_CC10"][0]["status"], "TYPE MISMATCH")
        self.assertEqual(st["PX_DD10"][0]["status"], "DUPLICATE")
        self.assertIn("Root/Area/Unit1/DD10", st["PX_DD10"][0]["ignition_path"])
        self.assertIn("Root/Area/Unit2/DD10", st["PX_DD10"][0]["ignition_path"])
        self.assertEqual(st["PX_ZZ99"][0]["status"], "NOT FOUND")
        self.assertEqual(st["OTHER_BB10"][0]["status"], "NO PREFIX")
        self.assertEqual(read_text(self.json), before)  # input untouched

    def test_clean_run_exit_0(self):
        write_csv(self.inp, [ROWS[0], ROWS[1], ROWS[2], ROWS[7]])
        self.assertEqual(m.run(self.args()), 0)
        self.assertEqual(len(read_csv(self.out)), 3)

    def test_without_exclude_the_copies_are_duplicates(self):
        write_csv(self.inp, [ROWS[0]])
        a = [x for x in self.args() if x not in ("--exclude-folder", "Root/Area/OldCopies")]
        self.assertEqual(m.run(a), 2)
        self.assertEqual(read_csv(self.out), [])
        self.assertEqual(statuses(self.rep), ["DUPLICATE"])

    def test_exclude_folder_typo_stops(self):
        a = self.args()
        a[a.index("Root/Area/OldCopies")] = "Root/Area/OldCopy"
        self.assertEqual(m.run(a), 1)
        self.assertFalse(os.path.exists(self.out))

    def test_only_excluded_copy_is_not_found(self):
        exp = json.loads(json.dumps(EXPORT))
        exp["tags"][0]["tags"][1]["tags"].append(atom("EE01"))
        write_json(self.json, exp)
        write_csv(self.inp, [("TAG", "PX_EE01", "only in old folder")])
        self.assertEqual(m.run(self.args()), 2)
        self.assertEqual(sorted(statuses(self.rep)), ["LEFT ALONE", "NOT FOUND"])

    def test_case_sensitive(self):
        write_csv(self.inp, [("TAG", "PX_aa01", "lower case")])
        self.assertEqual(m.run(self.args()), 2)
        self.assertEqual(statuses(self.rep), ["NOT FOUND"])

    def test_duplicate_input_rows(self):
        write_csv(self.inp, [ROWS[0], ROWS[0]])
        self.assertEqual(m.run(self.args()), 2)
        self.assertEqual(statuses(self.rep), ["DUPLICATE INPUT", "DUPLICATE INPUT"])

    def test_unused_skip_is_note_only(self):
        write_csv(self.inp, [ROWS[2]])
        self.assertEqual(m.run(self.args()), 0)
        self.assertEqual(statuses(self.rep, drop_notes=False), ["NOTE"])

    def test_excel_input(self):
        import openpyxl
        x = os.path.join(TMP, "list.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["TYPE", "NAME", "DESCRIPTION"])
        ws.append(list(ROWS[0]))
        ws.append([None, None, None])
        ws.append(list(ROWS[2]))
        wb.save(x)
        self.assertEqual(m.run(self.args(inp=x)), 0)
        rows = read_csv(self.out)
        self.assertEqual([r["source_row"] for r in rows], ["2", "4"])

    def test_refuses_existing_output_and_inputs(self):
        m.run(self.args())
        with self.assertRaises(SystemExit):
            m.run(self.args())
        self.assertEqual(m.run(self.args(["--replace-output"])), 2)
        a = self.args()
        a[a.index(self.out)] = self.inp
        with self.assertRaises(SystemExit):
            m.run(a)

    def test_device_with_brackets_rejected(self):
        a = self.args()
        a[a.index("Dev 1")] = "[Dev 1]"
        with self.assertRaises(SystemExit):
            m.run(a)

    def test_required_arguments(self):
        with self.assertRaises(SystemExit):
            m.parse_args(["--input", self.inp, "--json", self.json, "--out", self.out])

    def test_tag_map_binds_with_script2(self):
        """The tag map is accepted by csv_to_ignition_opc_tags.py as is."""
        write_csv(self.inp, [ROWS[0], ROWS[1], ROWS[2]])
        self.assertEqual(m.run(self.args()), 0)
        sample = os.path.join(TMP, "sample.json")
        write_json(sample, {"dataType": "Float4", "name": "X", "tagType": "AtomicTag",
                            "valueSource": "opc", "opcServer": "Example OPC UA Server",
                            "opcItemPath": "ns=1;s=[Other Dev]Arr[3]"})
        bound = os.path.join(TMP, "bound.json")
        self.assertEqual(s2.run(["--csv", self.out, "--base", self.json, "--sample", sample,
                                 "--out", bound]), 0)
        with open(bound, encoding="utf-8") as f:
            area = json.load(f)["tags"][0]["tags"]
        line_a = {t["name"]: t for t in area[0]["tags"]}
        old = {t["name"]: t for t in area[1]["tags"]}
        self.assertEqual(line_a["AA01"]["opcItemPath"], "ns=1;s=[Dev 1]PX_AA01")
        self.assertEqual(old["AA01"]["valueSource"], "memory")  # left alone
        self.assertNotIn("opcItemPath", old["AA01"])


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
