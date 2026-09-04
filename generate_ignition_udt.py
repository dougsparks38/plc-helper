#!/usr/bin/env python3
"""
TASK_004 — Generate an Ignition UDT definition JSON from a PLC AOI.

Given an AOI type name, an L5X export containing that AOI's
AddOnInstructionDefinition, and a reference Ignition UDT definition
export, emit a brand-new Ignition UDT definition JSON with one member
per AOI parameter.

SCOPE DECISION (Doug-approved, 2026-09-04): every AOI parameter becomes a
member. No exclusions, no filtering, no judgment about which parameters
are "needed for SCADA/HMI." See PLCHelper_Tasks.md TASK_004 for why this
is a deliberate exception to the Hard scope boundary that governs
*correcting an existing* UDT.

HISTORIZATION RULE (Doug-supplied, 2026-09-04): members whose names match
an explicit suffix rule get History enabled with fixed settings chosen by
signal type. This is a supplied rule, not a guess -- see PLCHelper_Tasks.md
TASK_004 "Historization rule" and CLAUDE.md's "Ignition tag History"
section. Members that do not match get no history keys at all, exactly as
before.

The reference UDT is read to learn CONVENTIONS ONLY (OPC Server value,
OPC Item Path template shape, member JSON key set and constant values,
top-level type shape, and -- for historized members -- the history
*context* values such as storage provider and historical tag group). Its
member data is never copied into the output, and its per-member data types
are deliberately NOT trusted -- the reference is known to contain
hand-entry data-type errors, so the PLC -> Ignition mapping is fixed from
the confirmed-correct majority instead.

CONFIDENTIALITY: the L5X and reference UDT typically live in a job's own
project folder and are read cross-folder by path. They are never copied
into PLCHelper, and output should be written back into the job's folder.

Usage:
    python generate_ignition_udt.py \
        --aoi FLOWIN3_AOI \
        --l5x "<path to job folder>/program.L5X" \
        --reference "<path to job folder>/reference UDT tags.json" \
        --output "<path to job folder>/FLOWIN3_AOI UDT.json"

Optional:
    --udt-name NAME   Name for the generated UDT type. Defaults to the
                      AOI type name. Supplied explicitly because Ignition
                      UDT names do NOT track PLC AOI version numbers --
                      a UDT named CONSPD2_AOI legitimately corresponds to
                      PLC type CONSPD4_AOI. Never inferred by name.
    --list-aois       List every AOI type in the L5X and exit.
"""

import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET

# PLC (L5X) -> Ignition data type mapping.
#
# Confirmed empirically against real files (2026-09-04) rather than taken
# from generic documentation, per Rule 33. BOOL->Boolean held for 24 of 25
# BOOL members in the real reference UDT; DINT->Int4 for 3 of 4; REAL->Float4
# with no counterexample. The minority disagreements were traced to
# hand-entry mistakes in the reference UDT, NOT to a convention -- which is
# precisely why this mapping is fixed here rather than learned per-member.
DATA_TYPE_MAP = {
    "BOOL": "Boolean",
    "SINT": "Int4",
    "INT": "Int4",
    "DINT": "Int4",
    "LINT": "Int8",
    "REAL": "Float4",
    "LREAL": "Float8",
    "STRING": "String",
}

# Mapping entries confirmed directly against the real files. Anything mapped
# but not in this set is reported as an inference so it gets a human look.
CONFIRMED_TYPES = {"BOOL", "DINT", "REAL", "STRING"}

# Keys computed per-member rather than copied as a convention constant.
COMPUTED_KEYS = {"name", "dataType", "opcItemPath"}

