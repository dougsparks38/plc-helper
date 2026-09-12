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

THE PLC AOI TYPE NAME AND THE IGNITION UDT NAME ARE TWO DIFFERENT THINGS
(Doug-confirmed 2026-09-10, general convention going forward): a PLC-side
AOI type name carries a version number that changes as the AOI is revised
(`CONSPD2_AOI` -> `CONSPD4_AOI`), but the Ignition UDT it maps to keeps a
fixed name deliberately, so Ignition does not need re-working every time
the PLC AOI is revised. The two names being equal — as they happen to be
for ALARM_AOI — is a coincidence of that one family, not the rule.

  So the two are separate inputs here. `--aoi-type` means "match
  instances of this PLC AOI type in the L5X"; `--udt-name` means "build
  typeId from this Ignition UDT name." `--udt-name` defaults to the
  `--aoi-type` value when not supplied, which is what keeps ALARM_AOI's
  behavior identical to before this option existed.

  THE MAPPING IS EXPLICIT PER-RUN INPUT, NOT LOGIC IN THIS SCRIPT. There
  is deliberately no pattern-matching, no regex, and no built-in table of
  AOI-name -> UDT-name pairs. Doug's own rule for the CONSPD family —
  "any PLC AOI matching CONSPD<digits>_AOI always maps to Ignition UDT
  CONSPD2_AOI, whatever the PLC number is" — is *his reasoning for what
  value to pass*, not something this script infers. Encoding it here
  would make the script quietly wrong the moment a family broke the
  pattern, and would contradict the same "explicit input, never inferred"
  principle the qualifying-AOI-type list already follows. The known
  per-family mappings are recorded in PLCHelper_Tasks.md TASK_005 for a
  human to read and pass, and nowhere in this file.

Written 2026-09-10 for PLCHelper (github.com/dougsparks38/plc-helper).
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

# Reuse, not duplicate (2026-09-12): native-UDT member parsing already
# exists, correctly, in generate_ignition_udt.py (TASK_008) -- including
# the Hidden="true" bit-packing-member exclusion, which is real logic
# worth not re-deriving. Resolves the "reuse vs. duplicate parsing logic
# with TASK_004" open question that had sat unresolved in
# PLCHelper_Tasks.md since 2026-09-10. This does re-parse the L5X a
# second time (parse_udt_members takes a path, not this script's already-
# parsed root) -- accepted as a small, one-time-per-type cost rather than
# changing generate_ignition_udt.py's signature for this script's benefit.
from generate_ignition_udt import parse_udt_members, resolve_exclusions, apply_exclusions


# ---------------------------------------------------------------------------
# Per-type parameter mapping — Doug's own words, 2026-09-10; extended
# 2026-09-12 to also cover native UDTs (MODVLV), not just AOIs.
#
# `params`   : top-level Ignition parameters the instance carries.
# `verified` : whether this row has been checked against a real Ignition
#              tag-instance export. Only ALARM_AOI has.
# `source`   : "aoi" (default, read from AddOnInstructionDefinition) or
#              "datatype" (read from a native Class="User" DataType).
#              Added 2026-09-12 rather than a separate CLI flag: this
#              table already uniquely maps a type name to its parameter
#              spec, so adding one more per-entry field is a small,
#              consistent extension of something already there, not a new
#              inference mechanism. Every pre-existing entry defaults to
#              "aoi" (no behavior change for anything already working).
#
# Parameter spec entries are (name, dataType, default_value_or_None).
# A default of None means "look the value up per instance" (Description) or
# "supplied for the whole run" (DeviceName). A literal means that literal
# is written for every instance.
#
# DELIBERATELY NOT IN THIS TABLE: the Ignition UDT name. Earlier revisions
# of this file carried a `udt_name` per row, which quietly made the script
# the authority on AOI-name -> UDT-name pairings. That was removed
# 2026-09-10 once Doug confirmed the drift is a general, ongoing convention
# rather than a fixed set of three exceptions: PLC AOI names gain version
# numbers over time, so any table baked in here starts rotting immediately
# and would silently emit a stale typeId. The UDT name is now supplied per
# run via `--udt-name` (see the module docstring), and the known per-family
# mappings live in PLCHelper_Tasks.md TASK_005 where a human reads them.
# This table is only about *parameters* (and now *source*) now.
# ---------------------------------------------------------------------------

DEVICE_NAME = ("DeviceName", "String", None)      # one value for the whole run
DESCRIPTION = ("Description", "String", None)     # looked up per instance
ENG_UNIT = ("EngUnit", "String", "")              # created, deliberately blank
ANALOG_VLV = ("Analog_Vlv", "Integer", 0)         # MODVLV only

