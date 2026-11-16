#!/usr/bin/env python3
"""
audit_ignition_orphan_tags.py -- TASK_006: find Ignition tags that have no
matching tag in the current PLC program.

The reverse of TASK_005 (generate_ignition_tags.py). TASK_005 goes PLC ->
Ignition and creates what is missing; this goes Ignition -> PLC and lists
what is there but should not be. Doug's framing: "if they're there, they
should be in my program. If they're not in my program, then I need to know
why they're there."

READ ONLY. Never deletes, edits or moves anything. Both inputs are only
read; the one output is a new report CSV, and the script refuses to write
over an input.

Inputs:
  --json   an Ignition tag export (Tag Browser > More Options > Export),
           any folder depth.
  --l5x    a fresh full-program L5X export of the PLC the tags read from.
  --map    PLC_TYPE=IGNITION_UDT (repeatable, optional). The PLC AOI/UDT
           type that an Ignition UDT name stands for, where the two names
           differ (for example CONSPD4_AOI=CONSPD2_AOI). Never inferred: a
           UDT name with no --map entry is taken to mean the PLC type of
           the same name, and nothing else. Same rule as TASK_005.
  --output the report CSV to write.

What is checked, per Ignition tag (tag level only):
  * UdtInstance -- the instance name is the PLC tag name (the UDT's OPC
    path template is [{DeviceName}]{InstanceName}.<member>, TASK_004).
      ORPHAN  no controller-scope tag of that name in the L5X.
      REVIEW  a tag of that name exists, but its PLC type is not the type
              the instance's Ignition UDT stands for (type changed in the
              PLC, or a --map pair not given); or the name exists only as
              a program-scope tag (needs a Program: path to bind).
  * AtomicTag with an OPC item path -- the base tag (and, for an AOI/UDT
    base tag, its first member) is looked up in the L5X.
      ORPHAN  base tag not in the L5X, or the member is not a parameter /
              member of the base tag's type.
      REVIEW  the path cannot be read as ns=..;s=[Device]Tag..., or it is
              parameter-bound, or it uses a Program: scope that is missing.
  * AtomicTag with no OPC binding (memory, expression, ...) -- REVIEW: not
    PLC-bound, so there is nothing to compare.
  * Folders are walked, not reported.

Deliberately NOT checked: UDT instance members against AOI parameters.
Comparing an existing UDT's members to the AOI is the Hard scope boundary
in PLCHelper_Status.md (never flag members on an existing UDT); this tool
works at tag level only.

Report columns: status, ignition_path, ignition_type, reason. ORPHAN rows
first, then REVIEW rows (the ambiguous cases for Doug's decision). Matched
tags are not listed; their count is printed.

Exit code: 0 = nothing flagged, 1 = bad input, 2 = finished with flags.

Written 2026-11-16 for PLCHelper (github.com/dougsparks38/plc-helper).
"""

import argparse
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

REPORT_COLUMNS = ["status", "ignition_path", "ignition_type", "reason"]
OPC_PATH_RE = re.compile(r"^ns=\d+;s=\[(?P<device>[^\]]*)\](?P<path>.+)$")


# ---------------------------------------------------------------------------
# L5X
# ---------------------------------------------------------------------------

def load_l5x(path):
    if not os.path.isfile(path):
        sys.exit("ERROR: L5X not found: %s" % path)
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        sys.exit("ERROR: could not parse L5X as XML: %s" % exc)


def index_l5x(root):
    """Return (controller_tags, program_tags, type_members).

    controller_tags: {name: data_type}
    program_tags:    {(program, name): data_type}
    type_members:    {type_name: set(member/parameter names)} for every AOI
                     and every Class="User" DataType (visible members).
    """
    controller_tags = {}
    controller = root.find("Controller")
    if controller is not None and controller.find("Tags") is not None:
        for tag in controller.find("Tags").findall("Tag"):
            controller_tags[tag.get("Name")] = tag.get("DataType")

    program_tags = {}
    for program in root.iter("Program"):
        tags = program.find("Tags")
        if tags is None:
            continue
        for tag in tags.findall("Tag"):
            program_tags[(program.get("Name"), tag.get("Name"))] = tag.get("DataType")

    type_members = {}
    for aoi in root.iter("AddOnInstructionDefinition"):
        params = aoi.find("Parameters")
        names = set()
        if params is not None:
            names = {p.get("Name") for p in params.findall("Parameter")}
        type_members[aoi.get("Name")] = names
    for dt in root.iter("DataType"):
        if dt.get("Class") != "User":
            continue
        members = dt.find("Members")
        names = set()
        if members is not None:
            names = {m.get("Name") for m in members.findall("Member")
                     if m.get("Hidden") != "true"}
        type_members[dt.get("Name")] = names
    return controller_tags, program_tags, type_members


