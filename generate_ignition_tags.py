#!/usr/bin/env python3
"""
TASK_005 — Generate Ignition tag INSTANCES from AOI usages in an L5X.

TASK_004 generates the Ignition UDT *type definition* from an AOI. This
script is the level below it: it reads the AOI *instances* (the actual
controller tags whose DataType is that AOI) out of an L5X export and
emits one Ignition `UdtInstance` entry per instance, combined into a
single consolidated JSON file ready to import in Designer.

This is the first PLCHelper task that reads instance-level AOI usage
data. TASK_004 only ever parses type definitions.

JOB-AGNOSTIC (confirmed 2026-09-10): like TASK_004/009/010, nothing here
is specific to Blue Sky. Blue Sky is simply the first real input. Every
job-specific value — the device name, the destination folder, the UDT
path prefix, the qualifying AOI type list — is an explicit input with no
default, and the script refuses to run without it.

THE QUALIFYING AOI TYPE LIST IS EXPLICIT INPUT, NEVER INFERRED
(Doug-decided 2026-09-10): this script does not scan for "AOI types that
look like they have a UDT," and it does not decide on its own that a
type qualifies. Doug supplies the list with `--aoi-type`, once per type.
An AOI type present in the L5X but absent from that list is skipped
silently by design — that is the whole point of the list.

  DELIBERATELY NOT INVENTED: where that list eventually *lives* (a small
  per-job JSON file? a text file? something else?) is an open question in
  PLCHelper_Tasks.md TASK_005 that Doug has explicitly not answered yet,
  with the instruction "don't invent the format, ask." So this script
  takes the list as repeatable command-line arguments and invents no file
  format at all. When Doug decides on a home for it, a loader can be
  added in front of the same argument.

DEVICE NAME IS ONE VALUE FOR THE WHOLE RUN (Doug-decided 2026-09-10):
not per-instance. `--device-name` is required and is written verbatim
into every generated instance's `DeviceName` parameter.

DESCRIPTION IS LOOKED UP PER INSTANCE (Doug-confirmed 2026-09-10): read
from that specific AOI instance's own `<Description>` in the L5X — real
per-instance data, not the type-level description TASK_004 reads.

  A BLANK DESCRIPTION IS A REAL VALUE, NOT A MISSING FIELD. The
  `Description` parameter is always emitted when the AOI type's mapping
  calls for it, even when the looked-up text is empty. This is deliberate
  and was confirmed against the real reference export. Note the
  asymmetry that makes it necessary: Ignition's *exporter* omits a
  parameter whose value is blank (documented in TRUSTED_SOURCES.md), so a
  key missing from a real export does NOT mean the instance lacks that
  parameter — it can equally mean the parameter is present and blank.
  Reading "absent" as "not needed" would be exactly the wrong inference.

DESTINATION FOLDER IS ALWAYS ASKED, NEVER HARDCODED (Doug-decided
2026-09-10): `--dest-folder` is required. Doug's own value today is
`[default]O2InjectionSystem` — the folder the reference export came from
— but a different engineer may organize tags differently, so the script
has no default and will not guess one. See `--folder-mode` for how the
value is applied.

PER-AOI PARAMETER MAPPING: which top-level parameters an instance gets
depends on its AOI type, and there is no way to derive that from the L5X
— the parameters live on the Ignition UDT, not in the PLC. Doug supplied
the mapping directly (2026-09-10); it is recorded in AOI_PARAMETERS
below and in PLCHelper_Tasks.md TASK_005. Only ALARM_AOI has been
verified against a real Ignition export; every other type prints an
UNVERIFIED warning when used.

Written 2026-09-10 for PLCHelper (github.com/dougsparks38/plc-helper).
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Per-AOI parameter mapping — Doug's own words, 2026-09-10.
#
# `params`   : top-level Ignition parameters the instance carries.
# `udt_name` : the Ignition UDT's name where it differs from the PLC AOI
#              type name. TASK_004 already documents that these legitimately
#              disagree (a UDT named CONSPD2_AOI corresponds to PLC type
#              CONSPD4_AOI) and that the mapping is never inferred by name.
# `verified` : whether this row has been checked against a real Ignition
#              tag-instance export. Only ALARM_AOI has.
#
# Parameter spec entries are (name, dataType, default_value_or_None).
# A default of None means "look the value up per instance" (Description) or
# "supplied for the whole run" (DeviceName). A literal means that literal
# is written for every instance.
# ---------------------------------------------------------------------------

DEVICE_NAME = ("DeviceName", "String", None)      # one value for the whole run
DESCRIPTION = ("Description", "String", None)     # looked up per instance
ENG_UNIT = ("EngUnit", "String", "")              # created, deliberately blank
ANALOG_VLV = ("Analog_Vlv", "Integer", 0)         # MODVLV only

AOI_PARAMETERS = {
    "ALARM_AOI": {
        "udt_name": "ALARM_AOI",
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": True,
    },
    "CONSPD4_AOI": {
        "udt_name": "CONSPD2_AOI",   # UDT name differs from the PLC AOI name
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
    },
    "FLOWIN3_AOI": {
        "udt_name": "FLOWIN3_AOI",
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
    },
    "FLOWVLV_AOI": {
        "udt_name": "FLOWVLV2_AOI",  # UDT name differs from the PLC AOI name
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
    },
    "INTERLOCK_AOI": {
        # Doug: "many other parameters with default values expected to read in
        # correctly with no special handling, plus the same DeviceName /
        # Description pair." Those defaulted parameters live on the UDT
        # definition and are inherited by the instance, so nothing is emitted
        # for them here. Flagged as the natural next test candidate.
        "udt_name": "INTERLOCK_AOI",
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
    },
    "LEVELIN3_AOI": {
        "udt_name": "LEVELIN3_AOI",
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
    },
    "MODVLV": {
        "udt_name": "MODVLV",
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT, ANALOG_VLV],
        "verified": False,
    },
    "VARSPD2_AOI": {
        "udt_name": "VARSPD_AOI",    # UDT name differs from the PLC AOI name
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
    },
}


# ---------------------------------------------------------------------------
# L5X parsing
# ---------------------------------------------------------------------------

def load_l5x(path):
    if not os.path.isfile(path):
        sys.exit("ERROR: L5X not found: %s" % path)
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        sys.exit("ERROR: could not parse L5X as XML: %s" % exc)


def read_description(element):
    """Return an element's <Description> text, flattened and stripped.

    L5X descriptions are CDATA and routinely carry leading/trailing
    newlines from the exporter's own formatting; those are not part of the
    engineer's text. itertext() is used rather than .text because a
    description can contain nested localized-text elements.

    Returns "" when there is no description element or it is empty. That
    empty string is a real value here, not a failure — see the module
    docstring.
    """
    desc = element.find("Description")
    if desc is None:
        return ""
    return " ".join("".join(desc.itertext()).split())


def aoi_definition_parameters(root, aoi_type):
    """Return the AOI's parameter names, in L5X document order.

    Document order is the order the engineer sees in Studio 5000 — the same
    choice TASK_004 makes. Ignition matches UDT members by name on import,
    so member order in the file is presentation only.
    """
    for aoi in root.iter("AddOnInstructionDefinition"):
        if aoi.get("Name") != aoi_type:
            continue
        params = aoi.find("Parameters")
        if params is None:
            return []
        return [p.get("Name") for p in params.findall("Parameter")]
    return None


def find_instances(root, aoi_type):
    """Every tag in the L5X whose DataType is this AOI type.

    Both controller-scope and program-scope tags are collected; an AOI
    instance is a normal tag whose data type happens to be the AOI. The
    scope is recorded so the report can show it, and so a program-scoped
    instance cannot be silently confused with a controller-scoped one of
    the same name.
    """
    found = []

    for controller in root.iter("Controller"):
        tags = controller.find("Tags")
        if tags is None:
            continue
        for tag in tags.findall("Tag"):
            if tag.get("DataType") == aoi_type:
                found.append(("Controller", tag))

    for program in root.iter("Program"):
        tags = program.find("Tags")
        if tags is None:
            continue
        for tag in tags.findall("Tag"):
            if tag.get("DataType") == aoi_type:
                found.append((program.get("Name") or "<unnamed program>", tag))

    return found


# ---------------------------------------------------------------------------
# Instance construction
# ---------------------------------------------------------------------------

def build_parameters(spec, device_name, description):
    out = {}
    for name, data_type, default in spec:
        if name == "DeviceName":
            value = device_name
        elif name == "Description":
            value = description
        else:
            value = default
        out[name] = {"dataType": data_type, "value": value}
    return out


def build_instance(tag_name, description, member_names, type_id,
                   param_spec, device_name):
    """One Ignition UdtInstance entry.

    Shape is taken verbatim from the real reference export
    (`BlueSky/ALARM_AOI example tags.json`), not from generic docs:
    `name`, `parameters`, `tagType: "UdtInstance"`, a `tags` array of
    minimal `AtomicTag` members, and `typeId`.

    Members carry only `name` and `tagType`. Everything else — data type,
    OPC item path, OPC server, permissions — is inherited from the UDT
    definition TASK_004 generated, which is why the reference's members
    carry nothing else either. Emitting a data type or an OPC path here
    would create a second, competing source for values the definition
    already owns; that is exactly the class of drift TASK_004 exists to
    prevent.
    """
    return {
        "name": tag_name,
        "parameters": build_parameters(param_spec, device_name, description),
        "tagType": "UdtInstance",
        "tags": [{"name": m, "tagType": "AtomicTag"} for m in member_names],
        "typeId": type_id,
    }


def parse_aoi_type_arg(value):
    """`--aoi-type NAME` or `--aoi-type NAME=UDT_NAME`.

    The optional `=UDT_NAME` overrides the mapping table for one run,
    because a UDT's name legitimately differs from its PLC AOI type name
    and the correct pairing is never inferred (TASK_004's standing note).
    """
    if "=" in value:
        aoi, udt = value.split("=", 1)
        return aoi.strip(), udt.strip()
    return value.strip(), None


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="TASK_005 - generate Ignition tag instances from the AOI "
                    "usages in an L5X export.")
    parser.add_argument("--l5x", required=True,
                        help="Path to the L5X export (lives in the job's own "
                             "folder; never copied into PLCHelper)")
    parser.add_argument("--aoi-type", action="append", required=True,
                        metavar="NAME[=UDT_NAME]",
                        help="A qualifying AOI type. Repeat once per type. "
                             "Explicit input - never inferred.")
    parser.add_argument("--device-name", required=True,
                        help="DeviceName parameter value. One value for the "
                             "whole run.")
    parser.add_argument("--dest-folder", required=True,
                        help="Destination folder for the generated tags, e.g. "
                             "'[default]O2InjectionSystem'. Always explicit; "
                             "the script has no default.")
    parser.add_argument("--udt-path-prefix", required=True,
                        help="Folder path of the UDT definitions inside the "
                             "provider, e.g. 'BlueSky/AOI'. Combined with the "
                             "UDT name to form typeId.")
    parser.add_argument("--output", required=True,
                        help="Path for the consolidated JSON. Write this into "
                             "the job's own folder, never into PLCHelper.")
    parser.add_argument("--folder-mode", choices=("wrap", "flat"),
                        default="flat",
                        help="'flat' (default): emit {\"tags\": [...]} and "
                             "select the destination folder in the Tag Browser "
                             "at import time. 'wrap': nest the instances "
                             "inside an explicit Folder entry named after "
                             "--dest-folder.")
    parser.add_argument("--list-aoi-types", action="store_true",
                        help="List every AOI type in the L5X with an instance "
                             "count, then exit. Use this to see what is "
                             "available before choosing the qualifying list.")
    args = parser.parse_args()

    root = load_l5x(args.l5x)

    # ---- discovery aid -----------------------------------------------------
    if args.list_aoi_types:
        counts = {}
        for aoi in root.iter("AddOnInstructionDefinition"):
            counts.setdefault(aoi.get("Name"), 0)
        for controller in root.iter("Controller"):
            tags = controller.find("Tags")
            if tags is None:
                continue
            for tag in tags.findall("Tag"):
                dt = tag.get("DataType")
                if dt in counts:
                    counts[dt] += 1
        print("AOI types defined in %s:" % os.path.basename(args.l5x))
        for name in sorted(counts):
            mapped = "mapped" if name in AOI_PARAMETERS else "NOT in mapping"
            print("  %-20s %3d controller instances   (%s)"
                  % (name, counts[name], mapped))
        print("\nThis is a discovery aid only. Which of these qualify is "
              "Doug's explicit decision, not this script's.")
        return 0

    dest_folder = args.dest_folder.strip()
    prefix = args.udt_path_prefix.strip().strip("/")

    print("=" * 72)
    print("TASK_005 - Ignition tag instance generation")
    print("=" * 72)
    print("L5X            : %s" % args.l5x)
    print("DeviceName     : %s   (one value for the whole run)" % args.device_name)
    print("Destination    : %s   (explicit input - never hardcoded)" % dest_folder)
    print("UDT path prefix: %s" % prefix)
    print("Folder mode    : %s" % args.folder_mode)
    print()

    all_instances = []
    warnings = []
    blank_descriptions = []

    for raw in args.aoi_type:
        aoi_type, udt_override = parse_aoi_type_arg(raw)

        mapping = AOI_PARAMETERS.get(aoi_type)
        if mapping is None:
            warnings.append(
                "AOI type '%s' has no entry in AOI_PARAMETERS. Its parameter "
                "set is unknown and nothing was generated for it. Add it to "
                "the mapping table (and to PLCHelper_Tasks.md TASK_005) "
                "before using it." % aoi_type)
            continue

        if not mapping["verified"]:
            warnings.append(
                "AOI type '%s' parameter mapping is UNVERIFIED - it records "
                "Doug's stated intent but has never been checked against a "
                "real Ignition tag-instance export. Verify one instance by "
                "hand before importing in bulk." % aoi_type)

        udt_name = udt_override or mapping["udt_name"]
        if udt_override:
            print("NOTE: --aoi-type override in effect: %s -> UDT '%s'"
                  % (aoi_type, udt_name))
        elif udt_name != aoi_type:
            print("NOTE: UDT name differs from the PLC AOI type by design: "
                  "%s -> %s" % (aoi_type, udt_name))

        member_names = aoi_definition_parameters(root, aoi_type)
        if member_names is None:
            warnings.append(
                "AOI type '%s' has no AddOnInstructionDefinition in this L5X. "
                "Nothing generated for it." % aoi_type)
            continue
        if not member_names:
            warnings.append(
                "AOI type '%s' has a definition but no parameters. Nothing "
                "generated for it." % aoi_type)
            continue

        instances = find_instances(root, aoi_type)
        if not instances:
            warnings.append(
                "AOI type '%s' is defined in this L5X but has no instances. "
                "Nothing generated for it." % aoi_type)
            continue

        type_id = "%s/%s" % (prefix, udt_name) if prefix else udt_name

        print("-" * 72)
        print("%s  ->  typeId '%s'" % (aoi_type, type_id))
        print("  %d parameters (become UDT members), %d instances found"
              % (len(member_names), len(instances)))
        print()

        seen = {}
        for scope, tag in instances:
            tag_name = tag.get("Name")
            description = read_description(tag)

            if tag_name in seen:
                warnings.append(
                    "Duplicate instance name '%s' (scopes: %s and %s). Ignition "
                    "tag names must be unique within a folder - resolve this "
                    "before importing."
                    % (tag_name, seen[tag_name], scope))
            seen[tag_name] = scope

            if tag.get("Dimensions"):
                warnings.append(
                    "Instance '%s' is an ARRAY (Dimensions='%s'). Arrays of "
                    "AOI instances are not handled - this entry describes the "
                    "array tag itself, which is almost certainly not what you "
                    "want. Review before importing."
                    % (tag_name, tag.get("Dimensions")))

            if not description:
                blank_descriptions.append(tag_name)

            all_instances.append(build_instance(
                tag_name=tag_name,
                description=description,
                member_names=member_names,
                type_id=type_id,
                param_spec=mapping["params"],
                device_name=args.device_name,
            ))

            print("  %-34s %s" % (tag_name, description or "(blank description)"))
        print()

    if not all_instances:
        print("Nothing generated. See warnings below.")
        for w in warnings:
            print("  WARNING: %s" % w)
        return 1

    # ---- consolidated output ----------------------------------------------
    # One file for everything in scope, not a file per instance and not a
    # file per AOI type (Doug-confirmed 2026-09-10).
    if args.folder_mode == "wrap":
        folder_name = dest_folder.split("]")[-1].strip("/")
        payload = {"tags": [{"name": folder_name,
                             "tagType": "Folder",
                             "tags": all_instances}]}
    else:
        payload = {"tags": all_instances}

    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.isdir(out_dir):
        sys.exit("ERROR: output directory does not exist: %s" % out_dir)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print("=" * 72)
    print("Wrote %d tag instance(s) to %s" % (len(all_instances), args.output))
    print("=" * 72)

    if blank_descriptions:
        print()
        print("%d instance(s) have a BLANK description in the L5X:"
              % len(blank_descriptions))
        for name in blank_descriptions:
            print("  %s" % name)
        print("A blank description is a valid value, not an error - the "
              "Description parameter is still created for these. Listed only "
              "so it is a visible fact rather than a silent one.")

    if warnings:
        print()
        print("WARNINGS (%d):" % len(warnings))
        for w in warnings:
            print("  - %s" % w)

    print()
    print("BEFORE IMPORTING - import the UDT definitions FIRST.")
    print("  Ignition's own docs: \"it is recommended to import UDT "
          "definitions before importing any instances.\" An instance whose")
    print("  typeId names a definition that is not there yet will not bind.")
    if args.folder_mode == "flat":
        print("  Select '%s' in the Tag Browser before importing - with "
              "--folder-mode flat the" % dest_folder)
        print("  destination comes from your Tag Browser selection, not from "
              "this file.")
    print("  Use the Tag Browser's More Options (hamburger) menu -> Import "
          "Tags, not the right-click menu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
