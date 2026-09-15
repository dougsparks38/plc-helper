# PLCHelper — Status
*Cross-project PLCHelper infrastructure. Job-specific PLC work is tracked
in that job's own status file (e.g. `BlueSky/BLUE_SKY_STATUS.md`) — this
file is for PLCHelper itself: the tool, not any one job's use of it.*

---

## Open Work Items

1. ⬜ **TASK_003 — Rung-comment scaling & TODO audit** *(moved here
   2026-09-10 from `BlueSky/BLUE_SKY_STATUS.md` — it's a PLCHelper
   capability, not Blue Sky-specific, same reasoning as the
   AOI-master-source cleanup item below. Not urgent — Doug's own framing:
   "we'll probably find ourselves taking care of it whenever it's the
   right time naturally.")*
   - Finds every `@`-marked TODO comment and every filled-in 4-20mA
     scaling comment, resolves each to its field-instrument tag via AOI
     context, cross-checks against a job's Instrument List. First
     real-world input lined up: Blue Sky's L5X
     (`BOP_O2_CombinedTest_v35_Emulate.L5X`) and its Instrument List —
     blocker there was never the input data, it's the PLCHelper agent
     itself maturing enough to run the task.
   - Full spec: `PLCHelper_Tasks.md`, TASK_003 (Spec Ready) — reads a
     job's L5X + Instrument List cross-folder rather than copying the
     Instrument List into PLCHelper, keeping the tool reusable across
     jobs.

2. 🔄 **TASK_012 — Embed Ignition alarm definitions into generated UDT
   definitions** *(raised 2026-09-15; Rule 16 design gate cleared the same
   day. **4 of 8 types LIVE-VERIFIED 2026-09-15** — `ALARM_AOI` (pilot),
   `CONSPD4_AOI`, `FLOWIN3_AOI` and `FLOWVLV_AOI`, all imported by Doug and
   confirmed firing and clearing on real instances. 3 types unstarted;
   `INTERLOCK_AOI` is excluded.)*
   - **`FLOWVLV_AOI` LIVE-VERIFIED 2026-09-15 — 4th type.** Deliverable:
     `BlueSky/FLOWVLV2_AOI UDT definition with alarms 2026-09-15.json`.
     2 alarms, 0 skipped (no `UnACK_Alm` on this type), zero blank `notes`,
     both members Boolean. **Uniform `High`, no split** — worth noting
     because it directly follows `FLOWIN3_AOI`'s per-member split: priority
     went split, then back to flat, which confirms it must be asked per type
     rather than inferred from the previous one. Built surgically;
     fidelity-checked to differ by exactly the 2 new `alarms` arrays.
   - **⚠ Name mismatch — target was `FLOWVLV2_AOI`, not `FLOWVLV_AOI`, and
     the import confirmed it.** There is **no** Ignition definition named
     `FLOWVLV_AOI` at all, so importing under the L5X name would have
     created a brand-new orphan rather than updating the live definition.
     Pairing was verified beforehand by count (L5X 38 parameters = Ignition
     38 members), and the build copies the live definition's own `name`
     field rather than writing one. Doug's import landed on `FLOWVLV2_AOI`
     with **no orphan created** — the hazard was real and was navigated
     correctly.
   - **Doug's full live pass, all steps passed (2026-09-15):**
     `MergeOverwrite` overwriting in place; landed on `FLOWVLV2_AOI` with no
     orphan under the L5X name; both alarmed members present at High; real
     instances show the alarms as **inherited** with pre-existing overrides
     intact; `FAIL_ACT_alm` and `FAIL_DEACT_alm` each forced independently,
     both going **Active at Priority High** and clearing correctly.
   - **Name mismatches are the norm, not the exception:** 2 of the 4 types
     built so far had one (`CONSPD4_AOI` → `CONSPD2_AOI`, `FLOWVLV_AOI` →
     `FLOWVLV2_AOI`). `VARSPD2_AOI` → `VARSPD_AOI` is the third known pair
     and is still unbuilt — check the Ignition name before building it.
   - **"deactuate" preserved verbatim.** `FAIL_DEACT_alm`'s description
     reads "Fail to deactuate alarm" — not a standard word, carried across
     unchanged rather than silently corrected to "deactivate". Same
     discipline as blank `notes`: if it should read differently, that is a
     Studio 5000 fix at the source.
   - **`FLOWIN3_AOI` LIVE-VERIFIED 2026-09-15 — 3rd type.** Deliverable:
     `BlueSky/FLOWIN3_AOI UDT definition with alarms 2026-09-15.json`.
     Ignition and L5X names match for this type, so no name-pairing hazard.
     6 alarms, 0 skipped (carries no `UnACK_Alm`). Built surgically from the
     live export; fidelity-checked to differ by exactly the 6 new `alarms`
     arrays.
   - **⚠ FIRST TYPE WITH A PER-MEMBER PRIORITY — don't read it as uniform.**
     High on `Hi_Alm`, `Lo_Alm`, `Xmtr_Alm`; Medium on `UnderRange_Alm`,
     `OverRange_Alm`, `ChFault_Alm` (Doug, 2026-09-15). Deliberately **not**
     a clean process-vs-diagnostic split — `Xmtr_Alm` is High alongside the
     two flow alarms, not with the other instrument faults. Built exactly as
     stated; "tidying" `Xmtr_Alm` to Medium would override a decision, not
     fix an inconsistency.
   - **The per-member split is confirmed working on a real gateway, not
     merely written correctly into the file.** Doug's verification pass
     checked the priorities in Designer after import and then forced a bit
     at *each* level: a High member went **Active at Priority High** and
     cleared, and a Medium member went **Active at Priority Medium** and
     cleared. That second check is the one that actually proves per-member
     priority survives `MergeOverwrite` and propagates to instances — a
     correct JSON file alone would not have shown it.
   - **Doug's full live pass, all steps passed (2026-09-15):**
     `MergeOverwrite` overwriting in place; landed on the existing
     `FLOWIN3_AOI` definition; all 6 alarmed members present; priorities
     correct per the split above; real instances show the alarms as
     **inherited** with pre-existing overrides intact; both a High and a
     Medium bit fired and cleared correctly.
   - **First type with zero blank `notes`** — all 6 members carry a real L5X
     Description, so nothing needed flagging. All 6 confirmed Boolean,
     checked deliberately because an analog input type with a REAL-typed
     alarm member would have made the `Equality`/`setpointA: 1.0` trip
     condition wrong.
   - **⚠ New open capability gap (not fixed):** `generate_ignition_udt.py`'s
     `--alarms` path reads one flat `ALARM_CONFIG['priority']` and cannot
     express a per-member value — the split above was applied by the
     surgical build. A future regenerate of `FLOWIN3_AOI` with `--alarms`
     would silently produce uniform `High` and lose the three `Medium`
     values, with no warning. Same *shape* as the latent
     `OPTIONAL_MEMBER_KEYS` bug: a quiet wrong answer, not a crash. Worth
     fixing before the remaining 4 types, now that priority is established
     as varying per member rather than per type.
   - **`CONSPD4_AOI` LIVE-VERIFIED 2026-09-15 — 2nd type, no new code.** The
     existing `--alarms` path pointed at a new type. Deliverable:
     `BlueSky/CONSPD2_AOI UDT definition with alarms 2026-09-15.json` —
     named and imported under the **Ignition** name `CONSPD2_AOI`, never
     the L5X name `CONSPD4_AOI` (importing under the wrong one creates an
     orphan definition instead of updating the live one). 3 alarms on
     `FAIL_alm`, `Stuck_On_Alm` and `CBAux_alm`, all `High` per Doug;
     `UnACK_Alm` skipped. Built surgically from the live export and
     fidelity-checked to differ by exactly the 3 new `alarms` arrays.
   - **Doug's live verification pass, all steps passed (2026-09-15):**
     imported with `MergeOverwrite` overwriting in place (no rename, no
     `zz delete`); landed on the existing `CONSPD2_AOI` definition with no
     orphan created under the L5X name; exactly 3 alarmed members confirmed
     with `UnACK_Alm` carrying none; spot-checked real instances show the
     alarms as **inherited**, not local overrides, and pre-existing
     per-instance overrides survived the import; a forced alarm bit went
     **Active, Priority High** and cleared correctly. `CBAux_alm`'s blank
     `notes` appeared exactly as predicted — confirmed expected, not a
     surprise.
   - **Second type to confirm the definition-level approach end-to-end.**
     The pilot proved the mechanism on a 1-alarm type; `CONSPD4_AOI` proves
     it holds for a multi-alarm definition, including that three alarms all
     named `Alarm` on different members do not collide.
   - **The `UnACK_Alm` exclusion fired for real for the first time here** —
     it was added ahead of need during the pilot, where no member matched
     it. Without it a 4th unwanted alarm would have been generated.
   - **⚠ Second blank-`notes` case:** `CONSPD4_AOI`'s `CBAux_alm` has no
     `<Description>` element at all in the L5X (verified against the raw
     XML), so its `notes` is blank — the same gap as `ALARM_AOI`'s, and
     nothing was invented for either. Same three options apply.
   - **⚠ Pipeline does not exist on the gateway yet.** Found during the
     live pilot test: `Hartman_KC_Dairy_SCADA/BlueSky` is the correct
     reference (the earlier `"BlueSky"` was wrong and was corrected), but
     no such pipeline is actually configured. Alarms fire and show Active;
     nothing notifies anyone. Gateway config work, not a PLCHelper defect
     — PLCHelper references a pipeline by name, it never creates one.
     Applies to `CONSPD4_AOI`'s 3 new alarms exactly as to `ALARM_AOI`'s.
   - **Built 2026-09-15:** `generate_ignition_udt.py` gained `--alarms` /
     `--alarm-pipeline`, the `ALARM_CONFIG` site-convention table, the
     `ALARM_DEFINITION_EXCLUSIONS` standing table, `is_alarm_member()` and
     `build_alarm_definition()`, plus a per-run alarm report. `--alarms` is
     opt-in — regression-verified that `ALARM_AOI`, `LEVELIN3_AOI` and
     `VARSPD2_AOI` all regenerate byte-identical without it.
   - **Latent bug fixed:** `alarms` was missing from
     `OPTIONAL_MEMBER_KEYS`. Left unfixed, the first reference UDT carrying
     an alarm would have had that one alarm stamped onto *every* generated
     member — silent mass-misconfiguration. Fixed before such a reference
     exists rather than after.
   - **Pilot deliverable:** `BlueSky/ALARM_AOI UDT definition with alarms
     2026-09-15.json`, built surgically from Doug's fresh live export
     rather than regenerated, and fidelity-checked to differ from it by
     exactly the one `alarms` array.
   - **⚠ One open item for Doug:** `ALARM_AOI`'s `Alarm` parameter has no
     `<Description>` in the L5X, so `notes` is blank. Nothing was invented
     to fill it. The alarm still fires; only the notification email body is
     empty. Three options written up in `PLCHelper_Tasks.md` TASK_012 —
     Doug picks one.
   - **Remaining: 3 types unstarted** — `LEVELIN3_AOI`, `VARSPD2_AOI` and
     `MODVLV`. `INTERLOCK_AOI` is excluded (0 alarm members). Each needs its
     own priority answer from Doug first (Rule 16), and that answer may be
     per-member or uniform — both have now occurred, so neither can be
     assumed. `LEVELIN3_AOI` (9 alarm members) and `VARSPD2_AOI` (7) are the
     two largest types remaining and both carry `UnACK_Alm`;
     `VARSPD2_AOI`'s Ignition name is `VARSPD_AOI`, the third known name
     mismatch.
     `LEVELIN3_AOI` and `VARSPD2_AOI` also carry `UnACK_Alm` and will
     exercise the same exclusion `CONSPD4_AOI` just did. `MODVLV` is
     assessed as needing zero extra code (native-UDT path, shared member
     builder) but was not built.

   - Background (unchanged from when this was raised): the goal is a
     definition-level alarm so all instances inherit it, per Inductive
     Automation's "Alarms in UDTs" page: *"If an alarm is configured
     inside a UDT, every instance of that UDT will automatically have that
     same alarm configuration."* Alarm-member census from
     `BOP_O2_CombinedTest_v35_Emulate.L5X`: ALARM_AOI 1, FLOWVLV_AOI 2,
     CONSPD4_AOI 4, MODVLV 4, FLOWIN3_AOI 6, VARSPD2_AOI 7, LEVELIN3_AOI 9,
     INTERLOCK_AOI 0 — re-verified 2026-09-15 by running the shipped
     `is_alarm_member()` predicate itself, and it reproduces these counts
     exactly. Starting state verified greenfield: **zero** `alarms` arrays
     across all 8 live definitions in the 2026-09-15 full export.
   - The three site conventions this was blocked on — `activePipeline`,
     `priority`, and whether `UnACK_Alm` counts as an alarm — were all
     answered by Doug on 2026-09-15 and are no longer open. Their Daily
     Planner entries under Blue Sky can be closed. Note `activePipeline`'s
     answer was corrected the same day during live testing: the real value
     is the full path `Hartman_KC_Dairy_SCADA/BlueSky`, not `BlueSky`.
   - Full write-up: `PLCHelper_Tasks.md`, TASK_012.

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
     reference data to work through this interactively, using Ignition
     Designer directly on `O2InjectionSystem/O2_AC001` (a CONSPD4_AOI
     instance) as the live test case:
     - **Known-working baseline**: a manually-browsed, non-UDT Ignition
       tag, `AUTO_hwdi` under `O2InjectionSystem`, OPC Item Path
       `ns=1;s=[BOP_O2_CombinedTest]O2_AC001.AUTO_hwdi` — confirms the
       OPC path shape (`[PLC program name]AOI_instance.parameter`) a
       parameterized UDT template needs to reproduce. Consistent with
       `AUTO_hwdi` as documented in the Casne AOI Reference (CONSPD4_AOI).
     - **Confirmed bug pattern #1 — OPC Server name typo**: the UDT's
       OPC Server field read `Ignition OPC-UA Server` (with a hyphen)
       while the actual configured/working server connection is named
       `Ignition OPC UA Server` (no hyphen). This alone produces
       `Error_Configuration("Server ... does not exist.")` — a totally
       different-looking error than a path/parameter problem, even
       though the real cause is a single stray character. This appears
       to be set per-member, not inherited from one shared location —
       every member needs checking individually, not just the type
       header.
     - **RETRACTED — `{InstanceName}` was never actually a bug**
       (corrected 2026-09-03, superseding what was logged earlier the
       same day): originally recorded as "confirmed bug pattern #2"
       because adding an explicit `InstanceName` parameter coincided
       with fixing `AUTO_hwdi`. That was a confounded test — two things
       were changed at once (the OPC Server name AND the parameter), and
       it later turned out `AUTO_hwdi`'s own path uses `{Name}`, not
       `{InstanceName}`, so the parameter addition could not have been
       what fixed it. Doug then proved this cleanly: after the OPC
       Server hyphen fix alone resolved almost every member, he deleted
       the `InstanceName` parameter entirely from the UDT and every
       previously-working member kept working. **`{InstanceName}` is
       genuinely automatic and built-in, exactly as Ignition's official
       docs originally described** — no manual parameter needed. The
       real, sole bug the whole time was the OPC Server name typo.
     - **Fix confirmed working**: the OPC Server hyphen correction alone
       resolved almost every member of the UDT (verified by Doug
       directly in Ignition). A small number of members were still
       showing errors — root cause since identified, see Confirmed bug
       pattern #2 below.
     - **Confirmed bug pattern #2 — member-name case mismatch between
       the UDT's OPC Item Path and the real AOI member name** *(diagnosed
       by Doug firsthand 2026-09-04, working on Blue Sky's `O2_FIT100` —
       a `FLOWIN3_AOI` instance. Numbering note: the label "#2" was
       briefly held by the `{InstanceName}` entry that was retracted
       above; it is now assigned to this, the second genuinely confirmed
       pattern.)*

       Ignition's tag diagnostic status distinguishes **two different
       root-cause categories** for a broken OPC UA tag binding to a
       Rockwell PLC, and the exact error text tells you which one you
       have:
       - `Error_Configuration(...)` — the OPC path/server *configuration*
         itself is malformed. Confirmed instance: the OPC Server name
         typo of pattern #1 above, which produces
         `Error_Configuration("Server ... does not exist.")`.
       - `Error` (bare, no `_Configuration`) — the OPC path syntax and
         the server reference are both valid, but the specific
         tag/member reference does not resolve. **Confirmed root cause:
         a case-sensitivity mismatch** between the member name
         referenced in the UDT template's OPC Item Path and the actual
         member name as it exists inside that specific AOI instance in
         the PLC. Communication will not resolve unless the case matches
         exactly.

       Confirmed example (from Ignition directly, on `O2_FIT100`): after
       Doug corrected the OPC-Server-hyphen issue across the UDT, most
       members resolved, but a couple still showed bare `Error` rather
       than resolving or showing `Error_Configuration`. For the
       `Analog_hwai` sub-element, the UDT's OPC Item Path referenced the
       parameter as `ANALOG_hwai`, while the actual member name inside
       the PLC's AOI instance is `Analog_hwai` — differing in
       capitalization only. Fixing Ignition's case to match the PLC
       resolved it. *(Corrected 2026-09-04 — Doug initially reported
       this backwards, i.e. PLC as `ANALOG_hwai` and Ignition as
       `Analog_hwai`; he double-checked directly in the PLC and confirmed
       the above is the correct direction. The general takeaway — case
       must match exactly, check the PLC directly rather than trust
       memory — is unaffected either way.)*

       **Practical diagnostic takeaway (the reusable part):** when
       triaging a batch of broken UDT members in Ignition's Tag Browser,
       read the specific error text before changing anything —
       `Error_Configuration` means go check the OPC Server / path
       configuration; bare `Error` on an otherwise-correctly-configured
       path means go check for a case mismatch between the OPC Item
       Path's referenced member name and the real PLC-side AOI member
       name. This is also the operational reason behind `CLAUDE.md`'s
       "member names copied exactly as they appear in the XML — no
       capitalization changes of any kind" convention: it is a
       functional requirement, not a cosmetic one.

       Scope note: confirmed on `FLOWIN3_AOI`/`O2_FIT100`. It is a
       strong candidate explanation for the still-failing members on the
       `CONSPD4_AOI`/`O2_AC001` UDT above, but that has not been
       verified there yet — diagnose each one, don't assume. Deliberately
       **not** tooled: no automated case-checking and no generated list
       of members that might have this issue, per the Hard scope
       boundary below. Natural candidate for a systematic check once the
       eventual UDT-vs-AOI comparison task is actually built — not
       designed or scoped now.
     - **Remaining scope, not yet done**: the OPC-Server-name-typo check
       from pattern #1 likely needs applying across every other UDT type
       in the project, since the same typo could have been copied around
       the same way — and the pattern #2 case check now belongs in that
       same sweep. This is the concrete case that justifies the task:
       doing this by hand, one member at a time, is exactly what
       PLCHelper should be able to do systematically.
     - **Export format decided**: JSON, not XML — Ignition natively
       exports tags/UDTs as JSON; XML is only an import format that gets
       converted to JSON internally anyway (confirmed via official docs,
       2026-09-03). Important gotcha also confirmed: exporting a UDT
       *instance* does not include the UDT *definition* — must export
       from the "UDT Definitions" tab specifically to get the full
       type/member structure PLCHelper needs.
     - **Hard scope boundary (confirmed 2026-09-03) — never add missing
       sub-elements, never generate a missing-elements list either.**
       Doug explicitly does not want PLCHelper adding UDT members just
       because the AOI has a matching parameter — some omissions are
       deliberate (not every AOI parameter is needed for SCADA/HMI), and
       Doug does not want speculative "here's what might be missing"
       reports either ("I want to stay away from guessing what people
       need in the future"). **The task is fix-confirmed-bugs only**:
       apply the two confirmed patterns above (OPC Server name typo,
       member-name case mismatch) across every member that needs them.
       Never add, remove, or flag any member based on AOI/UDT parameter-
       set differences — that judgment stays with Doug, always.
       *(Corrected 2026-09-04 — the "two confirmed patterns" list above
       previously named the `{InstanceName}` parameter as the second
       pattern; that was retracted and was never a real bug, so pattern
       #2 is now the member-name case mismatch.)*
     - **Export received and moved in (2026-09-03)**:
       `CONSPD2_AOI UDT definition tags.json` — CLEAN scan, moved into
       `BlueSky` via the general auto-move rule. Ready for PLCHelper to
       apply the two confirmed fixes across every member.
     - Still not yet formalized as a task spec — hands-on with Doug per
       the same pattern as TASK_003 and the AOI Reference itself.

## Completed

*(none yet)*

---

*Last updated: September 15, 2026 (7th) — `FLOWVLV_AOI` promoted from built
to **LIVE-VERIFIED**. Doug's full Designer import and live-fire pass came
back clean on every step, including the one this type was most at risk on:
the import landed on `FLOWVLV2_AOI` with **no orphan** created under the L5X
name `FLOWVLV_AOI`. Both members were forced independently and each went
Active at Priority High and cleared. That makes **4 of 8 types
live-verified** (`ALARM_AOI`, `CONSPD4_AOI`, `FLOWIN3_AOI`, `FLOWVLV_AOI`),
3 unstarted, `INTERLOCK_AOI` excluded. Nothing pending on `FLOWVLV_AOI`
itself. The generator's per-member-priority gap remains open and unfixed —
still Doug's call, logged to the Daily Planner.
Prior update, September 15, 2026 (6th) — `FLOWVLV_AOI` built (4th type),
awaiting Doug's live test, so not done per Rule 5. Delivered as
`BlueSky/FLOWVLV2_AOI UDT definition with alarms 2026-09-15.json` —
**imported under the Ignition name `FLOWVLV2_AOI`, not the L5X name**, since
no Ignition definition called `FLOWVLV_AOI` exists and the L5X name would
have created an orphan. Pairing verified by count (38 = 38) and the build
copies the live definition's own `name` field rather than writing one. 2
alarms, 0 skipped, zero blank `notes`, both Boolean, **uniform `High` with
no split** — notable because it follows `FLOWIN3_AOI`'s per-member split, so
priority has now gone split then flat and genuinely cannot be inferred
between types. `FAIL_DEACT_alm`'s "Fail to deactuate alarm" spelling was
preserved verbatim rather than corrected. Fidelity-checked to differ by
exactly the 2 new `alarms` arrays. Also recorded: PLC/Ignition name
mismatches are the norm — 2 of 4 types built so far — with `VARSPD2_AOI` →
`VARSPD_AOI` the third known pair, still unbuilt.
Prior update, September 15, 2026 (5th) — `FLOWIN3_AOI` promoted from built
to **LIVE-VERIFIED**; Doug's full Designer import and live-fire pass came
back clean on every step. The one that mattered most: he forced a bit at
**each** priority level, and a High member went Active at Priority High
while a Medium member went Active at Priority Medium, both clearing
correctly — so the per-member split is confirmed to survive
`MergeOverwrite` and propagate to instances, not merely to have been written
correctly into the file. That makes **3 of 8 types live-verified**
(`ALARM_AOI`, `CONSPD4_AOI`, `FLOWIN3_AOI`), 4 unstarted, `INTERLOCK_AOI`
excluded. Nothing pending on `FLOWIN3_AOI` itself. The generator's
per-member-priority gap remains open and unfixed — it is Doug's call whether
to close it before the remaining 4 types, and it is logged to the Daily
Planner.
Prior update, September 15, 2026 (4th) — `FLOWIN3_AOI` built (3rd type),
awaiting Doug's live test, so not done per Rule 5. 6 alarms, 0 skipped, and
zero blank `notes` — the first type where every member has a real L5X
Description. All 6 confirmed Boolean. Fidelity-checked to differ from the
live export by exactly the 6 new `alarms` arrays. **First type with a
per-member priority** — High on `Hi_Alm`/`Lo_Alm`/`Xmtr_Alm`, Medium on
`UnderRange_Alm`/`OverRange_Alm`/`ChFault_Alm`, deliberately not a clean
process-vs-diagnostic split (Doug put `Xmtr_Alm` at High). That surfaced a
**new open capability gap**: the generator's `--alarms` path reads one flat
priority and cannot express a per-member value, so a future regenerate would
silently produce uniform High and drop the three Mediums. Not fixed — no
code change was in scope — but worth fixing before the remaining 4 types now
that priority is established as varying per member rather than per type.
Prior update, September 15, 2026 (3rd) — `CONSPD4_AOI` promoted from built
to **LIVE-VERIFIED**. Doug ran the full Designer import and live-fire pass
and every step passed: `MergeOverwrite` overwrite-in-place, landed on the
existing `CONSPD2_AOI` definition with no orphan, exactly 3 alarmed members
with `UnACK_Alm` carrying none, alarms inherited rather than local on real
instances with pre-existing overrides intact, and a forced bit went Active
at Priority High and cleared correctly. `CBAux_alm`'s blank `notes` showed
up as predicted and was confirmed expected. That makes **2 of 8 types live-
verified** (`ALARM_AOI`, `CONSPD4_AOI`) with 5 remaining and
`INTERLOCK_AOI` excluded. Nothing is pending on `CONSPD4_AOI` itself; the
two open items that touch it — `CBAux_alm`'s blank `notes` and the
unconfigured `Hartman_KC_Dairy_SCADA/BlueSky` gateway pipeline — are both
pre-existing and tracked separately, and neither blocks this type.
Prior update, September 15, 2026 (2nd) — TASK_012's `CONSPD4_AOI` built,
the 2nd of 8 types and the first use of the capability since the pilot went
live. No new code — the existing `--alarms` path pointed at a new type.
Delivered as `BlueSky/CONSPD2_AOI UDT definition with alarms
2026-09-15.json` (imported under the Ignition name, not the L5X name), with
3 alarms at priority `High` and `UnACK_Alm` correctly skipped — the first
time that standing exclusion actually fired, having been added ahead of
need during the pilot. Fidelity-checked to differ from the live export by
exactly the 3 new `alarms` arrays. Awaiting Doug's Designer import, so not
done per Rule 5. Corrected in the same pass (Rule 37 sweep): this file and
`PLCHelper_Tasks.md` both still described the `ALARM_AOI` pilot as awaiting
import when Doug had already live-verified it on 2026-09-15 and
`BLUE_SKY_STATUS.md` had recorded the result — and both still carried the
superseded `activePipeline` value `BlueSky` instead of the corrected
`Hartman_KC_Dairy_SCADA/BlueSky`. Two open items, neither a defect in this
work: `CBAux_alm` has no L5X Description so its `notes` is blank (second
instance of the `ALARM_AOI` gap; nothing invented), and the
`Hartman_KC_Dairy_SCADA/BlueSky` pipeline is not yet configured on the
gateway, so these alarms fire but notify nobody. 5 types remain.
Prior update, September 15, 2026 — TASK_012 moved from "design reported,
no code written" to capability-implemented with the `ALARM_AOI` pilot file
built. Doug answered all 5 Rule 16 design questions, closing the three
site-convention blockers (`activePipeline` = `BlueSky`, `priority` =
`High`, `UnACK_Alm` = excluded). `generate_ignition_udt.py` gained
`--alarms`/`--alarm-pipeline` plus the `ALARM_CONFIG` and
`ALARM_DEFINITION_EXCLUSIONS` tables, and a latent `OPTIONAL_MEMBER_KEYS`
bug (missing `alarms`) was fixed. Still open and explicitly NOT claimed
done per Rule 5: nothing has been imported into a real gateway or seen to
fire — that step is Doug's. One item needs Doug's decision: `ALARM_AOI`'s
`Alarm` parameter has no L5X Description, so the alarm's `notes` is blank
and nothing was invented to fill it. Prior update, September 10, 2026 —
added Open Work Item 1: TASK_003
(rung-comment scaling & TODO audit), moved here from
`BlueSky/BLUE_SKY_STATUS.md` since it's a PLCHelper capability rather
than Blue Sky-specific work — Blue Sky's own L5X/Instrument List remain
the first real-world input lined up for it once the agent matures enough
to run it. Prior update, September 4, 2026 (2nd) — corrected the direction of
Confirmed bug pattern #2's case example (Doug had initially reported it
backwards; double-checked directly in the PLC and confirmed the real
member is `Analog_hwai`, Ignition had the wrong `ANALOG_hwai`). Prior
update, same day: added Confirmed bug pattern #2 under
"Handoff to SCADA" (member-name case mismatch between the UDT's OPC Item
Path and the real AOI member name, diagnosed firsthand on Blue Sky's
`O2_FIT100`/`FLOWIN3_AOI`), including the `Error_Configuration` vs. bare
`Error` diagnostic distinction; this closes out the previously
undiagnosed "still-failing members" question, so Remaining scope was
narrowed to the cross-UDT sweep, and the Hard scope boundary's stale
reference to the retracted `{InstanceName}` pattern was corrected. Prior
update (Sept 3): logged the full AOI-to-UDT troubleshooting session
(confirmed bug pattern #1, a confirmed working fix, export format
decision) under "Handoff to SCADA."*
