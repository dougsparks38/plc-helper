<!-- RULES POINTER START — verify this pointer whenever LESSONS_AND_RULES.md changes (Rule 26) -->
@../claude-workflow/LESSONS_AND_RULES.md
<!-- RULES POINTER END -->

# CLAUDE.md

This file provides guidance to Claude Code for the PLCHelper project —
a growing collection of tools and prompts to assist with common PLC
engineering tasks for Rockwell Automation RSLogix 5000 / Studio 5000.

## Project context

- Platform: Allen-Bradley / Rockwell Automation
- Software: RSLogix 5000 / Studio 5000
- File format: L5X (XML export format)
- Controller context: `BOP_O2_CombinedTest`, software revision v35.01

## L5X file format

L5X files are XML exports from Studio 5000. Two types are used in this
project:

**AOI files** (`AddOnInstructionDefinition` with `Use="Target"`):
```
RSLogix5000Content
  Controller (Use="Context")
    DataTypes (dependent UDTs, if any)
    AddOnInstructionDefinitions
      AddOnInstructionDefinition (Use="Target")
        Parameters       — inputs/outputs visible at the call site
        LocalTags        — internal variables (timers, ONS bits, accumulators)
        Routines/Logic   — Relay Ladder Logic (RLL) rungs in structured text
```

**UDT files** (`DataType` with `Use="Target"`):
```
RSLogix5000Content
  Controller (Use="Context")
    DataTypes
      DataType (Use="Target")
        Members          — the data members of the UDT
```

## Naming conventions

| Suffix | Meaning |
|--------|---------|
| `_hwai` | Hardware analog input — physical signal wired to I/O card |
| `_hwao` | Hardware analog output — physical signal to I/O card |
| `_hwdi` | Hardware digital input |
| `_hwdo` | Hardware digital output |
| `_scao` | Setpoint written from SCADA/HMI to PLC |
| `_scai` | Value reported from PLC to SCADA/HMI |
| `_scdo` | Digital command from SCADA/HMI to PLC |
| `_scdi` | Digital status reported from PLC to SCADA/HMI |
| `_alm`  | Alarm output bit |
| `_alm_dis` | Alarm disable input |
| `_alm_res` | Alarm reset input |
| `_alm_ack` | Alarm acknowledge bit |
| `_Tmr` | TIMER local tag |
| `_ONS` | One-shot latch bit |
| `_intm` | Intermediate accumulator (pre-rollover value) |
| `_` prefix | Internal implementation detail |

## Editing L5X files

- Ladder logic rungs are in `<Text><![CDATA[...]]></Text>` blocks
- Timer instructions: `TON(_DBTmr,?,?)` — `?,?` filled by Studio 5000
- `MOV(src,_Tmr.PRE)` exposes a timer preset as a visible parameter
- Branching in RLL text: `[branch1 ,branch2 ]`

## Key design patterns

**Alarm debounce**: All alarms use a `TON` timer before setting the
alarm output. The timer preset is driven by a visible DINT parameter.

**Alarm hysteresis**: Hi/Lo alarms use a reset-level calculation
(`_Hi_Rst_Lvl = Hi_scao - Hi_Rst_Diff_scao`) to prevent chattering.

**Rollover totalizer**: `FLOWIN3_AOI` uses paired `_intm` + rollover
count (`RC`) tags because REAL precision degrades above ~16.7 million.

**REAL floating-point quirk**: Use `0.199999` instead of `0.2` to
compensate for Logix5000 REAL precision issues.

**AOI reuse across projects — a source-of-truth risk (2026-09-02)**:
Casne engineers commonly copy Add-On Instructions from a prior project
into a new one rather than write them from scratch, since many AOIs are
built to be transportable. There is a master reference program
(something like "AOI Development") intended as the canonical source,
but in practice engineers just as often grab a copy from an old project
instead of checking the master. Implication: a bug fixed inside one
project's copy of an AOI (e.g. a stray comment, a scaling error) will
NOT automatically propagate anywhere else — the same bug can resurface
in a future project that copied the old version, and the master
reference may itself be stale if nobody updated it. When auditing or
fixing AOI-level issues, keep in mind the fix is local to this project's
copy unless someone deliberately updates the master AOI Development
program too.

## Reference document conventions

- All AOIs and UDTs are documented in a single unified markdown file —
  the "Casne AOI Reference," a general, company-wide library of AOIs
  Casne has built and reused across jobs, not scoped to any one job
- Sections are sorted alphabetically — AOIs and UDTs combined
- Member/parameter names copied exactly as they appear in the XML —
  no capitalization changes of any kind
- Every section is tagged with its source — **Casne** (no `Vendor`
  attribute on the source element) or the vendor named in that
  attribute (e.g. **Rockwell Automation**)
- Casne-sourced entries append the job/file this documentation was
  drawn from to the Source line (e.g. `Casne — Blue Sky O2 program
  (job 261183-001), BOP_O2_CombinedTest_v35_Emulate.L5X`); vendor
  entries need no job appended. Every entry also carries a
  `**Last updated:**` line immediately after Source. Standing
  convention: whenever an entry is substantively touched again (new
  job's program, rewritten description, changed parameters), update
  both its Source and Last-updated lines to the newest event — see the
  skill file for the full rule
- Every section has a top-level summary paragraph sourced only from
  that entry's own `<Description>`/`<RevisionNote>`/`<AdditionalHelpText>`;
  if none exist or none are usable, the exact placeholder
  `[No description in source — needs to be written]` is used instead —
  never an inferred guess at what the AOI does
- Current reference file: `PLCHelper_Reference.md`, updated in place —
  see git history for prior versions

### Reference file format

```
## SECTION_NAME

.MemberName - Description
.MemberName - Description
```

### Exclude marker

The engineer marks parameters or members to be excluded from Ignition
with `[exclude]` at the end of the description line. Entries without
this tag are included in Ignition by default. Claude Code must never
add or remove `[exclude]` tags unless explicitly instructed.

Example:
```
.Alarm - Alarm output bit
.EnableIn - Enable Input - System Defined Parameter [exclude]
```

## Tasks

Full task write-ups (purpose, inputs, process, outputs) live in
`PLCHelper_Tasks.md`, not here — that file is the catalog of what each
TASK_00X actually does. Building/updating the SCADA reference document
(TASK_001) is invoked as a Skill —
`claude-workflow/Skills/plc-aoi-reference-creation-and-update.skill.md`
— not a local file in this folder; the "Reference document conventions"
section above is a condensed summary, not the authoritative copy.

## Equipment abbreviation lookup table

Used by the Audit PLC task to recognize non-numeric loop identifiers.
When the audit finds a tag identifier that is not a numeric loop number,
it checks this table. If found, it is a known equipment abbreviation and
is not flagged. If not found, it is flagged for engineer review.

To add a new abbreviation, add a row to the table below. If an
abbreviation is ambiguous (can mean more than one thing), note all
meanings — the engineer must resolve which applies in context.

| Abbreviation | Meaning | Notes |
|--------------|---------|-------|
| CV | Control Valve | |
| FLR | Flare | |
| GEN | Generator | |
| LS | Lift Station or Limit Switch | Ambiguous — engineer must resolve |
| TK | Tank | |
| UPS | Uninterruptible Power Supply | |

Note: the Equipment abbreviation lookup table above is used by TASK_002
(Audit PLC) — see `PLCHelper_Tasks.md` for that task's full write-up.