# ---------------------------------------------------------------------------
# Ignition export
# ---------------------------------------------------------------------------

def load_json(path):
    if not os.path.isfile(path):
        sys.exit("ERROR: Ignition export not found: %s" % path)
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        sys.exit("ERROR: could not read the Ignition export as JSON: %s" % exc)


def walk_tags(node, parent_path):
    """Yield (full_path, tag_dict) for every non-folder tag, depth first.

    UDT instance members are not yielded as tags of their own; a member that
    carries its own OPC path override is yielded with the instance path as
    its parent, so a member-level override is still checked.
    """
    for child in node.get("tags") or []:
        name = child.get("name", "")
        path = "%s/%s" % (parent_path, name) if parent_path else name
        tag_type = child.get("tagType")
        if tag_type in ("Folder", "Provider"):
            for item in walk_tags(child, path):
                yield item
        elif tag_type == "UdtInstance":
            yield path, child
            for member in child.get("tags") or []:
                if "opcItemPath" in member:
                    yield "%s/%s" % (path, member.get("name", "")), member
        else:
            yield path, child


def roots_of(data):
    """The export may be one folder object, a {"tags": [...]} wrapper, or a
    bare list. Return a node whose "tags" are the top-level entries and the
    path prefix to use for them."""
    if isinstance(data, list):
        return {"tags": data}, ""
    if isinstance(data, dict) and data.get("tagType") in ("Folder", "Provider"):
        return {"tags": [data]}, ""
    if isinstance(data, dict) and "tags" in data:
        return data, ""
    if isinstance(data, dict) and data.get("tagType"):
        return {"tags": [data]}, ""
    sys.exit("ERROR: the Ignition export has no recognisable tag structure.")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def similar_names(name, controller_tags):
    """Controller tags sharing the name up to its last underscore. Listed as
    a hint in the reason only; never treated as a match."""
    if "_" not in name:
        return []
    stem = name.rsplit("_", 1)[0] + "_"
    return sorted(n for n in controller_tags if n.startswith(stem) and n != name)


def check_udt_instance(path, tag, plc, udt_to_plc):
    controller_tags, program_tags, _members = plc
    name = tag.get("name", "")
    type_id = tag.get("typeId") or ""
    udt_name = type_id.rsplit("/", 1)[-1]
    expected_plc_type = udt_to_plc.get(udt_name, udt_name)
    plc_type = controller_tags.get(name)

    if plc_type is None:
        in_programs = sorted(p for (p, n) in program_tags if n == name)
        if in_programs:
            return ("REVIEW",
                    "No controller-scope tag '%s'; a program-scope tag of that "
                    "name exists in program(s) %s. A {InstanceName} OPC path "
                    "reads controller scope only." % (name, ", ".join(in_programs)))
        reason = "No tag named '%s' in the PLC program." % name
        hints = similar_names(name, controller_tags)
        if hints:
            reason += " PLC tags with the same name stem: %s." % ", ".join(hints)
        return ("ORPHAN", reason)

    if plc_type != expected_plc_type:
        mapped = ("(via --map)" if udt_name in udt_to_plc
                  else "(same name; no --map entry)")
        return ("REVIEW",
                "PLC tag '%s' exists but is type %s; Ignition UDT '%s' stands "
                "for PLC type %s %s." % (name, plc_type, udt_name,
                                         expected_plc_type, mapped))
    return None


def check_opc_tag(path, tag, plc):
    controller_tags, program_tags, type_members = plc
    item_path = tag.get("opcItemPath")
    if isinstance(item_path, dict):
        return ("REVIEW", "OPC item path is parameter-bound (%s); it cannot be "
                "checked against the PLC on its own."
                % item_path.get("binding", item_path))
    match = OPC_PATH_RE.match(str(item_path).strip())
    if not match:
        return ("REVIEW", "OPC item path '%s' is not in the form "
                "ns=..;s=[Device]Tag; not checked." % item_path)
    plc_path = match.group("path")

    program = None
    if plc_path.startswith("Program:"):
        rest = plc_path[len("Program:"):]
        if "." not in rest:
            return ("REVIEW", "OPC item path '%s' names a program but no tag."
                    % item_path)
        program, plc_path = rest.split(".", 1)

    parts = re.split(r"\.", plc_path)
    base = re.sub(r"\[.*$", "", parts[0])
    if program is None:
        base_type = controller_tags.get(base)
    else:
        base_type = program_tags.get((program, base))
    if base_type is None:
        where = "controller scope" if program is None else "program '%s'" % program
        reason = "OPC item path '%s': no tag '%s' in %s of the PLC program." % (
            item_path, base, where)
        hints = similar_names(base, controller_tags) if program is None else []
        if hints:
            reason += " PLC tags with the same name stem: %s." % ", ".join(hints)
        return ("ORPHAN", reason)

    if len(parts) > 1 and base_type in type_members:
        member = re.sub(r"\[.*$", "", parts[1])
        if member not in type_members[base_type]:
            return ("ORPHAN", "OPC item path '%s': tag '%s' exists (type %s) "
                    "but that type has no member/parameter '%s'."
                    % (item_path, base, base_type, member))
    return None


