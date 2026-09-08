#!/usr/bin/env python3
"""
TASK_004 — Generate an Ignition UDT definition JSON from a PLC AOI.
TASK_008 — ...or from a native PLC UDT (`<DataType Class="User">`).

Given an AOI type name, an L5X export containing that AOI's
AddOnInstructionDefinition, and a reference Ignition UDT definition
export, emit a brand-new Ignition UDT definition JSON with one member
per AOI parameter.

NATIVE UDT SOURCE (TASK_008, added 2026-09-08): not every type on a job's
Ignition-handoff checklist is an AOI. MODVLV, for example, is a native
Rockwell UDT — a `<DataType Class="User">` element with a `<Members>`
block — not an `<AddOnInstructionDefinition>`. Pass `--datatype NAME`
instead of `--aoi NAME` to read one of those. Everything downstream of
the member list is shared verbatim with the AOI path: the same
convention derivation, the same fixed data-type mapping, the same
historization rule, the same output shape. Only the source element and
the hidden-member exclusion below differ.

HIDDEN BACKING MEMBERS ARE EXCLUDED (Doug-confirmed, 2026-09-08): when a
native UDT contains boolean members, Studio 5000 packs them into
auto-generated integer storage members named `ZZZZZZZZZZ<Type><n>` and
marked `Hidden="true"`, then exposes each real bit as its own visible
`DataType="BIT"` member carrying `Target` (the backing member) and
`BitNumber`. The hidden backing members are Studio 5000's own bit-packing
storage, not independent data points -- they do not appear in Doug's
Ignition tag list, and they are confirmed absent from the real MODVLV
reference UDT export. They are therefore dropped. The visible `BIT`
alias members ARE included, each as its own Boolean member, exactly like
any other real member.

SCOPE DECISION (Doug-approved, 2026-09-04): every AOI parameter becomes a
member. No exclusions, no filtering, no judgment about which parameters
are "needed for SCADA/HMI." See PLCHelper_Tasks.md TASK_004 for why this
is a deliberate exception to the Hard scope boundary that governs
*correcting an existing* UDT.

CONFIRMED-DEAD MEMBERS ARE EXCLUDED, BY EXPLICIT OPT-IN ONLY (added
2026-09-08): the scope decision above stands -- this script still never
decides on its own that a member is unwanted. But once Doug has
*confirmed* a specific member is genuinely dead code in the real PLC
program, continuing to emit it as a NEEDS REVIEW placeholder is no longer
"reporting instead of guessing," it is re-asking a settled question every
run. MEMBER_EXCLUSIONS below is the record of those settled answers, keyed
by source type name; --exclude adds one ad-hoc for a single run. It works
identically in --aoi and --datatype mode because the filtering happens on
the derived member list, downstream of both parsers -- the same reason the
conventions and the historization rule are shared code.

An exclusion is never silent. Every run prints each excluded member, its
PLC data type, the reason, and where the exclusion came from; and a
configured exclusion that matches NO member in the source raises a
warning rather than passing unnoticed, so a typo or a since-renamed
member surfaces instead of quietly doing nothing. Same
reports-itself-always principle as the hidden-backing-member exclusion.

HISTORIZATION RULE (Doug-supplied, 2026-09-04; extended 2026-09-08):
members whose names match an explicit name rule get History enabled with
fixed settings chosen by signal type. A name matches either by ENDING WITH
a signal-type suffix ("_hwdi", "_scao", "_alm", ...) or by BEING EXACTLY a
bare signal-type word with no underscore prefix ("Hwdi", "Alarm", ...).
The bare-word form was added 2026-09-08 after Doug found ALARM_AOI's real
PLC parameters use it instead of the suffixed convention. This is a
supplied rule, not a guess -- see PLCHelper_Tasks.md TASK_004
"Historization rule" and CLAUDE.md's "Ignition tag History" section.
Members that do not match get no history keys at all, exactly as before.

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

    python generate_ignition_udt.py \
        --datatype MODVLV \
        --l5x "<path to job folder>/program.L5X" \
        --reference "<path to job folder>/reference UDT tags.json" \
        --output "<path to job folder>/MODVLV UDT.json"

Optional:
    --udt-name NAME   Name for the generated UDT type. Defaults to the
                      source AOI or DataType name. Supplied explicitly
                      because Ignition UDT names do NOT track PLC AOI
                      version numbers -- a UDT named CONSPD2_AOI
                      legitimately corresponds to PLC type CONSPD4_AOI.
                      Never inferred by name.
    --list-aois       List every AOI type in the L5X and exit.
    --list-datatypes  List every native user DataType in the L5X and exit.
    --exclude NAME[=reason]
                      Drop one member from the generated UDT for this run
                      only. Repeatable. Additive to MEMBER_EXCLUSIONS
                      below -- it can add an exclusion but never cancel
                      one. For an exclusion that should apply on every
                      future run, put it in MEMBER_EXCLUSIONS instead of
                      relying on someone remembering the flag.
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
# BIT->Boolean was added 2026-09-08 for the native-UDT path (TASK_008) and is
# confirmed the same empirical way, not assumed: of MODVLV's 24 visible BIT
# members, the 21 that also exist in the real MODVLV Ignition UDT export are
# "Boolean" in all 21 cases, with zero counterexamples -- a cleaner agreement
# than the original BOOL confirmation. A BIT member is a single aliased bit of
# a hidden integer backing member, so Boolean is also the only type that could
# be correct.
DATA_TYPE_MAP = {
    "BOOL": "Boolean",
    "BIT": "Boolean",
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
CONFIRMED_TYPES = {"BOOL", "BIT", "DINT", "REAL", "STRING"}

# --------------------------------------------------------------------------
# Confirmed-dead member exclusions -- OPT-IN ONLY (added 2026-09-08).
#
# Keyed by the SOURCE type name as it appears in the L5X (the AOI name for
# --aoi, the DataType name for --datatype), matched case-insensitively.
# Value: {member name: why it is excluded}. Member names are matched
# case-insensitively too, and the report always prints the L5X's own
# verbatim spelling, not the spelling written here.
#
# WHAT BELONGS IN HERE, AND WHAT DOES NOT. Only a member Doug has
# explicitly confirmed is dead in the real PLC program. This table is NOT
# for:
#   * members whose PLC data type merely has no Ignition mapping -- those
#     already have a correct behavior (String placeholder + NEEDS REVIEW
#     warning) and that warning is the whole point; and
#   * members that "look unnecessary for SCADA." The 2026-09-04 scope
#     decision in the module docstring settles that: the script does not
#     get an opinion. An entry here is a record of Doug's decision, never
#     the script's.
#
# Adding an entry is therefore a documentation act as much as a code
# change -- write the reason as if the next reader has no memory of the
# conversation, because they won't. The same fact must also be recorded in
# PLCHelper_Reference.md's entry for that type (Rule 37): a member noted
# dead here and still described as live there is exactly the two-places-
# one-fact drift Lesson 9 exists to prevent.
#
# Deliberately NOT keyed by member name alone. `PID` and `DLYTMR` are dead
# in MODVLV; a member of the same name in some other type is a different
# member with a different history, and excluding it by name collision
# would be the script making a judgment call it is not entitled to make.
MEMBER_EXCLUSIONS = {
    # MODVLV -- all four confirmed dead by Doug, 2026-09-08. Each is a
    # Rockwell *structured* predefined type (PID, TIMER) that no single
    # Ignition atomic member can represent, so before confirmation they
    # were correctly emitted as String NEEDS REVIEW placeholders. Now
    # confirmed dead in the program itself, which is a stronger statement
    # than "unmappable": there is nothing to map, not merely no way to.
    "MODVLV": {
        "PID": (
            "Confirmed unused/obsolete (Doug, 2026-09-08). This valve's "
            "real PID control is a SEPARATELY DEFINED PIDE-type tag, not "
            "this embedded PID block. Doug found and fixed a live bug "
            "where PLC code referenced this obsolete embedded block "
            "instead of the correct separate PIDE tag -- so referencing "
            "this sub-element at all is the symptom, not the fix."
        ),
        "DLYTMR": (
            "Confirmed unused/legacy (Doug, 2026-09-08). TIMER member, "
            "not referenced anywhere in the current program -- leftover "
            "from example/template code that was never cleaned up."
        ),
        "FTO_TMR": (
            "Confirmed unused/legacy (Doug, 2026-09-08). TIMER member, "
            "not referenced anywhere in the current program -- leftover "
            "from example/template code that was never cleaned up."
        ),
        "FTC_TMR": (
            "Confirmed unused/legacy (Doug, 2026-09-08). TIMER member, "
            "not referenced anywhere in the current program -- leftover "
            "from example/template code that was never cleaned up."
        ),
    },
}

# Where a resolved exclusion came from, for the report. A run should make
# it obvious whether a dropped member is a standing, documented decision or
# a one-off someone typed on the command line.
EXCLUSION_ORIGIN_TABLE = "MEMBER_EXCLUSIONS"
EXCLUSION_ORIGIN_CLI = "--exclude"

CLI_EXCLUSION_DEFAULT_REASON = "no reason given on the command line"

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
# Historization rule -- Doug-supplied and confirmed 2026-09-04, extended
# 2026-09-08.
#
# A member gets History enabled if its name (case-insensitive) either:
#   (a) ends with one of the signal-type suffixes below, or is an alarm bit
#       ending in exactly "_alm" / "_alarm"; or
#   (b) IS exactly one of the bare signal-type words below, with no
#       underscore prefix at all -- a member literally named "Hwdi", "Alarm",
#       "Scai", and so on.
#
# Case (b) was added 2026-09-08, supplied by Doug after he found that
# ALARM_AOI's real PLC parameters are named with the bare signal-type word
# (members literally named "Alarm" and "Hwdi") rather than the
# underscore-suffixed convention every other AOI follows. Under the
# original suffix-only rule those members correctly received no History --
# that was not a bug, just a naming convention the rule had never seen.
# The bare form is matched EXACTLY, never as a suffix or substring: a
# member named "Alarm" matches, while "Hi_Alarm" already matched via case
# (a) and "AlarmEnable" or "PreAlarm" match neither, which is the intent.
#
# Compound alarm names (_alm_dis, _alm_ack, _alm_res, and anything else
# _alm_*) remain deliberately EXCLUDED -- they are alarm *controls*, not
# the alarm itself. Nothing else is historized; no other suffix, bare word,
# or pattern is inferred.
#
# The suffix meanings come from CLAUDE.md's "Naming conventions" table and
# are not re-derived here.
# --------------------------------------------------------------------------
ANALOG_SUFFIXES = ("_hwai", "_hwao", "_scai", "_scao")
DIGITAL_SUFFIXES = ("_hwdi", "_hwdo", "_scdi", "_scdo")
# Alarms are always Boolean at Casne (confirmed by Doug), regardless of how
# the AOI names or types the alarm parameter -- so these classify as digital.
ALARM_EXACT_SUFFIXES = ("_alm", "_alarm")

# Bare (no-underscore) forms of the same signal-type words, matched as an
# EXACT whole-name comparison rather than with str.endswith. Each bare word
# classifies identically to its underscore-suffixed counterpart above. The
# three sets are disjoint, so exact-match order never matters.
ANALOG_BARE = ("hwai", "hwao", "scai", "scao")
DIGITAL_BARE = ("hwdi", "hwdo", "scdi", "scdo")
ALARM_BARE = ("alm", "alarm")

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

    Implements the Doug-supplied historization rule verbatim, including the
    2026-09-08 bare-word extension. Two independent ways to match:

      * suffix   -- the name ENDS WITH "_hwdi", "_scao", "_alm", etc.
                    (original rule, unchanged)
      * bare word -- the name IS EXACTLY "Hwdi", "Alarm", "Scai", etc., with
                    no underscore prefix (added 2026-09-08 for ALARM_AOI)

    Matching is case-insensitive in both cases; the member's own name is
    never altered.
    """
    lowered = name.lower()
    # Suffix checks first, then the bare exact-match checks. Both are kept
    # for each signal class -- the bare form is an ADDITION to the suffix
    # rule, never a replacement for it.
    if lowered.endswith(ANALOG_SUFFIXES) or lowered in ANALOG_BARE:
        return "analog"
    if lowered.endswith(DIGITAL_SUFFIXES) or lowered in DIGITAL_BARE:
        return "digital"
    # Exactly "_alm" / "_alarm" as a suffix, or exactly "alm" / "alarm" as
    # the whole name. str.endswith already excludes every compound form
    # (_alm_dis, _alm_ack, _alm_res, _Alm_Enable, ...) because those end
    # with the trailing token, not with "_alm"; the bare check is a whole-
    # name equality test, so it cannot pick up "AlarmEnable" or "PreAlarm".
    if lowered.endswith(ALARM_EXACT_SUFFIXES) or lowered in ALARM_BARE:
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