AOI_PARAMETERS = {
    "ALARM_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": True,
        "source": "aoi",
    },
    "CONSPD4_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
        "source": "aoi",
    },
    "FLOWIN3_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
        "source": "aoi",
    },
    "FLOWVLV_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
        "source": "aoi",
    },
    "INTERLOCK_AOI": {
        # Doug: "many other parameters with default values expected to read in
        # correctly with no special handling, plus the same DeviceName /
        # Description pair." Those defaulted parameters live on the UDT
        # definition and are inherited by the instance, so nothing is emitted
        # for them here. Flagged as the natural next test candidate.
        "params": [DEVICE_NAME, DESCRIPTION],
        "verified": False,
        "source": "aoi",
    },
    "LEVELIN3_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
        "source": "aoi",
    },
    "MODVLV": {
        # Native Rockwell UDT, not an AOI (confirmed 2026-09-12: no
        # AddOnInstructionDefinition for it in the L5X) -- member list
        # comes from datatype_definition_parameters(), not
        # aoi_definition_parameters().
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT, ANALOG_VLV],
        "verified": False,
        "source": "datatype",
    },
    "VARSPD2_AOI": {
        "params": [DEVICE_NAME, DESCRIPTION, ENG_UNIT],
        "verified": False,
        "source": "aoi",
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


def datatype_definition_parameters(l5x_path, datatype_name, warnings):
    """Return a native UDT's member names, in document order. TASK_005's
    native-UDT counterpart to aoi_definition_parameters() -- same return
    contract (a list of names, or None if the type isn't found), so the
    main loop can treat both sources identically once it has this list.

    Delegates to generate_ignition_udt.py's parse_udt_members(), which
    already correctly excludes Hidden="true" bit-packing backing members
    -- re-deriving that filtering here would risk quietly getting it
    wrong a second time. parse_udt_members() raises SystemExit on a
    missing/wrong-Class DataType; caught here and converted to this
    script's own warn-and-skip convention so one bad type in a multi-type
    run doesn't kill the whole run, matching aoi_definition_parameters()'s
    behavior (returns None rather than exiting).

    ALSO applies the standing MEMBER_EXCLUSIONS table via
    resolve_exclusions()/apply_exclusions() (2026-09-12 fix -- an earlier
    version of this function called parse_udt_members() alone and missed
    this entirely, which would have silently leaked MODVLV's 4
    confirmed-dead members, `.PID`/`.DLYTMR`/`.FTO_TMR`/`.FTC_TMR`, into
    the generated instance's member-stub list. Those are excluded from
    the real Ignition UDT definition, so an instance still referencing
    them would be exactly the class of mismatch that broke `INTERLOCK_AOI`
    on import. This script has no `--exclude` flag of its own -- only the
    standing table applies here, not ad hoc per-run additions, since
    TASK_005 has no CLI surface for that and the table already holds
    every settled answer.
    """
    try:
        members, _attrs, _hidden = parse_udt_members(l5x_path, datatype_name)
    except SystemExit:
        return None
    exclusions = resolve_exclusions(datatype_name, cli_excludes=None)
    kept, dropped = apply_exclusions(members, exclusions, warnings)
    if dropped:
        print("  excluded %d confirmed-dead member(s) from '%s': %s"
              % (len(dropped), datatype_name,
                 ", ".join("%s (%s)" % (d["name"], d["reason"]) for d in dropped)))
    return [m["Name"] for m in kept]


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

    The optional `=UDT_NAME` names the Ignition UDT for that one AOI type.
    It exists so a run covering several AOI types can still give each one
    its own UDT name, which the single global `--udt-name` cannot express.
    For a single-type run `--udt-name` is the clearer form; the two are
    equivalent and it is an error to give both for the same type.

    A UDT's name legitimately differs from its PLC AOI type name and the
    correct pairing is never inferred (TASK_004's standing note).
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
                        help="A qualifying PLC AOI type to match instances of "
                             "in the L5X. Repeat once per type. Explicit input "
                             "- never inferred. The optional '=UDT_NAME' form "
                             "sets that type's Ignition UDT name, for runs "
                             "covering several types at once.")
    parser.add_argument("--udt-name", default=None, metavar="UDT_NAME",
                        help="Ignition UDT name to build typeId from. "
                             "DEFAULTS TO THE --aoi-type VALUE when omitted. "
                             "Supply it whenever the Ignition UDT name differs "
                             "from the PLC AOI type name - which is the normal "
                             "case, because PLC AOI names gain version numbers "
                             "over time while the Ignition UDT name stays "
                             "fixed. Applies to the whole run, so it may only "
                             "be used with a single --aoi-type; use the "
                             "'--aoi-type NAME=UDT_NAME' form for multi-type "
                             "runs. Never inferred from the AOI name.")
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
                        help="List every AOI type AND native Class=\"User\" "
                             "DataType in the L5X, each with an instance "
                             "count, then exit (combined listing, added "
                             "2026-09-12 when native-UDT support was added -- "
                             "one discovery view rather than a separate flag "
                             "per source kind). Use this to see what is "
                             "available before choosing the qualifying list.")
    args = parser.parse_args()

    root = load_l5x(args.l5x)

    # ---- discovery aid -----------------------------------------------------
    if args.list_aoi_types:
        # kind: "AOI" (AddOnInstructionDefinition) or "UDT" (native
        # Class="User" DataType) -- combined per Doug's 2026-09-12 decision.
        kinds = {}
        for aoi in root.iter("AddOnInstructionDefinition"):
            kinds.setdefault(aoi.get("Name"), "AOI")
        for datatype in root.iter("DataType"):
            if datatype.get("Class") == "User":
                kinds.setdefault(datatype.get("Name"), "UDT")

        counts = {name: 0 for name in kinds}
        for controller in root.iter("Controller"):
            tags = controller.find("Tags")
            if tags is None:
                continue
            for tag in tags.findall("Tag"):
                dt = tag.get("DataType")
                if dt in counts:
                    counts[dt] += 1

        print("AOI types and native UDTs defined in %s:"
              % os.path.basename(args.l5x))
        for name in sorted(counts):
            mapped = "mapped" if name in AOI_PARAMETERS else "NOT in mapping"
            print("  %-3s %-20s %3d controller instances   (%s)"
                  % (kinds[name], name, counts[name], mapped))
        print("\nThis is a discovery aid only. Which of these qualify is "
              "Doug's explicit decision, not this script's.")
        return 0

    dest_folder = args.dest_folder.strip()
    prefix = args.udt_path_prefix.strip().strip("/")

    # `--udt-name` is one value for the whole run, so it is only meaningful
    # when the run covers one AOI type. Refusing here rather than picking a
    # type to apply it to: silently attaching one UDT name to several AOI
    # types would emit instances pointing at a definition that is wrong for
    # most of them, and typeId errors do not surface until import time.
    # `is not None` rather than a truthiness test, so `--udt-name ""` is
    # caught as the mistake it is instead of silently defaulting.
    udt_name_arg = args.udt_name.strip() if args.udt_name is not None else None
    if udt_name_arg and len(args.aoi_type) > 1:
        sys.exit(
            "ERROR: --udt-name applies to the whole run and cannot be used "
            "with more than one --aoi-type (%d given). Use the per-type form "
            "instead, e.g. --aoi-type CONSPD4_AOI=CONSPD2_AOI --aoi-type "
            "VARSPD2_AOI=VARSPD_AOI." % len(args.aoi_type))
    if udt_name_arg == "":
        sys.exit("ERROR: --udt-name was given but is empty. Omit it to default "
                 "to the --aoi-type value.")

    print("=" * 72)
    print("TASK_005 - Ignition tag instance generation")
    print("=" * 72)
    print("L5X            : %s" % args.l5x)
    print("DeviceName     : %s   (one value for the whole run)" % args.device_name)
    print("Destination    : %s   (explicit input - never hardcoded)" % dest_folder)
    print("UDT path prefix: %s" % prefix)
    print("UDT name       : %s" % (
        udt_name_arg if udt_name_arg
        else "(not given - defaults to the --aoi-type value)"))
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

        type_kind = "Native UDT" if mapping.get("source") == "datatype" else "AOI type"
        if not mapping["verified"]:
            warnings.append(
                "%s '%s' parameter mapping is UNVERIFIED - it records "
                "Doug's stated intent but has never been checked against a "
                "real Ignition tag-instance export. Verify one instance by "
                "hand before importing in bulk." % (type_kind, aoi_type))

        # UDT name resolution, in priority order. Nothing is inferred from
        # the AOI name itself at any step — the last fallback is literally
        # reusing the AOI name, not deducing a UDT name from it.
        #   1. `--aoi-type NAME=UDT_NAME` (per-type, wins for that type)
        #   2. `--udt-name` (one value for the whole run)
        #   3. the `--aoi-type` name itself (the historical behavior, and
        #      what keeps ALARM_AOI byte-identical to before this option)
        if udt_override and udt_name_arg:
            sys.exit(
                "ERROR: UDT name for '%s' was given twice - '=%s' on "
                "--aoi-type and '%s' on --udt-name. They disagree or are "
                "redundant; give exactly one." % (aoi_type, udt_override,
                                                  udt_name_arg))

        if udt_override:
            udt_name = udt_override
            print("NOTE: per-type UDT name in effect: %s -> UDT '%s'"
                  % (aoi_type, udt_name))
        elif udt_name_arg:
            udt_name = udt_name_arg
            print("NOTE: --udt-name in effect: PLC AOI '%s' -> Ignition UDT "
                  "'%s'" % (aoi_type, udt_name))
        else:
            udt_name = aoi_type
            print("NOTE: no --udt-name given; using the PLC AOI type name "
                  "'%s' as the Ignition UDT name. If this job's UDT is named "
                  "differently, re-run with --udt-name." % udt_name)

        source = mapping.get("source", "aoi")
        if source == "datatype":
            member_names = datatype_definition_parameters(args.l5x, aoi_type, warnings)
            if member_names is None:
                warnings.append(
                    "Native UDT '%s' has no usable Class=\"User\" DataType in "
                    "this L5X (missing, wrong Class, or no <Members> block). "
                    "Nothing generated for it." % aoi_type)
                continue
        else:
            member_names = aoi_definition_parameters(root, aoi_type)
            if member_names is None:
                warnings.append(
                    "AOI type '%s' has no AddOnInstructionDefinition in this "
                    "L5X. Nothing generated for it." % aoi_type)
                continue
        if not member_names:
            warnings.append(
                "%s '%s' has a definition but no usable members/parameters. "
                "Nothing generated for it." % (type_kind, aoi_type))
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
