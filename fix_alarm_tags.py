#!/usr/bin/env python3
"""
TASK_010 -- Apply the corrections TASK_009's audit flags.

Read an Ignition Tag Export of one site's `Alarms` folder, correct every
field named by TASK_009's rules 2-9, and write a BRAND-NEW corrected export
JSON. The input file is never modified. Rule 1 (`notes`) is never
auto-fixed.

This is the companion to `audit_alarm_tags.py` (TASK_009), kept as a
separate tool on Doug's explicit design: "there will be one scanning tool
that just gives me a report of problems with alarms, and then another tool
that will fix those problems." The scanner had to be trustworthy on its own
before anything started changing tags.

THE TWO TOOLS SHARE ONE DEFINITION OF "CORRECT," IN CODE, NOT IN PROSE.
This module deliberately declares NONE of the correctness tables. It
imports `audit_alarm_tags` and reads SITE_PIPELINES, FOLDER_PRIORITIES,
REQUIRED_HISTORY_PROPERTIES, EXTRANEOUS_HISTORY_KEYS, CUSTOM_EMAIL_KEYS,
is_blank() and collect_tags() straight off it. A second copy of those
tables in this file could drift out of step with the audit's, and that
failure is silent: a fix tool that "corrects" a tag to a value the audit
then flags, or that agrees with a stale rule nobody remembers changing.
The audit and the fix tool must never be able to quietly disagree.
Consequence worth knowing: adding a site to SITE_PIPELINES or changing a
folder's required priority is a one-file edit that both tools pick up.

RULE 1 (`notes`) IS NEVER AUTO-FIXED. A blank `notes` needs a human-written
description of what that alarm actually means -- it is the text the
pipeline's default email template surfaces. Inventing it would be worse
than the blank it replaced, so the field is left exactly as found and
flagged in the report for Doug. This is the one rule with no fix.

AN UNVERIFIABLE FIELD IS LEFT ALONE, NEVER GUESSED. If the site is not in
SITE_PIPELINES, or the tag's folder is not in that site's entry,
`activePipeline` is NOT written -- the run reports CANNOT VERIFY and leaves
the existing value in place, mirroring the audit's own handling. Same for
`priority` against FOLDER_PRIORITIES. Writing a guessed pipeline name would
point a live alarm at a pipeline nobody confirmed exists, which is the
exact class of fault this pair of tools was built to find.

REWRITING A FIELD TO THE VALUE IT ALREADY HOLDS IS NOT A CHANGE. The
correct value is computed unconditionally for every field in scope -- that
is what "rule 5 always overwrites regardless of current value" means -- but
a change is recorded only where the value actually moved, the key was
absent, or the key was removed. That is what makes the change count
directly comparable to the audit's problem count (Weston: 367 = 367).

NOTHING OUTSIDE RULES 2-9 IS EVER WRITTEN, AND THE SCRIPT PROVES IT RATHER
THAN ASSERTING IT. A deep copy of the parsed input is kept, structurally
diffed against the corrected tree at the end, and the run ABORTS with a
non-zero exit code if that diff contains a single field not deliberately
recorded as a change. Every other key on every tag and alarm --
`opcItemPath`, `opcServer`, `valueSource`, `dataType`, `value`, `label`,
`mode`, `setpointA`, `timeOnDelaySeconds`, `voip.customMessage`,
`CustomSmsMessage`, `notes` -- comes through untouched, as does every tag
with no violations at all. A silent extra edit is not a possible outcome.

FORMATTING NOTE: output is written with `json.dump(..., indent=2,
sort_keys=True)`, matching `generate_ignition_udt.py`. Key order in the
output is therefore canonical (sorted), not the input's original order. The
*data* outside the corrected fields is identical -- that is what the
structural diff verifies -- and Ignition's importer does not care about key
order.

*** IMPORT THE OUTPUT WITH COLLISION POLICY `Overwrite`, NOT
`MergeOverwrite`. *** Verified 2026-09-09 against the official docs and an
Inductive Automation staff post (sources logged in
`claude-workflow/TRUSTED_SOURCES.md`). Rule 9b works by REMOVING
`sampleMode`/`historyMaxAge`/`historyMaxAgeUnits`, because a tag export
omits any property sitting at Ignition's default -- absence in the file is
how "use the default" is expressed. But `MergeOverwrite` treats a missing
key as "leave that property alone" (IA staff, Paul Griffith:
"MergeOverwrite means keep the existing values in the property set, unless
there's a conflict"), so importing this output under `MergeOverwrite`
applies every value change and SILENTLY KEEPS the three overridden history
properties. Only `Overwrite` -- "a complete overwrite of the tag" --
clears them.

This is the opposite of CLAUDE.md's UDT-definition guidance, and both are
correct; do not "fix" either to match the other. That guidance
(`MergeOverwrite`, never delete or rename first) is about replacing a UDT
*definition that has live instances*, where the risk is destroying member
IDs and losing per-instance overrides. This is a folder of plain alarm tags
with no definition and no instances, where removing overrides is the entire
point.

THE CORRECTED FILE IS ONLY AS CURRENT AS THE EXPORT IT WAS BUILT FROM.
Weston's export predates Doug's live `_Test500` correction, so it still
carries that tag's old email override. Re-export from the gateway before
importing a corrected file, or the import carries other since-changed
values backwards too.

CONFIDENTIALITY: the alarm export lives in the job's own project folder
(e.g. `CPKCR-Weston/`) and is read cross-folder by path; the corrected file
is written back beside it. Neither is ever copied into PLCHelper --
PLCHelper is a git repo that gets pushed to GitHub, and a site's alarm
export is client-confidential. See CLAUDE.md.

Usage:
    python fix_alarm_tags.py \
        --input "<path to job folder>/Weston Alarms tags.json" \
        --site Weston
"""

