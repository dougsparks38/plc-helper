<!-- RULES POINTER START — verify this pointer whenever LESSONS_AND_RULES.md changes (Rule 26) -->
@../claude-workflow/LESSONS_AND_RULES.md
<!-- RULES POINTER END -->

# CLAUDE.md

This file provides guidance to Claude Code for the PLCHelper project —
a growing collection of tools and prompts to assist with common PLC
engineering tasks for Rockwell Automation RSLogix 5000 / Studio 5000.

## Reference tip — resetting an Ignition gateway without a full PC reboot

Found 2026-09-10: [Schulman Engineering — Ignition Gateway Reset with
gwcmd.bat](https://schulmanengineering.com/ignition-gateway-reset-with-gwcmd-bat-how-to-unlock-and-restart-your-scada/).
Not independently verified against Casne's own systems — a starting
point, not a confirmed procedure. Also saved in `BlueSky/CLAUDE.md` — not
consolidated into one shared location since there isn't a natural common
home for both projects the way `CPKCR-Systemwide` serves the CPKCR
folders.

- Tool location (per source): `C:\Program Files\Inductive Automation\Ignition`
- Open Command Prompt as Administrator, `cd` into that folder
- `gwcmd.bat -p` — resets the gateway admin credentials and prompts for a
  service restart; does not overwrite existing projects
- `gwcmd.bat -r` — restarts the Ignition service directly from the
  command line; may require recommissioning via the web interface
  afterward
- **Caution (from the source):** a restart halts the system temporarily
  — notify operators/supervisors, plan for downtime, and confirm no
  safety/production risk before running this on a live system

## Confidentiality / PII intake — read before adding any file here

The general PII intake process (the `PII_Review` staging folder, the scan,
the confirmed-override mechanism) is shared across all Casne projects —
see `claude-workflow/CASNE_PII_INTAKE_PROCESS.md` for the full process.
That file is the single source of truth (Rule 9); do not restate its steps
here.

**Why this matters differently in PLCHelper — this folder IS a git repo.**
The other Casne folders that use this intake process (BlueSky, Augean,
UW_WCUP, UPRR_Systemwide) are deliberately **not** git repos and are never
pushed anywhere — their risk is client confidentiality, contained to this
machine. PLCHelper is the opposite shape: it is a real git repo
(`github.com/dougsparks38/plc-helper`) and its contents get committed and
**pushed to GitHub**, on Doug's personal account. So the intake discipline
here is guarding a different exposure — anything that lands in this folder
and gets committed leaves the machine permanently and lands in a personal
repo, separate from any question of which client it belongs to.

Practical consequences:

- **`PII_Review\` contents are git-ignored on purpose.** The folder itself
  is tracked (via a `.gitignore` inside it that ignores everything but
  itself — this repo had no prior empty-folder convention, so this is the
  standard git idiom). A document staged there has not yet been scanned, so
  it must not be committable. Do not remove or weaken that `.gitignore`,
  and do not `git add -f` anything out of that folder.
- **Passing the scan clears a document for the folder, not automatically
  for the repo.** Moving a CLEAN document out of `PII_Review` into the
  project folder proper makes it readable, and it then becomes a normal
  tracked file that will be pushed. For any document whose value is as
  local reference material rather than something that belongs in a public-
  facing repo, ask Doug before committing it — being CLEAN on `pii_scan.py`
  is not the same as "should live on GitHub."
- **Rule 36 still applies to every push from this folder** —
  `python pii_scan.py --agent PLCHelper` before any `git push`.

**Scope note:** most PLCHelper content is general, company-wide engineering
methodology (AOI/UDT conventions, audit tasks), which per the shared process
doc is not client-confidential by itself. This section exists because
PLCHelper is now also taking in general Casne internal reference material —
e.g. the PLC-engineer onboarding document — which is internal-to-Casne
content sitting in a repo that gets pushed publicly.

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

## Analog input diagnostic bits and I/O-wiring convention

Two related conventions: how a client-provided IO list's tag names become
real PLC tags, and how the resulting hardware IO actually gets referenced
in logic.

### IO-list tag → PLC tag translation

A client-provided IO list (e.g. a panel designer's Excel list) often uses
a dot before a signal-type suffix — e.g. `FIT_3001.F_RS` — because Excel
is meant for humans and the dot reads naturally. In Studio 5000, a dot
means "sub-element," which is wrong here (the suffix isn't a real
member), so it gets flattened to an underscore for the real PLC tag. When
a project has more than one PLC, a project-specific PLC-identifying
prefix is also prepended, separated by an underscore, to keep tags from
different PLCs distinguishable: `FIT_3001.F_RS` → `BOP_FIT_3001_F_RS`.
The prefix itself (e.g. `BOP_`/`O2_`) is **not** a universal convention —
it's chosen per project when multiple PLCs are involved; see that
project's own `CLAUDE.md` for its actual prefix values.

### Analog input diagnostic bits (best-effort, not guaranteed)

For analog inputs specifically — never analog outputs, never digital IO —
Casne tries to also bring in the module's own channel diagnostic bits
alongside the scaled value: Overrange, Underrange, and (channel) Fault,
one Boolean tag each, suffixed onto the base tag name: `<base
tag>_Overrange`, `<base tag>_Underrange`, `<base tag>_Fault`. **This is
aspirational, not guaranteed** — different Rockwell analog input module
families expose different diagnostic bit sets (some may lack one or more
of these, or expose additional/different ones). Map what the specific
module actually provides; never assume all three exist for every AI.

### Two I/O-wiring methods — Casne's preferred method vs. the "blanket" method

Two different ways exist to get physical IO (analog or digital) into use
by the rest of the program logic:

- **The "blanket" method** — one dedicated routine reads all IO of a
  given type (one routine for all AI, one for all AO, one for all DI, one
  for all DO), staging each point into a base application tag via a MOVE
  instruction (analog) or an XIC→OTE rung (each diagnostic bit), before
  it's used anywhere else. Rationale: PLC IO updates asynchronously
  relative to the program scan, so in theory a point read more than once
  in a single scan could see different values mid-scan; reading once into
  a base tag avoids that risk entirely. In practice, Casne engineers
  don't worry about this much — program scans run on the order of 1ms,
  far faster than real-world IO update rates, so the actual risk is low.
- **The Casne method (preferred)** — no staging routine at all. Every
  analog input gets up to 4 direct Rockwell Alias tags — the scaled value
  (`_hwai` suffix, per the Naming conventions table above) plus up to 3
  diagnostic-bit aliases (`_hwdi` suffix each, e.g. `..._Overrange`,
  `..._Underrange`, `..._Fault`) — each aliased directly to the module's
  own hardware tag
  (`Local:<slot>:I.Ch<NN>.Data`/`.Overrange`/`.Underrange`/`.Fault`).
  Each alias is referenced exactly once, typically typed directly as a
  parameter into the AOI instruction call that uses it (e.g.
  `FLOWIN3_AOI`'s `Analog_hwai`, `OverRange_hwdi`, `UnderRange_hwdi`,
  `ChFault_hwdi` parameters) — so it's still effectively read once per
  scan, just without a separate staging step or routine.

Both methods are real, both appear in real Casne code — check which one a
given project/instrument actually uses rather than assuming. Example:
Blue Sky's BOP PLC currently uses the blanket method for `FIT-3001`
(existing code, left as-is 2026-09-22 — not necessarily the pattern for
new instruments); Blue Sky's O2/Lagoon PLC's `O2_FM100` (`FLOWIN3_AOI`)
uses the Casne alias method.

## UDT type naming convention (source: `Casne Programming Standards for PLC.docx`, 2026-09-04)

This is about the **UDT type's own name** — a different thing from the
member-suffix table above.

- **Primary UDTs** (the main, general-purpose types): name them in
  **ALL CAPS** — e.g. `FLOWIN3_AOI`, `CONSPD2_AOI`.
- **Secondary UDTs** (supporting/dependent types used inside a primary
  UDT): start the name with an underscore `_`, and give the whole name
  **lowercase** letters. The leading underscore is what sorts them to the
  bottom of the UDT list in the Tag Browser, keeping primary types easy
  to find at the top.

Relevant to `generate_ignition_udt.py` (TASK_004)'s `--udt-name` option:
when generating a **primary** UDT, the name should be ALL CAPS per this
convention; the script does not enforce this itself (it takes whatever
name it's given), so follow the convention when choosing the value to
pass.

## Ignition Designer reference (tag history, UDT/instance import)

Tag-history digital/analog configuration, importing generated UDT
definitions, replacing a UDT definition that already has instances, and
the tag-instance "does not have item 'X' for overrides" error all moved
to the `ignition-designer-import` skill (2026-09-11, `/doctor` context
cleanup) — loaded on demand instead of every session. See that skill for
all four topics; not duplicated here (Lesson 9).

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

## Script + help-file naming convention (established 2026-09-10)

Every Python tool gets a companion help/reference markdown file, named
with the script's own base name as a prefix plus a short descriptive
suffix (e.g. `generate_ignition_tags.py`'s AOI-parameter mapping →
`generate_ignition_tags - AOI parameter help.md`). This makes the pair
sort together alphabetically in a folder listing. If a tool ever needs
more than one companion doc, each additional file keeps the same
script-name prefix so they all cluster together.

This is a lighter, script-adjacent layer distinct from
`PLCHelper_Tasks.md`'s full task write-ups — that file stays the
authoritative spec/history for each `TASK_00X`; a script's own help file
is the quick "how do I actually run this" reference sitting right next
to the tool itself, without needing to go find and search the big
catalog file.

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