# Per-member history/scaling keys. These are stripped out of the "member
# constants" learned from the reference, so a reference member's own
# history settings can never leak onto an unrelated generated member. The
# generated members' history block is built from the rule below instead.
OPTIONAL_MEMBER_KEYS = {
    "historyEnabled",
    "historyProvider",
    "historyTagGroup",
    "historyMaxAge",
    "historyMaxAgeUnits",
    "historicalDeadbandStyle",
    "historicalDeadbandMode",
    "historicalDeadband",
    "historyTimeDeadband",
    "historyTimeDeadbandUnits",
    "historySampleRate",
    "includeMetadata",
    "sampleMode",
    "deadband",
    "deadbandMode",
    "scaleMode",
}

MEMBER_PLACEHOLDER = "\x00MEMBER\x00"

# --------------------------------------------------------------------------
# Historization rule -- Doug-supplied and confirmed 2026-09-04.
#
# A member gets History enabled if its name (case-insensitive) ends with
# one of the signal-type suffixes below, or is an alarm bit ending in
# exactly "_alm" / "_alarm". Compound alarm names (_alm_dis, _alm_ack,
# _alm_res, and anything else _alm_*) are deliberately EXCLUDED -- they are
# alarm *controls*, not the alarm itself. Nothing else is historized; no
# other suffix or pattern is inferred.
#
# The suffix meanings come from CLAUDE.md's "Naming conventions" table and
# are not re-derived here.
# --------------------------------------------------------------------------
ANALOG_SUFFIXES = ("_hwai", "_hwao", "_scai", "_scao")
DIGITAL_SUFFIXES = ("_hwdi", "_hwdo", "_scdi", "_scdo")
# Alarms are always Boolean at Casne (confirmed by Doug), regardless of how
# the AOI names or types the alarm parameter -- so these classify as digital.
ALARM_EXACT_SUFFIXES = ("_alm", "_alarm")

# Ignition data types that agree with each signal class. Used only to raise
# a review warning when the name's suffix and the PLC data type disagree --
# the rule is name-based and the classification is never overridden by type.
ANALOG_IGNITION_TYPES = {"Float4", "Float8"}
DIGITAL_IGNITION_TYPES = {"Boolean"}

# History settings by signal type. Values are the Casne standing defaults
# and the documented correctness rules from CLAUDE.md's "Ignition tag
# History -- digital vs. analog configuration" section; they are not
# re-derived here.
#
# JSON key names and enum spellings below were taken from real Ignition UDT
# definition exports rather than from the Designer UI labels, because the
# two differ: the UI's "On Change" serializes as "OnChange", "Minutes" as
# "MIN", and the Analog deadband style as "Analog_Compressed".
#
# Historical Deadband choices:
#   digital -- 0.0. CLAUDE.md allows 0 or 0.01; 0.0 is chosen because
#     CLAUDE.md also notes a non-zero deadband next to Discrete style is
#     inert/vestigial, and 0.0 states "store every transition" plainly.
#     Both are safely below the >= 1.0 value that would silently suppress
#     ALL history for a BOOL (CLAUDE.md's documented trap).
#   analog -- see ANALOG_DEADBAND_PLACEHOLDER below. NOT a verified value.
HISTORY_DIGITAL = {
    "historyEnabled": True,
    # Explicit Discrete rather than relying on the Auto default: on a BOOL
    # this is redundant today but survives a later data-type change on the
    # member (CLAUDE.md's reasoning, digital case).
    "historicalDeadbandStyle": "Discrete",
    "historicalDeadbandMode": "Absolute",
    "historicalDeadband": 0.0,
    "sampleMode": "OnChange",
    "historyMaxAge": 20,
    "historyMaxAgeUnits": "MIN",
}

# ⚠ NOT a verified-correct number. CLAUDE.md is explicit that the Ignition
# docs give no method, recommended value, or rule of thumb for choosing a
# Historical Deadband -- it is purely an engineering judgment call per
# signal. 0.01 is used here only because it is the value in the docs' own
# worked example, which CLAUDE.md cites. Doug must review and adjust this
# per signal; the script says so loudly on every run that emits one.
ANALOG_DEADBAND_PLACEHOLDER = 0.01

