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
| TASK_005 | Generate Ignition tag instances from AOI usages with valid UDTs | Idea | Given a fresh L5X export, find every AOI *instance* whose type already has a valid, generated UDT definition, and emit a folder of importable Ignition tag *instance* JSONs — `DeviceName` supplied as a parameter, `Description` read from that instance's own PLC description, `EngUnit` left blank for Doug to fill in. Auto-populates missing tag instances instead of building each by hand in Designer. |
| TASK_006 | Audit Ignition tags for orphaned/unmatched instances | Idea | Given a real export of existing Ignition tags (e.g. all `O2_`-prefixed instances) and a fresh L5X, find any Ignition tag with no matching real tag in the current PLC program and flag it for Doug's review — never auto-deletes or auto-resolves. The reverse direction of TASK_005: TASK_005 fills in what's missing, TASK_006 finds what shouldn't be there. |
| TASK_007 | Bulk-update a derived convention across an existing UDT's members | Idea | Given an existing UDT definition JSON and a convention field (e.g. `opcServer`) plus a new value, update that field across every member in one pass — for when a different client/site uses a different OPC Server connection name than the one baked into Blue Sky's references. Not urgent; raised while confirming the OPC Server convention is already applied as one uniform value, not per-member. |
| TASK_008 | Generate Ignition UDT definition from a native PLC UDT | Implemented | The same operation as TASK_004 but sourced from a native Rockwell UDT (`<DataType Class="User">`) instead of an AOI — for handoff-checklist items like `MODVLV` that turn out not to be AOIs at all. One member per **visible** UDT member; Studio 5000's hidden `ZZZZZZZZZZ*` bit-packing backing members are excluded, and the visible `BIT` bit-alias members are included as Booleans. Conventions, historization, and data-type mapping are shared with TASK_004, unchanged |
| TASK_009 | Audit Ignition alarm tag configuration for formatting problems | Spec Ready | Given an export of one site's alarm tags (Weston first), check every alarm against 8 correctness rules (pipeline validity, blank email overrides, enabled, priority, tagGroup, name/displayPath consistency) and produce an alphabetized report of problems — read-only, no fixes. Unblocked 2026-09-09: root cause confirmed for `AlmLIT107_HiHi_Alm` (CS0175981) via Andrew's actual received email plus a cross-site comparison across 921 alarms / 8 sites. |
| TASK_010 | Fix flagged Ignition alarm tag configuration problems | Idea | The companion tool to TASK_009 — applies fixes to whatever TASK_009 flags. Deliberately kept as a separate tool, not merged into TASK_009, and only built once TASK_009 is proven reliable (now Spec Ready, not yet Implemented). Each site's alarm pipeline gets verified independently before either tool is trusted against it — no assumption that sites share the same setup. |

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

**Status:** Idea (raised 2026-09-07, refined and re-scoped 2026-09-08 —
still not fully speced)

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

### Process (as Doug described it 2026-09-08)

1. Read every **AOI instance** in the L5X (not just type definitions —
   this needs instance-level data TASK_004 doesn't currently parse).
2. **Only act on instances whose AOI type already has a valid, generated
   UDT definition** — cross-reference against whatever set of AOI types
   currently have a confirmed-working UDT (the per-AOI checklist in
   `BLUE_SKY_STATUS.md` is the live version of that set for Blue Sky).
   Skip anything else — this task doesn't invent UDTs, TASK_004 does.
3. For each qualifying instance, emit an Ignition tag instance JSON:
   - `DeviceName` — supplied as an explicit parameter (Doug's "device
     string"), not derived. Open question: one value for the whole run,
     or per-instance? Not yet confirmed.
   - `Description` — read directly from **that specific AOI instance's**
     own `<Description>` in the L5X (real per-instance data, not the
     type-level description TASK_004 already reads). This is new: no
     existing PLCHelper task currently reads instance-level AOI usage
     data, only type definitions.
   - `EngUnit` — **left blank.** No way to derive this automatically
     (same conclusion as everywhere else it's come up); Doug fills it in
     per instance afterward.

### Relationship to TASK_004

Depends on TASK_004's output existing first, now precisely (not loosely
— see re-scope above): this task can only assign a tag instance to a UDT
type already confirmed generated and working. Raised alongside Blue
Sky's O2-scope UDT regeneration work (`BLUE_SKY_STATUS.md` Open Item 1)
as the natural next step once enough of those UDTs are in place.

### Open Questions — needs a real scoping pass before this becomes Spec Ready

- **`DeviceName` parameterization** — one value for a whole run, or
  supplied per instance? Not yet confirmed.
- **Naming/instance-path convention** — what determines the emitted
  tag's name and folder placement in Ignition's tag tree? Likely needs
  the same kind of real-file-derived convention TASK_004 uses (learn from
  an existing example, don't assume).
- **Example Ignition tag export needed** — to derive the instance-level
  OPC path/binding convention the same way TASK_004 derives UDT
  conventions from a reference. Not yet supplied.
- **Reuse vs. duplicate parsing logic with TASK_004** — worth deciding
  before implementation, not after.

This task stays at Idea status until these are worked through with Doug,
per this file's own convention (spec first, build second).

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

**Status:** Spec Ready (2026-09-09) — read-only report tool, not yet implemented

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
5. **`priority` is present and non-blank.**
6. **`tagGroup` and `historyTagGroup` match the site being audited** —
   catches copy-paste artifacts like a Weston alarm carrying `tagGroup:
   "MasonCity"`.
7. **The alarm's own `name` field matches its parent tag's `name`.**
8. **The last segment of `displayPath` matches the tag's `name`.**

Rules 1–8 apply uniformly to every tag in the export, including tags
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

---

## TASK_010 — Fix flagged Ignition alarm tag configuration problems

**Status:** Idea (raised 2026-09-09, blocked on TASK_009 — TASK_009 is now
Spec Ready but not yet Implemented)

### Purpose

The companion tool to TASK_009 — once the scanner reliably finds real
problems, this applies the actual fixes. Deliberately kept as a
**separate tool**, not merged into TASK_009's scan-and-report behavior —
Doug's explicit design: "there will be one scanning tool that just gives
me a report of problems with alarms, and then another tool that will fix
those problems."

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

### Open Questions

- Everything, pending TASK_009 being implemented first. Not worth
  speccing further until TASK_009's own report format and rule set are
  proven against real Weston data.

---

*Last updated: September 9, 2026 (2nd) — moved TASK_009 from Idea
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