def audit(data, plc, udt_to_plc):
    rows = []
    matched = 0
    node, prefix = roots_of(data)
    for path, tag in walk_tags(node, prefix):
        tag_type = tag.get("tagType")
        if tag_type == "UdtInstance":
            ign_type = tag.get("typeId") or "(no typeId)"
            result = check_udt_instance(path, tag, plc, udt_to_plc)
        elif "opcItemPath" in tag:
            ign_type = "%s %s" % (tag_type or "AtomicTag", tag.get("dataType", ""))
            result = check_opc_tag(path, tag, plc)
        else:
            ign_type = "%s %s" % (tag_type or "(no tagType)", tag.get("dataType", ""))
            result = ("REVIEW", "Not bound to the PLC (valueSource '%s'); "
                      "nothing to compare." % tag.get("valueSource", "(not set)"))
        if result is None:
            matched += 1
        else:
            rows.append({"status": result[0], "ignition_path": path,
                         "ignition_type": ign_type.strip(), "reason": result[1]})
    order = {"ORPHAN": 0, "REVIEW": 1}
    rows.sort(key=lambda r: (order[r["status"]], r["ignition_path"].lower()))
    return rows, matched


# ---------------------------------------------------------------------------

def parse_maps(values):
    udt_to_plc = {}
    for value in values or []:
        if "=" not in value:
            sys.exit("ERROR: --map needs PLC_TYPE=IGNITION_UDT, got '%s'." % value)
        plc_type, udt = (s.strip() for s in value.split("=", 1))
        if not plc_type or not udt:
            sys.exit("ERROR: --map needs PLC_TYPE=IGNITION_UDT, got '%s'." % value)
        if udt in udt_to_plc and udt_to_plc[udt] != plc_type:
            sys.exit("ERROR: Ignition UDT '%s' is mapped to two PLC types (%s, "
                     "%s); give one." % (udt, udt_to_plc[udt], plc_type))
        udt_to_plc[udt] = plc_type
    return udt_to_plc


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="TASK_006 - list Ignition tags with no matching tag in the "
                    "current PLC program. Read only.")
    parser.add_argument("--json", required=True, help="Ignition tag export")
    parser.add_argument("--l5x", required=True, help="Fresh L5X export")
    parser.add_argument("--map", action="append", metavar="PLC_TYPE=IGNITION_UDT",
                        help="PLC type an Ignition UDT name stands for, where the "
                             "names differ. Repeatable. Never inferred.")
    parser.add_argument("--output", required=True, help="Report CSV to write")
    args = parser.parse_args(argv)

    out = os.path.abspath(args.output)
    if out in (os.path.abspath(args.json), os.path.abspath(args.l5x)):
        sys.exit("ERROR: --output must not be one of the inputs.")
    if not os.path.isdir(os.path.dirname(out)):
        sys.exit("ERROR: output folder does not exist: %s" % os.path.dirname(out))

    udt_to_plc = parse_maps(args.map)
    plc = index_l5x(load_l5x(args.l5x))
    rows, matched = audit(load_json(args.json), plc, udt_to_plc)

    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    orphans = sum(1 for r in rows if r["status"] == "ORPHAN")
    review = len(rows) - orphans
    print("TASK_006 orphan audit")
    print("  Ignition export : %s" % args.json)
    print("  L5X             : %s" % args.l5x)
    for udt, plc_type in sorted(udt_to_plc.items()):
        print("  map             : Ignition %s -> PLC %s" % (udt, plc_type))
    print("  matched         : %d" % matched)
    print("  ORPHAN          : %d" % orphans)
    print("  REVIEW          : %d" % review)
    print("  report          : %s" % out)
    for r in rows:
        print("  %-6s %-40s %s" % (r["status"], r["ignition_path"], r["ignition_type"]))
    print("Nothing was changed. Every flagged tag is Doug's decision.")
    return 2 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
