# PLCHelper — Task Catalog
*The reference for "what does TASK_00X actually do" — read this instead of trying to remember.*
*CLAUDE.md holds standing project conventions (naming, L5X structure, design patterns). This file holds the task write-ups.*

---

## Task Write-Up Format

Every task in this file follows the same shape:

- **Task ID / Name**
- **Status** — one of:
  - `Idea` — described but not fully speced
  - `Spec Ready` — fully speced, not yet implemented (waiting on an
    input file, or on this format itself being new)
  - `Implemented` — has been run successfully at least once
  - `Retired` — no longer a separate task (folded into standing
    CLAUDE.md conventions, or superseded)
- **Purpose** — why this task exists, what problem it solves
- **Inputs** — exact files/data needed, and where they typically live
- **Process** — the actual step-by-step method
- **Outputs** — what you get at the end
- **Open Questions** — anything not yet nailed down; resolve before
  moving a task from `Spec Ready` to `Implemented`

Write the spec first (this file). Build the actual skill/prompt second,
once the spec is solid.

---

## Task Catalog

| ID | Name | Status | One-line description |
|---|---|---|---|
| TASK_001 | Document data structures for SCADA designer | Implemented (as a Skill) | Moved out of PLCHelper into `claude-workflow/Skills/plc-aoi-reference-creation-and-update.skill.md` — reusable across sessions instead of a loose local file |
| TASK_002 | Audit PLC | Spec Ready | Cross-reference IO list, PLC tag database, and PLC code to find discrepancies |
| TASK_003 | Rung-comment scaling & TODO audit | Spec Ready | Find every `@`-marked TODO comment and every filled-in 4-20mA scaling comment, resolve each to its field-instrument tag via AOI context, cross-check against the Instrument List |
| TASK_004 | Generate Ignition UDT definition from an AOI | Implemented | Given an AOI type name, an L5X export, and a reference UDT JSON, generate a brand-new Ignition UDT definition JSON with one member per AOI parameter — every parameter, no exclusions — with History enabled on the members matching the Historization rule |
| TASK_005 | Generate Ignition tag instances from AOI usages with valid UDTs | **`ALARM_AOI` + `CONSPD4_AOI` + `FLOWIN3_AOI` Implemented and export-verified; `FLOWVLV_AOI` Implemented, structurally verified only (2026-09-11), awaiting Designer import; other 4 AOI types still Idea** | Job-agnostic like TASK_004/009/010. Given a fresh L5X export and an explicit, Doug-supplied list of AOI types with a confirmed-working UDT (not inferred by the script), find every AOI *instance* of a qualifying type and emit its Ignition `UdtInstance` entry, all combined into **one consolidated JSON**. `DeviceName` is one value for the whole run; `Description` is looked up per instance from that instance's own L5X description (blank is a valid value); `EngUnit` is created but left blank. Destination folder is always an explicit input, never hardcoded. Implemented 2026-09-10 as `generate_ignition_tags.py`; first run produced **31 `ALARM_AOI` instances**, verified field-by-field against a real Ignition export. The per-AOI parameter mapping is recorded for all 8 types but **only `ALARM_AOI` is verified** — the script warns on the rest. Auto-populates missing tag instances instead of building each by hand in Designer. |
| TASK_006 | Audit Ignition tags for orphaned/unmatched instances | Idea | Given a real export of existing Ignition tags (e.g. all `O2_`-prefixed instances) and a fresh L5X, find any Ignition tag with no matching real tag in the current PLC program and flag it for Doug's review — never auto-deletes or auto-resolves. The reverse direction of TASK_005: TASK_005 fills in what's missing, TASK_006 finds what shouldn't be there. |
| TASK_007 | Bulk-update a derived convention across an existing UDT's members | Idea | Given an existing UDT definition JSON and a convention field (e.g. `opcServer`) plus a new value, update that field across every member in one pass — for when a different client/site uses a different OPC Server connection name than the one baked into Blue Sky's references. Not urgent; raised while confirming the OPC Server convention is already applied as one uniform value, not per-member. |
| TASK_008 | Generate Ignition UDT definition from a native PLC UDT | Implemented | The same operation as TASK_004 but sourced from a native Rockwell UDT (`<DataType Class="User">`) instead of an AOI — for handoff-checklist items like `MODVLV` that turn out not to be AOIs at all. One member per **visible** UDT member; Studio 5000's hidden `ZZZZZZZZZZ*` bit-packing backing members are excluded, and the visible `BIT` bit-alias members are included as Booleans. Conventions, historization, and data-type mapping are shared with TASK_004, unchanged |
| TASK_009 | Audit Ignition alarm tag configuration for formatting problems | Implemented, patched, and re-run (all 9 rules live) | Given an export of one site's alarm tags (Weston first), check every alarm against 9 correctness rules (pipeline validity, blank email overrides, enabled, folder-based priority match, tagGroup, name/displayPath consistency, historian config) and produce an alphabetized report of problems — read-only, no fixes. Unblocked 2026-09-09: root cause confirmed for `AlmLIT107_HiHi_Alm` (CS0175981) via Andrew's actual received email plus a cross-site comparison across 921 alarms / 8 sites. Implemented same day as `audit_alarm_tags.py`; first run flagged all 143 Weston tags with 356 problems under the original 8-rule/looser-priority version. Rules 5 and 9 were then tightened going through those findings with Doug line by line, and the script was patched and re-run the same day: **143 tags, 0 OK, 367 problems** (+1 priority override, +10 historian config). |
| TASK_010 | Fix flagged Ignition alarm tag configuration problems | Implemented | The companion tool to TASK_009 — applies the corrections the audit flags, for rules 2–9 only (rule 1 `notes` is never auto-fixed, only flagged for Doug). Implemented 2026-09-09 as `fix_alarm_tags.py`; it emits a brand-new corrected export JSON and never writes to its input. Correctness is not restated — it `import`s `audit_alarm_tags` and uses that module's own tables, so the two tools cannot disagree about what "correct" means. First real run on Weston: **143 tags, 367 fields changed** (matching the audit's 367 problems exactly), and re-auditing the corrected output reports **0 problems / 143 OK**. ⚠ Import the output with Collision Policy **`Overwrite`**, not `MergeOverwrite` — rule 9 works by *removing* keys, and MergeOverwrite treats a missing key as "leave alone." Each site's pipelines are still verified independently: an unconfirmed site leaves `activePipeline` untouched rather than guessing. |

---

## TASK_001 — Document data structures for SCADA designer

**Status:** Implemented — as a Skill, not a PLCHelper-local task (corrected 2026-09-02)

Originally a standalone paste-in task file (`TASK_001.md`) inside
PLCHelper, renamed `zz delete TASK_001.md` by Doug on 2026-08-27 and
deleted 2026-09-02 — but this was NOT a retirement, it was a move.
The same day it was marked for deletion, its exact step-by-step
methodology was written into `claude-workflow/Skills/plc-aoi-reference-creation-and-update.skill.md`
word-for-word, making it a proper reusable Skill instead of a loose
file inside one project's folder. `PLCHelper/CLAUDE.md`'s "Reference
document conventions" section is a separate, condensed summary of the
same convention — not the authoritative copy. **The skill file is the
authoritative version of TASK_001's methodology.** This entry exists so
the TASK_001 ID points somewhere real if it's ever referenced again.

---

## TASK_002 — Audit PLC

**Status:** Spec Ready (not yet implemented)

### Purpose

Cross-reference three sources of truth against each other to find
discrepancies, orphaned tags, unanswered questions, and scope errors.
Replaces a manual audit process that is time-consuming and error-prone.

### Inputs

| Input | Format | Notes |
|-------|--------|-------|
| IO list | Excel (.xlsx) | Hand-maintained by engineer. Rich document with many columns — structure varies by project. Share at task build time. |
| PLC tag database | CSV export from Studio 5000 | Contains real tags, UDTs, IO tags, aliases, and rung comments. Lot of noise — must filter carefully. |
| PLC code | L5X export of full program | Full program export, not individual AOI files. |

### Process

**Three bidirectional cross-references:**

1. **IO List ↔ PLC Tag Database** — every device on the IO list should
   have corresponding tags in the controller tag database, and vice versa.
2. **IO List ↔ PLC Code** — every device on the IO list should appear
   somewhere in the PLC code, and every IO tag used in the code should
   be on the IO list.
3. **PLC Tag Database ↔ PLC Code** — every tag in the database should
   be used somewhere in the code, and every tag referenced in the code
   should exist in the database.

**Loop identifier matching** — the matching key between all three
sources. Loop identifiers can be numeric loop numbers (e.g. `1234`,
`023`) or alphanumeric equipment abbreviations (e.g. `FLR`, `UPS`,
`GEN`) — see the Equipment abbreviation lookup table in `CLAUDE.md`. Any
identifier matching neither pattern is flagged for engineer review.

**PLC tag database — tag types to process:**

| Type | Action |
|------|--------|
| Real tags | Include |
| UDT instances | Include |
| IO tags | Include |
| Aliases | Include |
| Rung comments containing a question or unresolved note | Flag as "unanswered question" |
| All other rung comments | Ignore |

Unresolved-note phrases: "ask", "what", "why", "todo", "fix", "check", "?", or similar.

### Outputs

Audit flags:
- Device on IO list with no matching tags in PLC tag database
- Tag in PLC tag database with no match on IO list
- Device on IO list with no appearance in PLC code
- IO tag used in PLC code with no match on IO list
- Tag in PLC tag database not used anywhere in PLC code
- Tag referenced in PLC code not found in tag database
- Tags that are program scope instead of controller scope
- Loop identifiers not matching any numeric pattern or known abbreviation
- Rung comments containing unanswered questions

### Open Questions / Notes

- IO list column structure varies by project — inspect the file at
  runtime to identify the column containing the device/loop identifier
- The audit is read-only — it flags issues but does not make changes
- Program scope tag findings should be reviewed carefully before any
  changes are made in Studio 5000
- Additional audit features may be added as they are discovered

---

## TASK_003 — Rung-comment scaling & TODO audit

**Status:** Spec Ready (blocked on Doug exporting the combined program as L5X)

### Purpose

Doug marks unresolved items directly in rung comments with an `@`
symbol (e.g. `@ document Speed Feedback scaling here when known`) as he
codes, since the real transmitter range often isn't known yet at write
time. This task finds every one of those markers — plus scaling
comments he's already filled in — and cross-references them against the
project's Instrument List, so nothing gets forgotten and nothing
conflicts silently.

### Inputs

| Input | Format | Notes |
|-------|--------|-------|
| PLC program | L5X (full combined BOP+O2 bench program) | Confirmed L5X export is available (2026-09-02) — use this, not L5K; PLCHelper's whole methodology assumes L5X. |
| Instrument List | Excel (.xlsx), job-specific | Lives in the job's own project folder (e.g. `BlueSky\A3 Blue Sky Dairy - Instrument List djs copy.xlsx`), NOT copied into PLCHelper — this task reads it cross-folder so PLCHelper stays reusable across jobs. Column F ("Range") is the calibration/scaling data. Watch for: section-header rows mixed into the data (skip these), and rows covering a pair of tags (e.g. `PT-010A / B` as one row for both A and B). |

### Process