def parse_udt_members(l5x_path, datatype_name):
    """Read a native UDT's usable member list from an L5X, in document order.

    TASK_008. The native-UDT counterpart to parse_aoi_parameters, returning
    the same dict shape so every downstream step (convention application,
    data-type mapping, historization, output) is shared code rather than a
    parallel implementation.

    Returns (members, datatype_attributes, hidden). `hidden` is the list of
    excluded Hidden="true" backing members, each as
    (name, plc_type, [names of visible BIT members aliased onto it]), kept
    so the run can report exactly what was dropped and why instead of
    dropping it silently.
    """
    try:
        root = ET.parse(l5x_path).getroot()
    except ET.ParseError as exc:
        raise SystemExit(f"ERROR: could not parse L5X as XML: {exc}")

    for datatype in root.iter("DataType"):
        if datatype.get("Name") != datatype_name:
            continue

        # Class="User" is the user-defined UDT. Predefined/module-defined
        # types are a different animal and are not in scope here.
        if datatype.get("Class") != "User":
            raise SystemExit(
                f"ERROR: DataType '{datatype_name}' has Class="
                f"'{datatype.get('Class')}', not 'User'. Only user-defined "
                f"UDTs are supported."
            )

        members_el = datatype.find("Members")
        if members_el is None:
            raise SystemExit(
                f"ERROR: DataType '{datatype_name}' has no <Members> block "
                f"in this L5X."
            )

        all_members = members_el.findall("Member")

        # Which visible BIT members alias onto which backing member. Built
        # first so an excluded hidden member can be reported together with
        # the real members it stores -- and so a hidden member that backs
        # NOTHING can be flagged rather than assumed to be bit-packing.
        aliases = collections.defaultdict(list)
        for member in all_members:
            target = member.get("Target")
            if target:
                aliases[target].append(member.get("Name"))

        members = []
        hidden = []
        for member in all_members:
            name = member.get("Name")

            # --- The exclusion. Hidden="true" members are Studio 5000's own
            # auto-generated bit-packing storage, not independent data
            # points (see the module docstring). Compared case-insensitively
            # because the attribute is a serialized boolean, not a keyword.
            if (member.get("Hidden") or "").strip().lower() == "true":
                hidden.append(
                    (name, member.get("DataType"), aliases.get(name, []))
                )
                continue

            desc_el = member.find("Description")
            description = ""
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip()

            members.append(
                {
                    # Verbatim, case preserved -- same functional requirement
                    # as the AOI path (bug pattern #2).
                    "Name": name,
                    "DataType": member.get("DataType"),
                    # A native UDT member has no Input/Output/InOut usage the
                    # way an AOI parameter does. Carried as None so the shared
                    # member dict shape stays identical.
                    "Usage": None,
                    "Required": None,
                    "Visible": None,
                    "ExternalAccess": member.get("ExternalAccess"),
                    "Dimension": member.get("Dimension"),
                    "Description": description,
                    # Bit-alias detail, kept for reporting only. Nothing
                    # downstream consumes these -- a BIT member becomes a
                    # plain Boolean Ignition member with no trace of which
                    # hidden integer happened to store it, which is correct:
                    # the packing is a PLC storage detail and has no meaning
                    # on the Ignition side.
                    "Radix": member.get("Radix"),
                    "Target": member.get("Target"),
                    "BitNumber": member.get("BitNumber"),
                }
            )

        return members, dict(datatype.attrib), hidden

    available = sorted(
        d.get("Name") for d in root.iter("DataType")
        if d.get("Class") == "User"
    )
    raise SystemExit(
        f"ERROR: user DataType '{datatype_name}' not found in {l5x_path}.\n"
        f"User DataTypes present ({len(available)}): {', '.join(available)}"
    )