import argparse
import copy
import json
import os
import sys

# The audit is the single source of truth for what "correct" means. See the
# module docstring -- nothing from these tables is re-declared here.
import audit_alarm_tags as audit


# Marker for "this key was not present," so an absent key is reported as
# `(absent)` rather than as a value someone set to None -- the same
# distinction the audit's report wording makes, for the same reason: an
# export omits a property sitting at its default, so absent and wrong are
# different faults with different fixes.
class _Missing:
    def __repr__(self):
        return "(absent)"


MISSING = _Missing()


# Marker for a key this tool deletes outright (rule 9b). Distinct from
# MISSING so the report can say `-> (removed)` and the fidelity check can
# tell a deletion apart from a value write.
class _Removed:
    def __repr__(self):
        return "(removed)"


REMOVED = _Removed()


def describe(value):
    """Format an old/new value for one report line."""
    if isinstance(value, (_Missing, _Removed)):
        return repr(value)
    return repr(value)


def set_field(container, key, new_value, changes, scope, path):
    """Write one field, recording a change only if something actually moved.

    `container` is the tag dict or the alarm dict. `path` is the dotted
    label used in the report (e.g. "alarm.activePipeline"). Returns True if
    a change was recorded.
    """
    old_value = container[key] if key in container else MISSING
    container[key] = new_value
    if isinstance(old_value, _Missing) or old_value != new_value:
        changes.append({
            "scope": scope,
            "path": path,
            "key": key,
            "old": old_value,
            "new": new_value,
        })
        return True
    return False


def remove_field(container, key, changes, scope, path):
    """Delete one key entirely (rule 9b), recording a change if it existed."""
    if key in container:
        old_value = container[key]
        del container[key]
        changes.append({
            "scope": scope,
            "path": path,
            "key": key,
            "old": old_value,
            "new": REMOVED,
        })
        return True
    return False


