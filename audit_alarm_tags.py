#!/usr/bin/env python3
"""
TASK_009 -- Audit Ignition alarm tag configuration for formatting problems.

Read an Ignition Tag Export of one site's `Alarms` folder and check every
alarm in it against the eight correctness rules confirmed in
PLCHelper_Tasks.md TASK_009. Report-only: this script never writes to the
export, never emits a corrected file, and never touches a gateway.
Applying the fixes is deliberately a separate tool (TASK_010), so that the
scanner can be trusted on its own before anything starts changing tags.

WHY THIS EXISTS: CPKCR-Weston ticket CS0175981 (`AlmLIT107_HiHi_Alm`) was
traced to a `CustomEmailSubject`/`CustomEmailMessage` override that every
other site on the shared alarm-notification system leaves blank -- Weston's
override replaced the pipeline's own better default with a generic,
site-less email. The same investigation found 56 of Weston's 800-series
alarms pointing at `activePipeline: "Site Pipelines/Weston"`, a pipeline
Doug confirmed does not exist, meaning those alarms likely notify nobody at
all. Both are configuration-formatting faults that are invisible until an
alarm actually fires, which is exactly what a static audit can catch first.

THE EIGHT RULES (spec: PLCHelper_Tasks.md TASK_009 "Process"):
  1. `notes` non-blank -- this is what the pipeline's default template
     surfaces, so a blank one produces a contentless notification.
  2. `activePipeline` matches the tag's own site/folder, against the
     SITE_PIPELINES table below. A tag under `.../500/` must reference that
     site's `_500` pipeline, not `_800`. The offending value is always
     printed by name so a known-bad one is recognizable on sight.
  3. `CustomEmailSubject` and `CustomEmailMessage` both blank -- non-blank
     overrides the pipeline's own template. Doug's confirmed fix direction.
  4. `enabled` is `true`.
  5. `priority` present and non-blank.
  6. `tagGroup` and `historyTagGroup` match the site being audited --
     catches copy-paste artifacts like a Weston alarm carrying
     `tagGroup: "MasonCity"`.
  7. The alarm's own `name` matches its parent tag's `name`.
  8. `displayPath` exactly matches the tag's real position in the tree,
     reconstructed as `<Site>/Alarms/<folder>/<tagname>`.

NO EXEMPTIONS, INCLUDING TEST TAGS (Doug-confirmed 2026-09-09): rules 1-8
apply uniformly to every tag in the export, `_Test*`/`Test*` included. Test
tags are triggered manually to validate real notification behavior, so a
test tag configured differently from the real alarms it stands in for is
worse than useless -- it validates the wrong thing.

RULE 8 IS AN EXACT MATCH, NOT A SUFFIX CHECK (broadened 2026-09-09): the
rule originally read "last segment matches the tag name," which passed
`[default]Weston/Alarms/800/_Test800` -- the provider-prefix inconsistency
found on `_Test500`, `_Test800`, and `CP_6000_PLC_Comm_Loss_Alm` -- because
only the trailing segment was ever compared. The expected path is therefore
rebuilt from the tag's real tree position and compared literally.

A BLANK `displayPath` IS REPORTED DISTINCTLY FROM A WRONG ONE (verified
against the docs and forum -- sources logged in
`claude-workflow/TRUSTED_SOURCES.md`, "Alarm Event Properties Reference"
and the blank-Display-Path forum entry): Ignition treats a blank Display
Path as "use the
default," and the Alarm Status page then shows the tag's own source path.
So a blank value is not the same kind of fault as a wrong explicit value.
It still fails rule 8 -- the rule requires a full match and blank is not a
match, and the site's own convention is an explicit path on 140 of 143 tags
-- but the problem line says so in as many words rather than implying
someone typed the path wrong.

PRIORITY 0 IS A VALID PRIORITY (verified, same sources): the docs
document `priority` as Integer or String with Diagnostic = 0, Low = 1,
Medium = 2, High = 3, Critical = 4. A plain truthiness test on this field
would flag `priority: 0` -- a legitimately configured Diagnostic alarm --
as missing, so rule 5 tests for presence and blankness specifically.

ABSENT KEYS ARE REPORTED AS ABSENT, NOT AS WRONG VALUES: an Ignition tag
export omits a property sitting at its default rather than writing the
default out, so `enabled` absent means "true, by default" and `tagGroup`
absent means "the Default tag group." Those are still rule failures (rule 6
wants the site name, and Doug wants a missing `enabled` surfaced -- it was
one of the expected findings on `_Test500`/`_Test800`), but the report says
"absent" so nobody reads it as a value that was set incorrectly.

CONFIDENTIALITY: the alarm export lives in the job's own project folder
(e.g. `CPKCR-Weston/`) and is read cross-folder by path. It is never copied
into PLCHelper -- PLCHelper is a git repo that gets pushed to GitHub, and a
site's alarm export is client-confidential. See CLAUDE.md.

Usage:
    python audit_alarm_tags.py \
        --input "<path to job folder>/Weston Alarms tags.json" \
        --site Weston
"""