def list_datatypes(l5x_path):
    """List every Class="User" DataType in the L5X. TASK_008."""
    rows = []
    for datatype in ET.parse(l5x_path).getroot().iter("DataType"):
        if datatype.get("Class") != "User":
            continue
        members_el = datatype.find("Members")
        all_members = (
            members_el.findall("Member") if members_el is not None else []
        )
        hidden = sum(
            1 for m in all_members
            if (m.get("Hidden") or "").strip().lower() == "true"
        )
        rows.append(
            (datatype.get("Name"), len(all_members) - hidden, hidden,
             datatype.get("Family") or "NoFamily")
        )
    for name, visible, hidden, family in sorted(rows):
        print(f"  {name:28} {visible:3} members "
              f"({hidden} hidden, excluded)   [{family}]")
    print(f"\n{len(rows)} user-defined DataTypes in {l5x_path}")


def resolve_exclusions(source_name, cli_excludes):
    """Build this run's exclusion set for one source type.

    Merges the standing MEMBER_EXCLUSIONS entry for `source_name` (matched
    case-insensitively) with any --exclude values given on the command
    line. Returns a dict keyed by LOWERCASED member name, each value a
    dict of {name, reason, origin} -- `name` being the spelling the
    exclusion was configured with, kept only for reporting an exclusion
    that matched nothing.

    --exclude is deliberately ADDITIVE and cannot cancel a table entry: a
    standing, documented decision should not be overridable by a
    command-line typo. A CLI value naming a member the table already
    covers keeps the table's reason, since that reason is the one someone
    took the trouble to write down.
    """
    resolved = {}

    for type_name, members in MEMBER_EXCLUSIONS.items():
        if type_name.lower() != source_name.lower():
            continue
        for member_name, reason in members.items():
            resolved[member_name.lower()] = {
                "name": member_name,
                "reason": reason,
                "origin": EXCLUSION_ORIGIN_TABLE,
            }

    for raw in cli_excludes or []:
        # NAME=reason, with the reason optional. Split on the first "=" only,
        # so a reason may itself contain "=".
        member_name, _, reason = raw.partition("=")
        member_name = member_name.strip()
        reason = reason.strip() or CLI_EXCLUSION_DEFAULT_REASON
        if not member_name:
            raise SystemExit(
                f"ERROR: --exclude {raw!r} has no member name. Expected "
                f"--exclude NAME or --exclude NAME=reason."
            )
        key = member_name.lower()
        if key in resolved:
            # Already a standing decision. Say so rather than silently
            # appearing to honor the command line's own wording.
            continue
        resolved[key] = {
            "name": member_name,
            "reason": reason,
            "origin": EXCLUSION_ORIGIN_CLI,
        }

    return resolved


