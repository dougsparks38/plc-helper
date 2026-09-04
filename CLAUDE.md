<!-- RULES POINTER START — verify this pointer whenever LESSONS_AND_RULES.md changes (Rule 26) -->
@../claude-workflow/LESSONS_AND_RULES.md
<!-- RULES POINTER END -->

# CLAUDE.md

This file provides guidance to Claude Code for the PLCHelper project —
a growing collection of tools and prompts to assist with common PLC
engineering tasks for Rockwell Automation RSLogix 5000 / Studio 5000.

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

## Ignition tag History — digital vs. analog configuration (verified 2026-09-04)

Source: official Inductive Automation docs, [Configuring Tag
History](https://www.docs.inductiveautomation.com/docs/8.1/ignition-modules/tag-historian/configuring-tag-history),
cross-checked against Inductive Automation forum consensus. Verified while
reviewing `AUTO_hwdi` on the Blue Sky `CONSPD2_AOI` UDT.

**Scope note:** this documents what the History settings *mean* and which
values are correct for a digital vs. an analog signal. It is **not** a rule
for *which* members get historized — that remains an explicit
per-member engineering decision, see `PLCHelper_Tasks.md` TASK_004's
history-tag note and the Hard scope boundary there.

**Deadband Style is the one setting that must differ by signal type:**

| Setting | Digital (`_hwdi`, `_hwdo`, `_scdi`, `_scdo`, `_alm`, any BOOL) | Analog (`_hwai`, `_hwao`, `_scai`, `_scao`, any REAL/Float4) |
|---|---|---|
| Deadband Style | **Discrete** | **Analog**, or Discrete — see note below |
| Deadband Mode | Absolute | Absolute (Percent = % of EU span; meaningless without an EU span) |
| Historical Deadband | must be **less than 1** — 0 or 0.01 both fine | a real engineering value chosen for the signal |

**Why Discrete is the correct style for a digital signal — two reasons,
both from the docs:**

1. **Storage.** Under Discrete, "a new value (V1) will only be stored when:
   `|V1-V0| >= Deadband`." A BOOL transition is always a change of exactly
   1, so any deadband below 1 always passes and every transition is stored.
2. **Retrieval — this is the bigger one.** Under Discrete the value "will
   not be interpolated. The value returned will be the previous known
   value" (step interpolation). Under Analog it "will be interpolated
   linearly between the last stored value and the next value" — which on a
   Boolean produces meaningless fractional values like 0.4 on a trend.
   Analog style on a digital tag is wrong for this reason, not just
   stylistically odd.

**The `Auto` default already does the right thing** — it picks Analog for
Float/Double and Discrete for every other data type. Setting Discrete
explicitly on a BOOL is therefore correct *and* redundant; explicit is
preferred because it survives a data-type change on the member.

**On a non-zero Historical Deadband next to Discrete style (e.g. 0.01 on a
BOOL):** harmless, but vestigial — it can never change the outcome, since
the smallest possible BOOL change (1) always exceeds it. The docs do **not**
state that the deadband field is ignored for Discrete style or for Boolean
tags; they give a formula that is simply always satisfied. Treat it as
inert, not as proof the engine skips the math.

⚠️ **The real trap:** a Historical Deadband of **1 or greater** on a BOOL
would silently suppress *all* history for that tag, because `|1-0| >= 1` is
the boundary and nothing larger is achievable. Values like 0.01 are safe
precisely because they are below 1. When reviewing an inherited UDT, check
the *magnitude* of the deadband on digital members, not just the style.

**Analog members:** Analog style is the documented match for Float, but
forum consensus is that its slope-compression behavior makes trends read as
flat lines in charts that assume step data, so many integrators use Discrete
for floats too. Either is defensible — this is a judgment call, not a
correctness question, and Casne has no standing convention on it yet.
**Updated below:** the docs now do lean one way on this, but only in a
version-and-provider-scoped note — see "Official lean against Analog style."

### Analog-specific findings (verified 2026-09-04, reviewing `Analog_hwai`)

Verified while reviewing `Analog_hwai` on the superseded
`zzDelete_FLOWIN3_AOI_old` UDT (Float/REAL, 0.0–100.0 EU range). Extends the
digital review above; nothing above is retracted.

**`Auto` on a Float is not "equivalent to explicit Analog" in the way
explicit `Discrete` was equivalent on a BOOL — and the type-change argument
does not carry over.** `Auto` on a Float resolves to Analog, so today `Auto`
and explicit `Analog` behave identically. But the reason explicit was
preferred on a BOOL was that it *survives a data-type change on the member*,
and that reasoning is specific to the digital case:

- On a BOOL, explicit `Discrete` protects the correct choice — if the member
  later became a Float, `Auto` would silently flip it to Analog.
- On a Float, explicit `Analog` protects a choice you would probably *not*
  want on any other type, so pinning it is arguably worse under a type change
  than leaving `Auto`.

The practical consequence that matters more: **`Auto` can never give you
Discrete on a Float.** If Discrete is what's wanted on an analog member (see
next item), it must be set explicitly — leaving `Auto` silently opts into
Analog.