def fix_alarm(tag, alarm, folders, site, pipelines, unverified_site,
              changes, flags):
    """Apply rules 2-5 and 7-8 to one alarm. Rule 1 is deliberately absent."""
    tag_name = tag.get("name")
    folder_name = folders[-1] if folders else None
    alarm_label = alarm.get("name")

    # --- Rule 1: notes. NOT FIXED, BY DESIGN. Only flagged, never written.
    # See the module docstring -- a blank notes needs Doug's own words.
    if audit.is_blank(alarm.get("notes")):
        flags.append(
            f"{tag_name}: alarm {alarm_label!r} has blank `notes` -- LEFT "
            f"UNCHANGED. Rule 1 is never auto-fixed; this needs a "
            f"human-written description of what the alarm means, since the "
            f"pipeline's default email template surfaces this text."
        )

    # --- Rule 2: activePipeline -> the confirmed pipeline for this folder.
    # Never guessed: an unverifiable pipeline is left exactly as found.
    if unverified_site:
        flags.append(
            f"{tag_name}: alarm {alarm_label!r} `activePipeline` is "
            f"{alarm.get('activePipeline')!r} -- CANNOT VERIFY, LEFT "
            f"UNCHANGED: site {site!r} has no confirmed pipeline list in "
            f"audit_alarm_tags.SITE_PIPELINES. Confirm this site's pipelines "
            f"in Designer and add them there before fixing this field."
        )
    elif folder_name not in pipelines:
        flags.append(
            f"{tag_name}: alarm {alarm_label!r} `activePipeline` is "
            f"{alarm.get('activePipeline')!r} -- CANNOT VERIFY, LEFT "
            f"UNCHANGED: folder {folder_name!r} is not in the confirmed "
            f"pipeline table for site {site!r}."
        )
    else:
        set_field(alarm, "activePipeline", pipelines[folder_name],
                  changes, "alarm", "activePipeline")

    # --- Rule 3: both custom email overrides -> blank, so the pipeline's
    # own template is used. This is the fault that started the whole task.
    for key in audit.CUSTOM_EMAIL_KEYS:
        set_field(alarm, key, "", changes, "alarm", key)

    # --- Rule 4: enabled -> true. The ALARM's enabled, matching the audit;
    # a tag-level `enabled` is not in scope and is left untouched.
    set_field(alarm, "enabled", True, changes, "alarm", "enabled")

    # --- Rule 5: priority -> the folder's required value, ALWAYS written
    # regardless of what is there now (Doug: "they need to match the rule").
    # Only an unconfirmed folder is exempt, and then it is left alone.
    if folder_name not in audit.FOLDER_PRIORITIES:
        flags.append(
            f"{tag_name}: alarm {alarm_label!r} `priority` is "
            f"{alarm.get('priority')!r} -- CANNOT VERIFY, LEFT UNCHANGED: "
            f"folder {folder_name!r} has no confirmed required priority in "
            f"audit_alarm_tags.FOLDER_PRIORITIES."
        )
    else:
        set_field(alarm, "priority", audit.FOLDER_PRIORITIES[folder_name],
                  changes, "alarm", "priority")

    # --- Rule 7: the alarm's own name -> its parent tag's name.
    set_field(alarm, "name", tag_name, changes, "alarm", "name")

    # --- Rule 8: displayPath -> the reconstructed correct full path. Built
    # from the tag's real tree position, exactly as the audit builds the
    # expected value it compares against.
    expected_display_path = "/".join(
        [site] + [f for f in folders if f] + [str(tag_name)])
    set_field(alarm, "displayPath", expected_display_path,
              changes, "alarm", "displayPath")


def fix_tag_groups(tag, site, changes):
    """Apply rule 6 -- tagGroup and historyTagGroup -> the site name.

    Tag-level, not alarm-level, so this runs once per tag no matter how many
    alarms sit on it. Catches copy-paste artifacts like a Weston alarm
    carrying `tagGroup: "MasonCity"`.
    """
    for key in ("tagGroup", "historyTagGroup"):
        set_field(tag, key, site, changes, "tag", key)


