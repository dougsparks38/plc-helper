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

1. **"Handoff to SCADA" — AOI-to-UDT structure verification** *(raised
   2026-09-03, sparked by a real situation — a coworker's Ignition
   screen design work stalled for weeks after the test PLC/tags became
   ready, apparently just because she got pulled onto another project)*

   At Casne, "SCADA" and "HMI" are used interchangeably. The actual
   concept, now understood concretely:
   - An AOI (Add-On Instruction) in the Rockwell PLC is a data-structure
     wrapper — one tag reference with a full parameter set defined
     underneath it. PLCHelper already reads this (see the Casne AOI
     Reference).
   - On the Ignition side, Doug mirrors each AOI type with a matching
     **UDT (User Defined Type)** — Ignition's own equivalent concept.
     Every AOI instance in the PLC gets a same-named UDT instance in
     Ignition (tag name matched **exactly**, including capitalization),
     so Ignition can bind to the PLC tag automatically. For this to
     work, the UDT's sub-elements must exactly match the AOI's real
     parameters.
   - Current problem: the coworker built UDTs matching the AOI
     structures, but they aren't quite right — some mismatch against
     the actual AOI parameter sets.
   - **Proposed task**: for each distinct AOI type used in a job, Doug
     exports the corresponding Ignition UDT (format not yet confirmed —
     XML or JSON) and gives it to PLCHelper, which compares it against
     that AOI's real parameter structure (from the Casne AOI Reference
     or the L5X directly) and corrects the UDT definition so every
     sub-element matches, name for name.
   - **Naming convention — UDT names do NOT track PLC AOI version numbers**
     (confirmed 2026-09-03): a PLC AOI's version bumps only when new
     sub-elements are *added* (never on removal — deleting a parameter
     doesn't break the Ignition screen, so it doesn't force a bump). On
     the Ignition side, the UDT is never renamed to match a new AOI
     version — it's kept as-is and just gets new sub-elements added when
     the PLC side adds them. Example found in the wild: Ignition UDT
     named `CONSPD2_AOI` legitimately corresponds to current PLC type
     `CONSPD4_AOI` — **this is expected, not an error, and must never be
     flagged as a mismatch.** Real design consequence: the eventual task
     cannot assume UDT name == AOI type name. It needs an explicit
     UDT-name ↔ AOI-type mapping (supplied by Doug per UDT), not a
     name-matching heuristic.
   - **In progress (2026-09-03)** — Doug is actively feeding PLCHelper
     reference data to work through this interactively. First data point
     received: a known-working single (non-UDT) Ignition tag,
     `AUTO_hwdi` under `O2InjectionSystem`, OPC Item Path
     `ns=1;s=[BOP_O2_CombinedTest]O2_AC001.AUTO_hwdi` — confirms the
     OPC path shape (`[PLC program name]AOI_instance.parameter`) that a
     parameterized UDT template needs to reproduce, with the AOI-instance
     segment (`O2_AC001`) becoming a UDT parameter and everything else
     fixed per member. Consistent with `AUTO_hwdi` as documented in the
     Casne AOI Reference (CONSPD4_AOI). Session ongoing — not yet
     buildable as a formal task, still hands-on with Doug per the same
     pattern as TASK_003 and the AOI Reference itself.

## Completed

*(none yet)*

---

*Last updated: September 2, 2026*