**Official lean against Analog style — real, but narrowly scoped.** The
Ignition **8.3** Configuring Tag History page carries a note box, "Using
Deadband with the Core Historian," stating: "Out of order writes (such as with
the Analog deadband style) for the Core Historian can be taxing on your
system. To avoid potential impacts on performance and I/O utilization, it is
recommended to use either the Discrete deadband style or turn deadband mode
off and use the Periodic Sample Mode."

Scope limits, verified rather than assumed — do not over-read this note:

- It is **absent from the 8.1 docs entirely** (that page's note boxes were
  checked; no out-of-order-writes/performance note exists there).
- "Core Historian" is the **8.3-only QuestDB-backed internal provider**. The
  term appears nowhere in the 8.1 provider docs; every 8.1 provider is
  SQL/database-based (Datasource, Internal/SQLite, Remote, Splitter, DB
  Table, Simulator, OPC-HDA).

So this is the first *official* support for the Discrete-on-floats
preference the forum consensus above already described — but it is an
8.3 + Core-Historian performance note, not a general correctness rule.
**Whether it applies to a given job depends on the Ignition version and
whether the provider is Core Historian or a SQL provider** — for `Hist_IW`
that is unresolved and has not been assumed either way.

Separately, an 8.1 retrieval-side note on Analog style: "Be aware that if a
tag is storing history using the Analog style, the returned dataset will
include post-query seed values."

**Deadband Mode `Absolute` with `0.01` on a 0–100 span:** Absolute is the
documented default and is correct here. Note the arithmetic — Percent mode is
"calculated as a percentage of the tag's engineering unit span," so on a
**0–100 span specifically, Absolute and Percent are numerically identical**
(X% of a 100-unit span = X units). The Absolute/Percent choice only starts to
matter on this member if its EU range ever changes off 0–100; Percent would
then rescale with it and Absolute would not.

**On choosing the deadband value: the docs give no guidance at all.** Both
the 8.1 and 8.3 pages were checked; neither offers a method, a recommended
value, or a rule of thumb for picking a Historical Deadband. This is purely
an engineering judgment call about how much signal noise is worth storing —
there is no documented right answer, and one should not be invented. For
reference only, `0.01` is the value used in the docs' own worked example, and
0.01 on a 0–100 span is a very fine deadband (0.01% of span) that will store
nearly every change.

**Sample Mode for an analog tag — the docs do not address this.** Neither the
8.1 nor the 8.3 page states a default Sample Mode, and neither distinguishes
analog from discrete/Boolean tags in choosing one. The only official
statement touching it is the 8.3 Core Historian note above (which pairs
"deadband off" with Periodic). Forum discussion is community-only — no
Inductive Automation staff replies were found in the threads reviewed — and
treats float tags as warranting *rate-based bucketing* (fast/medium/slow,
e.g. pressure vs. temperature) rather than a single correct mode.