def fix_tag_history(tag, changes):
    """Apply rule 9 -- historian configuration. Tag-level, once per tag."""
    # 9a -- the three required properties, written to their exact values.
    for key, expected in audit.REQUIRED_HISTORY_PROPERTIES.items():
        set_field(tag, key, expected, changes, "tag", key)

    # 9b -- the three keys that must not be present AT ALL. Removed, not set
    # to a value: an export omits a property sitting at Ignition's default,
    # so absence is how "use the default" is expressed. This is the half
    # that needs Collision Policy `Overwrite` on import -- see the docstring.
    for key in audit.EXTRANEOUS_HISTORY_KEYS:
        remove_field(tag, key, changes, "tag", key)


def fix_tag(folders, tag, site, pipelines, unverified_site, flags):
    """Correct one tag and every alarm on it. Returns its change records."""
    changes = []
    alarms = tag.get("alarms") or []

    # Mirrors the audit's own defensive case: a tag in an Alarms folder with
    # no alarm on it cannot have rules 2-8 applied. Rule 9 is tag-level and
    # still applies. None exist in Weston's export; this reports itself if
    # it ever fires rather than passing silently.
    if not alarms:
        flags.append(
            f"{tag.get('name')}: tag has no alarms configured -- none of the "
            f"alarm-level fixes (rules 2-5, 7-8) could be applied. Confirm "
            f"this tag belongs in the Alarms folder."
        )

    for alarm in alarms:
        fix_alarm(tag, alarm, folders, site, pipelines, unverified_site,
                  changes, flags)

    # Rules 6 and 9 last and in that order, so a tag's change list reads in
    # rule order. Both are tag-level, which is why they sit outside the
    # per-alarm loop above.
    fix_tag_groups(tag, site, changes)
    fix_tag_history(tag, changes)
    return changes


def diff_json(original, corrected, path="$"):
    """Every leaf-level difference between two parsed JSON trees.

    Returns a list of (path, old, new) with MISSING/REMOVED markers for keys
    that appear or disappear. Used only by the fidelity check below -- this
    is how "nothing outside rules 2-9 was written" is proven rather than
    asserted.
    """
    diffs = []
    if isinstance(original, dict) and isinstance(corrected, dict):
        for key in sorted(set(original) | set(corrected)):
            child = f"{path}.{key}"
            if key not in corrected:
                diffs.append((child, original[key], REMOVED))
            elif key not in original:
                diffs.append((child, MISSING, corrected[key]))
            else:
                diffs.extend(diff_json(original[key], corrected[key], child))
    elif isinstance(original, list) and isinstance(corrected, list):
        if len(original) != len(corrected):
            # A changed list length is a structural edit this tool never
            # makes -- it would mean a tag or an alarm was added or dropped.
            diffs.append((f"{path}[]", f"{len(original)} item(s)",
                          f"{len(corrected)} item(s)"))
        else:
            for index, (a, b) in enumerate(zip(original, corrected)):
                diffs.extend(diff_json(a, b, f"{path}[{index}]"))
    elif original != corrected or type(original) is not type(corrected):
        diffs.append((path, original, corrected))
    return diffs


def verify_fidelity(original, corrected, changes):
    """Confirm the output differs from the input ONLY in recorded changes.

    Returns a list of unexplained differences. A non-empty result means the
    script edited something it did not declare, and the run must fail --
    "everything else comes out identical" is a guarantee, not an intention.
    Compared by (key, old, new) triples rather than by path, because the
    change records are per-tag and do not carry the full JSON pointer.
    """
    declared = {}
    for change in changes:
        signature = (change["key"], describe(change["old"]),
                     describe(change["new"]))
        declared[signature] = declared.get(signature, 0) + 1

    unexplained = []
    for path, old, new in diff_json(original, corrected):
        key = path.rsplit(".", 1)[-1]
        signature = (key, describe(old), describe(new))
        if declared.get(signature):
            declared[signature] -= 1
        else:
            unexplained.append((path, old, new))
    return unexplained