import argparse
import json
import sys

# Known-valid alarm notification pipelines, keyed by site name, then by the
# tag's own folder name inside that site's `Alarms` tree.
#
# THIS TABLE IS NOT DERIVABLE FROM A TAG EXPORT and is never guessed. A tag
# export states which pipeline each alarm *points at*, which is precisely the
# thing under audit -- it cannot also be the authority on which pipelines
# exist. Every entry here is a value Doug confirmed against the live gateway.
#
# ONLY WESTON IS CONFIRMED. Sites are NOT assumed uniform -- that caution is
# Doug's own and it has already paid off: `All Alarms tags.json` (8 sites, 921
# alarms) shows StLuc carrying `activePipeline: "WWHMPWTP2/StLuc"`, a
# genuinely separate and unsynchronized Ignition installation on Gateway 2,
# not the `WWHMPWWT1` gateway every Weston pipeline lives on. Adding a site
# here means someone verified that site's pipelines in Designer, one site at a
# time. An unlisted site is reported as unverifiable, never assumed to follow
# Weston's naming.
SITE_PIPELINES = {
    "Weston": {
        "500": "WWHMPWWT1/Weston_500",
        "800": "WWHMPWWT1/Weston_800",
    },
    # "Golden":   NOT YET CONFIRMED -- do not populate from a tag export.
    # "MasonCity": NOT YET CONFIRMED
    # "MooseJaw":  NOT YET CONFIRMED
    # "Nahant":    NOT YET CONFIRMED
    # "PoCo":      NOT YET CONFIRMED
    # "StLuc":     NOT YET CONFIRMED -- see the Gateway 2 note above.
    # "StPaul":    NOT YET CONFIRMED
}

# The two alarm properties that must be blank (rule 3). Named here rather
# than inline so the pair stays a pair -- the fault is that Weston overrides
# the pipeline template at all, and it takes both fields to do it.
CUSTOM_EMAIL_KEYS = ("CustomEmailSubject", "CustomEmailMessage")


