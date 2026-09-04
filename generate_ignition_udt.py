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

The reference UDT is read to learn CONVENTIONS ONLY (OPC Server value,
OPC Item Path template shape, member JSON key set and constant values,
top-level type shape). Its member data is never copied into the output,
and its per-member data types are deliberately NOT trusted -- the
reference is known to contain hand-entry data-type errors, so the PLC ->
Ignition mapping is fixed from the confirmed-correct majority instead.

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

# Optional per-member engineering choices in Ignition. These are NOT
# conventions -- Doug enables history on the specific members he wants it
# on, in Designer -- so they are never invented for a generated member.
OPTIONAL_MEMBER_KEYS = {
    "historyEnabled",
    "historyProvider",
    "historyTagGroup",
    "historyMaxAge",
    "historyMaxAgeUnits",
    "historicalDeadbandStyle",
    "sampleMode",
    "deadband",
    "deadbandMode",
    "scaleMode",
}

MEMBER_PLACEHOLDER = "\x00MEMBER\x00"


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

    return {
        "opc_server": opc_server,
        "template": template,
        "bind_type": bind_type or "parameter",
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
    return member


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
    print()

    # --- Step 3/4: build one member per parameter. Every parameter.
    warnings = []
    members = [build_member(p, conventions, warnings) for p in parameters]

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
