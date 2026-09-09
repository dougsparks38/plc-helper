#!/usr/bin/env python3
"""
TASK_009 -- Audit Ignition alarm tag configuration for formatting problems.

Read an Ignition Tag Export of one site's `Alarms` folder and check every
alarm in it against the nine correctness rules confirmed in
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

THE NINE RULES (spec: PLCHelper_Tasks.md TASK_009 "Process"):
  1. `notes` non-blank -- this is what the pipeline's default template
     surfaces, so a blank one produces a contentless notification.
  2. `activePipeline` matches the tag's own site/folder, against the
     SITE_PIPELINES table below. A tag under `.../500/` must reference that
     site's `_500` pipeline, not `_800`. The offending value is always
     printed by name so a known-bad one is recognizable on sight.
  3. `CustomEmailSubject` and `CustomEmailMessage` both blank -- non-blank
     overrides the pipeline's own template. Doug's confirmed fix direction.
  4. `enabled` is `true`.
  5. `priority` exactly matches the folder-based rule in FOLDER_PRIORITIES
     below -- `500` must be `Medium`, `800` must be `High`. This is a
     match, not a presence test: it overrides an existing wrong value, so a
     tag already set to something else is still flagged.
  6. `tagGroup` and `historyTagGroup` match the site being audited --
     catches copy-paste artifacts like a Weston alarm carrying
     `tagGroup: "MasonCity"`.
  7. The alarm's own `name` matches its parent tag's `name`.
  8. `displayPath` exactly matches the tag's real position in the tree,
     reconstructed as `<Site>/Alarms/<folder>/<tagname>`.
  9. Historian configuration matches the site-wide convention, two-sided:
     the three properties in REQUIRED_HISTORY_PROPERTIES must be present
     with those exact values, AND none of EXTRANEOUS_HISTORY_KEYS may be
     present at all. Tag-level, not alarm-level, so it is checked once per
     tag.

NO EXEMPTIONS, INCLUDING TEST TAGS (Doug-confirmed 2026-09-09): rules 1-9
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

RULE 5 IS A FOLDER-BASED MATCH, NOT A PRESENCE TEST (tightened 2026-09-09):
the rule originally read "present and non-blank," which passed
`CP_6000_PLC_Comm_Loss_Alm`'s `priority: "Critical"` in the `800` folder.
Doug's standing rule for this Ignition system is that the folder decides the
priority -- `500` is `Medium`, `800` is `High` -- and it overrides an
existing value rather than merely filling a missing one. His words on that
one real exception: "they need to match the rule... it is wrong." No other
priority value is valid on this system.

Ignition itself is looser than this rule, and the report says so rather than
implying a typo. The docs define `priority` as Integer **or** String, with
Diagnostic = 0, Low = 1, Medium = 2, High = 3, Critical = 4. So `priority: 3`
in an `800` folder is a legitimate Ignition configuration meaning High -- it
still fails rule 5, because the rule is an exact match against this site's
string convention, but it gets its own problem wording noting it is
numerically equivalent. Same treatment as a blank `displayPath` above: still
a failure, worded so nobody hunts for a severity mistake that isn't there.
None exist in Weston's export -- every priority there is a string.

RULE 9's EXTRANEOUS KEYS ARE A VIOLATION BY THEIR MERE PRESENCE (verified
against the docs -- sources logged in `claude-workflow/TRUSTED_SOURCES.md`,
"Ignition Tag Properties -- History section" and "Configuring Tag History"):
an Ignition tag export omits a History property entirely when it sits at
Ignition's own default, so "Sample Mode: On Change" and "Deadband Mode:
Absolute" as seen in Designer are defaults being *displayed*, not overrides
stored in the file. Every compliant tag therefore has no `sampleMode`,
`historyMaxAge`, or `historyMaxAgeUnits` key at all, and an explicit value --
whatever it is -- is itself the non-compliance. Confirmed on Weston: 140 of
143 tags omit all three; only `CP_6000_PLC_Comm_Loss_Alm` sets them, which is
also the one tag whose `historyTagGroup` is functional at all (that field is
inert unless `sampleMode` is `"TagGroup"`). Doug confirmed 2026-09-09 this
should be normalized to match every other tag, not preserved as a deliberate
exception.

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

# Required alarm `priority`, keyed by the tag's own folder name inside the
# site's `Alarms` tree (rule 5).
#
# UNLIKE SITE_PIPELINES, THIS TABLE IS NOT PER-SITE. Doug's rule (confirmed
# 2026-09-09) is a standing convention for the whole Ignition system, not one
# site's naming: the folder decides the priority everywhere. That is why it is
# keyed by folder alone -- if that ever turns out to vary by site, this table
# has to grow a site level the way SITE_PIPELINES has one, not get quietly
# special-cased at a call site.
#
# THIS IS AN OVERRIDE, NOT A DEFAULT. A tag already carrying some other value
# is still flagged -- confirmed explicitly against the one real exception,
# `CP_6000_PLC_Comm_Loss_Alm` (`Critical`, in the `800` folder).
FOLDER_PRIORITIES = {
    "500": "Medium",
    "800": "High",
}

# Ignition's own documented priority levels, for wording only -- never for
# deciding compliance. Rule 5 is an exact match against FOLDER_PRIORITIES; this
# table only lets the report say "3 is numerically High" instead of implying
# somebody set the wrong severity. See the module docstring.
PRIORITY_LEVEL_NUMBERS = {
    "Diagnostic": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}

# Tag-level History properties that must be present with exactly these values
# (rule 9a), and the site-wide historian convention Doug confirmed 2026-09-09
# from his own Designer screenshot.
REQUIRED_HISTORY_PROPERTIES = {
    "historyEnabled": True,
    "historyProvider": "Hist_IW",
    "historicalDeadbandStyle": "Discrete",
}

# Tag-level History properties that must NOT appear at all (rule 9b). Presence
# is the violation regardless of value -- a tag export omits any property
# sitting at Ignition's default, so an explicit value here is by definition an
# override of a default every other tag on the site relies on.
EXTRANEOUS_HISTORY_KEYS = ("sampleMode", "historyMaxAge", "historyMaxAgeUnits")

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

    # --- Rule 5: priority exactly matches the folder-based rule. An override,
    # not a default -- a wrong existing value fails just as a missing one does.
    #
    # A folder absent from FOLDER_PRIORITIES is reported as unverifiable rather
    # than passed or failed, matching rule 2's handling: the table is a
    # confirmed convention, and a folder nobody confirmed is not evidence
    # either way.
    priority = alarm.get("priority")
    if folder_name not in FOLDER_PRIORITIES:
        problems.append(
            f"priority is {priority!r} -- CANNOT VERIFY: folder "
            f"{folder_name!r} has no confirmed required priority (known "
            f"folders: {', '.join(sorted(FOLDER_PRIORITIES)) or 'none'})"
        )
    else:
        expected_priority = FOLDER_PRIORITIES[folder_name]
        if "priority" not in alarm:
            problems.append(
                f"priority key is absent -- expected {expected_priority!r} "
                f"for a tag in folder {folder_name!r}"
            )
        elif is_blank(priority):
            problems.append(
                f"priority is blank ({priority!r}) -- expected "
                f"{expected_priority!r} for a tag in folder {folder_name!r}"
            )
        elif priority != expected_priority:
            # Ignition accepts the numeric form, so say when a value is the
            # right severity in the wrong notation -- it is a different fix
            # from an actually-wrong severity. See the module docstring.
            if priority == PRIORITY_LEVEL_NUMBERS.get(expected_priority):
                problems.append(
                    f"priority is {priority!r} -- numerically the same level "
                    f"as the expected {expected_priority!r}, but this site "
                    f"states priority as a string; expected "
                    f"{expected_priority!r} for a tag in folder "
                    f"{folder_name!r}"
                )
            else:
                problems.append(
                    f"priority is {priority!r} -- expected "
                    f"{expected_priority!r} for a tag in folder "
                    f"{folder_name!r}; the folder rule overrides whatever is "
                    f"set here"
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


def audit_tag_history(tag):
    """Check rule 9 -- historian configuration. Returns problem strings.

    Tag-level, not alarm-level, so this runs once per tag no matter how many
    alarms sit on it. Two-sided and reported one problem per line, same as
    every other rule: each required property missing or wrong is its own line,
    and each extraneous property present is its own line.
    """
    problems = []

    # 9a -- the three required properties, present with exactly these values.
    for key, expected in REQUIRED_HISTORY_PROPERTIES.items():
        if key not in tag:
            problems.append(
                f"{key} key is absent on the tag -- expected {expected!r}; "
                f"this tag is not on the site's historian convention"
            )
        elif tag.get(key) != expected:
            problems.append(
                f"{key} is {tag.get(key)!r} -- expected {expected!r} per the "
                f"site's historian convention"
            )

    # 9b -- the three properties that must not be present at all. Presence is
    # the violation; the value is reported only so the reader can see what was
    # overridden.
    for key in EXTRANEOUS_HISTORY_KEYS:
        if key in tag:
            problems.append(
                f"{key} is explicitly set to {tag.get(key)!r} -- expected the "
                f"key to be absent entirely; a tag export omits this property "
                f"when it relies on Ignition's default, so any explicit value "
                f"is itself the non-compliance"
            )

    return problems


def audit_tag(folders, tag, site, pipelines, unverified_site):
    """Check every alarm on one tag, plus the tag's own historian config.

    Returns a list of problem strings.
    """
    alarms = tag.get("alarms") or []

    problems = []

    # Not one of the nine rules -- a precondition for the alarm-level ones. A
    # tag sitting in an Alarms folder with no alarm on it cannot be checked
    # against rules 1-8 at all, and counting it as OK would be a silent pass.
    # Rule 9 is tag-level and is still checked below, since a historian
    # misconfiguration does not need an alarm to be real. None exist in
    # Weston's export; this is defensive, and it reports itself if it fires.
    if not alarms:
        problems.append(
            "tag has no alarms configured -- none of the alarm-level rules "
            "(1-8) can be evaluated; confirm this tag belongs in the Alarms "
            "folder"
        )

    for alarm in alarms:
        found = audit_alarm(
            tag, alarm, folders, site, pipelines, unverified_site)
        if len(alarms) > 1:
            # Only prefix when it is actually ambiguous which alarm is meant.
            found = [f"[alarm {alarm.get('name')!r}] {p}" for p in found]
        problems.extend(found)

    # Rule 9 last, so the per-tag listing reads in rule order, and unprefixed
    # even on a multi-alarm tag because it belongs to the tag, not an alarm.
    problems.extend(audit_tag_history(tag))
    return problems


def main():
    parser = argparse.ArgumentParser(
        description="Audit an Ignition alarm tag export against TASK_009's "
                    "nine alarm-configuration correctness rules. "
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
        print(f"No problems found -- every tag passed all nine rules.")
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
