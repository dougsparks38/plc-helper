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

## Reference document conventions

- All AOIs and UDTs are documented in a single unified markdown file
- Sections are sorted alphabetically — AOIs and UDTs combined
- Member/parameter names copied exactly as they appear in the XML —
  no capitalization changes of any kind
- Version bumped by 0.1 with every change; previous version kept
- Current reference file: `PLCHelper_Reference_v1.0.md`

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

## Available Tasks

```
Document data structures for SCADA designer (TASK_001)
```

To run a task, open the corresponding file and paste its contents into
Claude Code.

## Task Ideas (not yet implemented)

Audit PLC — IO list, tag database, and code cross-reference (TASK_002)

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

## TASK_002 detail — Audit PLC

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

### Three bidirectional cross-references

**Cross-reference 1: IO List ↔ PLC Tag Database**
- Every device on the IO list should have corresponding tags in the
  controller tag database
- Every relevant tag in the controller tag database should appear on
  the IO list

**Cross-reference 2: IO List ↔ PLC Code**
- Every device on the IO list should appear somewhere in the PLC code
- Every IO tag used in the PLC code should be on the IO list

**Cross-reference 3: PLC Tag Database ↔ PLC Code**
- Every tag in the database should be used somewhere in the code
- Every tag referenced in the code should exist in the tag database

### Loop identifier matching

The matching key between all three sources is the loop identifier.
Loop identifiers can be:
- Numeric loop numbers (e.g. `1234`, `023`) — standard ANSI case
- Alphanumeric equipment abbreviations (e.g. `FLR`, `UPS`, `GEN`)

See the Equipment abbreviation lookup table in this file. Any identifier
not matching a numeric pattern and not found in the lookup table should
be flagged for engineer review.

### PLC tag database — tag types to process

The CSV export from Studio 5000 contains mixed content. Handle as follows:

| Type | Action |
|------|--------|
| Real tags | Include |
| UDT instances | Include |
| IO tags | Include |
| Aliases | Include |
| Rung comments containing a question or unresolved note | Flag as "unanswered question" |
| All other rung comments | Ignore |

Rung comments that suggest unanswered questions include phrases like
"ask", "what", "why", "todo", "fix", "check", "?", or similar.

### Audit output flags

- Device on IO list with no matching tags in PLC tag database
- Tag in PLC tag database with no match on IO list
- Device on IO list with no appearance in PLC code
- IO tag used in PLC code with no match on IO list
- Tag in PLC tag database not used anywhere in PLC code
- Tag referenced in PLC code not found in tag database
- Tags that are program scope instead of controller scope
- Loop identifiers not matching any numeric pattern or known abbreviation
- Rung comments containing unanswered questions

### Notes

- IO list column structure varies by project — inspect the file at
  runtime to identify the column containing the device/loop identifier
- The audit is read-only — it flags issues but does not make changes
- Program scope tag findings should be reviewed carefully before any
  changes are made in Studio 5000
- Additional audit features may be added as they are discovered