**So this is a judgment call, the same way Analog-vs-Discrete style is** —
not a documented correctness question.

**Casne standing default for analog signals (decided 2026-09-04):**
resolves the Sample Mode judgment call above, same as the digital decision.

| Setting | Analog default |
|---|---|
| Sample Mode | **On Change** — same choice as digital; per the reasoning above, on an OPC tag this is already bounded by the tag's own scan rate, not unbounded |
| Max Time Between Samples | **20 minutes** — same value as digital (confirmed 2026-09-04) |
| Max Time Units | Minutes |

This makes Sample Mode = On Change **and** Max Time Between Samples =
20 minutes the Casne default for **both** digital and analog tags. With
Sample Mode now On Change (not Tag Group), the tag's own Max Time setting
governs directly — the Tag-Group-override caveat below no longer applies
to newly-configured members using this default; it only explains why the
*old* `zzDelete_` reference's `20 Minutes` (under Tag Group mode) wasn't
reliable evidence of anything. What still differs by signal type is
**Deadband Style** (Discrete for digital, Analog or Discrete for analog
per the note above) — that's the one setting the docs actually mandate
differently, not Sample Mode or Max Time.

Two things that *are* documented and worth checking against a Tag-Group
configuration like `History 5 Sec`:

1. "Typically, the Historical Tag Group should execute at the same rate as
   the tag's Tag Group or slower" — a 5-second historical group is only
   appropriate if the member's own tag group scans at 5 seconds or faster.
2. Reasoning from the doc definitions (not a doc statement): `On Change`
   checks "each time the tag value changes," and an OPC tag's value only
   updates when its own tag group scans it — so `On Change` on an analog is
   already bounded by the tag's scan rate, not unbounded.

⚠️ **`Max Time Between Samples` = 20 Minutes may be inert here, because
Sample Mode is `Tag Group`.** Official 8.1 docs, How the Tag Historian System
Works: "When using a Tag Group sample mode, there are two locations where a
Max Time can be defined: On the tag's history settings, and on the Tag
Group's history settings. The Tag Group's settings override the settings on
the Tag, *except* when the Tag Group is using it's default values."

**This is a real asymmetry with the digital standing default above.** The
digital convention pairs 20 minutes with `On Change`, where the tag's own max
time governs directly. Here the same 20 minutes sits next to `Tag Group`
mode, so whether it takes effect depends on the `History 5 Sec` tag group's
own max-time setting — the number showing in the tag editor is not proof it
is in force. A community-reported wrinkle (not official, and not verified
first-hand): once a tag group's max time has been touched, the group's value
reportedly keeps winning even after being set back to its default.

**On the 20 Minutes matching the new digital default:** treat this as
coincidence/template artifact, not evidence for an analog default. This UDT
is a superseded `zzDelete_` reference that Doug did not just configure, and
the surrounding values are the Ignition defaults or doc-example values
(`Auto` is confirmed the default Deadband Style; `Absolute` the default
Deadband Mode; `0.01` the docs' example value — whether `0.01` is also the
shipped default could not be confirmed). A settings block sitting at its
defaults is not an independent engineering decision that happens to agree
with the new convention.

**Casne standing default for digital signals (decided 2026-09-04):**
resolves the Sample Mode judgment call the initial review flagged.

| Setting | Digital default |
|---|---|
| Sample Mode | **On Change** — not "Tag Group" polling, so a transition shorter than a polled interval can't be missed |
| Max Time Between Samples | **20 minutes** — forces a periodic log even with no change, so a stuck/dead connection is visible as a gap in history rather than silence that could be mistaken for "nothing happened" |
| Max Time Units | Minutes |

This is a **standing convention for digital tags going forward**, distinct
from the Deadband Style/Mode correctness rules above (which are not
optional) — Sample Mode has no single "correct" answer the docs mandate,
so this is Casne's own choice, not something derived from documentation.

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
