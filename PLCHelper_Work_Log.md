# PLCHelper — Work Log
*Dated history of work done, failed attempts and fixes, decisions and lessons for PLCHelper itself (the tool, not any one job's use of it — job-specific detail goes in that job's own work log). Entries follow `claude-workflow/PROJECT_WORK_LOG_FORMAT.md` (Rule 41): newest first, add-only, no IP addresses, email addresses, or contact details. Git-tracked and pushed to GitHub — no client-confidential detail; PII scan (Rule 36) before every push.*

---

### 2026-10-29 — no job number — Three AOI lessons added
- **Work done:** Added an "AOI lessons (added 2026-10-29)" sub-list at the end of the "AOI conventions" section of `CLAUDE.md`: making a parameter Required forces every existing call to be edited (only Required parameters appear in a call's ladder text); latch SCADA command bits inside the AOI, ahead of its unlatch rung, when the AOI unlatches them every scan; update EditedDate (and TargetLastEdited) on a hand-edited AOI L5X or an import will not overwrite the existing AOI. Finished. Documentation only; no script changed.
- **What failed / what fixed it:** nothing.
- **Decisions:** Doug's: copy the day's client-neutral lessons to PLCHelper.
- **Learned:** nothing beyond the lessons themselves.
- **Open / follow-up:** nothing.
- **Billing note:** not job-specific; tool work.
- **Source:** Assistant session 2026-10-29 (PLCHelper subagent).

### 2026-10-29 — no job number — Three AOI conventions recorded as standing rules
- **Work done:** Added an "AOI conventions (Doug's standing rules, 2026-10-29)" section to `CLAUDE.md`, after "Naming conventions": parameters and local tags each kept in alphabetical order (with a caution to keep the Required parameters' existing order so existing call argument order is not broken); every local tag name starts with `_` and no parameter does; descriptions of `s`-suffix parameters begin with "PLC - to - SCADA" (scdi/scai) or "SCADA - to - PLC" (scdo/scao). A one-line pointer to this section was added in a client project's own CLAUDE.md (outside this repo). Finished. Documentation only; no script changed.
- **What failed / what fixed it:** nothing.
- **Decisions:** Doug's: write the rules once in PLCHelper and point to them from the project folder (Rule 9).
- **Learned:** nothing.
- **Open / follow-up:** nothing; applying the conventions to an existing AOI is a separate step.
- **Billing note:** not job-specific; tool work.
- **Source:** Assistant session 2026-10-29 (PLCHelper subagent).

### 2026-10-28 — no job number — Four rung-import and tag-description lessons added
- **Work done:** Added four client-neutral lessons from the day's PLC work to `CLAUDE.md` under "Editing L5X files": check every referenced tag against a fresh live-project export before building a rung export (added to the rung-structure working steps); translating an existing routine for another device; the Logix Designer 38.01 freeze on online multi-rung edits (Rockwell technote BF33049, corrected in 36.06/37.05/38.02); building a tag-description CSV from a communications list. Documentation only; no script changed.
- **What failed / what fixed it:** nothing failed in PLCHelper itself; the lessons come from the day's job work (detail stays in that job's own log).
- **Decisions:** Doug approved copying these four lessons into PLCHelper, written with no client, site, project or tag names.
- **Learned:** on Logix Designer 38.01, multi-rung imports are best done offline.
- **Open / follow-up:** nothing.
- **Billing note:** internal, no job number.
- **Source:** Assistant session 2026-10-28 (PLCHelper subagent).

### 2026-10-28 — no job number — Rung-structure lesson corrected to Rockwell-only
- **Work done:** Rewrote the "Rung structure" lesson in `CLAUDE.md` so it holds only what Rockwell's documents say (last instruction on a rung must be an output; input vs output definitions; compare = input, math/move = output; NOP behaves like an output), plus two working steps: finish a rung that has nothing to act on yet with NOP last, never NOP first; check the last instruction of every rung before finishing any rung edit or export. Documentation only; no script changed.
- **What failed / what fixed it:** the earlier entry below labeled NOP-last as "Doug's convention" and added an "every branch that carries an output" rule. Both removed.
- **Decisions:** Doug decided that where his wording differs from Rockwell, Rockwell is right. Rockwell has no rule that every branch ends in an output; parallel input branches are normal.
- **Learned:** NOP-last follows from Rockwell's rule that a rung must end in an output, so it is not a separate convention.
- **Open / follow-up:** nothing.
- **Billing note:** internal, no job number.
- **Source:** Assistant session 2026-10-28 (PLCHelper subagent).

### 2026-10-28 — no job number — Rung-structure lesson (NOP placement, rung endings)
- **Work done:** A rung export put NOP first on the rung. Researched Rockwell's own rung rules and added a lesson to `CLAUDE.md` under "Editing L5X files": check the ending of every rung and branch when writing rung text; NOP goes last per Doug's convention. Documentation only; no script changed.
- **What failed / what fixed it:** the current 1756-RM003 PDF was too large to fetch; the 2007 edition (1756-RM003I-EN-P) was used for instruction details.
- **Decisions:** Rockwell's rules and Doug's stricter convention are written separately, labeled.
- **Learned:** 1756-PM008J says the last instruction on a rung must be an output, and defines outputs to include copying data and calculating a value. 1756-RM003I says NOP can go anywhere on a rung — Doug's "NOP last" is a convention, not a Rockwell rule.
- **Open / follow-up:** NOP's formal input/output label not confirmed in text; whether Studio 5000 verify rejects a branch ending in an input not found in the manuals.
- **Billing note:** internal, no job number.
- **Source:** Assistant session 2026-10-28 (PLCHelper subagent).

### 2026-10-23 — no job number — New script to match PLC tags to an Ignition tag export
- **Work done:** Added `match_plc_tags_to_ignition_json.py` and `test_match_plc_tags.py`. The script takes a list of PLC tag names (xlsx or csv), strips a prefix, matches each name to an atomic tag in an Ignition tag JSON export, and writes a tag-map CSV in the columns `csv_to_ignition_opc_tags.py` reads, plus a review report. It supports skip names and excluded folders, never guesses (not found, duplicate and type mismatch are reported), and never overwrites an input. 13 tests with made-up fixtures pass, and the 12 existing TASK_014 tests still pass. Used once on a real job (details in that job's own work log) to bind 26 tags. Committed and pushed as `f03de1c`.
- **What failed / what fixed it:** nothing.
- **Decisions:** the match key and the folder exclusion are command-line inputs with no defaults, so nothing job-specific is hard-coded. Binding stays in the existing `csv_to_ignition_opc_tags.py`; the new script only builds the reviewed map.
- **Learned:** the binding script needs a template tag; one was built from an existing bound tag with the device name and path changed, which worked.
- **Open / follow-up:** nothing.
- **Billing note:** internal tooling, no job number.
- **Source:** Assistant session 2026-10-23 (PLCHelper subagent).

### 2026-10-21 — no job number — PLC comms array review skill added
- **Work done:** At Doug's direction, from a day of reviewing vendor data lists, a new skill `claude-workflow/Skills/plc-comms-array-review.skill.md` was added (15 working conventions for reviewing data arrays passed between PLCs), with a pointer line in `claude-workflow/AGENTS.md`'s PLCHelper entry and a one-line pointer in this folder's `CLAUDE.md` under "Tasks". Finished. Documentation only; no script changed.
- **What failed / what fixed it:** nothing
- **Decisions:** The content was drafted by Claude and corrected by Doug: word 0 is "often" used for control bits; BOOL arrays are "possibly not possible"; the client file default changes if the client's needs change; the instance versus input tag naming convention was explained by Doug. The content lives only in the skill file (Lesson 9); CLAUDE.md only points to it.
- **Learned:** nothing else.
- **Open / follow-up:** nothing
- **Billing note:** Internal, no job number.
- **Source:** Assistant session 2026-10-21 (PLCHelper subagent).

### 2026-10-19 — no job number — TASK_014: vendor comms-list PDF → tag-map CSV → Ignition OPC import JSON
- **Work done:** Built `pdf_comms_list_to_csv.py` (vendor "data communication list" PDFs → one reviewable tag-map CSV + issues report) and `csv_to_ignition_opc_tags.py` (reviewed CSV + existing tag export + one hand-bound sample tag → new import JSON binding each listed tag as a plain OPC atomic tag + build report), companion help files, `test_task014.py` (12 synthetic tests, all pass), and the TASK_014 catalog entry. Ran both on a client job's two lists and export: all comms sections parsed, none stopped; every tag the CSV could place was bound, with no data-type conflicts. Finished as tooling; the Ignition import itself is not yet validated (trial import pending with Doug).
- **What failed / what fixed it:** pdfplumber's table cells were unusable as rows on several pages (whole columns merged into one cell, matched only by order), so rows are rebuilt from word positions instead and the table cells are kept only as an order cross-check. First description-column detection took the most common word position and split multi-word tag names wrongly; fixed by taking the position after the widest gap in each row. A first units rule took a short remark as units; tightened to no digits / no "=", with the raw text kept in its own column.
- **Decisions:** Doug (approved plan): two scripts with a CSV between them; device name is a required argument per PDF, never guessed; counts must match per section or the section is stopped; exact-name Ignition matching only, near-misses flagged, not fixed. Coordinator (same day): build script 2 on Doug's real one-tag sample instead of a synthetic one; keep each base tag's name/folder/tooltip/engUnit, change only the binding properties; report base-vs-CSV data-type disagreements instead of choosing. Agent: a point is a row holding a type word followed by an address; direction left blank where the page header and the address array name disagree.
- **Learned:** Ignition's single-tag export of a dragged OPC tag carries only non-default properties (dataType, name, opcItemPath, opcServer, tagType, valueSource), so default deadband/scale/limit settings never need writing. Vendor lists can repeat an address, mix data types in one array, and reuse a bit-word element as a float; the scripts flag these for the vendor rather than choosing.
- **Open / follow-up:** Trial import in Ignition (TASK_014 Open Question 1); whether memory-tag `value` keys matter on an OPC tag (Open Question 2). Client-specific findings belong in that job's own work log (not written by this agent; reported to the Assistant session).
- **Billing note:** Built for a client job; the tool itself is internal.
- **Source:** Assistant session 2026-10-19 (PLCHelper subagent). Client detail removed for this git-tracked log.

### 2026-10-14 — no job number — Analog scaling, "RAW" and `_RS` convention recorded
- **Work done:** Added a new section "Analog scaling, "RAW" and `_RS` (Doug, 2026-10-14)" to `PLCHelper_Tasks.md` under TASK_013, directly after the existing `_RS` notes, and updated that file's Last-updated footer. Added a one-line pointer to it in CLAUDE.md's IO-list tag translation section, next to the Device Index pointer. Finished.
- **What failed / what fixed it:** nothing
- **Decisions:** Doug: the panel designer's IO lists end analog input descriptions with "RAW" and tag names with `_RS`, which is right for unscaled inputs scaled in the program. On module-scaled analog inputs (a channel setting maps 4-20 mA to engineering units) the PLC value is not raw, so Doug leaves `_RS`, "RAW" and obvious words like "transmitter" off what he writes. PLCHelper treats those differences as intentional (no flagging, no "fixing", no suggesting the IO list be corrected) and still transcribes verbatim when extracting. Placed in TASK_013 because the existing `_RS` and verbatim-transcription notes already live there; the new text agrees with them.
- **Learned:** The `_RS` suffix and "RAW" mark an unscaled analog input; they do not fit inputs the module scales itself.
- **Open / follow-up:** Future idea, not built: per-hardware knowledge of old-style vs. new-style analog inputs (recorded in the TASK_013 section).
- **Billing note:** Internal, no job number.
- **Source:** Assistant session 2026-10-14 (PLCHelper subagent), Doug's approved wording.

### 2026-10-05 — no job number — Ignition data storage tips added
- **Work done:** Added `Ignition_Data_Storage_Tips.md` to the repo root: general, de-identified lessons from a client investigation of a wrong stored value in Ignition daily/monthly data storage (current vs "Last" transactions, mixed PLC and gateway clocks, server/PLC time zone offset, duplicate tag folders, a day-1 month test in a tag event script, site-to-site setting differences, a stored zero after a rollover, and how to compare two sites). Each lesson is marked CONFIRMED or INFERENCE/THEORY. Finished.
- **What failed / what fixed it:** nothing
- **Decisions:** Doug: keep the tips in the job's own log during the investigation, then copy them here de-identified so they can be reused on other jobs. Placed in the repo root as a standalone file; no existing file covers Ignition transaction groups.
- **Learned:** nothing beyond the tips file.
- **Open / follow-up:** nothing
- **Billing note:** Internal, no job number (job-specific detail is in that job's own work log).
- **Source:** Assistant session 2026-10-05 (PLCHelper subagent). Client detail removed for this git-tracked log.
- **Later 2026-10-05 (Ignition 8.3.8 version note added) — work done:** Added a short "Ignition version in use (2026-10-05)" section at the top of `.claude/skills/ignition-designer-import/SKILL.md`: on a recent job both the Edge gateway (Ignition Edge 8.3.8, build b2026071409) and the standard gateway run 8.3.8, confirmed from the Designer's About box; the Edge gateway's activated module list; its history provider shown as "Edge Historian" in the Tag Editor; and a pointer that anything marked 8.1 only should be read with 8.3.8 in mind. Existing notes were not rewritten or re-verified. Finished.
- **Later 2026-10-05 (Ignition version note) — what failed / what fixed it:** nothing
- **Later 2026-10-05 (Ignition version note) — decisions:** Placed in the skill rather than CLAUDE.md or a new file, because the skill holds PLCHelper's Ignition notes and their 8.1/8.3 version statements, including the Core Historian note the open question bears on.
- **Later 2026-10-05 (Ignition version note) — learned:** A Historian Core 1.3.8 module is listed as activated on an Ignition Edge 8.3.8 gateway, which does not match earlier research notes (Core Historian as a full-gateway feature; Edge on the legacy internal historian).
- **Later 2026-10-05 (Ignition version note) — open / follow-up:** What Historian Core on Edge means for the Edge history provider is unresolved; recorded as an open question in the skill's version section.
- **Later 2026-10-05 (Ignition version note) — billing note:** Internal, no job number (job-specific detail is in that job's own work log).
- **Source (later bullet):** Assistant session 2026-10-05 (PLCHelper subagent), from the Designer's About box. Client detail removed for this git-tracked log.

### 2026-10-03 — no job number — Casne Programming Standards converted from Word to Markdown
- **Work done:** As part of re-checking every older `.docx` under the new intake rule, `Casne Programming Standards for PLC.docx` (Casne's own PLC programming standard, the source of the UDT naming convention in CLAUDE.md) was converted to `Casne Programming Standards for PLC.md` with `docx_to_md.py` (118 paragraphs, 13 document properties, no images, tables or hidden links; all checks matched) and the Word file was removed. The scan was CLEAN on a copy outside the repo (the scanner skips git-ignored files). A line was added to `.gitignore` so the `.md` stays out of the GitHub-pushed repo, as the `.docx` always was.
- **What failed / what fixed it:** The scanner skipped the converted file because the staging folder and the repo's `.gitignore` both exclude it, so it could not give a CLEAN result there; it was scanned from a neutral folder instead.
- **Also found and fixed:** the Rule 36 scan of this repo (the first full scan since the scanner learned to read Excel's list of commenters) flagged `BOP PLC_IO List  v0.5.xlsx`: an email-type user ID in `xl/persons/person.xml`. The file was committed on 2026-09-02, before the scanner read that part. The repo on GitHub is private. Doug: clean the file, but do not clean it out of the repo's history. The sanitizer redacted the one value (only that part was rewritten, everything else byte-identical, openpyxl re-opens the file), the re-scan was CLEAN, and the cleaned file was committed. The earlier version is still in the repo's history by Doug's decision.
- **Decisions:** Doug (2026-10-03): convert and replace. CLAUDE.md still names the source as the `.docx`; the file is now the `.md`. Doug: the repo is private and the history is not to be cleaned.
- **Learned:** nothing beyond the above.
- **Open / follow-up:** nothing
- **Billing note:** Internal, no job number.
- **Source:** Assistant session 2026-10-03.

### 2026-09-30 — no job number — Firmware note reordered; three notes added to CLAUDE.md
- **Work done:** Edited CLAUDE.md (finished, same day). (1) "Firmware as a network-communication troubleshooting step": rewrote the tooling step to the order that works on Compact 5000 I/O: in Logix Designer inhibit each I/O module (Module Properties > Connection > Inhibit), go offline, flash the modules first, flash the controller last, then uninhibit the modules. Added the reason and the output-module warning, and kept the old controller-first text under a dated "Corrected 2026-09-30" note. (2) Added a short note that RSLinx Classic and FactoryTalk Linx are both in use across Rockwell projects, and to ask or check which one a project uses before giving browse/driver instructions. (3) Added to the IO-list tag translation section: Studio 5000 tag names cannot contain "-", so a readability dash in an IO list or Device Index becomes "_" in the PLC tag, and a "." means a sub-element. (4) Device Index column conventions were already documented in PLCHelper_Tasks.md TASK_013, so CLAUDE.md got a one-line pointer there instead of a copy.
- **What failed / what fixed it:** The old firmware note gave the controller-first order. That is what made ControlFLASH Plus refuse the update with "target device is not in the proper mode" on 2026-09-22: a Compact 5000 I/O module rejects a firmware update while its owner controller holds an open connection to it, and Program mode keeps that connection open. Fixed by inhibiting the modules first.
- **Decisions:** Doug (2026-09-30): change the firmware note to the inhibit-first order, modules before controller; add the RSLinx Classic vs. FactoryTalk Linx note, generic (which client uses which belongs in that client's own CLAUDE.md); add the dash rule to the tag-translation section; document the Device Index conventions (first column `PLC`; Notes left blank for Doug and not copied from the panel designer's file; Tagname in dash form for reading, real PLC tag uses underscores; Rack 0 for the local rack; Type carries the IO list's literal labels such as `HART - P` / `HART - S`), pointing to an existing home if there is one.
- **Learned:** Inhibiting an output module drives its outputs to their configured Program-mode state, so check the physical effect before inhibiting.
- **Open / follow-up:** nothing
- **Billing note:** Internal, no job number.
- **Source:** Assistant session 2026-09-30.
- Correction (2026-09-30): the RSLinx vs. Linx note described above was NOT added to CLAUDE.md — the edit was blocked by the permission classifier and is still to be done (Doug approved it). The firmware-note reorder, the dash rule and the Device Index pointer were made as described.
- Resolution (2026-09-30), from Doug: the plc-helper GitHub repo is private. The two client-named spreadsheets tracked since 2026-08-27 stay as they are. The pre-push PII scan flagged an email address in one of them (not new in this push); Doug reviewed it and chose to leave it, so the two local commits were pushed.
- Update (2026-09-30): the RSLinx vs. Linx note was added to CLAUDE.md after all, in the retry later that day.

### 2026-09-24 — no job number — TASK_013: extracting equipment IO points into a job's Device/Tags index
- **Work done:** Created TASK_013 in `PLCHelper_Tasks.md`: extract a named piece of equipment's IO points from the job's IO list into that job's Device/Tags index. First run was one equipment (6 points); then bulk mode was added and run for whole sheets (three sheets in all, about 140 rows). Rules recorded in the task: verbatim transcription of names and descriptions as the IO list's author typed them; match existing rows on prefix + loop + letter + suffix, not on Tagname; dry run first and check counts; report differences with existing rows but never change them; the `PLC` value and the rack are confirmed with Doug for each sheet, never taken from the sheet name or the previous sheet; tags with no separator are split from the Equipment ID only if it joins back exactly, otherwise held back and flagged. Commits: bf3a4e5, a0aff3b, 0919bee, f65aa68, 8641ebf, 9011e3b (PII scan CAUTION each time for two `.gitignore` files, reviewed and cleared).
- **What failed / what fixed it:** The first bulk pass on a second sheet used the wrong `PLC` value, which showed up as many points at the same slot and channel as another sheet. Fixed the same day, and the task now says to compare slot and channel against sheets already extracted and to confirm the value. One push failed with a GitHub server error and succeeded on retry.
- **Decisions:** Doug: copy rows verbatim; he removes things like an `_RS` suffix himself when he types the tag into the PLC. Doug: IO extraction is not to be scripted, because people name things on the fly at the panel. Doug: when he says to use PLCHelper, use PLCHelper, so learnings are kept in its catalog.
- **Learned:** Different people name the same thing differently during development; flag it and fix it without ceremony. `PLC` and rack are per-sheet facts.
- **Open / follow-up:** nothing
- **Billing note:** Internal, no job number (job-specific detail is in that job's work log).
- **Source:** Assistant session "Assistant 1.07" (transcript read 2026-10-01), PLCHelper subagent reports. Client detail generalized for this git-tracked log.

### 2026-09-22 — no job number — CLAUDE.md: IO-list tag translation, AI diagnostic bits, two IO-wiring methods, firmware note
- **Work done:** Added the section "Analog input diagnostic bits and I/O-wiring convention" to CLAUDE.md, dictated by Doug (3235e22). It covers: flattening a panel designer's `TAG.SUFFIX` to `TAG_SUFFIX` with a per-project PLC prefix when there are several PLCs; AI-only Overrange/Underrange/Fault bits, best effort because modules differ; and two wiring methods: the "blanket" per-IO-type staging routines, and the Casne method of direct aliases referenced once in the AOI call, which is Doug's preference. Added "Firmware as a network-communication troubleshooting step" (c675b06).
- **What failed / what fixed it:** Claude first wrote the diagnostic bits as a guaranteed rule. Doug corrected it: "more like what I wish we could do". Later the same day, a firmware update on a client controller was refused until the I/O modules were inhibited (details in that job's log).
- **Decisions:** Doug: document both wiring methods and name the Casne alias method as preferred. Project-specific prefix values belong in the job's own CLAUDE.md, not here.
- **Learned:** Doug: Studio 5000 tag names can't contain "-", so a human-readable dash becomes "_" in the PLC. A dot in a tag means sub-element.
- **Open / follow-up:** Doug approved changing the firmware section to the inhibit-first order on 2026-09-30; the change was made the same day (see the 2026-09-30 entry). Doug's RSLinx vs. Linx note was never written (see report).
- **Billing note:** Knowledge from a client job; documentation is internal, no job number.
- **Source:** Assistant session "Assistant 1.06" (earlier run, transcript read 2026-09-30), PLCHelper subagent report. Client detail generalized for this git-tracked log.

### 2026-09-15 — no job number — TASK_012: alarm-embedded UDTs for 6 more AOI types; generator per-member priority gap found
- **Work done:** Used the existing `--alarms` capability and the surgical-build method to produce alarm-embedded UDT definitions for six more AOI types on a client job. There was no code change and no version bump. Commits, all pushed: a97dfea, 4c5ac9d, 31b6a23, 653d01a, d05cd04, df28241, 86b753d, 7edd3d3, b75b1ea. Before each push the PII scan returned CAUTION for two `.gitignore` files; both were reviewed and cleared. Also fixed stale PLCHelper docs: they still called the pilot unverified and still used the old pipeline shorthand. Committed `PLCHelper_Executive_Summary.md` (3180dab), which had been untracked since 2026-09-10; this closes that loose end from the 2026-09-10 Assistant log.
- **What failed / what fixed it:** The client asked for per-member priority splits on two types, which exposed a gap. `generate_ignition_udt.py --alarms` reads a single flat `ALARM_CONFIG['priority']`, so it cannot express per-member values. The splits were applied by hand in the surgical build. Regenerating those two types with `--alarms` would silently flatten them to one priority. This is documented, not fixed.
- **Decisions:** Doug: alarm priority is asked for each type and never carried over from the previous type.
- **Learned:** The native-UDT (`--datatype`) path shares the single `build_member()` call site with the AOI path, so alarms work there with no extra code (checked in the code, not assumed from an old note). The UnACK_Alm exclusion table was used for the first time. Several members can each carry an alarm named "Alarm" without colliding, because names only need to be unique per tag. PLC and Ignition type names often differ (3 of 7 types). Verify the pairing by member count, and copy the live definition's name rather than typing it.
- **Open / follow-up:** Daily Planner, Casne Admin: flagged decision on the generator's per-member priority support. PLCHelper_Tasks.md TASK_012.
- **Billing note:** Built and run for a client job (logged in that job's work log); the tool itself is internal.
- **Source:** Assistant session "Assistant 1.02" (transcript read 2026-09-30), PLCHelper subagent reports.

### 2026-09-11 — no job number — Tag generator: 3 more AOI types verified, one import failure diagnosed; Perspective know-how; /doctor trim
- **Work done:** Ran `generate_ignition_tags.py` for three more AOI types on a client job and promoted each to export-verified after Doug's Designer import (commits 8ae9974, e0b2a13, d347805, 014680f). A fourth type was generated and passed structural checks (1a59088) but failed on import. Root cause documented (47f8600, 17dd59a) and the task catalog marked it blocked (931c144). Added TASK_011: a "Broader use case" note per AOI, documentation only, first entry for CONSPD4_AOI (e7381b8). Added Perspective sections to the `ignition-designer-import` skill: tag drop configuration (`dropConfig`) (c7a9b78), view vs root custom properties (ed4544b, d8b6ec1), and Embedded View binding scope and tooltip convention (b1b3174). `/doctor` moved 68% of PLCHelper CLAUDE.md (40,845 to 13,402 characters) into that skill; left uncommitted on purpose for Doug to review.
- **What failed / what fixed it:** The import error `Bad_Unsupported(... does not have item 'EnableIn' for overrides, and cannot accept children tags)` meant the hand-built Ignition UDT had different member names from the L5X parameters the generator emits. A UDT instance cannot hold a member its definition doesn't declare. Proposed fix: remove the per-instance `tags` array and re-import with MergeOverwrite. Not applied.
- **Decisions:** Doug: TASK_011 is a written reference in `PLCHelper_Reference.md`, not a tool and not in the status file. Doug: the generator's `--udt-name` stays always-explicit (open question closed without changing anything).
- **Learned:** CONSPD4_AOI is used for any on/off device that can fail to run, not only motors. The member stubs the generator emits for each instance carry no information and are the only part that can raise this error. The Designer's Property Picker produces the correct binding path (see the client job's log).
- **Open / follow-up:** ASSISTANT_STATUS.md: the uncommitted CLAUDE.md and skill edits from `/doctor`. PLCHelper_Tasks.md TASK_005: the import fix and the 3 remaining AOI types.
- **Billing note:** The generator runs were client work under the client job's number (logged in that job's work log); the tool improvements are internal.
- **Source:** Assistant session "Assistant 1.00" (transcript read 2026-09-30).

### 2026-09-10 — no job number — generate_ignition_tags.py (TASK_005) first build; AOI-to-UDT name mapping
- **Work done:** Wrote the TASK_005 spec with Doug (d9e44e2, 36a95d9). Built `generate_ignition_tags.py`. It creates Ignition UDT instances from AOI uses in an L5X and requires `--dest-folder`, `--device-name` and similar inputs every run. First run: 31 instances of one AOI type, checked field by field against a real Ignition export; Doug imported it successfully (16b51f5, 862f3b2). Added `--udt-name` so the PLC AOI name and the Ignition UDT name can differ, and removed a hard-coded mapping table (9604c40). Added the script + help-file naming convention to CLAUDE.md (13f042f). Saved the Ignition gateway-reset tip (gwcmd.bat) to CLAUDE.md (8a14649). Moved TASK_003 here from a client job's status file, and logged the PROCESSOR_STATUS array-mapping notes in PLCHelper_Status.md.
- **What failed / what fixed it:** Pushed a partial spec (36a95d9) while Doug was still answering; see the Assistant log. The generated `Description` differs from the reference export on purpose. Doug confirmed that is the intended result.
- **Decisions:** Doug: the AOI types to run are an explicit list he supplies, never guessed by the script. Test one AOI type at a time first; the end goal is one big JSON. Doug: the destination folder is always asked, never defaulted. Doug: in the PLC, `CONSPD<n>_AOI` always maps to the Ignition UDT `CONSPD2_AOI`, so PLC version bumps don't force Ignition changes. Doug: each script gets a help file named with the script's name as a prefix.
- **Learned:** An Ignition tag import file cannot choose its own destination folder. A key missing from an export means "not overridden", not "blank". The `{"tags": [...]}` wrapper is required.
- **Open / follow-up:** PLCHelper_Tasks.md TASK_005 (where the AOI list lives; sharing L5X parsing with TASK_004).
- **Billing note:** Built for, and run on, a client job (logged in that job's work log); the tool itself is internal.
- **Source:** Assistant session "Assistant 1.00" (transcript read 2026-09-30).