HISTORY_ANALOG = {
    "historyEnabled": True,
    # No "historicalDeadbandStyle" key on purpose. Auto is Ignition's
    # default style and resolves to Analog on a Float, which is what
    # CLAUDE.md's analog findings call for; real Ignition exports represent
    # Auto by OMITTING the key rather than writing a literal, and no
    # "Auto" literal appears in any real export checked. Writing the key
    # only when a non-default style is wanted matches Ignition's own
    # serialization.
    "historicalDeadbandMode": "Absolute",
    "historicalDeadband": ANALOG_DEADBAND_PLACEHOLDER,
    "sampleMode": "OnChange",
    "historyMaxAge": 20,
    "historyMaxAgeUnits": "MIN",
}

# History keys this script sets itself, from the tables above. Any history
# key seen on the reference that is NOT in here and NOT in
# HISTORY_CONTEXT_KEYS is reported rather than copied or invented.
HISTORY_RULE_KEYS = set(HISTORY_DIGITAL) | set(HISTORY_ANALOG) | {
    "historicalDeadbandStyle"
}

# History keys that are project/environment context rather than a
# per-signal engineering choice -- which historian stores the data and
# under which historical tag group. There is no correct value to invent for
# these, so they are DERIVED from the reference's own historized members,
# the same way the OPC Server value and path template already are.
HISTORY_CONTEXT_KEYS = ("historyProvider", "historyTagGroup", "includeMetadata")


def classify_history(name):
    """Return 'analog', 'digital', or None for a member name.

    Implements the Doug-supplied historization rule verbatim. Matching is
    case-insensitive; the member's own name is never altered.
    """
    lowered = name.lower()
    if lowered.endswith(ANALOG_SUFFIXES):
        return "analog"
    if lowered.endswith(DIGITAL_SUFFIXES):
        return "digital"
    # Exactly "_alm" / "_alarm" only. str.endswith already excludes every
    # compound form (_alm_dis, _alm_ack, _alm_res, _Alm_Enable, ...) because
    # those end with the trailing token, not with "_alm".
    if lowered.endswith(ALARM_EXACT_SUFFIXES):
        return "digital"
    return None


def _freeze(value):
    """Hashable stand-in for a JSON value, so dicts can be counted."""
    return json.dumps(value, sort_keys=True)


def _most_common(values):
    """Most common JSON value in an iterable, or None if empty."""
    counter = collections.Counter(_freeze(v) for v in values)
    if not counter:
        return None
    return json.loads(counter.most_common(1)[0][0])


def parse_aoi_parameters(l5x_path, aoi_name):
    """Read an AOI's complete parameter list from an L5X, in document order.

    Returns (parameters, aoi_attributes). Each parameter is a dict of the
    attributes needed to build a UDT member, with Name preserved verbatim.
    """
    try:
        root = ET.parse(l5x_path).getroot()
    except ET.ParseError as exc:
        raise SystemExit(f"ERROR: could not parse L5X as XML: {exc}")

    for aoi in root.iter("AddOnInstructionDefinition"):
        if aoi.get("Name") != aoi_name:
            continue

        params_el = aoi.find("Parameters")
        if params_el is None:
            raise SystemExit(
                f"ERROR: AOI '{aoi_name}' has no <Parameters> block in this L5X."
            )

        parameters = []
        for param in params_el.findall("Parameter"):
            desc_el = param.find("Description")
            description = ""
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip()
            parameters.append(
                {
                    # Verbatim, case preserved. CLAUDE.md: "no capitalization
                    # changes of any kind" -- a functional requirement, since a
                    # case mismatch breaks the OPC binding (bug pattern #2).
                    "Name": param.get("Name"),
                    "DataType": param.get("DataType"),
                    "Usage": param.get("Usage"),
                    "Required": param.get("Required"),
                    "Visible": param.get("Visible"),
                    "ExternalAccess": param.get("ExternalAccess"),
                    "Dimension": param.get("Dimension"),
                    "Description": description,
                }
            )

        return parameters, dict(aoi.attrib)

    available = sorted(
        a.get("Name") for a in root.iter("AddOnInstructionDefinition")
    )
    raise SystemExit(
        f"ERROR: AOI '{aoi_name}' not found in {l5x_path}.\n"
        f"AOI types present ({len(available)}): {', '.join(available)}"
    )