def is_blank(value):
    """True if an alarm property is absent or holds only whitespace.

    A number is never blank -- `priority: 0` is Diagnostic, a real
    configured priority, and must not be mistaken for an unset field.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def collect_tags(node, folders):
    """Walk the export tree and yield (folder_segments, tag_dict) pairs.

    `folders` is the path of folder names from the export root down to (but
    not including) the tag -- for Weston's export that is ["Alarms", "800"],
    which is exactly what rule 8's expected path is rebuilt from.
    """
    if node.get("tagType") == "Folder":
        for child in node.get("tags") or []:
            yield from collect_tags(child, folders + [node.get("name")])
    else:
        yield folders, node


def audit_alarm(tag, alarm, folders, site, pipelines, unverified_site):
    """Check one alarm against rules 1-8. Returns a list of problem strings.

    One string per problem, phrased to stand alone on its own line in the
    report -- a reader should not need the rule number or the surrounding
    lines to know what is wrong or what the right value would have been.
    """
    problems = []
    tag_name = tag.get("name")

    # --- Rule 1: notes non-blank.
    if is_blank(alarm.get("notes")):
        problems.append(
            "notes is blank -- the pipeline's default email template "
            "surfaces this text, so the notification carries no description"
        )

    # --- Rule 2: activePipeline matches the tag's own site/folder.
    #
    # The folder name is the last segment of the tag's folder path (the "500"
    # or "800" in Alarms/500). A folder absent from the site's table is
    # reported as unverifiable rather than assumed valid or assumed invalid --
    # same reports-instead-of-guessing principle the rest of PLCHelper uses.
    active_pipeline = alarm.get("activePipeline")
    folder_name = folders[-1] if folders else None
    if unverified_site:
        problems.append(
            f"activePipeline is {active_pipeline!r} -- CANNOT VERIFY: site "
            f"{site!r} has no confirmed pipeline list in SITE_PIPELINES. "
            f"Confirm this site's pipelines in Designer before trusting or "
            f"distrusting this value"
        )
    elif folder_name not in pipelines:
        problems.append(
            f"activePipeline is {active_pipeline!r} -- CANNOT VERIFY: folder "
            f"{folder_name!r} is not in the confirmed pipeline table for "
            f"site {site!r} (known folders: "
            f"{', '.join(sorted(pipelines)) or 'none'})"
        )
    else:
        expected_pipeline = pipelines[folder_name]
        if is_blank(active_pipeline):
            problems.append(
                f"activePipeline is blank -- expected "
                f"{expected_pipeline!r}; a blank pipeline means this alarm "
                f"notifies nobody"
            )
        elif active_pipeline != expected_pipeline:
            problems.append(
                f"activePipeline is {active_pipeline!r} -- expected "
                f"{expected_pipeline!r} for a tag in folder {folder_name!r}"
            )

    # --- Rule 3: CustomEmailSubject and CustomEmailMessage both blank.
    for key in CUSTOM_EMAIL_KEYS:
        value = alarm.get(key)
        if not is_blank(value):
            problems.append(
                f"{key} is non-blank ({value!r}) -- expected blank so the "
                f"pipeline's own template is used"
            )

    # --- Rule 4: enabled is true.
    if "enabled" not in alarm:
        problems.append(
            "enabled key is absent -- Ignition defaults it to true, but the "
            "site's own convention is to state it explicitly"
        )
    elif alarm.get("enabled") is not True:
        problems.append(
            f"enabled is {alarm.get('enabled')!r} -- expected true; this "
            f"alarm is not being evaluated"
        )

    # --- Rule 5: priority present and non-blank. Presence and blankness, not
    # truthiness -- priority 0 (Diagnostic) is a real priority.
    if "priority" not in alarm:
        problems.append("priority key is absent -- expected a priority")
    elif is_blank(alarm.get("priority")):
        problems.append(
            f"priority is blank ({alarm.get('priority')!r}) -- expected a "
            f"priority"
        )

    # --- Rule 6: tagGroup and historyTagGroup match the site being audited.
    # Both are tag-level properties, not alarm-level ones.
    for key in ("tagGroup", "historyTagGroup"):
        if key not in tag:
            problems.append(
                f"{key} key is absent on the tag -- expected {site!r}"
            )
        elif tag.get(key) != site:
            problems.append(
                f"{key} is {tag.get(key)!r} -- expected {site!r}; this looks "
                f"like a copy-paste artifact from another site"
            )

    # --- Rule 7: the alarm's own name matches its parent tag's name.
    if alarm.get("name") != tag_name:
        problems.append(
            f"alarm name is {alarm.get('name')!r} -- expected "
            f"{tag_name!r} to match its parent tag's name"
        )

    # --- Rule 8: displayPath exactly matches the tag's real tree position.
    expected_display_path = "/".join(
        [site] + [f for f in folders if f] + [str(tag_name)])
    display_path = alarm.get("displayPath")
    if "displayPath" not in alarm or is_blank(display_path):
        # Blank is a documented "use the default," not a mistyped path -- see
        # the module docstring. Still a rule-8 failure; worded so nobody
        # chases a typo that isn't there.
        problems.append(
            f"displayPath is blank/absent -- Ignition falls back to the "
            f"tag's own source path; expected an explicit "
            f"{expected_display_path!r}, the convention used by the rest of "
            f"this site"
        )
    elif display_path != expected_display_path:
        problems.append(
            f"displayPath is {display_path!r} -- expected "
            f"{expected_display_path!r} (exact match required)"
        )

    return problems


def audit_tag(folders, tag, site, pipelines, unverified_site):
    """Check every alarm on one tag. Returns a list of problem strings."""
    alarms = tag.get("alarms") or []

    # Not one of the eight rules -- a precondition for them. A tag sitting in
    # an Alarms folder with no alarm on it cannot be checked at all, and
    # counting it as OK would be a silent pass. None exist in Weston's export;
    # this is defensive, and it reports itself if it ever fires.
    if not alarms:
        return [
            "tag has no alarms configured -- none of the eight rules can be "
            "evaluated; confirm this tag belongs in the Alarms folder"
        ]

    problems = []
    for alarm in alarms:
        found = audit_alarm(
            tag, alarm, folders, site, pipelines, unverified_site)
        if len(alarms) > 1:
            # Only prefix when it is actually ambiguous which alarm is meant.
            found = [f"[alarm {alarm.get('name')!r}] {p}" for p in found]
        problems.extend(found)
    return problems


def main():
    parser = argparse.ArgumentParser(
        description="Audit an Ignition alarm tag export against TASK_009's "
                    "eight alarm-configuration correctness rules. "
                    "Report-only -- no fixes are applied and the input file "
                    "is never modified. Applying fixes is TASK_010, a "
                    "deliberately separate tool.",
    )
    parser.add_argument("--input", required=True,
                        help="Path to the Ignition tag export JSON of the "
                             "site's Alarms folder")
    parser.add_argument("--site", required=True,
                        help="Site name being audited, e.g. Weston. Selects "
                             "the confirmed pipeline list from "
                             "SITE_PIPELINES and is the expected value for "
                             "tagGroup/historyTagGroup and the leading "
                             "segment of every displayPath")
    args = parser.parse_args()

    site = args.site
    pipelines = SITE_PIPELINES.get(site, {})
    unverified_site = site not in SITE_PIPELINES

    print(f"TASK_009 -- Audit Ignition alarm tag configuration")
    print(f"{'=' * 68}")
    print(f"Input       : {args.input}")
    print(f"Site        : {site}")
    if unverified_site:
        print(f"Pipelines   : *** NONE CONFIRMED for this site ***")
    else:
        print(f"Pipelines   : " + ", ".join(
            f"{folder}={name!r}" for folder, name in sorted(pipelines.items())))
    print(f"Mode        : read-only -- no fixes applied, input not modified")
    print()

    if unverified_site:
        print(f"*** WARNING: site {site!r} is not in SITE_PIPELINES, so rule "
              f"2 (activePipeline) cannot be checked.")
        print(f"    Sites are NOT assumed uniform -- Weston's pipeline names "
              f"are not evidence for any other site's.")
        print(f"    Every other rule is still checked. Confirm this site's "
              f"pipelines in Designer and add them to")
        print(f"    SITE_PIPELINES before relying on this run's rule-2 "
              f"results.")
        print()

    with open(args.input, encoding="utf-8") as handle:
        export = json.load(handle)

    findings = []
    total = 0
    for folders, tag in collect_tags(export, []):
        total += 1
        problems = audit_tag(folders, tag, site, pipelines, unverified_site)
        if problems:
            findings.append((str(tag.get("name")), problems))

    # Sorted alphabetically by tag name, per TASK_009's Outputs section.
    findings.sort(key=lambda entry: entry[0])
    problem_count = len(findings)
    ok_count = total - problem_count

    print(f"Scanned {total} tag(s): {ok_count} OK, "
          f"{problem_count} with problems "
          f"({sum(len(p) for _, p in findings)} problem(s) total)")
    print()

    if findings:
        print(f"Tags with problems, alphabetically by tag name:")
        print(f"{'-' * 68}")
        for tag_name, problems in findings:
            print(f"{tag_name}")
            for problem in problems:
                print(f"  - {problem}")
        print()
    else:
        print(f"No problems found -- every tag passed all eight rules.")
        print()

    # Per-rule tally. The per-tag listing above is the report Doug asked for;
    # this is the one thing it cannot show -- whether a finding is one tag's
    # local mistake or a systemic pattern across the site, which is the whole
    # reason the CustomEmailSubject issue was worth a tool instead of a fix.
    print(f"Problems by kind:")
    tally = {}
    for _, problems in findings:
        for problem in problems:
            kind = problem.split(" -- ")[0].split(" is ")[0].split(" (")[0]
            tally[kind] = tally.get(kind, 0) + 1
    if tally:
        width = max(len(kind) for kind in tally)
        for kind, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {kind.ljust(width)}  {count}")
    else:
        print(f"  (none)")

    print(f"\nNext step: review the findings above, then apply fixes via "
          f"TASK_010 -- this tool never writes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