1. **Collect every `@` comment.** Scan all rung comments in the L5X for
   the `@` symbol. Do not assume they're all about scaling — collect
   every one and note its topic (e.g. "scaling," "alarms not yet
   commissioned," or whatever else turns up). Doug has confirmed these
   are mixed-topic TODO markers, not scaling-specific.
2. **Collect already-filled-in scaling comments.** Separately scan for
   rung comments stating an explicit scaling formula without an `@`
   (e.g. "4 to 20 mA = 0 to 15 psig") — these are ones Doug has already
   resolved in code and wants checked, not just found.
3. **Resolve each comment to its field-instrument tag via AOI context —
   never by searching the comment text for a tag name.** The comment
   text does not name the tag (confirmed by example: "Speed Feedback"
   describes the `SpeedFB_hwai` parameter of a `VARSPD2_AOI` instance,
   which resolves to tag `BOP_BL_1_SPD_FBK`). This means: identify which
   AOI instance the comment sits on, find the specific parameter it's
   describing, then read that parameter's mapped tag.
4. **Multiple AOI types are involved, not just one.** `VARSPD2_AOI`
   (VFD blocks) is one; a straight analog-transmitter scaling AOI is
   another (name TBD — discover from the actual L5X, don't assume);
   `INTERLOCK_AOI` is generic and not relevant to scaling at all. Build
   the AOI-type list from what's actually in the file.
5. **Look up the resolved tag in the Instrument List.** Match against
   the Tag column (handling combined `A / B` rows). Skip devices with
   `Range = "-"` (digital-only, no scaling applies).
6. **Categorize:**
   - `@` scaling comment + Instrument List has a Range → ready to fill in
   - `@` scaling comment + no Instrument List match → no source found
     yet (not necessarily "ask the client" — some resolved tags, like
     VFD-internal speed feedback, may just never be field instruments
     the Instrument List tracks; distinguish "genuinely missing" from
     "wrong kind of thing to look for here")
   - Already-filled-in comment + matches Instrument List → confirmed correct
   - Already-filled-in comment + does NOT match Instrument List →
     **mismatch, flag for review** (this is a real find, not a false positive)
   - Non-scaling `@` comments (e.g. "alarms not yet commissioned") →
     list separately by topic, do not force into the scaling analysis

### Outputs

A structured report, categorized per Step 6 above — likely best saved
as a dated file in the job's own project folder (e.g. `BlueSky`), not
in PLCHelper, since the result is job-specific even though the method
is generic.

### Open Questions

- Exact set of AOI types carrying scaling-relevant parameters — to be
  discovered from the real L5X, not assumed in advance.
- Whether "no Instrument List match" cases (like VFD speed feedback)
  need a second data source later (e.g. VFD datasheets) or are simply
  out of scope for this task permanently.
- Whether "alarms not yet commissioned" and other non-scaling `@`
  topics deserve their own future task once enough examples accumulate
  — for now this task just surfaces and categorizes them, does not act
  on them.

---

## TASK_004 — Generate Ignition UDT definition from an AOI

**Status:** Implemented (2026-09-04) — script: `generate_ignition_udt.py`

### Purpose

At Casne, every AOI type used in a PLC job is mirrored on the Ignition
side by a UDT (User Defined Type) whose members correspond to that AOI's
parameters. Building those UDTs by hand — one member at a time, in
Ignition Designer — is slow and produces exactly the class of errors
already documented in `PLCHelper_Status.md` under "Handoff to SCADA":
an OPC Server name typo (confirmed bug pattern #1) and member-name
case mismatches (confirmed bug pattern #2). Both are single-character
mistakes that produce confusing, misleading Ignition errors.

This task removes the manual step entirely: point it at an AOI type and
a fresh L5X export, and it emits a complete, ready-to-import Ignition
UDT definition JSON. Because the member names and OPC Item Paths are
generated directly from the L5X, both confirmed bug patterns become
structurally impossible rather than something to catch later.

### Scope decision — include EVERY parameter, always (Doug-approved, 2026-09-04)

**This task generates one member for every single parameter of the AOI.
No exclusions. No filtering. No judgment about which parameters are
"needed for SCADA/HMI."**

This is a deliberate, explicitly Doug-approved exception to the general
"never guess which parameters to include" principle, and it applies to
**this one operation only** — generating a brand-new UDT from scratch.
Doug's reasoning: he was unable to identify any actual benefit to
excluding parameters from a new UDT, and the manual filtering step was a
recurring source of error and rework.

**How this relates to the Hard scope boundary in `PLCHelper_Status.md`:**
that boundary — never add members to a UDT, never generate a
"missing members" list — remains fully in force for *correcting an
existing* UDT. The distinction is:

| Operation | Rule |
|---|---|
| Correcting an **existing** UDT | Never add/remove/flag members based on AOI-vs-UDT differences. Fix confirmed bugs only. Judgment stays with Doug. |
| Generating a **brand-new** UDT (this task) | Include every AOI parameter. No filtering. |

The reason these don't conflict: an existing UDT's omissions may be
deliberate engineering decisions, and overriding them would be guessing.
A brand-new UDT has no such decisions embedded in it yet — so the
complete parameter set is the only non-speculative starting point, and
Doug can delete what he doesn't want in Designer afterward. Deleting a
member Doug can see is cheap; discovering a missing member months later
via a broken Ignition screen is not.

The `[exclude]` marker convention in `CLAUDE.md` is a
**reference-document** convention (which parameters get documented in
the Casne AOI Reference) and is deliberately **not** consulted by this
task.

### Inputs

| Input | Format | Notes |
|-------|--------|-------|
| AOI type name | string | e.g. `FLOWIN3_AOI`. Must match the `Name` attribute of an `AddOnInstructionDefinition` in the L5X exactly. |
| L5X export | `.L5X` (XML) | Full program export from Studio 5000. Lives in the **job's own folder** (e.g. `BlueSky\`), read cross-folder — never copied into PLCHelper, same pattern as TASK_003, so PLCHelper stays reusable across jobs and no client content enters this repo. |
| Reference UDT JSON | `.json` | An existing Ignition UDT **definition** export, used only to learn *conventions* — OPC Server value, OPC Item Path template shape, member JSON structure, top-level type structure. Its actual member data is never copied. Must be exported from Ignition's **"UDT Definitions"** tab; exporting a UDT *instance* does not include the definition. |

### Process

1. **Parse the L5X** for the named `AddOnInstructionDefinition` and read
   its `<Parameters>` block. Each `<Parameter>` carries `Name`,
   `DataType`, `Usage` (Input/Output/InOut), `Required`, `Visible`,
   `ExternalAccess`, `Radix`, and an optional `<Description>` CDATA.
   Take the parameter list in **document order** — that is the order the
   engineer sees in Studio 5000.
2. **Parse the reference UDT JSON** to derive conventions rather than
   assume them:
   - **OPC Server** — the value used by its members. Verified in the real
     files as `Ignition OPC UA Server` (**no hyphen**). The hyphenated
     `Ignition OPC-UA Server` is confirmed bug pattern #1 and produces
     `Error_Configuration("Server ... does not exist.")`.
   - **OPC Item Path template** — derived by taking each reference
     member's `opcItemPath.binding` and replacing that member's own name
     with a placeholder, then using the **most common** result. Verified
     shape: `ns=1;s=[{DeviceName}]{InstanceName}.<MemberName>` with
     `bindType: "parameter"`.
   - **Member JSON shape** — the **most common key set** across the
     reference's members, which is the minimal correct member. Optional
     per-member extras (`historyEnabled`, `historyProvider`,
     `historyTagGroup`, `historyMaxAge`, `sampleMode`,
     `historicalDeadbandStyle`, …) are stripped out of that key set, so a
     reference member's own history settings can never leak onto an
     unrelated generated member. Generated members get their history from
     the Historization rule below instead — except for the storage
     provider and historical tag group, which *are* derived from the
     reference's historized members as a convention.
   - **Top-level type shape** — `tagType: "UdtType"`, plus the
     reference's `parameters` block (e.g. `DeviceName`, `Description`),
     `tagGroup`, permissions, and `dataType`.
3. **Map each PLC data type to its Ignition equivalent.** Mapping
   confirmed empirically against the real files (see Data type mapping
   below), not from generic docs.
4. **Emit one member per parameter**, with:
   - `name` set to the AOI parameter name **verbatim, case included** —
     no capitalization changes of any kind
   - `opcItemPath.binding` built from the derived template with the same
     verbatim name substituted in
   - Because both come from the same L5X string, the member name and the
     path can never disagree in case — confirmed bug pattern #2 is
     eliminated by construction.
5. **Apply the historization rule** to each member by name — see
   "Historization rule" below. Matching members get History enabled with
   the settings for their signal type; every other member gets no history
   keys at all.
6. **Write the output JSON** into the **job's own folder**, never into
   PLCHelper.

### Data type mapping (confirmed from real files, 2026-09-04)

| PLC (L5X) | Ignition | How confirmed |
|---|---|---|
| `BOOL` | `Boolean` | 24 of 25 BOOL members in the real reference UDT |
| `BIT` | `Boolean` | 21 of 21 (added 2026-09-08 for TASK_008 — see below) |
| `DINT` | `Int4` | 3 of 4 DINT members |
| `REAL` | `Float4` | consistent, no counterexample |
| `SINT` / `INT` | `Int4` | inferred from the DINT integer mapping — flagged in the report when hit, not silently assumed |
| `STRING` | `String` | observed in the real instance exports |

`BIT` only ever appears in a **native UDT** (TASK_008), never in an AOI
parameter list — it is the data type Studio 5000 gives a single aliased
bit of a hidden integer backing member. Confirmed the same empirical way
as the rest of this table rather than assumed: of MODVLV's 24 visible
`BIT` members, the 21 that also exist in the real MODVLV Ignition UDT
export are `Boolean` in all 21 cases, with **zero counterexamples** — a
cleaner agreement than the original `BOOL` confirmation. It is also the
only type that *could* be correct for a single bit.

**The reference UDT contains its own data-type errors** — found while
deriving this mapping: `AutoCall_INTRLK_scdi` is `BOOL` in the PLC but
`Int4` in the UDT, and `AUTO_STATUS_scai` is `DINT` in the PLC but
`Float4`. These are hand-entry mistakes in the coworker-built UDT, not
conventions. The mapping is therefore **fixed in the script from the
confirmed-correct majority**, and is *not* learned per-member from the
reference — learning it per-member would faithfully reproduce the bugs.
Any PLC data type the script has no confirmed mapping for is reported as
a warning rather than guessed.

### Historization rule (Doug-supplied and confirmed 2026-09-04, implemented; extended 2026-09-08)

A generated member gets History enabled **only** if its name
(case-insensitive) matches one of these. Nothing else is historized, and
no other suffix, bare word, or pattern is inferred:

| Match | Signal type |
|---|---|
| **ends with** `_hwai`, `_hwao`, `_scai`, `_scao` | **analog** |
| **ends with** `_hwdi`, `_hwdo`, `_scdi`, `_scdo` | **digital** |
| **ends with** exactly `_alm` or `_alarm` | **digital** |
| **is exactly** `hwai`, `hwao`, `scai`, `scao` | **analog** |
| **is exactly** `hwdi`, `hwdo`, `scdi`, `scdo` | **digital** |
| **is exactly** `alm` or `alarm` | **digital** |

The eight suffixes are the ones already in `CLAUDE.md`'s "Naming
conventions" table; that table is the single source of truth for what
they mean and is not restated here.

**The bare-word rows (bottom three) were added 2026-09-08**, supplied by
Doug after he found that `ALARM_AOI`'s real PLC parameters use the bare
signal-type word — members literally named `Alarm` and `Hwdi` — instead
of the underscore-suffixed convention every other AOI follows. Under the
original suffix-only rule those two members correctly received **no**
History; that was not a bug, just a naming convention the rule had never
anticipated. A bare word classifies exactly the same as its
underscore-suffixed counterpart.

**The bare form is matched as an exact whole-name comparison**, never as
a suffix or substring. So a member named `Alarm` matches, `Hi_Alarm`
already matched via the suffix rows, and `AlarmEnable`, `PreAlarm`, and
`Alarms` match nothing — which is the intent. The suffix rows are
unchanged; bare-word matching is purely additive and does not alter the
result for any AOI already using the suffixed convention (verified by a
regression run against `FLOWIN3_AOI`, whose output was byte-identical
before and after the change).

**Compound alarm names are deliberately excluded** — `_alm_dis`,
`_alm_ack`, `_alm_res`, `Alarm_Ack`, and any other `_alm_*` /
`alarm_*` form. Those are alarm *controls*, not the alarm itself. Only
the bare `_alm` / `_alarm` ending, or the whole name being exactly `alm`
/ `alarm`, matches. **Alarms are always Boolean at Casne** (confirmed by
Doug), so they classify as digital regardless of how the AOI names or
types the alarm parameter.

Members that match nothing get **no history keys at all** — the same as
the script's original behavior.

**Settings applied by signal type.** The values come from `CLAUDE.md`'s
"Ignition tag History — digital vs. analog configuration" section (its
correctness rules plus the two Casne standing defaults) and are not
re-derived here:

| Setting | Digital | Analog |
|---|---|---|
| History Enabled | true | true |
| Deadband Style | `Discrete`, set explicitly | `Auto` — represented by **omitting the key**, see below |
| Deadband Mode | `Absolute` | `Absolute` |
| Historical Deadband | `0.0` | ⚠ `0.01` **placeholder — not a verified value** |
| Sample Mode | `On Change` | `On Change` |
| Max Time Between Samples | 20 | 20 |
| Max Time Units | Minutes | Minutes |

Three implementation notes worth keeping:

1. **JSON key names and enum spellings differ from the Designer UI
   labels**, and were taken from real Ignition UDT definition exports
   rather than assumed from the UI: `On Change` serializes as
   `"OnChange"`, `Minutes` as `"MIN"`, the setting names are
   `historicalDeadbandStyle` / `historicalDeadbandMode` /
   `historicalDeadband` / `historyMaxAge` / `historyMaxAgeUnits`, and the
   Analog style serializes as `"Analog_Compressed"` — not `"Analog"`.
2. **`Auto` is written by omitting `historicalDeadbandStyle`.** Ignition
   omits settings sitting at their default when it exports, and no
   `"Auto"` literal appears in any real export checked — so omitting the
   key is how a real Ignition file represents Auto. On a Float, Auto
   resolves to Analog, which is what CLAUDE.md's analog findings call
   for.
3. **The digital deadband `0.0` is a deliberate choice between the two
   values CLAUDE.md allows** (0 or 0.01). `0.0` was chosen because
   CLAUDE.md also notes a non-zero deadband next to Discrete style is
   inert/vestigial; `0.0` states "store every transition" plainly. Both
   are safely below the `>= 1.0` value that would silently suppress *all*
   history on a BOOL — CLAUDE.md's documented trap.

⚠ **The analog Historical Deadband is a flagged placeholder, not an
engineering answer.** CLAUDE.md is explicit that the Ignition docs give
no method, recommended value, or rule of thumb for choosing this number —
it is a per-signal judgment call. `0.01` is used only because it is the
value in the docs' own worked example, which CLAUDE.md cites. The script
prints a REVIEW REQUIRED block on every run that emits one, and Doug must
adjust it per signal. The digital deadband is not a judgment call and
needs no review.

**History context comes from the reference, not from this spec.** Storage
provider (`historyProvider`) and historical tag group (`historyTagGroup`)
are project/environment facts with no correct value to invent, so they
are derived from the reference UDT's own historized members — the same
"most common value across the reference" pattern already used for the OPC
Server value and the path template. If the reference has no historized
members, they are left unset and the script prints a warning that history
will not store until a provider is chosen. Any *other* history key the
reference's historized members carry is reported but not applied, so an
unrecognized convention gets a human look instead of being silently
copied or silently dropped.

### Reference JSON preparation convention (Doug-confirmed, 2026-09-07)

Prompted by a real gap found on the first live run: `FLOWIN3_AOI`'s
generated UDT was missing an `ENGUNIT` top-level parameter because the
reference used to build the script didn't have one. Root cause: the
top-level `parameters` block (`DeviceName`, `Description`, `ENGUNIT`,
etc.) is **entirely** derived from the reference JSON — it has no
connection to the L5X at all, unlike the per-signal members. Considered
and rejected: hardcoding "always include DeviceName/Description,
conditionally include ENGUNIT by AOI type" into the script. That would
be the first place TASK_004 embeds an engineering judgment call instead
of deriving it from a real file, and would create two parallel sources
for the same thing (reference-derived vs. hardcoded) — a likely source
of future confusion, not less. Kept the rule simple instead: **the
top-level parameters always come from whichever reference is supplied,
full stop** — and moved "which parameters this AOI category needs" into
an explicit, human-prepared reference file per target UDT, the same
pattern already used for the Historization rule and the data-type
mapping table.

**Workflow for preparing references (no script change needed):**
1. For each target UDT, create one small Ignition export with the
   correct top-level `parameters` for that AOI's category — `DeviceName`
   and `Description` always; `ENGUNIT` only for AOI types where
   engineering units genuinely apply (flow/level/pressure-style
   instrument AOIs) — Doug decides per category, not the script.
2. **The reference cannot be parameters-only.** The script also derives
   the OPC Server value, OPC Item Path template, and member JSON shape
   from the reference's own **members** — it needs at least one real,
   correctly-configured member to learn those conventions from. Easiest
   path: base each new reference on a UDT already fixed (e.g. keep one
   known-good member from `FLOWIN3_AOI`'s corrected UDT), swapping in
   the new top-level parameters for that category.
3. **Export from the "UDT Definitions" tab specifically** — the same
   established gotcha as always: a tag *instance* export does not
   include the UDT *definition* the script needs.
4. Multiple reference JSONs (one per target UDT) can be PII-scanned
   together in a single `pii_scan.py` pass — no need to combine them
   into one file; the scanner already handles a whole folder at once.
5. Run the script once per target UDT, each time pointing at the L5X
   and that UDT's own dedicated reference JSON.

**Immediate next step:** regenerate `FLOWIN3_AOI` using
`FLOWIN3_AOI old tags.json` (received and cleared via `PII_Review`
2026-09-07) as the corrected reference, since it has `ENGUNIT` where
Friday's original reference did not.

### Outputs

1. A new Ignition UDT definition JSON, written to the job's folder,
   importable via Ignition Designer's **UDT Definitions** tab, with one
   member per AOI parameter. For the actual Designer import steps — and
   why right-click → *Import Tags* can show up greyed out — see
   `CLAUDE.md`'s "Importing generated UDT definitions into Ignition
   Designer" section. Short version: use the Tag Browser's **More
   Options (hamburger)** menu → Import, not the right-click menu.
2. A console report: parameter count, the conventions derived from the
   reference (so they can be eyeballed before import), which members the
   historization rule enabled History on (split digital vs. analog, with
   the non-matching count), the analog-deadband REVIEW REQUIRED block,
   and warnings for any unmapped data type.

**Reporting note (Doug-confirmed, 2026-09-07):** the script's own
REVIEW REQUIRED block already surfaces the analog-deadband-placeholder
caveat on every run. Don't restate it as a separate reminder when
reporting results back to Doug — the console output already covers it,
and repeating it every time is unwanted noise, not a helpful safeguard.

### Open Questions / Notes

- **UDT name does not track the AOI version number.** A UDT named
  `CONSPD2_AOI` legitimately corresponds to PLC type `CONSPD4_AOI` —
  expected, not an error. The script therefore takes the output UDT name
  as an explicit option (`--udt-name`) and defaults to the AOI type name
  only when not told otherwise. It never infers a mapping by name.
- **Historization is now applied automatically by an explicit rule** —
  see the "Historization rule" section above. This supersedes the
  previous behavior, in which generated members deliberately carried no
  history configuration at all because no explicit rule existed yet
  (Doug set History Enabled by hand, per member, in Designer). Doug
  supplied the rule on 2026-09-04 and it is now built in. What has
  **not** changed: the script still never *guesses* which members to
  historize — it applies a rule Doug stated, exactly as written, the
  same way it already applies the OPC Server and path-template
  conventions. Members outside the rule still get no history keys at all.
  **Related but distinct (verified 2026-09-04):** what the History
  settings themselves should *be*, once a member has already been chosen
  for historization, is documented — see `CLAUDE.md`'s "Ignition tag
  History — digital vs. analog configuration" section. That covers
  Deadband Style/Mode/value correctness by signal type (digital vs.
  analog) only — the two concerns stay separate: CLAUDE.md says what the
  settings should be, the Historization rule above says which members
  receive them. Neither narrows the Hard scope boundary, which governs
  *correcting an existing* UDT, not generating a new one.
- `{InstanceName}` is a genuine built-in Ignition parameter requiring no
  manual setup; `{Name}` is **not** built-in and must be a custom
  parameter where it appears. Generated templates use `{InstanceName}`.
- The script does not import into Ignition and does not modify any
  existing UDT — it only writes a new file. Correcting existing UDTs
  remains a separate concern under the Hard scope boundary.

---

## TASK_005 — Generate Ignition tag instances from AOI usages with valid UDTs

**Status:** **`ALARM_AOI`, `CONSPD4_AOI`, `FLOWIN3_AOI`, and `FLOWVLV_AOI`
all Implemented and export-verified** (`ALARM_AOI` 2026-09-10, the other
three all 2026-09-11). **`INTERLOCK_AOI` and `LEVELIN3_AOI` are
Implemented and structurally verified** (`INTERLOCK_AOI` 2026-09-11, all
15 checks passed; `LEVELIN3_AOI` 2026-09-12, all 13 checks passed) —
**both awaiting Designer import confirmation** before promotion to
export-verified. **`MODVLV` and `VARSPD2_AOI` remain Idea.**
Script: `generate_ignition_tags.py`.

`INTERLOCK_AOI` was the fifth type run through the tool and the type Doug
originally flagged as the natural next test candidate after `ALARM_AOI`.
It inverts the shape of every prior run — the most instances (10) and by
far the fewest members (5) — and it is the first run where **every**
instance has a blank L5X description. All 15 structural checks passed,
including the one that matters most for this type: the parameter set is
exactly `DeviceName` + `Description`, with none of this AOI's many
UDT-defaulted parameters leaking into the instances.

**Blocked 2026-09-11 — real member-name mismatch, confirmed on import.**
The two flat `Interlocks`/`Visibility` members flagged as "one thing to
watch" turned out to be the actual failure, not just a cosmetic
observation: Doug's Designer import errored on every one of the 9
colliding paths with `Bad_Unsupported(...does not have item 'EnableIn'
for overrides, and cannot accept children tags.)`. Root cause, confirmed
directly against Doug's own `INTERLOCK_AOI` definition export: the real
Ignition UDT declares **64 members** (`Interlock_00`–`_31`,
`Visibility_00`–`_31`, the per-bit expansion), not the 5 L5X AOI
parameters this run emitted — **zero name overlap**. This is not a
Collision Policy or `--folder-mode` problem; a `UdtInstance` simply
cannot hold a member its definition doesn't declare. Full diagnosis,
sources, and fix steps are in `CLAUDE.md`'s "Importing tag instances —
`does not have item 'X' for overrides...`" section — not duplicated here
(Lesson 9). **This is now believed to be a structural limitation of
every AOI whose real Ignition UDT was hand-built with more/differently
named members than its L5X parameter list** (bitfield-expanded UDTs
like this one being the known case), not an `INTERLOCK_AOI`-specific
bug — worth watching on any future type with a similar hand-expansion
history. See "Fifth run — `INTERLOCK_AOI`" below for the original run
detail.

`FLOWVLV_AOI` was the fourth type run through the tool and the second
whose Ignition UDT name differs from its PLC AOI name (`FLOWVLV2_AOI`,
passed with `--udt-name`). It produced a single instance, `O2_MV112A`,
with 38 members; all 15 structural checks passed and the anomaly scan was
completely clean. **Doug confirmed 2026-09-11 that all 7 test steps
passed on Designer import**, promoting it to the same export-verified
grade as the other three types, despite the thinner one-instance sample
size — see "Fourth run — `FLOWVLV_AOI`" below.

`FLOWIN3_AOI` was the third type run through the tool and the first to
exercise the three-parameter mapping (`DeviceName`, `Description`,
`EngUnit`). Its structural checks all passed — see "Verification of the
`FLOWIN3_AOI` run" below — and **Doug confirmed 2026-09-11 that all test
steps passed on Designer import**, promoting it to the same
export-verified grade as `ALARM_AOI` and `CONSPD4_AOI`. The script's
UNVERIFIED warning for this type is now stale and hasn't been removed
from the code itself — cosmetic only, same known gap already noted for
`CONSPD4_AOI` above.

`CONSPD4_AOI` reached export verification in two steps: structural
verification only on 2026-09-10 (no reference export existed yet), then
**Doug imported the generated JSON into Ignition Designer 2026-09-11 and
confirmed it looks perfect** — that's the real, same-grade confirmation
`ALARM_AOI` already had. See "Verification of the `CONSPD4_AOI` run"
below for the structural checks, and the note appended to that section
for the 2026-09-11 import confirmation.

Why the status is split rather than a single label. The dispatch that
built this offered a choice between leaving the whole task at "Idea,
unblocked" and promoting it to "Spec Ready" for the `ALARM_AOI` case.
Neither fits, and forcing one would misrepresent the state:

- "Idea, unblocked" is now false for `ALARM_AOI`. Working code exists,
  it has been run against the real L5X, and its output was verified
  field-by-field against a real Ignition export.
- "Spec Ready" *understates* `ALARM_AOI` — that label means "speced but
  not built," and this is built and tested.
- Promoting the **whole task** would be wrong in the other direction:
  the remaining 7 types have a recorded parameter mapping but **no
  verification against any real export**, and this task's two genuinely
  open questions (below) are still open for all of them.

So the honest state is one type done and seven not. Do not read
`ALARM_AOI`'s completion as evidence the rest will work — see the
UNVERIFIED warning the script prints.

**Unblocked 2026-09-10** — Blue Sky's O2-scope UDT checklist (the thing
this task was waiting on) is done: 7 AOI types confirmed working, the
remaining 4 confirmed genuinely not needed for now (not just paused).

### Purpose

TASK_004 generates Ignition UDT *type definitions* from an AOI — but
someone still has to manually create every individual tag *instance* in
Ignition Designer, one at a time, pointing each at the right UDT type.
For a scope with many tags (e.g. every Blue Sky O2-scope PLC tag), this
is the same class of slow, error-prone manual work TASK_004 already
eliminated on the definition side — just one level down, on the instance
side.

**Re-scoped 2026-09-08** (was originally a generic `O2_`-prefix match —
see the retired framing at the bottom of this section): the actual
trigger was Doug noticing that after regenerating several UDT
definitions during the Blue Sky batch, the *instances* in Ignition still
needed real, manual work — this task exists to automate that instance
creation, scoped precisely rather than by a loose tag-name prefix.

### Scope — confirmed job-agnostic (2026-09-10)

Like TASK_004/TASK_009/TASK_010, this works against any job's L5X, not
just Blue Sky's — Blue Sky is just the first real input lined up.

### Output shape — confirmed 2026-09-10

Small test runs first (a handful of instances, to validate the approach)
— but the end goal is **one consolidated JSON file** covering everything
in scope, not a separate file per tag instance and not one file per AOI
type. Supersedes the "emit a folder of ... JSONs" framing in this task's
one-line catalog description above; that line needs updating once this
is built.

### Destination folder — always asked, never hardcoded (Doug-decided 2026-09-10)

The folder the generated tags land in is **an explicit input on every
run**, with no default in the script. Doug's own value today is
`[default]O2InjectionSystem` — "the same folder the reference export came
from" — but that is *his* organization for *this* job, not a convention:
a different engineer may want a different tag-tree layout, so the script
refuses to guess and requires `--dest-folder`.

**How the value is actually applied — worth understanding before
importing.** Verified against official Ignition docs 2026-09-10: an
Ignition tag import file **cannot choose its own destination**. The
destination is the folder selected in the Tag Browser (Designer) or the
`basePath` argument (`system.tag.importTags`). So `--dest-folder` is,
by default, a *stated intent* that the script echoes back in its console
report and its import instructions — it is not a field inside the JSON,
because there is no such field. `folderPath` is **not** part of the tag
JSON format; do not invent one.

Two modes, for that reason:

| `--folder-mode` | Output | When to use |
|---|---|---|
| `flat` (default) | `{"tags": [ ...instances... ]}` | Normal case. Select the destination folder in the Tag Browser, then import. Matches how the reference export is shaped. |
| `wrap` | instances nested inside an explicit `{"tagType": "Folder"}` entry named after `--dest-folder` | When the import should *create* the folder underneath whatever is selected. |

⚠ `wrap` creates a folder **relative to** the import target, so
importing a wrapped file while already inside `O2InjectionSystem`
produces `O2InjectionSystem/O2InjectionSystem`. `flat` is the default for
this reason.

### Per-AOI parameter mapping (Doug's own words, 2026-09-10)

Which top-level Ignition parameters an instance carries depends on its
AOI type, and **there is no way to derive this from the L5X** — these
parameters live on the Ignition UDT, not in the PLC program. Doug
supplied the mapping directly. It is implemented in
`generate_ignition_tags.py`'s `AOI_PARAMETERS` table.

| PLC AOI type | Ignition UDT name — pass with `--udt-name` | Parameters | Verified? |
|---|---|---|---|
| `ALARM_AOI` | `ALARM_AOI` (same — omit `--udt-name`) | `DeviceName`, `Description` | ✅ **Yes** — against a real export |
| `CONSPD4_AOI` | **`CONSPD2_AOI`** | `DeviceName`, `Description` | ✅ **Yes** — Doug confirmed the Designer import 2026-09-11 |
| `FLOWIN3_AOI` | `FLOWIN3_AOI` (same — omit `--udt-name`) | `DeviceName`, `Description`, `EngUnit` | ✅ **Yes** — Doug confirmed all test steps passed on Designer import 2026-09-11 |
| `FLOWVLV_AOI` | **`FLOWVLV2_AOI`** | `DeviceName`, `Description` | ✅ **Yes** — Doug confirmed all 7 test steps passed on Designer import 2026-09-11 |
| `INTERLOCK_AOI` | `INTERLOCK_AOI` (same — omit `--udt-name`) | `DeviceName`, `Description` (+ many defaulted params, see note) | ❌ **Blocked** — 15/15 structural checks passed 2026-09-11, but the real UDT's 64 hand-expanded members (`Interlock_00`–`_31`/`Visibility_00`–`_31`) share zero names with the 5 emitted here; import fails. See `CLAUDE.md`'s import-troubleshooting section for the fix (strip the `tags` array, re-import with `MergeOverwrite`). |
| `LEVELIN3_AOI` | `LEVELIN3_AOI` (same — omit `--udt-name`) | `DeviceName`, `Description`, `EngUnit` | ❌ No |
| `MODVLV` | `MODVLV` (same — omit `--udt-name`) | `DeviceName`, `Description`, `EngUnit`, `Analog_Vlv` (Integer, default `0`) | ❌ No |
| `VARSPD2_AOI` | **`VARSPD_AOI`** | `DeviceName`, `Description`, `EngUnit` | ❌ No |

Notes on this table:

- ⚠ **This table is now the ONLY home for the UDT-name column — the
  script no longer carries it (changed 2026-09-10).** `AOI_PARAMETERS` in
  `generate_ignition_tags.py` used to hold a `udt_name` per row, which
  quietly made the script the authority on these pairings. That field was
  removed once Doug confirmed the name drift is a general ongoing
  convention rather than three fixed exceptions — see "PLC AOI name vs.
  Ignition UDT name" below. The UDT name is now supplied per run via
  `--udt-name`, and the column above is what a human reads to decide what
  to pass. **Consequence to be aware of: a run that omits `--udt-name`
  for `CONSPD4_AOI`, `FLOWVLV_AOI`, or `VARSPD2_AOI` will now emit a
  `typeId` built from the PLC AOI name and will not bind on import.** The
  script prints the name it used on every run so this is visible rather
  than silent, but it is no longer caught automatically.
- **Three UDT names deliberately differ from their PLC AOI type name**
  (bolded). This is the same already-documented phenomenon as TASK_004's
  `--udt-name` note — a UDT's name does not track the AOI's version
  number. The mapping is **never inferred by name**; it is recorded
  here and passed per run with `--udt-name` (single-type runs) or
  `--aoi-type NAME=UDT_NAME` (multi-type runs).
- **`EngUnit` is created but left blank** wherever it applies. There is
  no way to derive an engineering unit automatically — the same
  conclusion reached everywhere else this has come up. Doug fills it in
  per instance afterward.
- **`INTERLOCK_AOI`'s "many other parameters with default values"** are
  expected to read in correctly with no special handling. They live on
  the UDT *definition* and are inherited by the instance, so the script
  emits nothing for them — an instance only carries parameters it
  actually overrides. Doug flagged `INTERLOCK_AOI` as the natural next
  first-pass test candidate after `ALARM_AOI`.
- **Only `ALARM_AOI` is verified.** Every other row records Doug's
  stated intent and has never been checked against a real Ignition
  tag-instance export. The script prints an UNVERIFIED warning for them
  on every run. Verify one instance by hand before importing in bulk.
- **`Analog_Vlv`'s `Integer` type is unverified in a second way:**
  Ignition's docs officially document only `String` as a UDT parameter
  data type. `Integer` is widely used in practice but is not documented
  anywhere official (checked 2026-09-10, 8.1 and 8.3). Note this is a
  *parameter* type vocabulary, which is **not** the same list as the
  *tag* data types (`Int4`, `Float4`, `Boolean`, …) — don't mix them.

### PLC AOI name vs. Ignition UDT name — a general convention, not a set of exceptions (Doug-confirmed 2026-09-10)

**The principle.** A PLC-side AOI type name carries a version number that
**changes as the AOI is revised** (`CONSPD2_AOI` → `CONSPD4_AOI`). The
Ignition UDT it maps to **keeps a fixed name deliberately** — so Ignition
does not have to be re-worked every time the PLC-side AOI is revised.
The two names are therefore **not assumed identical, ever**, and the fact
that they happen to be equal for `ALARM_AOI` is a coincidence of that one
family rather than the rule. This was already documented for this exact
family in `PLCHelper_Status.md`'s "Handoff to SCADA" section (UDT names
do not track PLC AOI version numbers); what is new on 2026-09-10 is
Doug's confirmation that it is a **general, going-forward convention**
that the tooling must accommodate structurally.

**What that means for this task's tooling.** An AOI-type list alone is
not enough input — the tool needs an **explicit AOI-name → UDT-name
mapping**. `--aoi-type` and `--udt-name` are two independent inputs:

| Input | Means |
|---|---|
| `--aoi-type NAME` | "match instances of this **PLC** AOI type in the L5X" — also the source of the member list, read from that AOI definition's parameters |
| `--udt-name NAME` | "build `typeId` from this **Ignition** UDT name" — defaults to the `--aoi-type` value when omitted |

`typeId` is built from `--udt-name`. The instance member list (`tags`
array) is still built from the L5X's own `--aoi-type` AOI definition's
parameters, unaffected — those parameters are what the Ignition UDT's
members were generated from in the first place (TASK_004), so they remain
the right source.

**The mapping is per-run input, never logic in the script.** Same
principle the qualifying-AOI-type list already follows (Process step 2).
There is deliberately **no pattern-matching, no regex, and no built-in
table of name pairs** in `generate_ignition_tags.py` — encoding a family
rule would make the script quietly wrong the moment a family broke the
pattern, and a wrong `typeId` does not surface until import time.

**First real example — the `CONSPD` family (Doug's rule, 2026-09-10):**

> Any PLC AOI type matching **`CONSPD<digits>_AOI`** — currently one
> digit, may become two later, so match the *pattern*, not a fixed digit
> count — always maps to Ignition UDT **`CONSPD2_AOI`**, regardless of
> the actual number in the PLC.

⚠ **That rule is Doug's own reasoning for choosing what value to pass,
not logic the script implements.** A future `CONSPD5_AOI` or
`CONSPD12_AOI` is still run as `--aoi-type CONSPD12_AOI --udt-name
CONSPD2_AOI`; nothing needs changing in the script, and nothing in the
script will work it out on its own.

**Ignition-side confirmation (three-part search, 2026-09-10).** This
whole approach depends on `typeId` binding purely by name, which is
confirmed:

- `typeId` is a plain, **provider-relative, forward-slash-separated path**
  to the definition (`BlueSky/AOI/CONSPD2_AOI`), with the `_types_`
  segment **not** part of the value. Already recorded in
  `TRUSTED_SOURCES.md`'s "Tag JSON Format" entry.
- The binding carries **no version number, UUID, or internal handle** —
  official docs describe `typeId` as "the name of the UDT Definition this
  UDT is an instance of," and renaming a definition *orphans* its
  instances, which is only possible if the binding is by name. So a UDT
  whose name deliberately differs from the PLC type name binds correctly
  as long as the string matches. **This is what makes the convention
  above safe rather than a workaround.**
- Officially constrained: `typeId` is **provider-scoped** (parent data
  types "can only be set from UDT Definitions within the same provider"),
  so no `[provider]` prefix belongs in the value.
- ⚠ **A `typeId` naming a definition that does not exist appears to fail
  SILENTLY on import** — forum report IGN-2712 (8.1.7): "no errors are
  shown if some tags don't import … if their … UDT instance definitions
  don't exist." Community-sourced, not staff-confirmed, and it is
  **unresolved** whether the instance is created-but-broken or not
  created at all. Practical consequence: **do not rely on the import to
  report a wrong `--udt-name`.** Import definitions first and eyeball the
  instances. This is why the script echoes the UDT name it used on every
  run.
- **Not documented anywhere, do not assume:** `typeId` case sensitivity
  and leading/trailing-slash handling. Both were searched for
  specifically and no official or forum statement exists. Match the
  definition's name exactly rather than relying on any normalization.
- Also worth knowing (same search): the official docs are **internally
  inconsistent** — the UDTs concept page calls `typeId` a "name," both
  the 8.1 and 8.3 Tag Properties pages call it "a path." No official page
  shows a folder-qualified example, so the folder-path form is confirmed
  by Casne's own real export and `TRUSTED_SOURCES.md`, not by Inductive
  Automation's documentation.

### Verified output shape (2026-09-10)

Ground truth is `BlueSky/ALARM_AOI example tags.json`, a real Ignition
tag-instance export for `O2_AC001_FAILURE`, cross-checked against
official Inductive Automation documentation.

```json
{
  "name": "O2_AC001_FAILURE",
  "parameters": {
    "DeviceName":  {"dataType": "String", "value": "BOP_O2_CombinedTest"},
    "Description": {"dataType": "String", "value": "AC-001 Air Compressor Failure"}
  },
  "tagType": "UdtInstance",
  "tags": [{"name": "Alarm", "tagType": "AtomicTag"}, ...14 members...],
  "typeId": "BlueSky/AOI/ALARM_AOI"
}
```

- **Members carry only `name` + `tagType`.** Everything else — data
  type, OPC item path, OPC server, permissions — is inherited from the
  UDT definition TASK_004 generated. Confirmed both by the real export
  and by the official JSON-format docs. Emitting an OPC path here would
  create a second, competing source for a value the definition already
  owns — exactly the drift TASK_004 exists to prevent.
- **Member *order* differs from the reference and that is fine.** The
  script emits L5X document order (TASK_004's convention); Ignition's
  export order is internal. Members bind by name on import.
- **Keys are written sorted** (`json.dump(..., sort_keys=True)`), which
  is what real Ignition exports do — same as `generate_ignition_udt.py`.
- **The consolidated file needs the `{"tags": [...]}` wrapper.** A bare
  top-level JSON array fails on import with `Not a JSON Object` —
  confirmed by two Inductive Automation staff on their own forum. Note
  the reference file itself is a *bare object* with no wrapper, because
  it came from a single tag rather than a folder export; do not copy
  that shape for a multi-instance file.

### Process (as Doug described it 2026-09-08)

1. Read every **AOI instance** in the L5X (not just type definitions —
   this needs instance-level data TASK_004 doesn't currently parse).
2. **Only act on instances whose AOI type already has a valid, generated
   UDT definition** — cross-reference against a list of qualifying AOI
   type names. **Decided 2026-09-10: this list is explicit input, not
   something the script infers or scans for on its own.** Doug supplies
   it (starting point: Blue Sky's per-AOI checklist in
   `BLUE_SKY_STATUS.md` — the 7 confirmed-working types), and it needs
   its own real home once this gets built (not yet decided whether that's
   a small JSON/text file per job, or something else — don't invent the
   format, ask). Skip anything else — this task doesn't invent UDTs,
   TASK_004 does.
3. For each qualifying instance, build its Ignition tag instance entry
   (see Output shape above — these get combined into one file, not
   emitted individually). **Which of the fields below actually apply
   depends on the AOI type** — e.g. `ALARM_AOI`'s generated UDT only has
   `DeviceName` and `Description` among these (confirmed 2026-09-10);
   other AOI types may have more (see `EngUnit` below). Do not assume
   every AOI type needs every field — check each type's own UDT.
   - **`DeviceName`** — **resolved 2026-09-10: one single value for the
     whole task run**, not per-instance (closes the open question below).
     Supplied as an explicit parameter when the task is run. Today's
     value: `"BOP_O2_CombinedTest"`.
   - **`Description`** — **confirmed 2026-09-10.** Looked up automatically
     per instance: read directly from **that specific AOI instance's**
     own `<Description>` in the L5X (real per-instance data, not the
     type-level description TASK_004 already reads) and used to fill the
     `Description` parameter's value in the generated tag instance. This
     is new: no existing PLCHelper task currently reads instance-level
     AOI usage data, only type definitions.
   - `EngUnit` — **left blank**, for AOI types that have it (not one of
     `ALARM_AOI`'s two). No way to derive this automatically (same
     conclusion as everywhere else it's come up); Doug fills it in per
     instance afterward.

### Inputs

| Input | Flag | Notes |
|---|---|---|
| L5X export | `--l5x` | Full program export from Studio 5000. Lives in the **job's own folder**, read cross-folder — never copied into PLCHelper, same rule as TASK_003/004. |
| Qualifying **PLC AOI** type(s) | `--aoi-type` (repeatable) | Explicit, Doug-supplied, never inferred. Matches instances in the L5X *and* supplies the member list. Accepts `NAME=UDT_NAME` to set that one type's UDT name — the form to use on multi-type runs. |
| **Ignition UDT name** | `--udt-name` | Builds `typeId`. **Defaults to the `--aoi-type` value when omitted.** Supply it whenever the UDT name differs from the PLC AOI name — the normal case, see "PLC AOI name vs. Ignition UDT name" above. One value for the whole run, so it is refused alongside more than one `--aoi-type` (use the `NAME=UDT_NAME` form there instead). Giving both forms for the same type is also refused rather than silently resolved. |
| Device name | `--device-name` | One value for the whole run. |
| Destination folder | `--dest-folder` | Always asked; no default. |
| UDT path prefix | `--udt-path-prefix` | Folder path of the UDT definitions inside the provider, e.g. `BlueSky/AOI`. Combined with the UDT name to form `typeId`. |
| Output path | `--output` | Write into the **job's own folder**, never PLCHelper. |

Note what is *not* an input: there is no reference-JSON parameter. Unlike
TASK_004, this task derives no conventions from a reference file at run
time — instance members carry no OPC paths, servers, or permissions to
learn. The reference export was used once, during development, to
confirm the output shape.

### Outputs

1. **One consolidated JSON** containing every generated tag instance,
   written to the job's folder. Import via the Tag Browser's **More
   Options (hamburger)** menu → Import Tags — and **import the UDT
   definitions first**, per Ignition's own docs.
2. **A console report**: the run's inputs echoed back, per-AOI-type
   `typeId` and instance/parameter counts, every instance with its
   looked-up description, an explicit list of any instance whose
   description came back blank, warnings, and the pre-import checklist.

### Relationship to TASK_004

Depends on TASK_004's output existing first, now precisely (not loosely
— see re-scope above): this task can only assign a tag instance to a UDT
type already confirmed generated and working. Raised alongside Blue
Sky's O2-scope UDT regeneration work (`BLUE_SKY_STATUS.md` Open Item 1)
as the natural next step once enough of those UDTs are in place.

### First-pass build — `ALARM_AOI` only (2026-09-10)

Script: `generate_ignition_tags.py`. The run that produced the first
real output:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type ALARM_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/ALARM_AOI tag instances generated 2026-09-10.json"
```

**Result: 31 `ALARM_AOI` instances**, all controller-scoped, each with a
non-blank description read from its own L5X `<Description>`. Output is
one consolidated file written to the **job's folder**, never into
PLCHelper — same rule as TASK_004.

A useful structural confirmation fell out of this run: `ALARM_AOI`'s 14
L5X parameters and the reference export's 14 members are an **exact
set match, zero discrepancies either way**. That is independent evidence
that generating the member list from the L5X reproduces the real UDT.

`--list-aoi-types` was added as a discovery aid: it prints every AOI type
in the L5X with an instance count and whether it is in the mapping table.
It is *only* a discovery aid — which types qualify remains Doug's
explicit decision, never the script's.

### Verification against the real reference (2026-09-10) — PASSED

The generated `O2_AC001_FAILURE` entry was compared field by field
against `BlueSky/ALARM_AOI example tags.json`:

| Field | Result |
|---|---|
| `name` | match |
| `tagType` | match (`UdtInstance`) |
| `typeId` | match (`BlueSky/AOI/ALARM_AOI`) |
| `tags` — member count | match (14 / 14) |
| `tags` — member names | match (exact set) |
| `tags` — per-member key shape | match (`name` + `tagType` only) |
| `parameters.DeviceName` | match (`String` / `BOP_O2_CombinedTest`) |
| `parameters.Description` | **differs — expected and correct, see below** |
| `tags` — member order | differs — presentation only, binds by name |

**The `Description` difference is the intended result, not a bug.** The
reference file has no `Description` key at all; the script emits
`"AC-001 Air Compressor Failure"`, the real L5X description for that
instance. Doug confirmed explicitly that pulling the real per-instance
description is the whole point, and that the script must **not** be
"fixed" to reproduce the reference's absent value. Every other field
matches, which is what makes this difference safe to attribute to intent
rather than to a parsing error.

⚠ **One nuance the research turned up that refines — but does not
change — this.** The working assumption going in was "the reference has
no `Description` because that instance's description is blank." Official
Ignition docs say something slightly different and slightly weaker:
*"the tag export feature only exports the configuration properties that
have been **edited**."* An IA staff member confirmed on the forum that
there is currently no way to export all parameters. So a missing key
means **"not overridden at the instance level,"** which is *not* quite
the same claim as "the value is blank" — it could equally be inheriting
a non-blank default from the UDT definition.

This does not affect the build at all (Doug's decision is that
`Description` is always created and always filled from the L5X), but it
does affect how the reference file should be read in future: **absence
of a key in any Ignition export is evidence about override state, not
about value.** Worth knowing before using an export to answer "does this
instance have parameter X?"

### Second run — `CONSPD4_AOI` → UDT `CONSPD2_AOI` (2026-09-10)

The run that first exercised `--udt-name`, and the first time a generated
`typeId` deliberately does **not** match the PLC AOI type name:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type CONSPD4_AOI \
  --udt-name CONSPD2_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/CONSPD4_AOI tag instances generated 2026-09-10.json"
```

**Result: 4 `CONSPD4_AOI` instances**, all controller-scoped, each with a
non-blank description read from its own L5X `<Description>`, each with 68
members. Kept in its **own file**, not merged with `ALARM_AOI`'s — small
test scopes first, per Doug's standing instruction. `CONSPD4_AOI` is
revision 2.4 in this L5X.

| Instance | L5X description |
|---|---|
| `BOP_FLR` | Flare control |
| `O2_AC001` | AC-001 Air Compressor |
| `O2_AD002` | AD-002 Air Dryer |
| `O2_OG003` | OG-003 Oxygen (O2) Generator |

✅ **`BOP_FLR` is a flare tag, not an O2 tag, and this run puts it in the
O2 destination folder.** It is a genuine `CONSPD4_AOI` instance so the
script is right to emit it — the qualifying input is an *AOI type*, and
this task has no notion of job scope within a type. But
`--dest-folder "[default]O2InjectionSystem"` was chosen for the O2 scope,
and three of these four instances are `O2_`-prefixed while this one is
not. Flagging rather than filtering it: name-prefix filtering is
exactly the loose `O2_`-prefix approach this task retired in 2026-09-08's
re-scope, and re-introducing it silently would undo that decision.

**Resolved 2026-09-11, per Doug: `BOP_FLR` also imported and looks
perfect, staying in the O2 folder for this job.** More generally, worth
recording why a flare tag legitimately uses `CONSPD4_AOI` at all —
`CONSPD4_AOI` was originally scoped for single-speed motors (a thing that
turns on/off and can fail to do either, with runtime/failure alarming),
but its actual real-world use has broadened: **anything that turns
on/off and has the same class of failure modes reuses this AOI**, motor
or not. Blue Sky's flare is the concrete example. See TASK_011 below —
Doug wants PLCHelper to eventually be able to *suggest* an existing AOI
like this one when someone describes a new on/off-with-failure-modes
control need, instead of assuming a new AOI is required.

### Verification of the `CONSPD4_AOI` run (2026-09-10) — PASSED, structural only

**No reference export exists for this type** — Doug's explicit call was
to verify structurally instead of waiting for one. So this is *not* the
same grade of evidence as `ALARM_AOI`'s field-by-field comparison against
a real Ignition export, and the mapping table above still shows
`CONSPD4_AOI` as lacking export verification. What was checked, with the
output cross-read against the L5X by a separate throwaway script rather
than by the tool's own helpers:

| Check | Result |
|---|---|
| Member count vs. `CONSPD4_AOI`'s own L5X parameter set | **68 / 68** on all 4 instances |
| Member names — exact set match to the L5X parameters | match, zero missing / zero extra |
| Member order == L5X document order | match |
| No duplicate member names | match |
| `typeId` == `BlueSky/AOI/CONSPD2_AOI` on every instance | match, all 4 |
| String `CONSPD4` anywhere in the output file | **0 occurrences** — the PLC name leaks nowhere |
| `DeviceName` == `String` / `BOP_O2_CombinedTest` | match, all 4 |
| `Description` == that instance's own L5X description, verbatim | match, all 4 |
| Parameter set == exactly `DeviceName` + `Description` | match |
| Top-level key shape == the verified `ALARM_AOI` run's | match (`name`, `parameters`, `tagType`, `tags`, `typeId`) |
| `tagType` == `UdtInstance`; members only `name` + `tagType: AtomicTag` | match |
| Instance names == L5X tag names verbatim | match |

**What this does and does not establish.** It establishes that the
`--udt-name` plumbing works, that `typeId` is built from the UDT name and
not the AOI name, and that the member list still comes from the L5X. It
does **not** establish that `CONSPD2_AOI`'s real Ignition UDT has exactly
these 68 members or exactly these two parameters — only a real export or
a Designer import can show that. The UNVERIFIED warning still prints.

**Update 2026-09-11 — the missing piece is now done.** Doug imported the
2026-09-10 generated JSON into Ignition Designer and confirmed it "looks
perfect." That is the Designer-import confirmation this section said was
still needed — `CONSPD4_AOI` is now export-verified, same confidence
grade as `ALARM_AOI`. The UNVERIFIED warning in the script itself is
still generic to every non-`ALARM_AOI` type and hasn't been updated to
exempt `CONSPD4_AOI` specifically — cosmetic only, doesn't affect output,
flagged here in case it's confusing on a future run.

### Third run — `FLOWIN3_AOI` (2026-09-11)

Placed here, after the whole `CONSPD4_AOI` write-up rather than between
that run and its own verification section, so each run stays next to the
verification that belongs to it.

The third AOI type through the tool, and the first run whose parameter
mapping is **three** parameters rather than two — `EngUnit` is exercised
here for the first time. The Ignition UDT name is the same as the PLC AOI
name for this family, so `--udt-name` is deliberately omitted:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type FLOWIN3_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/FLOWIN3_AOI tag instances generated 2026-09-11.json"
```

**Result: 7 `FLOWIN3_AOI` instances**, all controller-scoped, none an
array, each with 51 members and a non-blank description read from its own
L5X `<Description>`. Kept in its **own file**, not merged with
`ALARM_AOI`'s or `CONSPD4_AOI`'s — small test scopes first, per Doug's
standing instruction. The AOI definition carries `Revision="0.1"` in this
L5X.

| Instance | L5X description |
|---|---|
| `BOP_FIT3001` | O2 Receiver Tank flow |
| `BOP_FIT3002` | description 3002 |
| `BOP_FIT3003` | description 3003 |
| `BOP_FIT3004` | description 3003 |
| `BOP_FIT3005` | description 3005 |
| `BOP_FIT3008` | description 3003 |
| `O2_FM100` | FM-100 Oxygen (O2) Discharge Flow Transmitter |

Three things to look at before importing. All three are **flagged, not
filtered** — same reasoning as the `BOP_FLR` flag on the `CONSPD4_AOI`
run: the qualifying input is an *AOI type*, and this task has no notion
of job scope, description quality, or name prefix within a type. Every
one of these is a faithful copy of what the PLC program actually says.

1. ✅ **Five of the seven descriptions are placeholders, not real
   engineering text.** `BOP_FIT3002`, `3003`, `3004`, `3005` and `3008`
   all read `description <number>` — clearly unfinished PLC-side text.
   The script copies descriptions verbatim by design, so these carry
   straight into Ignition and become the operator-visible description on
   each tag. Fixing them belonged in the L5X, not in the generated
   JSON, to survive the next regeneration. **Resolved 2026-09-11 — Doug
   confirms this is done.** (As with item 2: the L5X on file and this
   run's already-generated JSON still predate the fix; no re-run of this
   AOI type has been requested.)
2. ✅ **`description 3003` appears on three different tags** —
   `BOP_FIT3003`, `BOP_FIT3004` and `BOP_FIT3008`. `BOP_FIT3004` and
   `BOP_FIT3008` naming `3003` looks like copy-paste that was never
   updated, so this is likely a real PLC-side error rather than just
   placeholder text. **Fixed by Doug directly in the PLC code
   (2026-09-11).** The L5X on file, and therefore this run's generated
   JSON, still carry the old duplicated text — a fresh L5X export plus a
   re-run of this AOI type would be needed to pick up the fix. Doug is
   handling description accuracy by hand during import in the meantime
   (see item 3's resolution note below), so no re-run has been requested.
3. ✅ **Six of the seven instances are `BOP_`-prefixed, not `O2_`, and
   this run puts all of them in `[default]O2InjectionSystem`.** Same
   class of question as `BOP_FLR` on the `CONSPD4_AOI` run, but at a much
   larger share — there it was 1 of 4, here it is 6 of 7. Only `O2_FM100`
   carries the O2 prefix. Not filtered by name prefix, because prefix
   filtering is exactly the loose `O2_`-match approach this task retired
   in the 2026-09-08 re-scope. **Resolved 2026-09-11, per Doug: he is
   handling folder placement for `BOP_`-prefixed instances by hand,
   tag-by-tag, during the Designer import itself** — confirmed working
   well. No script-side filtering change requested or needed; this is
   Doug's own judgment call per instance, same as the `BOP_FLR` question
   on the `CONSPD4_AOI` run (also resolved 2026-09-11 — see that
   section).

### Verification of the `FLOWIN3_AOI` run (2026-09-11) — PASSED, structural only

**No reference export exists for this type either**, so this is the same
grade of evidence the `CONSPD4_AOI` run had on 2026-09-10 and *not* the
grade `ALARM_AOI` and `CONSPD4_AOI` now hold. The output was cross-read
against the L5X by a separate throwaway script that re-parses the L5X
with its own code and deliberately does **not** import
`generate_ignition_tags.py` — a bug in the tool's own helpers cannot hide
itself by being used on both sides of the comparison.

| Check | Result |
|---|---|
| Instance count vs. L5X instances of this type | **7 / 7** |
| Member count vs. `FLOWIN3_AOI`'s own L5X parameter set | **51 / 51** on all 7 instances |
| Member names — exact set match to the L5X parameters | match, zero missing / zero extra |
| Member order == L5X document order | match, all 7 |
| No duplicate member names | match |
| `typeId` == `BlueSky/AOI/FLOWIN3_AOI` on every instance | match, all 7 |
| `FLOWIN3_AOI` occurrences in the file == one per instance | **7 / 7** — appears only inside `typeId`, nowhere stray |
| `DeviceName` == `String` / `BOP_O2_CombinedTest` | match, all 7 |
| `Description` == that instance's own L5X description, verbatim | match, all 7 |
| `EngUnit` == `String` / `""` on every instance | match, all 7 — blank by design |
| Parameter set == exactly `DeviceName` + `Description` + `EngUnit` | match |
| Top-level key shape == the verified `ALARM_AOI`/`CONSPD4_AOI` runs | match (`name`, `parameters`, `tagType`, `tags`, `typeId`) |
| `tagType` == `UdtInstance`; members only `name` + `tagType: AtomicTag` | match |
| Instance names == L5X tag names verbatim | match, all 7, same order |
| No duplicate instance names | match |

Note on the `typeId` row and its `CONSPD4_AOI` counterpart. That run
could assert "the string `CONSPD4` appears **0** times," because the PLC
name and the UDT name differed and the PLC name had to leak nowhere. Here
the two names are the same, so zero is not the right expectation — the
equivalent check is that the name appears *exactly once per instance*,
inside `typeId` and nowhere else. Seven instances, seven occurrences.

**What this does and does not establish.** It establishes that the
three-parameter mapping emits correctly, that `EngUnit` is created and
blank rather than omitted, and that the member list comes from the L5X.
It does **not** establish that the real Ignition `FLOWIN3_AOI` UDT has
exactly these 51 members or exactly these three parameters — only a real
export or a Designer import can show that. The UNVERIFIED warning printed
on this run, as it should have.

**Update 2026-09-11 — Designer import done, all test steps passed.**
Doug ran the full test checklist (import UDT definitions, select the
destination folder, import via Tag Browser, confirm all 7 instances bind
with all 51 members, spot-check `EngUnit`/`DeviceName`, resolve the
`BOP_`-prefix folder-placement question tag-by-tag, note the still-open
description issues) and confirmed everything passed. `FLOWIN3_AOI` is now
export-verified, same confidence grade as `ALARM_AOI` and `CONSPD4_AOI`.

### Fourth run — `FLOWVLV_AOI` → UDT `FLOWVLV2_AOI` (2026-09-11)

Placed here, after the whole `FLOWIN3_AOI` write-up rather than between
that run and its own verification section, so each run stays next to the
verification that belongs to it — same arrangement as the third run.

The fourth AOI type through the tool. Back to the **two**-parameter
mapping (`DeviceName`, `Description`) — no `EngUnit` for this type — and
the second family whose Ignition UDT name **differs** from its PLC AOI
name, so `--udt-name FLOWVLV2_AOI` is required. Omitting it would have
emitted `typeId BlueSky/AOI/FLOWVLV_AOI`, which does not exist in
Ignition and would not bind on import:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type FLOWVLV_AOI \
  --udt-name FLOWVLV2_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/FLOWVLV_AOI tag instances generated 2026-09-11.json"
```

**Result: 1 `FLOWVLV_AOI` instance**, controller-scoped, not an array,
with 38 members and a non-blank description read from its own L5X
`<Description>`. Kept in its **own file**, not merged with the three
prior runs — small test scopes first, per Doug's standing instruction.

| Instance | L5X description |
|---|---|
| `O2_MV112A` | Blower-A Discharge Control Valve |

**Anomalies: none — this is the first run of the four with a completely
clean scan.** Worth stating explicitly rather than leaving as silence,
because the three prior runs each carried at least one flagged item and
an absent "flagged" list could otherwise read as an omission. All four
anomaly classes seen on earlier runs were checked for and none are
present here:

1. ✅ **No placeholder or unfinished descriptions.** The single
   description is real engineering text, unlike the five `description
   <number>` placeholders on the `FLOWIN3_AOI` run.
2. ✅ **No duplicated descriptions across tags** — trivially true with
   one instance, but checked rather than assumed.
3. ✅ **No folder-placement question.** `O2_MV112A` is `O2_`-prefixed, so
   it belongs in `[default]O2InjectionSystem` on its own name. This run
   raises none of the `BOP_FLR` / `BOP_FIT30xx` placement questions Doug
   has been resolving by hand during Designer import.
4. ✅ **No blank descriptions, no array instances, no program-scoped
   instances, no duplicate instance names.**

⚠ **The small scope is the thing to be aware of on this run, not an
anomaly in it.** One instance is the smallest scope any of the four runs
has had, and it exercises the two-parameter mapping that `ALARM_AOI` and
`CONSPD4_AOI` already proved. What is genuinely new here is only the
`FLOWVLV_AOI` → `FLOWVLV2_AOI` name mapping and this type's own 38-member
parameter list. A clean structural pass on one instance is correspondingly
weaker evidence than a clean pass on seven, and does not generalize to
any other `FLOWVLV_AOI` instance in a future job's L5X.

### Verification of the `FLOWVLV_AOI` run (2026-09-11) — PASSED, structural only

**No reference export exists for this type**, so this is the same grade
of evidence the `CONSPD4_AOI` and `FLOWIN3_AOI` runs each had before
their Designer imports — *not* the export-verified grade all three prior
types now hold. The output was cross-read against the L5X by a separate
throwaway script that re-parses the L5X with its own code and
deliberately does **not** import `generate_ignition_tags.py` — a bug in
the tool's own helpers cannot hide itself by being used on both sides of
the comparison.

| Check | Result |
|---|---|
| Instance count vs. L5X instances of this type | **1 / 1** |
| Member count vs. `FLOWVLV_AOI`'s own L5X parameter set | **38 / 38** on the instance |
| Member names — exact set match to the L5X parameters | match, zero missing / zero extra |
| Member order == L5X document order | match |
| No duplicate member names | match |
| `typeId` == `BlueSky/AOI/FLOWVLV2_AOI` | match |
| `FLOWVLV_AOI` (the PLC name) occurrences in the file | **0** — the required result, see note below |
| `DeviceName` == `String` / `BOP_O2_CombinedTest` | match |
| `Description` == that instance's own L5X description, verbatim | match |
| Parameter set == exactly `DeviceName` + `Description` (no `EngUnit`) | match |
| Top-level key shape == the verified prior runs | match (`name`, `parameters`, `tagType`, `tags`, `typeId`) |
| `tagType` == `UdtInstance`; members only `name` + `tagType: AtomicTag` | match |
| Instance names == L5X tag names verbatim | match |
| No duplicate instance names | match |
| Top-level payload shape == `{"tags": [...]}` | match (`--folder-mode flat`) |

15 checks, all passed.

Note on the zero-occurrence row — this is the `CONSPD4_AOI` variant of
the check, not the `FLOWIN3_AOI` one, and the distinction matters. Where
the PLC name and the UDT name are the **same** (`FLOWIN3_AOI`), the right
expectation is *one occurrence per instance*, inside `typeId`. Where they
**differ**, as here, the PLC name must leak nowhere at all and the right
expectation is **zero**. The substring test is genuinely meaningful in
this case: `FLOWVLV2_AOI` does not contain `FLOWVLV_AOI`, so the count is
not zero by accident of one name containing the other.

**What this does and does not establish.** It establishes that the
`FLOWVLV_AOI` → `FLOWVLV2_AOI` name mapping is applied correctly and
appears in `typeId` with no leakage of the PLC name, that the
two-parameter mapping emits with no `EngUnit`, and that the 38-member
list comes from the L5X. It does **not** establish that the real Ignition
`FLOWVLV2_AOI` UDT has exactly these 38 members or exactly these two
parameters — only a real export or a Designer import can show that. The
UNVERIFIED warning printed on this run, as it should have.

**Update 2026-09-11 — Designer import done, all 7 test steps passed.**
Doug confirmed the UDT bound correctly, all 38 members populated,
`DeviceName`/`Description` were correct, and no `EngUnit` parameter
existed on this type as expected. `FLOWVLV_AOI` is now export-verified,
same confidence grade as the other three types, despite the thinner
one-instance sample this run happened to produce.

### Fifth run — `INTERLOCK_AOI` (2026-09-11)

Placed here, after the whole `FLOWVLV_AOI` write-up rather than between
that run and its own verification section, so each run stays next to the
verification that belongs to it — same arrangement as the third and
fourth runs.

The fifth AOI type through the tool, and the type Doug originally flagged
back on 2026-09-10 as the natural next test candidate after `ALARM_AOI`.
Two-parameter mapping (`DeviceName`, `Description`) — no `EngUnit` — and
the Ignition UDT name is the **same** as the PLC AOI name for this
family, so `--udt-name` is deliberately omitted:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type INTERLOCK_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/INTERLOCK_AOI tag instances generated 2026-09-11.json"
```

**Result: 10 `INTERLOCK_AOI` instances**, all controller-scoped, none an
array, each with **5 members**. Kept in its **own file**, not merged with
the four prior runs — small test scopes first, per Doug's standing
instruction.

**This run inverts the shape of every prior run: the most instances (10,
where the previous high was 7) and by far the fewest members (5, where
the others were 38 and 51).** `INTERLOCK_AOI`'s entire L5X parameter set
is five parameters, in document order: `EnableIn`, `EnableOut`,
`Interlocks`, `Visibility`, `OutputState`. That is the correct and
expected outcome of the mapping-table note — this AOI's "many other
parameters" live on the Ignition UDT *definition* with defaults and are
inherited by the instance, so nothing is emitted for them; an instance
only ever carries parameters it actually overrides.

| Instance | L5X description |
|---|---|
| `BOP_BL1_INTERLOCK` | *(blank)* |
| `O2_AC001_INTERLOCK` | *(blank)* |
| `O2_AC010A_INTERLOCK` | *(blank)* |
| `O2_AC010B_INTERLOCK` | *(blank)* |
| `O2_AD002_INTERLOCK` | *(blank)* |
| `O2_BL2_INTERLOCK` | *(blank)* |
| `O2_MV112A_INTERLOCK` | *(blank)* |
| `O2_OG003_INTERLOCK` | *(blank)* |
| `O2_RB010A_INTERLOCK` | *(blank)* |
| `O2_RB010B_INTERLOCK` | *(blank)* |

Three things to look at before importing. All three are **flagged, not
filtered** — same reasoning as every prior run: the qualifying input is
an *AOI type*, and this task has no notion of job scope, description
quality, or name prefix within a type. Every one of these is a faithful
copy of what the PLC program actually says.

1. ⚠ **Every one of the 10 descriptions is blank — 10 of 10, the first
   run where this is true of any instance at all, let alone all of
   them.** A blank description is a real value here, not a missing field
   (see the script's module docstring and the `ALARM_AOI` run), so the
   `Description` parameter is still emitted for all 10 with an empty
   string, and the script listed every one of them explicitly rather
   than passing over them silently. This is a different anomaly class
   from `FLOWIN3_AOI`'s `description <number>` placeholders: there the
   PLC text was unfinished, here there is no PLC text at all. The
   operator-visible description on all 10 Ignition tags will be empty
   until something changes. Fixing it belongs in the L5X rather than in
   the generated JSON, so it survives the next regeneration — same
   conclusion as the `FLOWIN3_AOI` placeholders. Not acted on here;
   Doug's call.
2. ⚠ **One of the 10 is `BOP_`-prefixed, not `O2_`** —
   `BOP_BL1_INTERLOCK`; the other nine all carry the `O2_` prefix. Same
   class of folder-placement question as `BOP_FLR` on the `CONSPD4_AOI`
   run and the six `BOP_FIT30xx` tags on the `FLOWIN3_AOI` run, at the
   smallest share yet (1 of 10). Not filtered by name prefix — prefix
   filtering is exactly the loose `O2_`-match approach this task retired
   in the 2026-09-08 re-scope. Doug resolves placement by hand,
   tag-by-tag, during the Designer import.
3. ⚠ **The two DINT bitfield parameters (`Interlocks`, `Visibility`) are
   emitted as two flat `AtomicTag` members, one each — worth watching on
   import.** This is correct behavior for this script: members come from
   the L5X parameter list verbatim, and in the PLC each of these *is* a
   single DINT. But the real Ignition `INTERLOCK_AOI` UDT has per-bit
   tags manually bound for those bitfields, which is precisely the gap
   that has TASK_004's definition side on hold for this type (see
   `BLUE_SKY_STATUS.md`). So the generated instance's 5-member list is
   **not** expected to line up one-for-one with the real UDT's member
   list. Members are inherited from the definition and matched by name
   on import, so the practical question is what Designer does with two
   named members whose names may not exist on the definition. **Raised
   as an observation to watch during the import test, not a defect and
   not something to work around here** — the TASK_004 bitfield gap is a
   different task and explicitly out of scope for this run.

**No other anomaly classes present.** No duplicated descriptions across
tags (vacuously true — all blank, but checked rather than assumed), no
placeholder `description <number>` text, no array instances, no
program-scoped instances, no duplicate instance names.

### Verification of the `INTERLOCK_AOI` run (2026-09-11) — PASSED, structural only

**No reference export exists for this type**, so this is the same grade
of evidence the `CONSPD4_AOI`, `FLOWIN3_AOI` and `FLOWVLV_AOI` runs each
had before their Designer imports — *not* the export-verified grade all
four prior types now hold. The output was cross-read against the L5X by a
separate throwaway script that re-parses the L5X with its own code and
deliberately does **not** import `generate_ignition_tags.py` — a bug in
the tool's own helpers cannot hide itself by being used on both sides of
the comparison.

| Check | Result |
|---|---|
| Instance count vs. L5X instances of this type | **10 / 10** |
| Member count vs. `INTERLOCK_AOI`'s own L5X parameter set | **5 / 5** on all 10 instances |
| Member names — exact set match to the L5X parameters | match, zero missing / zero extra |
| Member order == L5X document order | match, all 10 |
| No duplicate member names | match |
| `typeId` == `BlueSky/AOI/INTERLOCK_AOI` on every instance | match, all 10 |
| `INTERLOCK_AOI` occurrences in the file == one per instance | **10 / 10** — appears only inside `typeId`, nowhere stray |
| `DeviceName` == `String` / `BOP_O2_CombinedTest` | match, all 10 |
| `Description` == that instance's own L5X description, verbatim | match, all 10 — all empty strings |
| Parameter set == exactly `DeviceName` + `Description` (no more, no less) | match, all 10 — no defaulted parameter leaked through |
| Top-level key shape == the verified prior runs | match (`name`, `parameters`, `tagType`, `tags`, `typeId`) |
| `tagType` == `UdtInstance`; members only `name` + `tagType: AtomicTag` | match |
| Instance names == L5X tag names verbatim | match, all 10, same order |
| No duplicate instance names | match |
| Top-level payload shape == `{"tags": [...]}` | match (`--folder-mode flat`) |

15 checks, all passed.

Note on the name-occurrence row — this is the `FLOWIN3_AOI` variant of
the check, not the `CONSPD4_AOI`/`FLOWVLV_AOI` one. Here the PLC name and
the UDT name are the **same**, so zero occurrences would be the wrong
expectation; the equivalent check is that the name appears *exactly once
per instance*, inside `typeId` and nowhere else. Ten instances, ten
occurrences.

Note on the parameter-set row — it carries more weight on this type than
on any prior run. `INTERLOCK_AOI` is the type with "many other
parameters" defined on the Ignition UDT, so the meaningful assertion is
not just that `DeviceName` and `Description` are present but that
**nothing else leaked through**: every one of those other parameters must
stay absent from the instance and be inherited from the definition's
defaults. Confirmed absent on all 10.

**What this does and does not establish.** It establishes that the
two-parameter mapping emits with no `EngUnit`, that no defaulted
parameter leaks into the instances, that the 5-member list comes from the
L5X in document order, and that the PLC-name-equals-UDT-name case builds
`typeId` correctly. It does **not** establish that the real Ignition
`INTERLOCK_AOI` UDT has exactly these 5 members — and for this type there
is positive reason to expect it does not, because of the manually
expanded bitfield tags noted as flag 3 above. Only a real export or a
Designer import can settle that. The UNVERIFIED warning printed on this
run, as it should have.

### Sixth run — `LEVELIN3_AOI` (2026-09-12)

Run against a freshly re-exported L5X (same filename,
`BOP_O2_CombinedTest_v35_Emulate.L5X`, intake-cleared through
`PII_Review` the same day — the two known LINT-timestamp false positives
applied per the standing exception in `BlueSky/CLAUDE.md`, no other flag
type present). Ignition UDT name is the **same** as the PLC AOI name for
this family, so `--udt-name` is deliberately omitted:

```
python generate_ignition_tags.py \
  --l5x "../BlueSky/BOP_O2_CombinedTest_v35_Emulate.L5X" \
  --aoi-type LEVELIN3_AOI \
  --device-name "BOP_O2_CombinedTest" \
  --dest-folder "[default]O2InjectionSystem" \
  --udt-path-prefix "BlueSky/AOI" \
  --output "../BlueSky/LEVELIN3_AOI tag instances generated 2026-09-12.json"
```

**Result: 26 `LEVELIN3_AOI` instances**, all controller-scoped, each
carrying the same **3-member set** — `Description`, `DeviceName`,
`EngUnit` — out of 90 total parameters defined on the AOI (the other 87
are UDT-defaulted and correctly not emitted, same pattern as every prior
run). Kept in its own file, not merged with the five prior runs.

| Instance | L5X description |
|---|---|
| `BOP_GC3001` | O2 Receiver Tank Gas CH4 |
| `BOP_GC3002` | O2 Receiver Tank Gas CH4 |
| `BOP_GC3003` | O2 Receiver Tank Gas CH4 |
| `BOP_GC3004` | O2 Receiver Tank Gas CH4 |
| `BOP_GC3005` | O2 Receiver Tank Gas CH4 |
| `BOP_GC3008` | O2 Receiver Tank Gas CH4 |
| `BOP_PIT3001` | RNG Pressure |
| `O2_BA400_CH4` | Analyzer BA-400 CH4 |
| `O2_BA400_CO2` | Analyzer BA-400 CO2 |
| `O2_BA400_H2S` | Analyzer BA-400 H2S |
| `O2_BA400_N2` | Analyzer BA-400 N2 (calculated) |
| `O2_BA400_O2` | Analyzer BA-400 O2 |
| `O2_PIT010A` | Blower-A Suction Pressure |
| `O2_PIT010B` | Blower-B Suction Pressure |
| `O2_PIT012A` | BLOWER-A DISCHARGE PRESSURE |
| `O2_PIT012B` | BLOWER-B DISCHARGE PRESSURE |
| `O2_PIT020A` | Digester-A Cover Pressure |
| `O2_PIT020B` | Digester-B Cover Pressure |
| `O2_PIT3012` | WSP-3 Lagoon Pressure 1 |
| `O2_PIT3013` | WSP-3 Lagoon Pressure 2 |
| `O2_PIT3014` | WSP-4 Lagoon Pressure 1 |
| `O2_PIT3015` | WSP-4 Lagoon Pressure 2 |
| `O2_TIT010A` | Blower-A Discharge Temperature |
| `O2_TIT010B` | Blower-B Discharge Temperature |
| `O2_TIT011A` | Digester-A After-cooler cooled-gas discharge temperature |
| `O2_TIT011B` | Digester-B After-cooler cooled-gas discharge temperature |

Two things to look at before importing. Both **flagged, not filtered**,
same reasoning as every prior run:

1. ⚠ **7 of the 26 are `BOP_`-prefixed** (`BOP_GC3001`–`BOP_GC3005`,
   `BOP_GC3008`, `BOP_PIT3001`) — the largest `BOP_` share of any run so
   far (previous high: 1 of 10 on `INTERLOCK_AOI`). Same class of
   folder-placement question as `BOP_FLR` (`CONSPD4_AOI`), the six
   `BOP_FIT30xx` tags (`FLOWIN3_AOI`), and `BOP_BL1_INTERLOCK`
   (`INTERLOCK_AOI`) — not filtered by name prefix, per the task's
   standing scope (qualifying input is an AOI type, not a job-scope
   prefix). Doug resolves placement by hand during the Designer import.
2. ⚠ **`EngUnit` is blank on all 26 instances.** A real value, not a
   missing field — same "blank is data, not absence" treatment as
   `INTERLOCK_AOI`'s all-blank descriptions. Every one of these tags will
   show no engineering unit in Ignition until the source AOI instances
   in the PLC program carry one. Not acted on here; Doug's call whether
   any of these actually need a unit filled in on the PLC side.

**No other anomaly classes present.** No duplicate instance names, no
array instances, no program-scoped instances, no placeholder
`description <number>` text (unlike `FLOWIN3_AOI`).

**The script's own printed warning applies to this type**: *"AOI type
'LEVELIN3_AOI' parameter mapping is UNVERIFIED — it records Doug's
stated intent but has never been checked against a real Ignition
tag-instance export. Verify one instance by hand before importing in
bulk."* Same evidence tier as `CONSPD4_AOI`, `FLOWIN3_AOI`,
`FLOWVLV_AOI`, and `INTERLOCK_AOI` before their own Designer imports —
not the export-verified grade the first four runs now hold.

### Verification of the `LEVELIN3_AOI` run (2026-09-12) — PASSED, structural only

**No reference export exists for this type**, so this is the same grade
of evidence as every run since `ALARM_AOI`. Cross-read against the L5X by
a separate throwaway script that independently re-parses the L5X and does
**not** import `generate_ignition_tags.py`.

| Check | Result |
|---|---|
| Instance count vs. L5X instances of this type | **26 / 26** |
| Instance names — exact set match to the L5X | match, zero missing / zero extra |
| Instance order == L5X document order | match, all 26 |
| No duplicate instance names (L5X or JSON) | match |
| `typeId` == `BlueSky/AOI/LEVELIN3_AOI` on every instance | match, all 26 |
| `LEVELIN3_AOI` occurrences in the file == one per instance | **26 / 26** — appears only inside `typeId`, nowhere stray |
| `tagType` == `UdtInstance` on every instance | match |
| `DeviceName` == `String` / `BOP_O2_CombinedTest` | match, all 26, one consistent value |
| `Description` == that instance's own L5X description, verbatim | match, all 26 |
| `EngUnit` == that instance's own L5X value, verbatim | match, all 26 — all blank |
| Member set == exactly `Description` + `DeviceName` + `EngUnit` (no more, no less) | match, all 26 — no defaulted parameter (of the other 87) leaked through |
| Top-level key shape == the verified prior runs | match (`name`, `parameters`, `tagType`, `tags`, `typeId`) |
| Top-level payload shape == `{"tags": [...]}` | match (`--folder-mode flat`) |

13 checks, all passed.

Note on scope: `Description`, `DeviceName`, and `EngUnit` are the tool's
standard always-emitted fields (confirmed against the `ALARM_AOI` and
`FLOWIN3_AOI` write-ups above), not members drawn from the AOI's own
90-parameter L5X list — an early draft of this verification incorrectly
checked emitted members against the raw AOI parameter list and threw a
false failure on exactly these three names before this was caught and
corrected. Recorded here so the same mistake isn't repeated verifying a
future run.

**What this does and does not establish.** It establishes that the
three-field mapping (`Description`, `DeviceName`, `EngUnit`) emits
correctly, that none of the other 87 UDT-defaulted parameters leak into
the instances, that instance order and names match the L5X exactly, and
that `typeId` builds correctly for the PLC-name-equals-UDT-name case. It
does **not** establish that the real Ignition `LEVELIN3_AOI` UDT expects
exactly these three members — only a real export or a Designer import
settles that, per the UNVERIFIED warning above.

### `ALARM_AOI` regression after adding `--udt-name` (2026-09-10) — PASSED

Re-run with **no `--udt-name` given**, output compared to the file
generated before the change: **byte-for-byte identical** (`cmp`, zero
differences). That is the real evidence the new parameter changed nothing
for the one type that was verified against a real export. Console output
gained one line naming the UDT name in use; the JSON is unchanged.

Two guard rails were also tested negatively, each exiting non-zero and
writing no file: `--udt-name` alongside more than one `--aoi-type`
(refused as ambiguous), and both `--udt-name` and `--aoi-type NAME=UDT`
given for the same type (refused rather than silently picking one). The
two equivalent forms were also confirmed to produce byte-identical output
for `CONSPD4_AOI`.

### Open Questions — still open for the remaining 7 AOI types

*(2026-09-10: the two questions below are genuinely unanswered. They were
**not** resolved by the `ALARM_AOI` build and must not be treated as
settled because code now exists.)*

- **Where the qualifying-AOI-type list lives** — still open. It is
  explicit input (Process step 2), but its *home* is undecided: a small
  per-job JSON file, a text file, or something else. Doug's standing
  instruction is **"don't invent the format, ask,"** so the first-pass
  build deliberately invented nothing — it takes the list as repeatable
  `--aoi-type` command-line arguments. When Doug decides, a loader can be
  added in front of that same argument with no change to anything else.
- **Reuse vs. duplicate parsing logic with TASK_004** — still open, and
  now concrete rather than hypothetical. `generate_ignition_tags.py`
  currently has its own small L5X parsing helpers; it does **not** import
  from `generate_ignition_udt.py`. That was the right call for a first
  pass (no risk of destabilizing a working, heavily-used script), but the
  duplication is real and should be resolved deliberately rather than
  left to drift.

Resolved, kept for history:

- ~~**`DeviceName` parameterization**~~ — resolved 2026-09-10: one value
  for the whole run (Process step 3).
- ~~**Naming/instance-path convention**~~ — resolved 2026-09-10. The tag
  name is the PLC instance tag name verbatim (confirmed: the reference's
  `O2_AC001_FAILURE` is exactly the L5X tag name). Folder placement is
  `--dest-folder`, and is chosen at import time — see the destination
  folder section above.
- ~~**Example Ignition tag export needed**~~ — resolved 2026-09-10:
  `BlueSky/ALARM_AOI example tags.json` supplied and intake-cleared. It
  also settled the OPC-path question in an unexpected direction: instance
  members carry **no** OPC path at all, because they inherit it from the
  definition. There was no instance-level OPC convention to derive.

*(Retired framing, superseded 2026-09-08: the original idea matched
tags by a loose `O2_`-prefix pattern rather than "AOI instances of a
type with a valid UDT" — kept here for history, not the current spec.)*

---

## TASK_006 — Audit Ignition tags for orphaned/unmatched instances

**Status:** Idea (raised 2026-09-08, not yet fully speced)

### Purpose

The reverse problem from TASK_005. TASK_005 fills in Ignition tag
instances that *should* exist but don't yet. This task finds Ignition
tag instances that *do* exist but arguably **shouldn't** — leftovers
from testing, stale references, or anything else that's drifted out of
sync with the real PLC program. Doug's own framing: *"if they're there,
they should be in my program. If they're not in my program, then I need
to know why they're there."*

### Process (as Doug described it 2026-09-08)

1. Take a real export of Doug's existing Ignition tags (e.g. every
   instance with an `O2_` prefix) — **this export doesn't exist yet**,
   Doug needs to produce one before this task can be built or run.
2. Cross-reference each exported Ignition tag against the real, current
   L5X.
3. Any Ignition tag with **no matching real tag in the current PLC
   program** gets flagged for Doug's review.
4. **Never auto-deletes or auto-resolves anything** — same Hard Scope
   Boundary philosophy as everywhere else in PLCHelper (see TASK_004's
   "never add/remove/flag members based on differences" for correcting
   an existing UDT). This task surfaces a list; Doug decides what each
   flagged tag actually means and what to do about it.

### Relationship to TASK_005

Opposite direction of data flow. TASK_005 is PLC → Ignition (create
what's missing); TASK_006 is Ignition → PLC (find what shouldn't be
there). Both came out of the same 2026-09-08 conversation about what's
needed once the Blue Sky UDT-regeneration batch is further along — kept
as two separate tasks rather than one combined one, since they need
different inputs and run in opposite directions.

### Open Questions — needs a real scoping pass before this becomes Spec Ready

- **The Ignition tag export itself doesn't exist yet** — format and
  scope (all `O2_`-prefixed tags? something narrower?) need Doug's input
  once he's ready to produce one.
- **What counts as "no match"?** Exact tag-name match against the L5X,
  or something looser (e.g. matching by AOI instance + member path)?
  Not yet defined.
- A cheap, immediate first step was offered and **explicitly deferred by
  Doug (2026-09-08): a plain list of every real `O2_`-prefixed tag in
  the current L5X**, as a baseline reference to eyeball against Ignition
  manually in the meantime. Available on request whenever Doug wants it
  — no need to re-derive this from scratch later.

This task stays at Idea status until these are worked through with Doug,
per this file's own convention (spec first, build second).

---

## TASK_007 — Bulk-update a derived convention across an existing UDT's members

**Status:** Idea (raised 2026-09-08, not urgent)

### Purpose

TASK_004 already derives conventions like `opcServer` as **one value**
from the reference and stamps it uniformly across every generated
member (verified 2026-09-08: `generate_ignition_udt.py` —
`derive_conventions()`'s single `opc_server` derivation, stamped onto
every member by `build_member()` — one derived value, no per-member
variation, confirmed against Doug's own stated vision for how this
should work. Cited by function rather than by line number on purpose:
the original citation gave line numbers, which went stale the moment the
file grew). But there's no way
yet to update that single value across an **existing** UDT definition's
members after the fact — e.g. if a different client/site uses a
different OPC Server connection name than the one baked into Blue Sky's
references.

### Process (rough idea, not yet speced)

Given an existing UDT definition JSON and a target field (e.g.
`opcServer`) plus a new value, rewrite that field across every member in
one pass — the update-equivalent of what TASK_004 already does at
generation time, applied to something already generated.

### Open Questions

- Not urgent — no second client/site has come up yet. Revisit when one
  does, or if Doug wants it sooner.
- Whether this generalizes to any convention field, or is scoped
  specifically to `opcServer`.

---

## TASK_008 — Generate Ignition UDT definition from a native PLC UDT

**Status:** Implemented (2026-09-08) — same script as TASK_004:
`generate_ignition_udt.py`, via `--datatype` instead of `--aoi`

### Purpose

Not everything on a job's Ignition-handoff checklist is an AOI. `MODVLV`
sat on Blue Sky's per-AOI checklist in `BLUE_SKY_STATUS.md` and turned
out not to be an AOI at all — it is a **native Rockwell UDT**, a
`<DataType Class="User">` element with its own `<Members>` block, not an
`<AddOnInstructionDefinition>`. TASK_004 could not read it, and there is
no reason a type's *source element* should decide whether Doug gets a
generated UDT or has to hand-build one in Designer.

This task closes that gap. It is deliberately **not** a second tool:
`--datatype NAME` selects a different parser for the member list, and
everything downstream is TASK_004's existing code path, unmodified.

### Relationship to TASK_004 — what is shared, what differs

**Shared, verbatim and by construction** (see TASK_004 for the full
detail of each — deliberately not restated here, per Lesson 9):

- the reference-UDT **convention derivation** (OPC Server value, OPC
  Item Path template shape, `bindType`, member JSON key set and constant
  values, top-level type shape, parameter blanking, history context)
- the **Historization rule**, including the suffix and bare-word forms
  and the `_alm_*` compound-control exclusion
- the **data type mapping** table and its report-never-guess behavior
  for unmapped types
- the **output shape**, the console report, and the
  analog-deadband REVIEW REQUIRED block
- `--udt-name`, which still never infers a name

This is possible because both parsers return the same member dict shape,
so the conventions and the historization rule operate on the derived
member list — not on anything AOI-specific.

**Only two things differ:**

| | TASK_004 (`--aoi`) | TASK_008 (`--datatype`) |
|---|---|---|
| Source element | `<AddOnInstructionDefinition>` → `<Parameters>` → `<Parameter>` | `<DataType Class="User">` → `<Members>` → `<Member>` |
| Member filtering | none — every parameter becomes a member | every **visible** member becomes a member; `Hidden="true"` backing members are excluded (below) |

The confirmed-dead **member-exclusion mechanism** added 2026-09-08 (see
Open Questions) is *not* one of the differences — it is shared, and works
the same way in both modes.

A native UDT member has no `Usage` (Input/Output/InOut) the way an AOI
parameter does, so the console report omits the by-usage line for this
mode and prints the hidden-member exclusion instead. Per-member
`<Description>` elements **do** exist on native UDT members (36 of
MODVLV's 49 carry one), same as AOI parameters — so nothing is lost
there.

### Hidden backing members are excluded (Doug-confirmed, 2026-09-08)

When a native UDT contains boolean members, Studio 5000 does not store
them as individual BOOLs. It **packs them into auto-generated integer
storage members** named `ZZZZZZZZZZ<TypeName><n>` and marked
`Hidden="true"`, then exposes each real bit as its own visible member
with `DataType="BIT"`, a `Target` naming the backing member, and a
`BitNumber`. MODVLV: 4 hidden `SINT` backers holding 24 visible `BIT`
members.

| Member kind | Treatment | Why |
|---|---|---|
| `Hidden="true"` backing member (`ZZZZZZZZZZMODVLV13`, …) | **Excluded** | Studio 5000's own bit-packing storage, not an independent data point. Doug confirmed these should not appear; they are absent from his Ignition tag list view, and independently absent from the real MODVLV UDT export used as the reference — 35 members, zero `ZZZ` members |
| `Hidden="false"`, `DataType="BIT"` bit-alias member (`FAILCLS_alm_dis`, …) | **Included**, as its own `Boolean` member | A real, independently addressable data point. Which hidden integer happens to store it is a PLC storage detail with no meaning on the Ignition side, so the generated member carries no trace of the packing |
| Every other `Hidden="false"` member | **Included**, exactly as TASK_004 would | no change |

**The exclusion reports itself rather than acting silently.** Every run
prints each excluded backing member, its PLC type, and the visible bits
aliased onto it. And a hidden member that backs **no** visible `BIT`
member raises a warning — that is not the bit-packing pattern this
exclusion was written for, so it gets a human look instead of being
assumed droppable.

### Inputs

Identical to TASK_004's inputs, with one substitution:

| Input | Format | Notes |
|-------|--------|-------|
| DataType name | string | e.g. `MODVLV`. Must match the `Name` attribute of a `<DataType>` in the L5X exactly, and that DataType must be `Class="User"` — a non-User class is refused rather than parsed |
| L5X export | `.L5X` (XML) | Same file and same cross-folder read pattern as TASK_004 |
| Reference UDT JSON | `.json` | Same requirement as TASK_004 — an Ignition **UDT Definitions** tab export, read for conventions only |

`--list-datatypes` lists every `Class="User"` DataType with its visible
and hidden member counts, the counterpart to `--list-aois`.

`--exclude NAME[=reason]` (repeatable) drops one member for a single run —
see the general member-exclusion mechanism in Open Questions below. It is
available in both `--aoi` and `--datatype` mode.

### Process

1. **Parse the L5X** for the named `<DataType Class="User">` and read its
   `<Members>` block in document order, dropping `Hidden="true"` members
   and recording which visible `BIT` members aliased onto each one.
2. **Apply confirmed-dead member exclusions**, if any are configured for
   this type — shared with the `--aoi` path, running on the parsed member
   list rather than inside either parser.
3. **Steps 3 onward are TASK_004's, unchanged** — derive conventions
   from the reference, map data types, apply the historization rule,
   build members, write the output JSON into the job's own folder.

### Outputs

1. A new Ignition UDT definition JSON in the job's folder, importable via
   Designer's **UDT Definitions** tab — same format and same import
   procedure as TASK_004's output.
2. The same console report as TASK_004, plus the hidden-member exclusion
   block described above.

**First real run (2026-09-08):** `MODVLV` →
`BlueSky\MODVLV UDT definition generated 2026-09-08.json`. 45 visible
members generated, 4 hidden backing members excluded, 17 members
historized by the naming rule (13 digital, 4 analog).

**Regenerated later the same day**, after Doug confirmed `.PID`,
`.DLYTMR`, `.FTO_TMR`, and `.FTC_TMR` are dead code (see Open Questions):
**41 members**, 4 hidden backing members excluded *plus* those 4
confirmed-dead members excluded, the same 17 historized members
(13 digital, 4 analog). The four `String`/NEEDS REVIEW placeholder
warnings are gone; the only remaining warning is the pre-existing `LBIAS`
(`INT` → `Int4`) inference note. Nothing else in the file changed —
verified member-by-member against the previous output, with document order
preserved.

### Open Questions / Notes

- **RESOLVED 2026-09-08 — MODVLV's `TIMER` and `PID` members are
  confirmed dead code and are now excluded.** MODVLV's three `TIMER`
  members (`DLYTMR`, `FTO_TMR`, `FTC_TMR`) and its one `PID` member are
  Rockwell *structured* predefined types, so no single Ignition atomic
  member can represent them, and until now they hit the unmapped-type
  path: a `String` placeholder plus a NEEDS REVIEW warning every run.
  That was the correct behavior while the question was open — the earlier
  note here recorded that Doug's own MODVLV reference UDT omits all four,
  and that dropping them on the script's own initiative would have been
  exactly the guessing the warning exists to prevent.

  **Doug has now confirmed all four are genuinely unused/dead in the real
  PLC program** — a stronger statement than "unmappable." `.PID` is an
  obsolete embedded PID block; this valve's real PID control is a
  separately defined **PIDE**-type tag, and Doug found and fixed a live
  bug where PLC code referenced the embedded block instead of the correct
  separate PIDE tag. The three `TIMER` members are leftover
  example/template code that was never cleaned up and are referenced
  nowhere in the current program. Full detail lives on each member's own
  line in `PLCHelper_Reference.md`'s MODVLV entry — including the standing
  warning that *referencing* `.PID` at all is the symptom of doing it
  wrong. All four are now dropped from generated output via the general
  mechanism below; the four NEEDS REVIEW warnings are gone and MODVLV
  generates 41 members instead of 45.

  The question this note originally left open for *future* native UDTs is
  still open, and is unchanged by the above: whether a structured type
  should be expanded into per-field members, omitted outright, or keep
  being flagged. Nothing here decides that in general — it only records
  Doug's decision about four specific MODVLV members.

- **General member-exclusion mechanism (added 2026-09-08) — opt-in, and
  it reports itself.** The MODVLV resolution above is not MODVLV-specific
  code. `generate_ignition_udt.py` gained a general exclusion mechanism
  any AOI or native UDT can use the same way, and it works identically in
  `--aoi` and `--datatype` mode because the filtering runs on the
  **derived member list, downstream of both parsers** — the same
  construction that already lets the conventions and the historization
  rule be shared code rather than duplicated per mode.

  Two ways in, deliberately asymmetric:

  | Route | Scope | Use it for |
  |---|---|---|
  | `MEMBER_EXCLUSIONS` table in the script, keyed by source type name | every future run | a **settled** decision. This is the persistent record, and it is where the MODVLV four live |
  | `--exclude NAME[=reason]`, repeatable | one run | an ad-hoc/exploratory drop. Additive to the table and **cannot cancel** a table entry — a documented decision is not overridable by a command-line typo |

  Design points worth not re-litigating later:

  - **Keyed by type name, not by member name alone.** `PID` and `DLYTMR`
    are dead *in MODVLV*; a member of the same name in some other type is
    a different member with a different history. Excluding by bare name
    collision would be the script making a judgment call it is not
    entitled to make.
  - **Names match case-insensitively; the report prints the L5X's own
    verbatim spelling.** Case-exactness matters functionally for a
    generated member name (bug pattern #2), not for looking one up in a
    config table.
  - **Nothing is ever dropped silently.** Every run prints each excluded
    member with its PLC data type, the reason, and which route it came
    from, at step 1 *and* again after the "Generated N members" line — the
    report is long and a dropped member must not be something a reader has
    to scroll back for. Same reports-itself principle as the hidden
    `ZZZZZZZZZZ*` backing-member exclusion.
  - **A configured exclusion that matches no member raises a warning.**
    A typo, or a member renamed in the PLC since the exclusion was
    written, would otherwise look exactly like a successful run. Same
    defensive shape as the "hidden member that backs no visible BIT"
    warning.
  - **The 2026-09-04 scope decision still stands.** The script does not
    get an opinion about which members are "needed for SCADA." An entry in
    `MEMBER_EXCLUSIONS` is a record of Doug's decision, never the
    script's, and the table's own comment says what does *not* belong in
    it: merely-unmappable data types (already correctly handled by the
    NEEDS REVIEW warning) and members that just "look unnecessary."
  - **Rule 37 pairing.** A member excluded here must also be marked
    dead in `PLCHelper_Reference.md`'s entry for that type. A member noted
    dead in the script and still described as live in the reference is
    exactly the two-places-one-fact drift Lesson 9 exists to prevent.
- **`LBIAS` (`INT`) mapped to `Int4` by inference,** flagged in the
  report as TASK_004 already does for `SINT`/`INT` — unchanged behavior,
  noted here only because MODVLV is the first type to actually hit it.
- **The reference and the current PLC UDT disagree on membership**, which
  is expected and not this task's problem: the real MODVLV Ignition UDT
  has 35 members, of which 3 (`MANCLOSE_scdo`, `MANOPEN_scdo`,
  `AUTO_hwdi`) no longer exist in the PLC type at all, while 13 current
  PLC members are missing from it. The generated file is built from the
  L5X, so it reflects the PLC as it is now. Reconciling the existing
  Ignition UDT against it is a TASK_006-flavored question, not part of
  generation.
- **The AOI path is provably untouched.** `FLOWIN3_AOI` and `ALARM_AOI`
  were both regenerated before and after this change with identical
  inputs and produced **byte-identical** JSON, and `--list-aois` output
  was unchanged. **Re-verified the same way for the 2026-09-08 exclusion
  mechanism**: both AOIs byte-identical before and after, `--list-aois`
  and `--list-datatypes` both unchanged, and the console report identical
  apart from the output filename. Neither AOI has an entry in
  `MEMBER_EXCLUSIONS`, so the exclusion code path is a no-op for them —
  which is exactly what "opt-in" has to mean to be worth anything.

---

## TASK_009 — Audit Ignition alarm tag configuration for formatting problems

**Status:** Implemented, patched, and re-run (2026-09-09) — script:
`audit_alarm_tags.py`, all 9 rules live. Rules 5 (priority) and 9
(historian config) were tightened after the first real run, going through
the findings with Doug line by line (see the two rules' own text for exact
detail); the script was patched to match the same day and re-run against
Weston's real export. **Re-run result: 143 tags, 0 OK, 367 problems** —
up from 356 under the original looser rule 5 ("present and non-blank")
and no rule 9 at all. The 11 new findings are 1 priority override
(`CP_6000_PLC_Comm_Loss_Alm`, `Critical` in the `800` folder) and 10
historian-config problems across 3 tags. See "Re-run after the rule 5/9
tightening" below.

### Purpose

CPKCR-Weston's ticket history (see `CPKCR-Weston/CPKCR_WESTON_STATUS.md`)
shows a recurring pattern: alarms with formatting/configuration problems
that only surface when the alarm actually fires and displays wrong.
Confirmed root cause this session for ticket CS0175981
(`AlmLIT107_HiHi_Alm`): Weston's alarm tags carry a
`CustomEmailSubject`/`CustomEmailMessage` override that every other site
on the shared Ignition alarm-notification system leaves blank — Weston's
override caused Andrew to receive a generic, site-less email instead of
the pipeline's own better default. A second, more serious issue was found
in the same investigation: 56 of Weston's 800-series alarms
(`AUTO_DIALER_CH_01`–`CH_56`) reference `activePipeline:
"Site Pipelines/Weston"`, a pipeline Doug confirmed does not exist — these
alarms likely send no notification at all. This tool checks every alarm
tag in a site's export against the correctness rules below and reports
problems — read-only, no fixes applied.

### Inputs

| Input | Format | Notes |
|---|---|---|
| Ignition alarm tag export | JSON (Ignition Tag Export of a site's `Alarms` folder) | e.g. `CPKCR-Weston/Weston Alarms tags.json` — a folder tree of `AtomicTag`s, each with an `alarms` array |
| List of valid pipeline names for the site being audited | Known ahead of time per site, not derivable from the tag export alone | For Weston: `WWHMPWWT1/Weston_500`, `WWHMPWWT1/Weston_800` |

### Process

For every alarm tag found in the export, check:

1. **`notes` non-blank** — every alarm needs a real, human-readable
   description; this is what the pipeline's default template surfaces.
2. **`activePipeline` matches the tag's own site/folder** — must equal a
   known-valid pipeline name for that site, specifically the pipeline
   matching the tag's folder (a tag under `.../500/` must reference the
   site's `_500` pipeline, not `_800` or vice versa). Flag the exact
   invalid value by name (not just "invalid") so a known-bad value like
   `"Site Pipelines/Weston"` is immediately recognizable in the report.
3. **`CustomEmailSubject` and `CustomEmailMessage` both blank** — these
   override the pipeline's own default template when non-blank; per
   Doug's confirmed fix direction, every alarm (including test tags — no
   exemptions) should leave both blank.
4. **`enabled` is `true`.**
5. **`priority` must exactly match a folder-based rule, not just be
   present.** Doug's confirmed standing rule (2026-09-09), for all
   alarms on this Ignition system: a tag in the `500` folder must be
   `Medium`; a tag in the `800` folder must be `High`. This overrides
   any existing value, not just fills in a missing one — confirmed
   explicitly against the one real exception found, `CP_6000_PLC_Comm_Loss_Alm`
   (currently `Critical`, in the `800` folder): Doug's own words, "they
   need to match the rule... it is wrong." No other priority values are
   valid on this system per this rule.
6. **`tagGroup` and `historyTagGroup` match the site being audited** —
   catches copy-paste artifacts like a Weston alarm carrying `tagGroup:
   "MasonCity"`.
7. **The alarm's own `name` field matches its parent tag's `name`.**
8. **`displayPath` fully matches the tag's actual path** — reconstruct
   the expected path from the tag's real position in the tree
   (`<Site>/Alarms/<folder>/<tagname>`, matching the convention 140 of
   Weston's 143 tags already use) and compare it against the literal
   `displayPath` value for an exact match — not just checking whether
   the tag name appears at the end. Broadened 2026-09-09 (was originally
   "last segment matches tag name" — too narrow, would miss the
   `[default]` provider-prefix inconsistency found on `_Test500`,
   `_Test800`, and `CP_6000_PLC_Comm_Loss_Alm`, since only the trailing
   segment was being checked).
9. **Historian configuration must match the site-wide convention.**
   Added 2026-09-09, confirmed with Doug after his own Designer
   screenshot showed the real convention: `historyEnabled: true`,
   `historyProvider: "Hist_IW"`, `historicalDeadbandStyle: "Discrete"`.
   Note that Ignition's tag JSON export omits a History property
   entirely when it matches Ignition's own default — so "Deadband Mode:
   Absolute," "Sample Mode: On Change," etc. shown in Designer are
   defaults being displayed, not actual overrides in the file. This
   rule is therefore two-sided: (a) the three properties above must be
   present with those exact values, and (b) **no tag should carry an
   explicit `sampleMode`, `historyMaxAge`, or `historyMaxAgeUnits` at
   all** — every compliant tag omits these and relies on the defaults;
   an explicit value is itself the violation. Found on
   `CP_6000_PLC_Comm_Loss_Alm` (the only tag with `sampleMode:
   "TagGroup"` plus its own `historyMaxAge`/`historyMaxAgeUnits`) —
   Doug confirmed 2026-09-09 this should be normalized to match every
   other tag, not preserved as a deliberate exception.

Rules 1–9 apply uniformly to every tag in the export, including tags
named `_Test*`/`Test*` — no special-casing or exemptions (confirmed with
Doug 2026-09-09; test tags should reflect the same corrected
configuration as real alarms, since they're used to validate real
notification behavior by being manually triggered).

### Outputs

A report, in this shape (exact wording TBD at implementation, structure
is fixed):
- A summary line: total tags scanned, count OK, count with problems.
- Every tag with at least one problem, **sorted alphabetically by tag
  name**, with **one problem description per line** (a tag with multiple
  problems gets multiple lines, grouped under that tag).
- No fixes are applied — report-only, per TASK_010 being a deliberately
  separate tool.

### Genuinely blocked → unblocked (2026-09-09)

Originally blocked because "nobody has yet determined what 'correctly
configured' actually means," with Doug's own planned path to unblock it:
(1) get the real notification email for `AlmLIT107_HiHi_Alm` from
Andrew, (2) diagnose the misconfiguration, (3) fix that one alarm and
re-trigger it to confirm, (4) only then spec the task.

Steps 1–2 happened this session — Andrew's actual received email was
compared byte-for-byte against the tag's `CustomEmailMessage` template
(exact match), and cross-referenced against `All Alarms tags.json` (8
sites, 921 alarms): **every single non-blank `CustomEmailSubject` in the
entire export belongs to Weston** — confirming the diagnosis is systemic,
not one alarm. Doug decided this evidence is sufficient to proceed to
Spec Ready without waiting on step 3 in its original form. Step 3 was completed via a safer substitute: the existing `_Test500`
memory tag (not the real `AlmLIT107` alarm) was updated to the corrected
configuration, imported into the live gateway, and manually triggered.
**Result, confirmed 2026-09-09:** the received email matched the
predicted corrected format exactly — subject "Weston IW: Ignition Alarm
Notification" (site name present), body leading with the bolded notes
text ("Notes Test 500"). The fix is proven live, without touching a real
production alarm. Not yet applied to Weston's other ~140 alarm tags
(including the real `AlmLIT107_HiHi_Alm`) — that's TASK_010's job once
this task's script exists.

**Follow-up same day:** Doug added `{displayPath}` to the `Weston_500`
pipeline's own Message template directly in Designer (a pipeline-level
change, applies automatically to every real 500-series alarm), and
re-confirmed the email now also states the full alarm path. This is a
pipeline-template detail, not a tag-level field this task's audit rules
check — noted here for completeness, no change to the 8-rule spec above.
`Weston_800`'s pipeline has not been given the same addition.

### Open Questions

- Export format/source confirmed: an Ignition Tag Export of the `Alarms`
  folder, per `CPKCR-Weston/Weston Alarms tags.json`.
- **Per-site valid-pipeline list is not derivable from the tag export
  alone** — must be supplied as a lookup the tool is given, or hardcoded
  per site with a documented source. For Weston it's confirmed:
  `WWHMPWWT1/Weston_500` / `WWHMPWWT1/Weston_800`.
- Sites are **not assumed uniform** — Doug's own caution stands. New
  finding this session that bears on it: `All Alarms tags.json` shows
  every other site (Golden, MasonCity, MooseJaw, Nahant, PoCo, StLuc,
  StPaul) already leaves `CustomEmailSubject`/`CustomEmailMessage` blank
  — Weston is the outlier there. But StLuc has its own separate open
  question (3 alarms with a hardcoded `activePipeline:
  "WWHMPWTP2/StLuc"` — Gateway 2, confirmed to be a genuinely separate,
  unsynchronized Ignition installation from Gateway 1 `WWHMPWWT1` — not
  yet confirmed whether this is legitimate or a bug; see
  `CPKCR-Weston/CPKCR_WESTON_STATUS.md` Open Questions/Gaps #3). **This
  tool's first implementation targets Weston only** — do not assume the
  same valid-pipeline list applies elsewhere without checking each site
  individually.
- Scope of rules 6–8 (tagGroup/name/displayPath consistency) was
  confirmed in-scope for v1 by Doug 2026-09-09, expanding beyond the
  originally-planned notification-path-only checks, after those exact
  issues were found on a real tag (`CP_6000_PLC_Comm_Loss_Alm`).

### Implementation notes (`audit_alarm_tags.py`, 2026-09-09)

**CLI:** `--input <alarm export JSON>` and `--site <name>`, both required.
`--site` does triple duty: it selects the confirmed pipeline list, it is
the expected `tagGroup`/`historyTagGroup` value, and it is the leading
segment of every expected `displayPath`. Stdlib only, no dependencies.

**How the two Open Questions above are honored in code, not just in
prose:**
- The per-site pipeline list is a module-level `SITE_PIPELINES` table with
  only Weston populated and every other known site listed as an explicit
  `NOT YET CONFIRMED` comment. A site absent from that table does not fall
  back to Weston's naming and does not silently pass — the run prints a
  warning block saying rule 2 cannot be checked for that site, still
  checks the other seven rules, and marks every rule-2 line
  `CANNOT VERIFY`. Verified by running `--site StLuc` against Weston's
  export. Same for a folder that isn't in a known site's table.
- Nothing about a pipeline is ever inferred from the export itself. An
  export states which pipeline each alarm *points at*, which is the thing
  under audit, so it cannot also be the authority on which pipelines
  exist.

**Two things the docs settled that a naive implementation would have got
wrong** (from the three-part search — sources logged in
`claude-workflow/TRUSTED_SOURCES.md`):
- `priority` is documented as Integer **or** String, with
  Diagnostic = **0**. A truthiness test on that field would report a
  legitimately-configured Diagnostic alarm as missing its priority, so
  rule 5 tests presence and blankness specifically.
- A **blank** `displayPath` is a documented "use the default" (Ignition
  then shows the tag's own source path), not a mistyped path. It still
  fails rule 8 — the rule requires a full match, and 140 of 143 tags use
  an explicit path — but it gets its own problem wording so nobody hunts
  for a typo that isn't there. Absent keys generally are reported as
  "absent" rather than as wrong values, since a tag export omits any
  property sitting at its default.

**First real run (pre-patch, 8 rules, looser rule 5) — Weston, 143 tags,
0 OK, 356 problems.** Every tag
fails at least one rule. Four distinct problem signatures, and they
account for all 143:

| Count | Tags | Problems |
|---|---|---|
| 84 | all of folder `500` | non-blank `CustomEmailSubject` + `CustomEmailMessage` |
| 56 | `AUTO_DIALER_CH_01`–`CH_56` | the above, plus `activePipeline: "Site Pipelines/Weston"` (nonexistent pipeline) |
| 2 | `_Test500`, `_Test800` | the email overrides, plus `enabled`/`priority`/`tagGroup`/`historyTagGroup` absent, alarm name `Test500`/`Test800` ≠ tag name, and a `[default]`-prefixed `displayPath` |
| 1 | `CP_6000_PLC_Comm_Loss_Alm` | `tagGroup`/`historyTagGroup` = `MasonCity`, alarm name missing an underscore (`CP6000_…` vs tag `CP_6000_…`), `[default]`-prefixed `displayPath` |

`0 OK` was checked rather than taken at face value: the only tag that
passes rule 3 is `CP_6000_PLC_Comm_Loss_Alm` (both email fields are
literally `""`), and it fails rules 6, 7 and 8 instead. Counts were
cross-verified against the raw JSON independently of the script.

**One finding beyond what the manual investigation had already spotted:**
`CP_6000_PLC_Comm_Loss_Alm`'s alarm `name` is `CP6000_PLC_Comm_Loss_Alm`
while the tag is `CP_6000_PLC_Comm_Loss_Alm` — a missing underscore, rule
7. Its `displayPath` also carries `_CP_6000_…` with a leading underscore
the tag name does not have, so that tag disagrees with itself three
different ways.

### Re-run after the rule 5/9 tightening (2026-09-09)

**Weston, 143 tags, 0 OK, 367 problems** — 356 from the pre-patch run,
unchanged, plus exactly 11 new ones. Nothing that was flagged before
stopped being flagged; rules 1-4 and 6-8 were deliberately not touched.

| New problems | Tags | What |
|---|---|---|
| 1 | `CP_6000_PLC_Comm_Loss_Alm` | `priority: "Critical"` in the `800` folder — expected `High`. This is the finding the old presence-only rule 5 silently passed. |
| 6 | `_Test500`, `_Test800` | all three required History properties absent (`historyEnabled`, `historyProvider`, `historicalDeadbandStyle`) — 3 problems each |
| 4 | `CP_6000_PLC_Comm_Loss_Alm` | `historicalDeadbandStyle` absent, plus all three extraneous keys present: `sampleMode: "TagGroup"`, `historyMaxAge: 20`, `historyMaxAgeUnits: "MIN"` |

**One correction to what was expected going in:** `CP_6000_PLC_Comm_Loss_Alm`
was predicted to be flagged for all three required History properties
being missing. It is not, and should not be — the raw export shows it
carries `historyEnabled: true` and `historyProvider: "Hist_IW"` already,
both correct. Only `historicalDeadbandStyle` is absent on that tag. Its
historian problem is therefore 1 missing property plus 3 extraneous ones,
not 3 missing plus 3 extraneous. Verified by reading the JSON directly,
independently of the script.

**Rule 9 is tag-level, so it is checked once per tag**, not once per alarm
— unlike rules 1-5 and 7-8, which are alarm-level. Weston has exactly one
alarm per tag so this makes no difference to this run's counts, but it
would on a multi-alarm tag, and it is why rule 9's problem lines are not
prefixed with an alarm name.

**Distribution of the 6 required-property problems:** 140 of 143 tags are
already fully compliant with rule 9 (all three properties present and
correct, all three extraneous keys absent). Only the 2 memory test tags
and `CP_6000` fail it — this is a narrow finding, not a systemic one, in
contrast to the email-override problem that hits 142 of 143.

**Branches the real data does not exercise were tested synthetically**
(Rule 5's "no done without a passed test", since real data cannot reach
them): a numeric `priority: 2` in a `500` folder correctly reports as
"numerically the same level as the expected 'Medium'" rather than as a
wrong severity; a tag in an unrecognized folder (`900`) reports
`CANNOT VERIFY` for both rule 2 and rule 5 rather than silently passing;
wrong-valued (as opposed to absent) History properties report the actual
value against the expected one. Regression re-checked with
`--site StLuc`, which still warns and marks all 143 rule-2 lines
`CANNOT VERIFY` while rule 5 still checks by folder — correct, because
Doug's priority rule is system-wide, not per-site.

**The export predates Doug's live `_Test500` correction.** The file still
shows `CustomEmailSubject: "Ignition Alarm"` on `_Test500`, so the script
flags it. Confirmed by reading the file directly — this is the export
being stale, not a script fault. Re-export before treating a `_Test500`
finding as current.

---

## TASK_010 — Fix flagged Ignition alarm tag configuration problems

**Status:** Implemented (2026-09-09) — script: `fix_alarm_tags.py`

### Purpose

The companion tool to TASK_009 — once the scanner reliably finds real
problems, this applies the actual fixes. Deliberately kept as a
**separate tool**, not merged into TASK_009's scan-and-report behavior —
Doug's explicit design: "there will be one scanning tool that just gives
me a report of problems with alarms, and then another tool that will fix
those problems."

Scope is exactly TASK_009's rules **2–9**. **Rule 1 (`notes` non-blank)
is never auto-fixed** — a blank `notes` needs a human-written
description of what that alarm actually means, and inventing text would
be worse than the blank it replaced. A blank `notes` is instead flagged
in the report as needing Doug's manual attention, and the field is left
exactly as found.

### Relationship to TASK_009

Strictly sequential, not parallel work:
1. TASK_009 must exist and be proven reliable first.
2. Only then does building TASK_010 make sense.
3. Same site-by-site verification caution as TASK_009 applies here too —
   a fix that's correct for Weston's alarm pipeline isn't assumed correct
   for a different site's pipeline without checking.

**Resequencing confirmed 2026-09-09:** the real `AlmLIT107_HiHi_Alm` fix
(and any other alarms TASK_009 flags) will be applied *after* TASK_009 is
built and has produced a real report — not before, and not as a
prerequisite for TASK_009's own spec. TASK_010 is what will eventually
apply those fixes.

**The two tools share one definition of "correct," in code, not in
prose.** `fix_alarm_tags.py` does not restate TASK_009's rules — it
`import`s `audit_alarm_tags` and reads `SITE_PIPELINES`,
`FOLDER_PRIORITIES`, `REQUIRED_HISTORY_PROPERTIES`,
`EXTRANEOUS_HISTORY_KEYS`, `CUSTOM_EMAIL_KEYS`, `is_blank()` and
`collect_tags()` straight off that module. This is deliberate and is the
single most important design constraint on this task: a second copy of
those tables in a second file could drift, and the failure mode of that
drift is silent — a fix tool that "corrects" tags to a value the audit
then flags, or worse, agrees with a stale rule nobody remembers changing.
The audit and the fix tool must never be able to quietly disagree about
what correct means. Adding a site to `SITE_PIPELINES` or changing a
folder's required priority is therefore a one-file edit that both tools
pick up at once.

### Inputs

Identical to TASK_009 — same file, same site argument.

| Input | Format | Notes |
|---|---|---|
| Ignition alarm tag export | JSON (Ignition Tag Export of a site's `Alarms` folder) | e.g. `CPKCR-Weston/Weston Alarms tags.json`. **Read-only — never written to.** |
| Site name | String, e.g. `Weston` | Selects the confirmed pipeline list from `audit_alarm_tags.SITE_PIPELINES`, and is the correct value for `tagGroup`/`historyTagGroup` and the leading segment of every `displayPath` |

### Process

For every tag in the export, compute the correct value for each field
named below and write it. Fields are grouped by the TASK_009 rule they
satisfy; the rule numbering is TASK_009's, not a second scheme.

| Rule | Field(s) written | Corrected value |
|---|---|---|
| 1 | *(none — never auto-fixed)* | A blank `notes` is left exactly as-is and flagged for Doug |
| 2 | `activePipeline` (alarm) | The confirmed pipeline for the tag's own folder |
| 3 | `CustomEmailSubject`, `CustomEmailMessage` (alarm) | `""` (both) |
| 4 | `enabled` (alarm) | `true` |
| 5 | `priority` (alarm) | The folder's required value (`500` → `Medium`, `800` → `High`) — **always written, regardless of the current value** |
| 6 | `tagGroup`, `historyTagGroup` (tag) | The site name |
| 7 | `name` (alarm) | The parent tag's own `name` |
| 8 | `displayPath` (alarm) | The reconstructed `<Site>/<folders…>/<tagname>` |
| 9a | `historyEnabled`, `historyProvider`, `historicalDeadbandStyle` (tag) | `true`, `"Hist_IW"`, `"Discrete"` |
| 9b | `sampleMode`, `historyMaxAge`, `historyMaxAgeUnits` (tag) | **The keys are removed entirely**, not set to a value |

Three properties of that table matter as much as its contents:

**Nothing outside it is ever written.** Every other key on every tag and
every alarm — `opcItemPath`, `opcServer`, `valueSource`, `dataType`,
`value`, `label`, `mode`, `setpointA`, `timeOnDelaySeconds`,
`voip.customMessage`, `CustomSmsMessage`, `notes` — comes through
untouched, and so does every tag that had no violations at all. The
script proves this rather than asserting it: it keeps a deep copy of the
parsed input, structurally diffs it against the corrected tree at the
end, and **aborts with a non-zero exit code if that diff contains a
single field it did not deliberately record as a change**. A silent
extra edit is not a possible outcome.

**Rewriting a field to the value it already holds is not a change.** The
correct value is computed unconditionally for every field (which is what
"rule 5 always overwrites" means), but the change report and the change
count only record a field whose value actually moved, whose key was
absent, or whose key was removed. This is what makes the change count
directly comparable to TASK_009's problem count — see Outputs.

**An unverifiable field is left alone, never guessed.** If the site is
absent from `SITE_PIPELINES`, or the tag's folder is absent from that
site's entry, `activePipeline` is **not** written — the script reports
`CANNOT VERIFY` and leaves the existing value in place, mirroring
TASK_009's own handling. Same for `priority` when the folder is absent
from `FOLDER_PRIORITIES`. Writing a guessed pipeline name would point a
live alarm at a pipeline nobody confirmed exists, which is the exact
class of fault this pair of tools was built to find.

`notes` is the only rule-1 field and the only deliberate no-op.
Rules 1–5 and 7–8 are alarm-level (applied to every alarm on the tag);
rules 6 and 9 are tag-level (applied once per tag). Rule 4's `enabled`
is the **alarm's** `enabled`, not the tag's — matching TASK_009, which
checks it at the alarm level; a tag-level `enabled` is left untouched
even when absent.

No tag is exempt, `_Test500`/`_Test800` included — same no-exemptions
rule as TASK_009, for the same reason (a test tag configured unlike the
alarms it stands in for validates the wrong thing).

### Outputs

**(a) A brand-new corrected JSON file.** Same structure as the input,
written to a new path. The input file is never opened for writing, and
the script refuses to run at all if the resolved output path is the same
file as the input. Default output path when `--output` is not given:
`<input filename without extension> - CORRECTED.json`, in the same
directory as the input — so Weston's export produces
`Weston Alarms tags - CORRECTED.json` beside it, inside the job folder,
never inside PLCHelper.

Formatting matches `generate_ignition_udt.py`: `json.dump(...,
indent=2, sort_keys=True)`. Note the consequence — **key order in the
output is canonical (sorted), not the input's original order.** The
*data* outside the corrected fields is identical, which is what the
structural diff above verifies; the byte layout is deliberately
normalized rather than preserved, and Ignition's importer does not care
about key order.

**(b) A console change report.** Every field actually changed, grouped
by tag name, alphabetically, one change per line, `old -> new` — same
shape and sort order as TASK_009's report so the two can be read side by
side. Absent keys are reported as `(absent)` and removals as
`(removed)` rather than as values, for the same reason TASK_009 words
them that way. Ends with a summary count of tags changed and fields
changed, a `Changes by kind` tally, and any manual-attention flags
(blank `notes`, `CANNOT VERIFY` fields).

**The change count is the cross-check on the whole tool.** Each TASK_009
problem line is one field-level violation, and every rule 2–9 violation
has exactly one corresponding field write — so for any export with no
rule-1 findings, *fields changed* must equal TASK_009's *problems
total*. On Weston that is **367 = 367**, verified. The real correctness
test is stronger still and is the one that matters: re-running
`audit_alarm_tags.py` against the corrected output file must report
**0 problems, 143 OK**.

### ⚠ Importing the corrected file — Collision Policy must be `Overwrite`

Verified 2026-09-09 against the official docs and an Inductive Automation
staff post (three-part search; sources logged in
`claude-workflow/TRUSTED_SOURCES.md`). This is not a detail — get it
wrong and rule 9b silently does nothing.

Rule 9b works by **removing** `sampleMode`, `historyMaxAge` and
`historyMaxAgeUnits` from the JSON, because an Ignition tag export omits
any property sitting at Ignition's default ("the tag export feature only
exports the configuration properties that have been edited in at least
one of the tags in the selected export folder"). Absence in the file is
how "use the default" is expressed.

But **`MergeOverwrite` treats a missing key as "leave that property
alone"** — IA staff (Paul Griffith): "MergeOverwrite means keep the
existing values in the property set, *unless* there's a conflict."
Importing this tool's output under `MergeOverwrite` would apply all the
value changes and silently keep the three overridden history properties
on `CP_6000_PLC_Comm_Loss_Alm`. Only **`Overwrite`** ("a complete
overwrite of the tag") actually clears them. The script prints this
instruction in its own report every run.

**This is the opposite of CLAUDE.md's UDT-definition guidance, and both
are correct** — do not "fix" either one to match the other. That
guidance (`MergeOverwrite`, never delete or rename first) is about
replacing a **UDT definition that has live instances**, where the risk
is destroying member IDs and losing per-instance overrides. This is a
folder of **plain alarm tags** with no definition and no instances, where
the goal is precisely to remove overrides. Different operation,
different correct policy.

### Open Questions

- **Resolved:** how fixes get applied. It emits a corrected export JSON
  for Doug to import by hand — it does not drive the gateway, and no
  scripting API / `system.tag.configure` route is used. Reason: the same
  one that made TASK_009 read-only. A file Doug reviews and imports
  deliberately is inspectable before it touches a live gateway; a script
  writing directly to the gateway is not.
- **Resolved:** `_Test800`. It is in normal scope like any other tag, not
  skipped as "already handled" — it was found still carrying the
  uncorrected `CustomEmailSubject`/`CustomEmailMessage` override (unlike
  `_Test500`, it was never corrected via a one-off JSON import). Both
  test tags are corrected by this tool in the normal course.
- **Still open — the export is stale relative to the live gateway.** The
  file still shows `_Test500`'s pre-correction email override, because
  Doug fixed that tag live in Designer after this export was taken.
  Re-export from the gateway before importing a corrected file, or the
  import will carry other since-changed values backwards too. This is a
  property of the export, not of either tool, and it applies to every
  run: **the corrected file is only as current as the export it was
  built from.**
- **Still open — only Weston is confirmed.** Same site-by-site caution as
  TASK_009, and it is enforced in code by the shared `SITE_PIPELINES`
  table rather than left to memory. Running against another site warns
  and leaves `activePipeline` untouched rather than applying Weston's
  naming.

### Implementation notes (`fix_alarm_tags.py`, 2026-09-09)

**CLI:** `--input` and `--site` required (identical meaning to
TASK_009's), `--output` optional with the default filename above.
Stdlib only. `main()` returns an int under `sys.exit(main())`; it returns
non-zero on a refusal (output path equal to input) or on a failed
fidelity check.

**First real run — Weston, 143 tags.** 143 tags changed, **367 fields
changed**, matching TASK_009's 367 problems exactly. Re-running
`audit_alarm_tags.py` against the corrected output reports **0 problems,
143 OK**. The original input file was confirmed byte-identical
afterwards (SHA-256 compared before and after the run). Change
distribution, by kind:

| Fields | Kind |
|---|---|
| 142 | `alarm.CustomEmailMessage` → `""` |
| 142 | `alarm.CustomEmailSubject` → `""` |
| 56 | `alarm.activePipeline` — `"Site Pipelines/Weston"` → `"WWHMPWWT1/Weston_800"` |
| 3 | `alarm.displayPath` |
| 3 | `alarm.name` |
| 3 | `alarm.priority` (2 absent, 1 `Critical` → `High`) |
| 3 | `tag.historicalDeadbandStyle` (absent → `"Discrete"`) |
| 3 | `tag.historyTagGroup` (2 absent, 1 `MasonCity` → `Weston`) |
| 3 | `tag.tagGroup` (2 absent, 1 `MasonCity` → `Weston`) |
| 2 | `alarm.enabled` (absent → `true`) |
| 2 | `tag.historyEnabled` (absent → `true`) |
| 2 | `tag.historyProvider` (absent → `"Hist_IW"`) |
| 1 each | `tag.sampleMode`, `tag.historyMaxAge`, `tag.historyMaxAgeUnits` — **removed** |

Every line of that tally reconciles against TASK_009's own
`Problems by kind` output, which is why the two reports are printed in
the same shape.

**One bug found by the change-count cross-check, worth recording because
the check is the only thing that caught it.** The first run reported
**361** changes, not 367. The six missing were rule 6 — `tagGroup` and
`historyTagGroup` — which the first version of the script simply never
implemented: rules 2-5 and 7-9 were all present, and nothing errored,
warned, or looked wrong. The audit's own per-kind tally is what localized
it in seconds (`tagGroup`/`historyTagGroup` absent from the fix tool's
tally entirely, 3 + 3 = the exact shortfall). An "it ran and produced a
corrected file" test would have passed this bug straight through, and so
would a re-audit run *only* on the tags that happened to be fixed. This
is the concrete argument for keeping the count cross-check in the task's
own test procedure permanently, not just as a one-time sanity check.

**Zero rule-1 findings on Weston** — every one of the 143 tags already
has non-blank `notes`. That is why the change count equals the problem
count exactly on this export, and it is a data fact about Weston, not a
property of the tool: an export with blank `notes` would show *fewer*
changes than problems, by exactly the number of blank-`notes` findings,
and the report says so.

**Branches the real data does not exercise were tested synthetically**
(Rule 5 — no "done" without a passed test): an unconfirmed site
(`--site StLuc`) leaves all 143 `activePipeline` values untouched and
reports them `CANNOT VERIFY` rather than rewriting them to Weston's
pipelines; a tag in an unrecognized folder (`900`) has neither
`activePipeline` nor `priority` written; a blank `notes` is left
untouched and flagged; refusing to overwrite the input was confirmed by
passing `--output` equal to `--input` (non-zero exit, no write); and the
fidelity check was confirmed to actually fail when deliberately fed an
undeclared edit, rather than passing vacuously.

---

## TASK_011 — Suggest existing AOIs for a described control need

**Status:** **Idea — first real content added 2026-09-11 (written
reference, not a tool). Confirmed with Doug: this is a documentation
feature, not an automated matching tool** — shape question 1 below is
now resolved.

### Purpose

When someone describes needing an AOI/control scheme for a new piece of
equipment, PLCHelper should be able to check whether an existing,
already-supported AOI already covers that need — instead of everyone
assuming a new AOI has to be designed from scratch every time.

Prompted directly by `CONSPD4_AOI` (see TASK_005's "Second run" section
above): it was originally scoped for single-speed motors — something
that turns on/off and can fail to do either, needing run-fail alarming
and runtime tracking — but its real-world use has broadened. Doug (or
someone else at Casne, not recalled who) realized **any** on/off
actuator with that same class of failure modes can reuse it, motor or
not. Blue Sky's flare tag (`BOP_FLR`) is a live example — a non-motor
device legitimately using `CONSPD4_AOI`.

### Doug's framing, verbatim (2026-09-11)

"...whenever we have a thing like this, like the flare, it can turn on
and off, and it has failure modes. So we just use that con spd for AOI
for that too... it would be pretty nice if in the future... when someone
says, oh, I need an AOI that'll control this thing that I need to turn
on and off, you can suggest, hey, that con spd AOI might work for this
situation."

### Resolved 2026-09-11

1. ✅ **Documentation/knowledge feature, confirmed — not an automated
   tool.** A written **Broader use case** note per AOI, for a future
   session or engineer to read and match by judgment. No matching
   engine, no new script.
2. ✅ **Lives in `PLCHelper_Reference.md`**, the existing AOI/UDT
   reference document — not `PLCHelper_Status.md` (that stays scoped to
   infrastructure/task tracking, per Lesson 9). A short intro note was
   added there explaining the convention, plus the first real entry: a
   **Broader use case** note on `CONSPD4_AOI` (any on/off actuator
   needing run-fail alarming and runtime/stuck-on tracking, motor or
   not — Blue Sky's flare tag `BOP_FLR` is the confirmed real example).

### Still open

3. **Which other AOIs need this treatment?** Only `CONSPD4_AOI` has a
   Broader use case note so far. Others may have similarly generalized
   real-world uses not reflected in their PLC-side names — a pass across
   the whole supported-AOI list in `PLCHelper_Reference.md` would be
   needed to find them. Not started; no timeline requested.

---

*Last updated: September 12, 2026 — TASK_005 sixth run: `LEVELIN3_AOI`
generated **26 instances, 3 members each** (`Description`, `DeviceName`,
`EngUnit`, out of 90 total AOI parameters), into its own file
`BlueSky/LEVELIN3_AOI tag instances generated 2026-09-12.json`, against a
freshly re-exported and PII-cleared L5X. All 13 structural checks passed,
cross-read against the L5X by an independent throwaway script;
**structural only — not yet Designer-confirmed**, same UNVERIFIED-mapping
grade as `CONSPD4_AOI`/`FLOWIN3_AOI`/`FLOWVLV_AOI`/`INTERLOCK_AOI` before
their own imports. Two anomalies flagged, neither acted on: 7 of 26
instances are `BOP_`-prefixed (largest `BOP_` share of any run so far,
same folder-placement question as every prior run with mixed prefixes);
`EngUnit` is blank on all 26 (a real value, not a missing field — same
treatment as `INTERLOCK_AOI`'s all-blank descriptions). Also caught and
corrected a false failure in this run's own verification script, which
had incorrectly checked emitted members against the AOI's raw 90-parameter
list instead of recognizing `Description`/`DeviceName`/`EngUnit` as the
tool's standard always-emitted fields — noted in the write-up so a future
verification doesn't repeat it. Added the "Sixth run — `LEVELIN3_AOI`" and
"Verification of the `LEVELIN3_AOI` run" sections; updated the Status line
(now: 4 export-verified, 2 structurally-verified-awaiting-import
[`INTERLOCK_AOI`, `LEVELIN3_AOI`], 2 still Idea [`MODVLV`, `VARSPD2_AOI`]).
Also corrected a stale line in `BlueSky/BLUE_SKY_STATUS.md` that still
described this whole task as "not yet speced beyond Idea" — it now points
here as the source of truth instead of duplicating detail (Lesson 9).
Prior update, September 11, 2026 (7th) — `INTERLOCK_AOI` moved from
⚠️ structural-only to ❌ blocked, once Doug's Designer import confirmed
the predicted member-name mismatch: the real UDT's 64 hand-expanded
`Interlock_NN`/`Visibility_NN` members share zero names with the 5
emitted by this run. Root cause, fix, and sources are in `CLAUDE.md`, not
duplicated here (Lesson 9). Flagged as a possibly general limitation for
any AOI whose real Ignition UDT was hand-expanded beyond its L5X
parameter list, not `INTERLOCK_AOI`-specific. Prior update, September 11, 2026 (6th) — TASK_005 fifth run:
`INTERLOCK_AOI` generated **10 instances, 5 members each**, into its own
file `BlueSky/INTERLOCK_AOI tag instances generated 2026-09-11.json`.
Ignition UDT name equals the PLC AOI name for this family, so
`--udt-name` was omitted and the name was verified to appear **exactly
once per instance, inside `typeId` only**. The run inverts the shape of
every prior one — most instances yet (10 vs. a previous high of 7), by
far the fewest members (5 vs. 38 and 51) — and the parameter-set check
carries the most weight here of any run so far: exactly `DeviceName` +
`Description`, with **none** of this AOI's many UDT-defaulted parameters
leaking into the instances. All 15 structural checks passed, cross-read
against the L5X by an independent throwaway script; **structural only —
not yet Designer-confirmed**, and the script's UNVERIFIED warning printed
as expected. Added the "Fifth run — `INTERLOCK_AOI`" and "Verification of
the `INTERLOCK_AOI` run" sections, updated the Status line and the
per-AOI parameter table's `INTERLOCK_AOI` row to the ⚠️ structural-only
grade. **Three anomalies flagged, none acted on:** all 10 descriptions
blank (a first — a valid value, not a missing field, but every
operator-visible description will be empty); one `BOP_`-prefixed instance
(`BOP_BL1_INTERLOCK`) raising the usual folder-placement question; and
the two DINT bitfield parameters (`Interlocks`, `Visibility`) emitted as
flat members where the real Ignition UDT has them manually expanded per
bit — flagged to watch on import, explicitly **not** an attempt to touch
the separate TASK_004 bitfield gap. Prior update, September 11, 2026 (5th) — TASK_005 fourth run:
`FLOWVLV_AOI` generated **1 instance (`O2_MV112A`), 38 members**, into its
own file `BlueSky/FLOWVLV_AOI tag instances generated 2026-09-11.json`.
Second family whose Ignition UDT name differs from its PLC AOI name —
run with `--udt-name FLOWVLV2_AOI`, and the PLC name verified to appear
**0 times** anywhere in the output. All 15 structural checks passed,
cross-read against the L5X by an independent throwaway script;
**structural only — not yet Designer-confirmed**, and the script's
UNVERIFIED warning printed as expected. Added the "Fourth run —
`FLOWVLV_AOI`" and "Verification of the `FLOWVLV_AOI` run" sections,
updated the Status line and the per-AOI parameter table's `FLOWVLV_AOI`
row to the ⚠️ structural-only grade. **No anomalies flagged — the first
run of the four with a completely clean scan** (real description, no
duplicates, and the sole instance is `O2_`-prefixed so it raises no
folder-placement question). Noted as a caveat rather than a win: one
instance is the smallest scope yet, so a clean pass here is weaker
evidence than `FLOWIN3_AOI`'s seven. Prior update, September 11, 2026 (4th) — TASK_011 scope confirmed with
Doug: a written reference (not a tool), living in `PLCHelper_Reference.md`
(not `PLCHelper_Status.md`, per Lesson 9). First real content added there:
an intro note on the new "Broader use case" convention, plus the first
entry on `CONSPD4_AOI` itself. Which other AOIs need the same treatment
stays open, not started. Prior update, September 11, 2026 (3rd) — resolved the `BOP_FLR` flag on
TASK_005's `CONSPD4_AOI` run: Doug confirmed it also imported perfectly
and stays in the O2 destination folder for this job. Recorded the
broader reason why a flare tag legitimately uses `CONSPD4_AOI` at all —
it was originally scoped for single-speed motors but its real use has
generalized to any on/off actuator with the same failure-mode class.
Added new **TASK_011** (Idea stage): a future PLCHelper capability to
suggest an existing AOI (like `CONSPD4_AOI`) when someone describes a new
on/off-with-failure-modes control need, instead of assuming a new AOI is
required — not yet scoped, three open questions logged, not started.
Prior update, September 11, 2026 (2nd) — TASK_005 third run:
`FLOWIN3_AOI` generated **7 instances, 51 members each**, into its own
file `BlueSky/FLOWIN3_AOI tag instances generated 2026-09-11.json`. First
run to exercise the three-parameter mapping (`EngUnit` created and
blank). All 16 structural checks passed, cross-read against the L5X by an
independent throwaway script; **structural only — not yet
Designer-confirmed**, the same state `CONSPD4_AOI` held before today, and
the script's UNVERIFIED warning printed as expected. Added the "Third run
— `FLOWIN3_AOI`" and "Verification of the `FLOWIN3_AOI` run" sections,
updated the Status line, the per-AOI parameter table's `FLOWIN3_AOI` row,
and the task-catalog row (which was still stale from before
`CONSPD4_AOI`'s promotion). Three anomalies flagged rather than filtered:
five placeholder descriptions carried verbatim from the PLC, `description
3003` duplicated across three tags, and six of seven instances being
`BOP_`-prefixed while landing in the O2 destination folder. Prior update,
September 11, 2026 — `CONSPD4_AOI` promoted to
export-verified for TASK_005: Doug imported the 2026-09-10 generated JSON
into Ignition Designer and confirmed it "looks perfect." Status line,
the per-AOI parameter table, and the "Verification of the `CONSPD4_AOI`
run" section all updated — `ALARM_AOI` and `CONSPD4_AOI` are now the two
verified types, 6 remain Idea stage. Prior update, September 10, 2026 (2nd) — TASK_005's `DeviceName`/
`Description` fields resolved: `DeviceName` is one value for the whole
task run (today's value `"BOP_O2_CombinedTest"`), not per-instance;
`Description` is auto-looked-up per instance from the AOI instance's own
L5X `<Description>`. Confirmed which fields actually apply is AOI-type-
dependent — `ALARM_AOI`'s UDT only has these two. `EngUnit` (for AOI
types that have it) still left blank, unchanged. Still at Idea status —
naming/instance-path convention, the qualifying-AOI-list format/location,
and the TASK_004 parsing-logic-reuse question remain open. Prior update,
September 10, 2026 — TASK_005 unblocked (Blue Sky's
O2-scope UDT checklist is done) and further scoped with Doug: confirmed
job-agnostic (like TASK_004/009/010, not Blue-Sky-only); the qualifying-
AOI-type list is explicit Doug-supplied input, not something the script
infers on its own; output is small test runs first, then one consolidated
JSON file rather than a file per instance. Field handling
(`DeviceName`/`Description`/`EngUnit`) still to be discussed — not
resolved by this update. Still at Idea status pending that discussion.
Prior update, September 9, 2026 (7th) — **TASK_010 speced and
implemented** as `fix_alarm_tags.py`, moving it from Idea to Implemented
and closing the last of its Open Questions except the two that belong to
the data rather than the tool (the export being stale relative to the
gateway, and only Weston being a confirmed site). Spec written first,
per this file's own convention, then built. The design constraint worth
carrying forward: the fix tool declares **none** of TASK_009's
correctness tables — it imports `audit_alarm_tags` and reads
`SITE_PIPELINES`, `FOLDER_PRIORITIES`, `REQUIRED_HISTORY_PROPERTIES`,
`EXTRANEOUS_HISTORY_KEYS` and `is_blank()` off that module, so the audit
and the fix can never quietly disagree, and adding a site is a one-file
edit both pick up. Rule 1 (`notes`) is deliberately never auto-fixed;
blank ones are flagged for Doug instead of being invented. Unverifiable
fields are left alone, never guessed: an unconfirmed site or folder
leaves `activePipeline`/`priority` exactly as found (verified with
`--site StLuc`, which rewrites nothing). First real run on Weston: 143
tags, **367 fields changed — equal to the audit's 367 problems** — and
re-auditing the corrected output gives **0 problems / 143 OK**, with the
input file confirmed byte-identical by SHA-256 afterwards. The change
count is not decoration: the first version silently omitted rule 6
entirely and reported 361, and the 6-field shortfall against the audit's
tally is the only thing that caught it — see the Implementation notes.
The three-part search turned up one finding that changed the design
rather than confirming it: rule 9 works by *removing* keys, and Ignition's
`MergeOverwrite` collision policy treats a missing key as "leave that
property alone" (IA staff, confirmed against the official
export/import docs), so the corrected file must be imported under
**`Overwrite`** or rule 9 silently does nothing — the tool now prints
that instruction every run. That is the opposite of CLAUDE.md's
UDT-definition guidance and both are correct; the spec says so
explicitly so neither gets "fixed" to match the other. Prior update,
September 9, 2026 (6th) — patched `audit_alarm_tags.py`
to implement TASK_009's current 9-rule spec and re-ran it against
Weston's real export: **143 tags, 0 OK, 367 problems**, up from 356.
Rule 5 became a folder-based exact match (`500` → `Medium`, `800` →
`High`) via a new `FOLDER_PRIORITIES` constant table, catching
`CP_6000_PLC_Comm_Loss_Alm`'s `Critical` that the old presence-only check
passed; rule 9 (historian config) was implemented from scratch as a
tag-level check, finding 10 problems across 3 tags. Rules 1-4 and 6-8
untouched and every pre-patch finding still reproduces. One expectation
corrected against the raw JSON: `CP_6000` already has `historyEnabled`
and `historyProvider` set correctly, so only `historicalDeadbandStyle` is
missing on it — see "Re-run after the rule 5/9 tightening." TASK_009's
Status line and the catalog row updated to drop the "needs a patch, not
yet re-run" caveat. Prior update, September 9, 2026 (5th) — added TASK_009's rule 9
(historian configuration must match the site-wide convention:
`historyEnabled: true`, `historyProvider: "Hist_IW"`,
`historicalDeadbandStyle: "Discrete"`, and no tag may carry an explicit
`sampleMode`/`historyMaxAge`/`historyMaxAgeUnits` at all). Raised after
Doug's own Designer screenshot revealed the real site-wide Sample Mode
convention (On Change, not Tag Group) and confirmed
`CP_6000_PLC_Comm_Loss_Alm`'s unique history settings should be
normalized like every other tagGroup/name/displayPath issue on that
tag, not preserved as deliberate. `audit_alarm_tags.py` implements
neither this new rule nor the tightened rule 5 yet — both a
still-pending patch. Prior update, September 9, 2026 (4th) — tightened TASK_009's rule 5
(priority) from "present and non-blank" to a strict folder-based match
(500→Medium, 800→High, no exceptions), per Doug's explicit confirmation
that this overrides existing values too — including downgrading
`CP_6000_PLC_Comm_Loss_Alm` from Critical to High. `audit_alarm_tags.py`
(built under the looser rule) needs a small patch to actually enforce
this; not yet done. Prior update, September 9, 2026 (3rd) — TASK_009 moved from Spec Ready
to **Implemented**: built `audit_alarm_tags.py` (stdlib-only, read-only,
`--input` + `--site`) and ran it against Weston's real 143-tag export.
All 143 tags fail at least one of the 8 rules, in four distinct problem
signatures — the 56 `AUTO_DIALER` tags' nonexistent
`"Site Pipelines/Weston"` pipeline and the site-wide non-blank
`CustomEmailSubject`/`CustomEmailMessage` overrides both confirmed at the
counts the manual investigation predicted, plus one new finding
(`CP_6000_PLC_Comm_Loss_Alm`'s alarm name is missing an underscore
relative to its tag). Added an Implementation notes subsection recording
the CLI, how the unconfirmed-site guard works in code, the two
docs-settled traps avoided (priority 0 is a real priority; a blank
`displayPath` is a documented default, not a typo), and the stale-export
caveat on `_Test500`. TASK_010's status and Open Questions updated to
match — its "TASK_009 must exist first" prerequisite is now met, but its
own fix mechanism is still unspeced. Prior update, same day (2nd) —
moved TASK_009 from Idea
(genuinely blocked) to Spec Ready, with a finalized 8-rule correctness
spec and full Inputs/Process/Outputs sections. Unblocked via CS0175981's
real investigation: Andrew's actual received email for `AlmLIT107_HiHi_Alm`
matched the tag's `CustomEmailSubject`/`CustomEmailMessage` override
byte-for-byte, and a cross-site comparison (`All Alarms tags.json`, 921
alarms / 8 sites) confirmed every non-blank override in the whole export
belongs to Weston alone — plus a second, more serious finding that 56 of
Weston's 800-series alarms point at a pipeline (`Site Pipelines/Weston`)
Doug confirmed does not exist. Doug decided this evidence supersedes the
originally-planned single-alarm live-retrigger prerequisite; that
confirmation step is instead happening via the existing `_Test500` memory
tag (not the real alarm) as a live but zero-risk validation, in parallel
with the tool now moving forward. TASK_010 updated to note TASK_009 is
Spec Ready (not Implemented) and that the real alarm fixes will follow
TASK_009's output rather than precede its spec. Prior update, same day —
logged TASK_009 (alarm-config audit,
read-only) and TASK_010 (the separate fix tool, blocked on TASK_009)
after CPKCR-Weston's ticket history revealed a recurring pattern of
alarm formatting/configuration bugs. Both are genuinely blocked, not
just unscoped: Doug's own plan is to manually diagnose and fix the
current `AlmLIT107_HiHi_Alm` issue first (get the real notification
email from Andrew, find the misconfiguration, fix it, verify the email
now displays correctly) before either tool can be speced, since nobody
yet knows what "correctly configured" means. Doug's explicit caution
carried into both tasks: alarm pipelines are not assumed uniform across
sites (Dates, Golden, MasonCity, MooseJaw, Nahant, PoCo, StLuc, StPaul,
Weston per the real Ignition tag tree) — each gets verified
independently, never blanket-applied. Prior update, September 8, 2026
(4th) — added a **general, opt-in
member-exclusion mechanism** to `generate_ignition_udt.py`, shared by both
`--aoi` and `--datatype` mode: a `MEMBER_EXCLUSIONS` table keyed by source
type name for settled decisions, plus a repeatable `--exclude
NAME[=reason]` for one-off runs (additive; it cannot cancel a table
entry). Nothing is ever dropped silently — every exclusion prints with its
PLC type, reason, and origin, twice per run, and an exclusion matching no
member raises a warning. Applied to MODVLV's `.PID`, `.DLYTMR`,
`.FTO_TMR`, and `.FTC_TMR`, which Doug confirmed are genuinely dead code
(the `.PID` block is obsolete — this valve's real PID control is a
separate PIDE-type tag, and a live bug referencing the embedded block was
found and fixed). This closes the TASK_008 Open Question that had those
four emitting `String`/NEEDS REVIEW placeholders; MODVLV regenerated at 41
members instead of 45, with nothing else in the file changed. The AOI path
was re-verified byte-identical. Prior update, same day (3rd) — added
**TASK_008** (Implemented):
generate an Ignition UDT definition from a **native PLC UDT**
(`<DataType Class="User">`) rather than an AOI, via a new `--datatype`
option on the existing `generate_ignition_udt.py`, plus
`--list-datatypes`. Prompted by `MODVLV` — an item on Blue Sky's per-AOI
handoff checklist that turned out not to be an AOI at all. Studio 5000's
hidden `ZZZZZZZZZZ*` bit-packing backing members are excluded
(Doug-confirmed; independently absent from the real MODVLV Ignition
export) while the visible `DataType="BIT"` bit-alias members are included
as Booleans; the exclusion reports every dropped member and warns on any
hidden member that backs no visible bit. Everything downstream of the
member list — conventions, historization, data-type mapping, output shape
— is TASK_004's code path unchanged, and that path is provably untouched
(`FLOWIN3_AOI` and `ALARM_AOI` byte-identical before and after). Also
added `BIT` → `Boolean` to TASK_004's data-type mapping table (21 of 21
agreement, zero counterexamples) and replaced TASK_007's line-number
citation of the script with a function-name citation, since the line
numbers went stale the moment the file grew. Prior update, same day (2nd) — verified the OPC Server
convention mechanism against the actual code at Doug's request (one
derived value, stamped uniformly on every member — matches Doug's own
stated vision exactly, not a per-member issue) and logged TASK_007
(Idea, not urgent): a future bulk-update tool for this and similar
derived conventions across an existing UDT. Prior update, same day —
extended TASK_004's Historization rule
to also match the **bare (no-underscore) form** of each signal-type word
(`hwai`/`hwao`/`scai`/`scao` analog, `hwdi`/`hwdo`/`scdi`/`scdo` and
`alm`/`alarm` digital) as an exact whole-name match, in addition to the
existing suffix behavior which is unchanged. Supplied by Doug after he
found `ALARM_AOI`'s real PLC parameters are named `Alarm` and `Hwdi`
rather than following the underscore-suffixed convention — those members
had correctly gotten no History under the suffix-only rule. Implemented in
`generate_ignition_udt.py` via new `ANALOG_BARE` / `DIGITAL_BARE` /
`ALARM_BARE` constants; `FLOWIN3_AOI` regression output was byte-identical
before and after, and `ALARM_AOI` was regenerated with `Alarm` and `Hwdi`
now historized as digital. Prior update, same day — re-scoped TASK_005 from a loose
`O2_`-prefix match into a precise "AOI instances of a type with a valid,
generated UDT" scope, with `DeviceName` as an explicit parameter,
`Description` read per-instance from the L5X, and `EngUnit` left blank
for Doug. Added TASK_006 (Idea stage): the reverse-direction audit,
flagging Ignition tags with no matching real PLC tag for Doug's review,
never auto-resolving anything — blocked on Doug producing an example
Ignition tag export. Both came out of noticing, mid-import, that
LEVELIN3_AOI (and others) have many existing tag instances that will
need real follow-up work once all the UDT definitions are solid. Prior
update, September 7, 2026 (4th) — TASK_004's Outputs now points at
`CLAUDE.md`'s new "Importing generated UDT definitions into Ignition
Designer" section for the actual Designer import steps, after a live
mid-import block: right-click → *Import Tags* showed greyed out because
the selected node was a UDT definition, not a folder. Pointer only, no
duplicated content (Lesson 9). Prior update, same day (3rd) — regenerated `FLOWIN3_AOI`'s UDT
using the new `FLOWIN3_AOI old tags.json` reference; `EngUnit` confirmed
present in the actual output file, zero data-type warnings, 25/51
members historized. Added a Reporting note to TASK_004: Doug confirmed
the analog-deadband REVIEW REQUIRED reminder should not be restated in
chat when reporting results — the script's own console output already
covers it. Prior update, same day (2nd) — added TASK_004's "Reference
JSON preparation convention": a real gap found live (Friday's
`FLOWIN3_AOI` UDT missing `ENGUNIT` because the reference used to build
it didn't have one, since top-level `parameters` come entirely from the
reference, not the L5X) led to a considered-and-rejected script change
(hardcoding which AOI types get which parameters) in favor of keeping
the script's single rule simple and moving that judgment into an
explicit, Doug-prepared reference file per target UDT — same pattern as
the Historization rule and data-type mapping table. Documented the prep
workflow (one small reference export per UDT, must retain a real member
for convention-derivation, export from UDT Definitions specifically,
batch-scan multiple references together, no script change needed) and
the immediate next step (regenerate `FLOWIN3_AOI` with the newly
received, PII-cleared `FLOWIN3_AOI old tags.json` as its corrected
reference). Prior update, same day — added TASK_005 (Idea stage): generate
importable Ignition tag instance JSONs for every L5X tag matching a given
prefix (e.g. `O2_`), depending on TASK_004's UDT definitions already
existing for whatever types those tags reference. Raised alongside Blue
Sky's O2-scope UDT regeneration work; several real open questions flagged
(how UDT type gets determined per tag, naming/path convention, scope
boundary against UDT-member double-counting) before this can move past
Idea to Spec Ready. Prior update, September 4, 2026 (4th) — TASK_004 now applies an explicit
Doug-supplied Historization rule instead of generating no history at all.
Added the "Historization rule" section (which members match, which
compound alarm forms are excluded, the settings by signal type, the real
JSON key/enum spellings taken from actual Ignition exports, and the
flagged analog-deadband placeholder), added it as a Process step, and
replaced the old "possible future enhancement, not built" note — that
enhancement is now built. Prior update, same day: cross-referenced TASK_004's
history-tag note to the new "Ignition tag History — digital vs. analog
configuration" section in CLAUDE.md, making explicit that the new section
covers History settings-correctness by signal type only and does not
narrow the Hard scope boundary on which members get historized. Prior
update, same day: expanded TASK_004's history-tag
note: confirmed the no-history-on-generated-members behavior is correct
(not a bug), documented Doug's current manual practice, and logged a
possible future enhancement (an explicit, Doug-supplied historization
rule) without designing it. Prior update, same day: added TASK_004
(generate a brand-new Ignition UDT definition JSON from an AOI's real
parameter set), including the Doug-approved "include every parameter"
scope decision and how it coexists with the existing Hard scope boundary
on correcting existing UDTs. Prior update: September 2, 2026.*