def list_aois(l5x_path):
    root = ET.parse(l5x_path).getroot()
    rows = []
    for aoi in root.iter("AddOnInstructionDefinition"):
        params = aoi.find("Parameters")
        count = len(params.findall("Parameter")) if params is not None else 0
        rows.append((aoi.get("Name"), aoi.get("Revision"), count,
                     aoi.get("Vendor") or "Casne"))
    for name, rev, count, vendor in sorted(rows):
        print(f"  {name:28} rev {str(rev):6} {count:3} parameters   [{vendor}]")
    print(f"\n{len(rows)} AOI definitions in {l5x_path}")


def derive_conventions(reference_path):
    """Learn UDT conventions from a real Ignition UDT definition export.

    Returns a dict of conventions. Deliberately does NOT return any of the
    reference's member names, data types, or history settings.
    """
    with open(reference_path, "r", encoding="utf-8-sig") as handle:
        ref = json.load(handle)

    if not isinstance(ref, dict):
        raise SystemExit("ERROR: reference UDT JSON is not a JSON object.")

    members = ref.get("tags")
    if not isinstance(members, list) or not members:
        raise SystemExit(
            "ERROR: reference UDT JSON has no 'tags' array of members. Make "
            "sure it was exported from Ignition's 'UDT Definitions' tab -- "
            "exporting a UDT *instance* does not include the definition."
        )

    tag_type = ref.get("tagType")
    if tag_type != "UdtType":
        print(
            f"  WARNING: reference top-level tagType is '{tag_type}', expected "
            "'UdtType'. This may be an instance export rather than a "
            "definition export.",
            file=sys.stderr,
        )

    # --- OPC Server: the confirmed-correct value has NO hyphen. A hyphenated
    # "Ignition OPC-UA Server" is confirmed bug pattern #1 and yields
    # Error_Configuration("Server ... does not exist.").
    opc_server = _most_common(
        m["opcServer"] for m in members if m.get("opcServer")
    )

    # --- OPC Item Path template. Replace each member's own name in its own
    # binding with a placeholder, then take the most common result. The
    # replacement is case-insensitive on purpose: the reference is known to
    # contain a member whose name and binding disagree in case, and that
    # member should still contribute its template shape.
    templates = []
    literal_bindings = 0
    for member in members:
        path = member.get("opcItemPath")
        name = member.get("name")
        if not isinstance(path, dict) or not name:
            continue
        binding = path.get("binding")
        if not binding:
            continue
        template, subs = re.subn(
            re.escape(name), MEMBER_PLACEHOLDER, binding, flags=re.IGNORECASE
        )
        if subs:
            templates.append(template)
        else:
            literal_bindings += 1

    if not templates:
        raise SystemExit(
            "ERROR: could not derive an OPC Item Path template -- no reference "
            "member's binding contained its own name."
        )

    template = _most_common(templates)
    bind_type = _most_common(
        m["opcItemPath"].get("bindType")
        for m in members
        if isinstance(m.get("opcItemPath"), dict)
        and m["opcItemPath"].get("bindType")
    )

    # --- Member key set: the most common key set is the minimal correct
    # member. Optional history/scaling keys are stripped -- they are
    # per-member choices, not conventions.
    key_sets = collections.Counter(
        tuple(sorted(set(m.keys()) - OPTIONAL_MEMBER_KEYS)) for m in members
    )
    member_keys = list(key_sets.most_common(1)[0][0])

    # --- Constant values for every non-computed key, taken as the most
    # common value across the reference's members.
    member_constants = {}
    for key in member_keys:
        if key in COMPUTED_KEYS:
            continue
        present = [m[key] for m in members if key in m]
        if present:
            member_constants[key] = _most_common(present)

    # --- Top-level type shape, with member data and the type name removed.
    type_shape = {
        k: v for k, v in ref.items() if k not in ("tags", "name")
    }
    # A new type must not inherit another type's parameter default values.
    # Blanking them also guarantees no reference instance data can leak out.
    blanked_parameters = []
    if isinstance(type_shape.get("parameters"), dict):
        for param_name, param_def in type_shape["parameters"].items():
            if isinstance(param_def, dict) and "value" in param_def:
                original = param_def["value"]
                if isinstance(original, str):
                    if original:
                        blanked_parameters.append(param_name)
                    param_def["value"] = ""
                elif isinstance(original, (int, float)) and original:
                    blanked_parameters.append(param_name)
                    param_def["value"] = 0

    # --- History context, derived from the reference's own historized
    # members. Same pattern as the OPC Server value: not invented here, read
    # off a real file. Anything the reference has no historized members to
    # teach is left unset and reported, never defaulted to a made-up value.
    historized = [m for m in members if m.get("historyEnabled")]
    history_context = {}
    for key in HISTORY_CONTEXT_KEYS:
        present = [m[key] for m in historized if key in m]
        if present:
            history_context[key] = _most_common(present)

    # History keys the reference's historized members use that this script
    # neither sets from the rule nor derives as context. Surfaced so an
    # unrecognized convention gets a human look instead of being silently
    # dropped or silently copied.
    unhandled_history_keys = sorted(
        {
            key
            for m in historized
            for key in m
            if key in OPTIONAL_MEMBER_KEYS
            and key not in HISTORY_RULE_KEYS
            and key not in HISTORY_CONTEXT_KEYS
        }
    )

    return {
        "opc_server": opc_server,
        "template": template,
        "bind_type": bind_type or "parameter",
        "history_context": history_context,
        "historized_reference_members": len(historized),
        "unhandled_history_keys": unhandled_history_keys,
        "member_keys": member_keys,
        "member_constants": member_constants,
        "type_shape": type_shape,
        "reference_member_count": len(members),
        "literal_bindings": literal_bindings,
        "blanked_parameters": blanked_parameters,
        "udt_parameters": sorted(
            (type_shape.get("parameters") or {}).keys()
        ),
    }