def default_output_path(input_path):
    """`<input without extension> - CORRECTED.json`, beside the input."""
    stem, _ = os.path.splitext(input_path)
    return f"{stem} - CORRECTED.json"


def main():
    parser = argparse.ArgumentParser(
        description="Apply TASK_009's flagged corrections to an Ignition "
                    "alarm tag export, writing a brand-new corrected JSON. "
                    "The input file is never modified. Rule 1 (`notes`) is "
                    "never auto-fixed -- a blank one is flagged for manual "
                    "attention instead. Correctness comes from "
                    "audit_alarm_tags.py's own tables, imported directly, so "
                    "the audit and this tool cannot disagree.",
    )
    parser.add_argument("--input", required=True,
                        help="Path to the Ignition tag export JSON of the "
                             "site's Alarms folder. Read-only.")
    parser.add_argument("--site", required=True,
                        help="Site name being corrected, e.g. Weston. Selects "
                             "the confirmed pipeline list from "
                             "audit_alarm_tags.SITE_PIPELINES and is the "
                             "value written to tagGroup/historyTagGroup and "
                             "the leading segment of every displayPath")
    parser.add_argument("--output",
                        help="Path for the corrected JSON. Defaults to "
                             "'<input without extension> - CORRECTED.json' "
                             "in the same directory as the input.")
    args = parser.parse_args()

    site = args.site
    pipelines = audit.SITE_PIPELINES.get(site, {})
    unverified_site = site not in audit.SITE_PIPELINES
    output_path = args.output or default_output_path(args.input)

    print(f"TASK_010 -- Fix Ignition alarm tag configuration")
    print(f"{'=' * 68}")
    print(f"Input       : {args.input}")
    print(f"Output      : {output_path}")
    print(f"Site        : {site}")
    if unverified_site:
        print(f"Pipelines   : *** NONE CONFIRMED for this site ***")
    else:
        print(f"Pipelines   : " + ", ".join(
            f"{folder}={name!r}" for folder, name in sorted(pipelines.items())))
    print(f"Rules fixed : 2-9 (rule 1 `notes` is never auto-fixed)")
    print(f"Correctness : imported from audit_alarm_tags.py -- one shared "
          f"definition")
    print()

    # Refuse to write over the input. The whole point of a separate output
    # file is that the original export stays available to re-run or diff
    # against; silently clobbering it would destroy the only pre-fix copy.
    if os.path.exists(args.input) and os.path.exists(output_path) and \
            os.path.samefile(args.input, output_path):
        print(f"*** REFUSING TO RUN: the output path is the same file as the "
              f"input.")
        print(f"    This tool never writes to its own input. Choose a "
              f"different --output.")
        return 1
    if os.path.abspath(args.input) == os.path.abspath(output_path):
        print(f"*** REFUSING TO RUN: --output resolves to the same path as "
              f"--input.")
        print(f"    This tool never writes to its own input. Choose a "
              f"different --output.")
        return 1

    if unverified_site:
        print(f"*** WARNING: site {site!r} is not in SITE_PIPELINES, so rule "
              f"2 (activePipeline) CANNOT be fixed.")
        print(f"    Every activePipeline is left exactly as found and listed "
              f"below -- a pipeline name is never guessed.")
        print(f"    Sites are NOT assumed uniform: Weston's pipeline names "
              f"are not evidence for any other site's.")
        print(f"    Every other rule is still applied. Confirm this site's "
              f"pipelines in Designer and add them to")
        print(f"    audit_alarm_tags.SITE_PIPELINES, then re-run.")
        print()

    with open(args.input, encoding="utf-8") as handle:
        export = json.load(handle)

    # The untouched reference the fidelity check compares against. Taken
    # before a single field is written.
    original = copy.deepcopy(export)

    flags = []
    all_changes = []
    per_tag = []
    total = 0
    for folders, tag in audit.collect_tags(export, []):
        total += 1
        changes = fix_tag(folders, tag, site, pipelines, unverified_site,
                          flags)
        if changes:
            per_tag.append((str(tag.get("name")), changes))
            all_changes.extend(changes)

    # Sorted alphabetically by tag name, matching TASK_009's report order so
    # the two can be read side by side.
    per_tag.sort(key=lambda entry: entry[0])
    flags.sort()

    # --- The fidelity check, before anything is written. An undeclared edit
    # means this tool has a bug, and the right outcome is no output file at
    # all rather than a corrupted one Doug might import.
    unexplained = verify_fidelity(original, export, all_changes)
    if unexplained:
        print(f"*** ABORTED: {len(unexplained)} difference(s) between input "
              f"and corrected output were NOT declared as changes.")
        print(f"    This is a bug in this script -- it edited something "
              f"outside rules 2-9. No output file was written.")
        for path, old, new in unexplained[:20]:
            print(f"    {path}: {describe(old)} -> {describe(new)}")
        if len(unexplained) > 20:
            print(f"    ... and {len(unexplained) - 20} more")
        return 1

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(export, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"Scanned {total} tag(s): {len(per_tag)} changed, "
          f"{total - len(per_tag)} already correct "
          f"({len(all_changes)} field(s) changed in total)")
    print()

    if per_tag:
        print(f"Changes applied, alphabetically by tag name:")
        print(f"{'-' * 68}")
        for tag_name, changes in per_tag:
            print(f"{tag_name}")
            for change in changes:
                print(f"  - {change['scope']}.{change['path']}: "
                      f"{describe(change['old'])} -> "
                      f"{describe(change['new'])}")
        print()
    else:
        print(f"No changes needed -- every tag already satisfies rules 2-9.")
        print()

    # Per-kind tally, deliberately the same shape as the audit's "Problems
    # by kind". Read side by side, the two answer the question neither can
    # alone: did every problem the audit found actually get a fix?
    print(f"Changes by kind:")
    tally = {}
    for change in all_changes:
        kind = f"{change['scope']}.{change['path']}"
        if isinstance(change["new"], _Removed):
            kind += " (removed)"
        tally[kind] = tally.get(kind, 0) + 1
    if tally:
        width = max(len(kind) for kind in tally)
        for kind, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {kind.ljust(width)}  {count}")
    else:
        print(f"  (none)")

    if flags:
        print()
        print(f"{len(flags)} item(s) NEEDING DOUG'S MANUAL ATTENTION "
              f"(left unchanged):")
        print(f"{'-' * 68}")
        for flag in flags:
            print(f"  - {flag}")

    print()
    print(f"Fidelity check: PASSED -- the output differs from the input in "
          f"exactly the {len(all_changes)} field(s)")
    print(f"                reported above and nowhere else. Every other "
          f"key on every tag, and every")
    print(f"                unchanged tag, is identical. Input file not "
          f"modified.")

    print()
    print(f"Wrote {output_path}")
    print()
    print(f"*** IMPORT WITH COLLISION POLICY `Overwrite`, NOT "
          f"`MergeOverwrite`. ***")
    print(f"    Rule 9 works by REMOVING sampleMode/historyMaxAge/"
          f"historyMaxAgeUnits, and `MergeOverwrite`")
    print(f"    treats a missing key as \"leave that property alone\" -- it "
          f"would apply every value change")
    print(f"    above and silently keep those overrides. Only `Overwrite` "
          f"clears them.")
    print()
    print(f"Next steps:")
    print(f"  1. Re-run audit_alarm_tags.py against the OUTPUT file to "
          f"confirm 0 problems.")
    print(f"  2. Re-export from the gateway if this export is stale -- the "
          f"corrected file is only as")
    print(f"     current as the export it was built from, and importing a "
          f"stale one carries other")
    print(f"     since-changed values backwards.")
    print(f"  3. Import into Ignition with Collision Policy `Overwrite`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