def apply_exclusions(parameters, exclusions, warnings):
    """Drop excluded members from a parsed member list.

    Runs on the derived member list, downstream of BOTH parsers, so an
    exclusion behaves identically in --aoi and --datatype mode -- the same
    construction that lets the conventions and the historization rule be
    shared code rather than duplicated per mode.

    Returns (kept, dropped). `dropped` carries the L5X's own verbatim name
    and PLC data type alongside the configured reason and origin, so the
    report describes what was actually removed rather than what someone
    intended to remove.

    Appends a warning for any configured exclusion that matched no member
    at all. That is the failure mode worth catching: a typo, or a member
    renamed in the PLC since the exclusion was written, would otherwise
    look exactly like a successful run.
    """
    if not exclusions:
        return list(parameters), []

    kept = []
    dropped = []
    for parameter in parameters:
        entry = exclusions.get((parameter["Name"] or "").lower())
        if entry is None:
            kept.append(parameter)
            continue
        dropped.append(
            {
                "name": parameter["Name"],
                "plc_type": parameter["DataType"],
                "reason": entry["reason"],
                "origin": entry["origin"],
            }
        )

    matched = {d["name"].lower() for d in dropped}
    for key, entry in exclusions.items():
        if key in matched:
            continue
        warnings.append(
            f"{entry['name']}: configured for exclusion ({entry['origin']}) "
            f"but NO member of this name exists in the source -- nothing was "
            f"dropped for it. Either the name is misspelled or the member was "
            f"renamed/removed in the PLC. Confirm which, rather than assuming "
            f"the exclusion worked."
        )

    return kept, dropped


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
                f"{name}: name classifies as {signal} by the naming rule, "
                f"but its "
                f"data type is '{ignition_type}' ({plc_type} in the PLC). "
                f"History was still applied per the naming rule -- the rule "
                f"is name-based -- but this disagreement is worth a look."
            )

    return member, signal