def build_member(parameter, conventions, warnings):
    """Build one Ignition UDT member from one AOI parameter."""
    name = parameter["Name"]
    plc_type = parameter["DataType"]

    ignition_type = DATA_TYPE_MAP.get(plc_type)
    if ignition_type is None:
        ignition_type = "String"
        warnings.append(
            f"{name}: PLC data type '{plc_type}' has no confirmed Ignition "
            f"mapping -- emitted as 'String' placeholder, NEEDS REVIEW. "
            f"(Likely a UDT-typed or array parameter.)"
        )
    elif plc_type not in CONFIRMED_TYPES:
        warnings.append(
            f"{name}: PLC data type '{plc_type}' mapped to '{ignition_type}' "
            f"by inference -- not directly confirmed against a real file. "
            f"Worth a look."
        )

    if parameter.get("Dimension") and parameter["Dimension"] not in ("0", None):
        warnings.append(
            f"{name}: parameter is an array (Dimension="
            f"{parameter['Dimension']}) -- Ignition needs array handling "
            f"here, review before import."
        )

    member = dict(conventions["member_constants"])
    member["name"] = name
    member["dataType"] = ignition_type
    # Both the member name and the binding come from the same verbatim L5X
    # string, so they cannot disagree in case -- bug pattern #2 is eliminated
    # by construction rather than caught after the fact.
    member["opcItemPath"] = {
        "bindType": conventions["bind_type"],
        "binding": conventions["template"].replace(MEMBER_PLACEHOLDER, name),
    }
    member["opcServer"] = conventions["opc_server"]

    # --- Historization rule. Name-based and deterministic; a member that
    # does not match gets no history keys at all.
    signal = classify_history(name)
    if signal:
        settings = HISTORY_DIGITAL if signal == "digital" else HISTORY_ANALOG
        member.update(settings)
        member.update(conventions["history_context"])

        expected = (
            DIGITAL_IGNITION_TYPES if signal == "digital"
            else ANALOG_IGNITION_TYPES
        )
        if ignition_type not in expected:
            warnings.append(
                f"{name}: name classifies as {signal} by suffix, but its "
                f"data type is '{ignition_type}' ({plc_type} in the PLC). "
                f"History was still applied per the naming rule -- the rule "
                f"is name-based -- but this disagreement is worth a look."
            )

    return member, signal


