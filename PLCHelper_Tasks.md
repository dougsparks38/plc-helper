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
| TASK_004 | Generate Ignition UDT definition from an AOI | Implemented | Given an AOI type name, an L5X export, and a reference UDT JSON, generate a brand-new Ignition UDT definition JSON with one member per AOI parameter — every parameter, no exclusions |

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
     `historicalDeadbandStyle`, …) are per-member engineering choices,
     **not** conventions — they are deliberately not invented for
     generated members. Doug enables history on the specific members he
     wants it on, in Designer.
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
5. **Write the output JSON** into the **job's own folder**, never into
   PLCHelper.

### Data type mapping (confirmed from real files, 2026-09-04)

| PLC (L5X) | Ignition | How confirmed |
|---|---|---|
| `BOOL` | `Boolean` | 24 of 25 BOOL members in the real reference UDT |
| `DINT` | `Int4` | 3 of 4 DINT members |
| `REAL` | `Float4` | consistent, no counterexample |
| `SINT` / `INT` | `Int4` | inferred from the DINT integer mapping — flagged in the report when hit, not silently assumed |
| `STRING` | `String` | observed in the real instance exports |

**The reference UDT contains its own data-type errors** — found while
deriving this mapping: `AutoCall_INTRLK_scdi` is `BOOL` in the PLC but
`Int4` in the UDT, and `AUTO_STATUS_scai` is `DINT` in the PLC but
`Float4`. These are hand-entry mistakes in the coworker-built UDT, not
conventions. The mapping is therefore **fixed in the script from the
confirmed-correct majority**, and is *not* learned per-member from the
reference — learning it per-member would faithfully reproduce the bugs.
Any PLC data type the script has no confirmed mapping for is reported as
a warning rather than guessed.

### Outputs

1. A new Ignition UDT definition JSON, written to the job's folder,
   importable via Ignition Designer's **UDT Definitions** tab, with one
   member per AOI parameter.
2. A console report: parameter count, the conventions derived from the
   reference (so they can be eyeballed before import), and warnings for
   any unmapped data type.

### Open Questions / Notes

- **UDT name does not track the AOI version number.** A UDT named
  `CONSPD2_AOI` legitimately corresponds to PLC type `CONSPD4_AOI` —
  expected, not an error. The script therefore takes the output UDT name
  as an explicit option (`--udt-name`) and defaults to the AOI type name
  only when not told otherwise. It never infers a mapping by name.
- Generated members intentionally carry **no history configuration**.
  History is a per-member engineering decision Doug makes in Designer.
- `{InstanceName}` is a genuine built-in Ignition parameter requiring no
  manual setup; `{Name}` is **not** built-in and must be a custom
  parameter where it appears. Generated templates use `{InstanceName}`.
- The script does not import into Ignition and does not modify any
  existing UDT — it only writes a new file. Correcting existing UDTs
  remains a separate concern under the Hard scope boundary.

---

*Last updated: September 4, 2026 — added TASK_004 (generate a brand-new
Ignition UDT definition JSON from an AOI's real parameter set), including
the Doug-approved "include every parameter" scope decision and how it
coexists with the existing Hard scope boundary on correcting existing
UDTs. Prior update: September 2, 2026.*