def main():
    parser = argparse.ArgumentParser(
        description="Generate an Ignition UDT definition JSON from a PLC AOI "
                    "(TASK_004) or a native PLC UDT (TASK_008). Includes "
                    "EVERY AOI parameter / every visible UDT member as a "
                    "member, except any member explicitly opted out via the "
                    "MEMBER_EXCLUSIONS table or --exclude -- every exclusion "
                    "is printed in the report, never applied silently.",
    )
    # --aoi and --datatype are the two mutually exclusive source modes. Every
    # step after the member list is read is shared between them.
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--aoi", help="AOI type name, e.g. FLOWIN3_AOI")
    source.add_argument("--datatype", help="Native user DataType (UDT) name, "
                                          "e.g. MODVLV")
    parser.add_argument("--l5x", required=True, help="Path to the L5X export")
    parser.add_argument("--reference", help="Path to a reference Ignition UDT "
                                           "definition JSON export")
    parser.add_argument("--output", help="Path for the generated UDT JSON")
    parser.add_argument("--udt-name", help="Name for the generated UDT type "
                                          "(defaults to the AOI or DataType "
                                          "name)")
    parser.add_argument("--list-aois", action="store_true",
                        help="List every AOI type in the L5X and exit")
    parser.add_argument("--list-datatypes", action="store_true",
                        help="List every native user DataType in the L5X "
                             "and exit")
    # Repeatable, per argparse's documented 'append' action. Additive to
    # MEMBER_EXCLUSIONS and unable to cancel it -- see resolve_exclusions.
    parser.add_argument("--exclude", action="append", metavar="NAME[=reason]",
                        help="Drop one member from the generated UDT for "
                             "this run only. Repeatable. Additive to the "
                             "standing MEMBER_EXCLUSIONS table; it cannot "
                             "cancel a standing exclusion. Every exclusion "
                             "is printed in the report.")
    args = parser.parse_args()

    if args.list_aois:
        list_aois(args.l5x)
        return 0

    if args.list_datatypes:
        list_datatypes(args.l5x)
        return 0

    if not args.aoi and not args.datatype:
        parser.error("missing required argument: --aoi or --datatype")

    missing = [
        flag for flag, value in
        (("--reference", args.reference), ("--output", args.output))
        if not value
    ]
    if missing:
        parser.error(f"missing required argument(s): {', '.join(missing)}")

    source_name = args.aoi or args.datatype
    udt_name = args.udt_name or source_name
    hidden = []
    # Collected from step 1 onward now, because the exclusion mechanism can
    # raise a warning (a configured exclusion that matched nothing) before
    # any member is built.
    warnings = []

    if args.aoi:
        print(f"TASK_004 -- Generate Ignition UDT definition")
        print(f"{'=' * 68}")
        print(f"AOI type    : {args.aoi}")
    else:
        print(f"TASK_008 -- Generate Ignition UDT definition "
              f"(native PLC UDT source)")
        print(f"{'=' * 68}")
        print(f"DataType    : {args.datatype}")
    print(f"L5X         : {args.l5x}")
    print(f"Reference   : {args.reference}")
    print(f"Output UDT  : {udt_name}")
    print()

    # --- Step 1: the source's real member list, straight from the L5X.
    #
    # Resolved before parsing only so the header line can state honestly
    # whether "ALL" members are becoming members on this run. Nothing is
    # filtered until after the parse, and the filtering itself is shared
    # between both modes below.
    exclusions = resolve_exclusions(source_name, args.exclude)
    all_claim = ("ALL will become members" if not exclusions
                 else "before exclusions -- see below")

    if args.aoi:
        parameters, aoi_attrs = parse_aoi_parameters(args.l5x, args.aoi)
        print(f"AOI found: revision {aoi_attrs.get('Revision')}, "
              f"{len(parameters)} parameters ({all_claim})")
    else:
        parameters, dt_attrs, hidden = parse_udt_members(
            args.l5x, args.datatype)
        print(f"User DataType found: family "
              f"{dt_attrs.get('Family')}, {len(parameters)} visible members "
              f"({all_claim})")
        if hidden:
            print(f"  excluded {len(hidden)} hidden backing member(s) -- "
                  f"Studio 5000 bit-packing storage, not data points:")
            for name, plc_type, backed in hidden:
                print(f"    {name} ({plc_type}) stores "
                      f"{len(backed)} visible bit(s)"
                      + (f": {', '.join(backed)}" if backed else ""))
        else:
            print(f"  no hidden backing members present -- nothing excluded")

    # --- Confirmed-dead member exclusions. Shared by both modes on purpose:
    # this runs on the parsed member list, not inside either parser.
    parameters, dropped = apply_exclusions(parameters, exclusions, warnings)
    if dropped:
        print(f"  excluded {len(dropped)} confirmed-dead member(s) by "
              f"explicit opt-in -- NOT a judgment call by this script:")
        for entry in dropped:
            print(f"    {entry['name']} ({entry['plc_type']}) "
                  f"[{entry['origin']}]")
            print(f"      reason: {entry['reason']}")
    elif exclusions:
        print(f"  {len(exclusions)} exclusion(s) configured but none matched "
              f"a member of this type -- see warnings below")

    if args.aoi:
        usage_counts = collections.Counter(p["Usage"] for p in parameters)
        print(f"  by usage: " + ", ".join(
            f"{u}={c}" for u, c in sorted(usage_counts.items())))
    type_counts = collections.Counter(p["DataType"] for p in parameters)
    print(f"  by type : " + ", ".join(
        f"{t}={c}" for t, c in sorted(type_counts.items())))
    if dropped:
        print(f"  final   : {len(parameters)} member(s) will be generated")
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

    # --- Step 3/4: build one member per parameter. Every parameter that
    # survived the exclusions above (which is all of them unless a member
    # was explicitly opted out).
    #
    # `warnings` was opened before step 1 -- the exclusion mechanism can
    # already have added to it.

    # A hidden member that backs no visible BIT member is not the bit-packing
    # pattern the exclusion was written for. Surface it instead of assuming
    # every Hidden="true" member is safely droppable storage.
    for name, plc_type, backed in hidden:
        if not backed:
            warnings.append(
                f"{name}: hidden member ({plc_type}) was excluded, but no "
                f"visible BIT member aliases onto it -- so it is NOT the "
                f"bit-packing storage pattern this exclusion targets. "
                f"Confirm it is genuinely not a needed data point."
            )

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
    # Repeated at the end as well as at step 1: this report is long, and a
    # dropped member must not be something a reader has to scroll back for.
    if dropped:
        print(f"  {len(dropped)} member(s) deliberately excluded and NOT in "
              f"this file: "
              f"{', '.join(entry['name'] for entry in dropped)}")

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