def main():
    parser = argparse.ArgumentParser(
        description="Generate an Ignition UDT definition JSON from a PLC AOI "
                    "(TASK_004). Includes EVERY AOI parameter as a member.",
    )
    parser.add_argument("--aoi", help="AOI type name, e.g. FLOWIN3_AOI")
    parser.add_argument("--l5x", required=True, help="Path to the L5X export")
    parser.add_argument("--reference", help="Path to a reference Ignition UDT "
                                           "definition JSON export")
    parser.add_argument("--output", help="Path for the generated UDT JSON")
    parser.add_argument("--udt-name", help="Name for the generated UDT type "
                                          "(defaults to the AOI type name)")
    parser.add_argument("--list-aois", action="store_true",
                        help="List every AOI type in the L5X and exit")
    args = parser.parse_args()

    if args.list_aois:
        list_aois(args.l5x)
        return 0

    missing = [
        flag for flag, value in
        (("--aoi", args.aoi), ("--reference", args.reference),
         ("--output", args.output))
        if not value
    ]
    if missing:
        parser.error(f"missing required argument(s): {', '.join(missing)}")

    udt_name = args.udt_name or args.aoi

    print(f"TASK_004 -- Generate Ignition UDT definition")
    print(f"{'=' * 68}")
    print(f"AOI type    : {args.aoi}")
    print(f"L5X         : {args.l5x}")
    print(f"Reference   : {args.reference}")
    print(f"Output UDT  : {udt_name}")
    print()

    # --- Step 1: the AOI's real parameter list, straight from the L5X.
    parameters, aoi_attrs = parse_aoi_parameters(args.l5x, args.aoi)
    print(f"AOI found: revision {aoi_attrs.get('Revision')}, "
          f"{len(parameters)} parameters (ALL will become members)")
    usage_counts = collections.Counter(p["Usage"] for p in parameters)
    print(f"  by usage: " + ", ".join(
        f"{u}={c}" for u, c in sorted(usage_counts.items())))
    type_counts = collections.Counter(p["DataType"] for p in parameters)
    print(f"  by type : " + ", ".join(
        f"{t}={c}" for t, c in sorted(type_counts.items())))
    print()

    # --- Step 2: conventions from the reference (conventions only).
    conventions = derive_conventions(args.reference)
    print(f"Conventions derived from reference "
          f"({conventions['reference_member_count']} members read):")
    print(f"  OPC Server   : {conventions['opc_server']!r}")
    if conventions["opc_server"] and "OPC-UA" in conventions["opc_server"]:
        print("  *** WARNING: reference OPC Server name contains a hyphen "
              "('OPC-UA'). This is confirmed bug pattern #1 and will produce")
        print("      Error_Configuration(\"Server ... does not exist.\"). "
              "Expected 'Ignition OPC UA Server'. Fix the reference or")
        print("      correct the generated file before import.")
    print(f"  Path template: "
          f"{conventions['template'].replace(MEMBER_PLACEHOLDER, '<MemberName>')}")
    print(f"  bindType     : {conventions['bind_type']!r}")
    print(f"  Member keys  : {', '.join(sorted(conventions['member_keys']))}")
    print(f"  UDT params   : "
          f"{', '.join(conventions['udt_parameters']) or '(none)'}")
    if conventions["literal_bindings"]:
        print(f"  note: {conventions['literal_bindings']} reference member(s) "
              f"had a literal (non-templated) binding -- ignored for template "
              f"derivation")
    if conventions["blanked_parameters"]:
        print(f"  note: blanked reference parameter default value(s) so no "
              f"reference data carries over: "
              f"{', '.join(conventions['blanked_parameters'])}")
    history_context = conventions["history_context"]
    if history_context:
        print(f"  History ctx  : "
              + ", ".join(f"{k}={v!r}" for k, v in sorted(history_context.items()))
              + f"  (from {conventions['historized_reference_members']} "
                f"historized reference member(s))")
    else:
        print(f"  History ctx  : (none derivable -- the reference has "
              f"{conventions['historized_reference_members']} historized "
              f"member(s))")
    if conventions["unhandled_history_keys"]:
        print(f"  note: reference historized members also carry history "
              f"key(s) this script does not set or derive: "
              f"{', '.join(conventions['unhandled_history_keys'])}. NOT "
              f"applied -- review whether they should be.")
    print()

    # --- Step 3/4: build one member per parameter. Every parameter.
    warnings = []
    built = [build_member(p, conventions, warnings) for p in parameters]
    members = [m for m, _ in built]
    historized = [(m["name"], signal) for m, signal in built if signal]

    udt = dict(conventions["type_shape"])
    udt["name"] = udt_name
    udt["tagType"] = "UdtType"
    udt["tags"] = members

    # --- Step 5: write the output. Keys sorted to match Ignition's own
    # export formatting; the members array keeps L5X document order.
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(udt, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Generated {len(members)} members -> {args.output}")

    # --- Historization report. Printed in full every run: which members got
    # History and why, so the rule's effect is reviewable at a glance rather
    # than something to go hunting for in the JSON.
    analog_members = [n for n, s in historized if s == "analog"]
    digital_members = [n for n, s in historized if s == "digital"]
    print()
    print(f"History enabled on {len(historized)} of {len(members)} members "
          f"by the naming rule ({len(digital_members)} digital, "
          f"{len(analog_members)} analog):")
    if digital_members:
        print(f"  digital ({len(digital_members)}): "
              f"{', '.join(digital_members)}")
    if analog_members:
        print(f"  analog  ({len(analog_members)}): "
              f"{', '.join(analog_members)}")
    if not historized:
        print("  (none matched)")
    print(f"  The other {len(members) - len(historized)} member(s) got no "
          f"history keys at all.")

    if analog_members:
        print()
        print(f"  *** REVIEW REQUIRED -- analog Historical Deadband is a "
              f"placeholder, not a verified value.")
        print(f"      Every analog member above was written with "
              f"historicalDeadband = {ANALOG_DEADBAND_PLACEHOLDER}. The "
              f"Ignition docs give NO method,")
        print(f"      recommended value, or rule of thumb for choosing this "
              f"number -- it is an engineering judgment call per signal.")
        print(f"      {ANALOG_DEADBAND_PLACEHOLDER} is used only because it "
              f"is the value in the docs' own worked example. Review and "
              f"adjust each")
        print(f"      analog member's deadband for its real signal before "
              f"relying on the history. The digital deadband "
              f"({HISTORY_DIGITAL['historicalDeadband']}) is not a")
        print(f"      judgment call and needs no review.")

    if historized and not history_context.get("historyProvider"):
        print()
        print(f"  *** WARNING: no historyProvider could be derived from the "
              f"reference, so the generated members have History enabled")
        print(f"      with no storage provider set. Ignition will not store "
              f"history until a provider is selected. Set the storage")
        print(f"      provider (and historical tag group) on these members "
              f"in Designer after import, or re-run against a reference")
        print(f"      UDT that already has historized members to derive "
              f"them from.")

    if warnings:
        print(f"\n{len(warnings)} warning(s) needing review:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("No warnings -- every parameter mapped to a confirmed Ignition "
              "data type.")

    print(f"\nNext step: import into Ignition Designer via the "
          f"'UDT Definitions' tab.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
