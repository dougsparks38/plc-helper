# PLCHelper — Status
*Cross-project PLCHelper infrastructure. Job-specific PLC work is tracked
in that job's own status file (e.g. `BlueSky/BLUE_SKY_STATUS.md`) — this
file is for PLCHelper itself: the tool, not any one job's use of it.*

---

## Open Work Items

*(none active right now)*

## Deferred — Not Active Yet

Logged so nothing is forgotten, but not pending action — do not bring
these up until Doug says it's time.

1. ⏸ **Update the master "AOI Development" reference program** *(moved
   here 2026-09-02 from BlueSky's status file — this is a company-wide
   concern, not Blue Sky-specific)*
   - An embedded 1993 Usenet code-attribution email was found and fixed
     inside an AOI while working on Blue Sky (2026-09-02), but Doug
     forgot which specific AOI he edited before fixing it, so the fix
     hasn't propagated to the canonical master source. Could check a
     backup copy of the Blue Sky PLC program later to identify which AOI
     it was. See `CLAUDE.md`, "AOI reuse across projects," for the
     general pattern (Casne engineers often copy AOIs from old projects
     rather than pulling from the master, so fixes don't automatically spread).

2. ⏸ **Make PLCHelper discoverable/usable by other Casne PLC
   programmers** *(2026-09-02)*
   - Doug's own analogy: before writing WoW addon code he looks up
     reference documentation first — he'd like the same to eventually
     exist here for coworkers. Not a small documentation task — real
     considerations before this is ready:
     1. Needs audience-shifted documentation (a plain-language "what is
        this / what can it do / how do I start" doc — different from
        `PLCHelper_Tasks.md` and `CLAUDE.md`, which assume Doug's own context)
     2. Repo currently lives at `github.com/dougsparks38/plc-helper` —
        Doug's personal account, not a Casne organizational one; worth
        reconsidering before wider sharing
     3. Per `CASNE_AI_USAGE_POLICY.md`, agentic AI use requires approval
        **per person** — Doug's approval doesn't cover coworkers; each
        would need their own
     4. The confidentiality discipline (PII_Review staging, sanitize-
        and-scan) needs to transfer as understanding, not just a rule
        someone's told once

## Talent Candidates (pending write-up)

*Logged as they come up during ad hoc PLCHelper Q&A/testing sessions.
Not full task specs yet — batch-formalized into `PLCHelper_Tasks.md`
later, on Doug's cue, per his stated preference.*

1. **"Handoff to SCADA"** *(raised 2026-09-03, sparked by a real
   situation — a coworker's Ignition screen design work stalled for
   weeks after the test PLC/tags became ready, apparently just because
   she got pulled onto another project)* — a task/skill for producing
   whatever a SCADA/Ignition designer actually needs to pick up and
   finalize screens/tag bindings for a job, once the PLC side is ready.
   At Casne, "SCADA" and "HMI" are used interchangeably. Still being
   scoped with Doug — open questions: exact deliverable (a job-specific
   tag/instance list ready for HMI binding? something else?); whether
   this is a general PLCHelper methodology applied to a job's L5X
   (output living in that job's own folder, matching the TASK_003
   pattern) or something else entirely.

## Completed

*(none yet)*

---

*Last updated: September 2, 2026*
