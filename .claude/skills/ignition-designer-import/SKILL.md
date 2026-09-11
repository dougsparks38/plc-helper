---
name: ignition-designer-import
description: Ignition Designer reference for PLCHelper — tag history (digital vs. analog config), importing generated UDT definitions, replacing a UDT definition that already has instances, the tag-instance "does not have item 'X' for overrides" error, and Perspective template work (dropConfig UDT drag-and-drop, indirect tag binding syntax, parameterizing a reusable equipment view). Load when configuring Ignition tag history, importing/troubleshooting a TASK_004/TASK_005-generated UDT definition or tag-instance JSON in Designer, or building/reviewing a Perspective view driven by a UDT tag path parameter.
---

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

## Perspective — drag-and-drop UDT-to-template binding, and how to parameterize a reusable template (verified 2026-09-11)

Scope: **Perspective only.** None of this applies to Vision, and the
differences from Vision are the whole point of the section. Verified
against the official Inductive Automation [Drop
Configuration](https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/tag-bindings-in-perspective/drop-configuration)
page on **both 8.1 and 8.3** (same mechanism, same property names, no
version difference found), the [Tag Bindings in
Perspective](https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/tag-bindings-in-perspective)
and [Binding Property Path
Reference](https://www.docs.inductiveautomation.com/docs/8.3/ignition-modules/perspective/working-with-perspective-components/bindings-in-perspective/binding-property-path-reference)
pages, the Inductive University 8.3 lesson *UDTs and Template Views*, and
Inductive Automation forum threads for the gotchas.

### Yes, the drag-and-drop exists — it is called `dropConfig`

Perspective does have a direct analog of Vision's "drag a UDT instance
onto a template." It is **not automatic** — it only works on views that
have been explicitly set up for it. The setup lives on the **view's own
`dropConfig` property** (a root-level property of the View object, next to
`params`, not on any component).

`dropConfig` has two sub-arrays:

- **`udts`** — associate this view with one or more UDT *definitions*
- **`dataTypes`** — associate this view with a raw tag data type (Int4,
  Float8, etc.)

Each entry carries three fields:

| Field | Meaning |
|---|---|
| `type` | the UDT definition this view accepts (in the `udts` array) |
| `param` | the name of a **view parameter on this same view** that receives the dropped tag |
| `action` | `bind` or `path` — what the parameter receives |

**`action` is the decision that matters:**

- **`path`** — populates the parameter with the **tag path as a string**.
  This is the `Tag_Path`-parameter pattern, and it is the one to use for a
  reusable equipment template driven by indirect bindings.
- **`bind`** — creates an actual **tag binding** between the view parameter
  and the dropped tag. If the parameter is typed as an **Object** whose
  keys exactly match the UDT's member names, the drop exposes each member's
  value on the matching key.

**What the drop actually does at design time:** drop a configured UDT
instance from the Tag Browser onto a view in the Designer and a popup
lists every view whose `dropConfig` matches that UDT; pick one and Ignition
creates an **Embedded View instance** with `param` already populated.

⚠️ **What it does NOT do — read this before assuming it fixes anything.**
The drop populates **exactly the one parameter named in `param`.** It does
not create, audit, repair, or even look at the bindings *inside* the view.
Every internal binding is authored once on the view definition and is
shared by all instances. A binding inside the view that points at a
hardcoded tag path stays hardcoded no matter how the instance was created.
So drag-and-drop is a convenience for *instantiating* a correct template —
it is **not** a safety net against a badly-parameterized one.

The docs describe the drop as *creating* an embedded view instance. They
do **not** state whether dropping onto an already-placed embedded view
re-points its parameter, and no forum thread was found that settles it —
**unverified, do not assume either way.**

### How to actually build the reusable template

The approach with the strongest support — IA's own docs for indirect
bindings, and the consistent recommendation on the forum — is the
**tag-path-parameter** pattern:

1. On the template view, add **one** view parameter, e.g. `Tag_Path`,
   typed **string**. This is the only per-instance input.
2. Bind **every** internal component property with an **Indirect Tag
   Binding** whose path is built from that parameter plus the member name.
   No component gets its own tag path.
3. Set `dropConfig.udts[0]` to `{ type: <the UDT>, param: "Tag_Path",
   action: "path" }` so a drag-and-drop fills `Tag_Path` and nothing else.

Note that Inductive University's 8.3 lesson demonstrates the *other*
option — a **UDT-typed Object parameter** with `action: "bind"`, with
components bound to `view.params.<param>.<memberName>`. That is
documented and works, and it has the advantage of one subscription instead
of many. The forum's countervailing argument, from long-time community
contributors (community opinion, **not** an IA staff position): a tag-path
parameter decouples the template from the UDT *type*, so one template
serves any UDT that happens to carry the member names it needs, and it
sidesteps the inheritance limitation below. Both are legitimate; pick one
per template and do not mix them.

### ⚠️ Perspective's indirect binding syntax is NOT Vision's

This is the single most likely thing to trip up someone coming from
Vision. In Vision you type a property reference inline into the tag path.
**Perspective does not work that way.**

Perspective's Indirect Tag Binding uses **numbered placeholders**. The
docs' own worked example:

- Direct path:   `[default]Motors/Motor 1/Amps`
- Indirect path: `[default]Motors/Motor {1}/Amps`

The docs state the parameters "are numbered starting at one, and denoted
by braces." Each numbered placeholder is then pointed at a property or
view parameter in the binding editor's own reference list — you pick the
source there, you do not type it into the path. Indirect Tag bindings also
have a **Bidirectional** checkbox for write-back.

Whether the longhand `{view.params.Tag_Path}` form can be typed directly
into the *indirect tag path field* was **not verified** — do not rely on
it. Use the documented numbered form.

The `{view.params.X}` form **is** documented for **property and expression
bindings**. The Binding Property Path Reference page gives the property
path vocabulary verbatim: `view.params.paramName`, `this.meta.name`,
`parent.props.complex.foo`, relative `../ButtonB.position.x` and
`../../LabelA.position.x`, absolute `/root/LabelA.position.x`, and array
indexing `/root/LabelA.props.complex.bar[5]`. Hard constraint from that
same page: **"Only properties on components in the same view are eligible
to be used in this way"** — cross-view sharing goes through session
custom properties.

### The bug class this prevents — and the one it doesn't

**It does not prevent a wrong internal binding.** If a property inside the
template carries a hardcoded tag path pointing at some *other* equipment
instance, that is a defect in the **view definition**, and `dropConfig`
never touches it. Every instance of that view inherits the same wrong
binding. This is easy to create (copy a binding from a working component,
forget to re-parameterize it) and easy to miss (the value populates and
looks plausible — it is just the wrong machine's data).

**The real diagnostic tell, and it is worth knowing:** a Perspective
view's internal bindings are part of the view definition and **cannot vary
per instance.** So if only *one* piece of equipment on a screen shows a
stray hardcoded path while its siblings are correct, those are almost
certainly **copy-pasted containers, not instances of one embedded view** —
which is the actual root problem, and no amount of drag-and-drop fixes it.
(This inference follows from the documented per-view binding model; it is
not a quoted doc statement.)

The audit that catches this class of bug: search the view JSON for any tag
path that does **not** derive from the template's parameter. In a
correctly-built template, the equipment identifier appears **exactly
once** — in the parameter — and nowhere else.

### Gotchas — flagged by confidence level

- **Inherited / child UDT instances are not recognized by `dropConfig`.**
  Dropping an instance of a UDT that *inherits* from the configured parent
  type reportedly finds no associated views, where Vision handles the
  inheritance. Forum-reported, **no IA staff acknowledgment, no version
  numbers, no ticket ID** — treat as community-grade and verify on the
  actual gateway before designing around it.
- **`udts` and `dataTypes` configured together on one view**: forum report
  that the UDT half works while the data-type half comes back blank.
  Community-grade, unconfirmed, no version given.
- **Spaces in UDT member names reportedly break tag-drop bindings.** Seen
  only in a secondary search summary, **not confirmed against a primary
  source** — recorded as a thing to watch for, not as established fact.
  Avoiding spaces in member names is cheap insurance regardless.

### What remains genuinely unresolved

Do not paper over these if they come up:

1. Whether dropping onto an **existing** embedded view re-points its
   parameter, or always creates a new instance.
2. Whether `{view.params.X}` is accepted verbatim in the **indirect tag
   path** field (as opposed to expression/property bindings, where it is
   documented).
3. The inheritance, combined-config, and member-name-space gotchas above —
   all community-grade, none version-pinned.

No behavioral difference between **8.1 and 8.3** was found for any part of
`dropConfig` or indirect tag bindings. Both versions' pages were fetched
and compared directly; the property names, the `udts`/`dataTypes` split,
and the `bind`/`path` actions are identical.

## Perspective — `view` vs. `root` are different objects; sharing one computed value across a view (verified 2026-09-11)

**The single highest-value fact in this section:** in Perspective, the
**View** and the **`root` container** are two *different objects*, and
**each has its own separate `custom` category.** A custom property added
to `root` is **not** reachable as `{view.custom.X}`, and vice versa.
Getting this backwards produces a bare `Error_ExpressionEval` with no
detail in the Designer's binding preview — the single most misleading
symptom in this whole area.

Carl Gould (Inductive Automation) states it directly on the forum: the
root container *"is actually the top of the component hierarchy"* while
*"the view is sort of special and not actually a component."* The docs
say the same structurally: *"Each view contains exactly one root level
container."* The View **contains** root; it is not root.

### The reference syntax, by where the property actually lives

| Property lives on | Reference it from a nested component as |
|---|---|
| The **View** (`params` category) | `{view.params.MyParam}` |
| The **View** (`custom` category) | `{view.custom.MyProp}` |
| The **`root` container** (`custom` category) | `{/root.custom.MyProp}` |
| A named child component | `{/root/Flex_0/Pump.custom.MyProp}` |

Note the shape of the root case: **`/root.custom.X`** — leading slash,
and **no second slash** before `custom`. `/root/custom.X` is wrong;
`custom` is a property category on root, not a child component. The
leading `/` is documented as an absolute path — *"a path that starts at
the top of the view hierarchy and is not relative to where the binding is
being configured."*

Forum confirmation for the root case, from a thread IA staff participated
in: *"the only way to reach properties on the root is to use an Absolute
path `/root.custom.prop1`."* Also established in that same thread:
**`parent.parent.parent` chaining does NOT work.** Multi-level traversal
is `../../../Name.custom.prop` or an absolute path — never dotted
`parent` chaining. Carl Gould's rationale: *"We didn't want to overload
the use of dot-dereferencing because that would have led to confusing
path parsing."*

### Diagnosing this in 10 seconds

Two reliable checks when a cross-component property reference errors:

1. **In the Designer's Project Browser**, click the **view node** (the
   top entry, named after the view) and read the Property Editor, then
   click the **`root`** node beneath it and read it again. They are two
   different property sets. Whichever one actually lists your property
   dictates the syntax per the table above.
2. **In the exported `view.json`**, a *View* custom property sits at the
   **top level**, as a sibling of `params` and `root`; a *root* custom
   property sits **inside** the `root` object:

```jsonc
{
  "custom": { "AnyFault": false },   // <-- VIEW custom  -> {view.custom.AnyFault}
  "params": { "Tag_Path": "" },
  "root": {
    "custom": { "AnyFault": false }, // <-- ROOT custom  -> {/root.custom.AnyFault}
    "type": "ia.container.flex"
  }
}
```

### Recommended pattern for "one computed boolean, whole view"

Put it on the **View's** `custom` category, not root's, and reference it
as `{view.custom.X}`. The docs endorse exactly this: *"Custom properties
can be defined for views. They act just like custom properties of a
component and are internal to the view, so they can be referenced by all
child components and containers in that view."* Two practical reasons to
prefer it over root:

- It survives someone restructuring or renaming containers under root.
- It reads identically to `view.params.*`, which is already the
  established idiom in a parameterized equipment template.

Root-custom + `{/root.custom.X}` is equally *valid* and is the right
choice when you don't want to re-author an existing binding — just be
deliberate about which one you picked, and don't mix the two spellings
for the same value.

### Worked example — the aggregate-fault pump template

Aggregate several alarm members into one boolean on the **View's**
`custom.AnyFault`, via an Expression binding:

```
tag(Concat({view.params.Tag_Path},"/FAIL_alm")) ||
tag(Concat({view.params.Tag_Path},"/DriveFault_alm")) ||
tag(Concat({view.params.Tag_Path},"/CURRENT_HiAlm"))
```

Then, on any nested component however deep — e.g.
`root > FlexContainer > FlexContainer_0 > Pump` (`ia.symbol.pump`), on
`props.state`:

```
if({view.custom.AnyFault},"faulted",
   if(tag(Concat({view.params.Tag_Path},"/Running_hwdi")),"running","stopped"))
```

This is a **chained binding** (a binding whose expression references a
property that is itself bound). That is supported and normal in
Perspective — Doug's own working
`if({view.params.Fault},…)` binding is the same shape. Chaining is *not*
the cause when this errors; a wrong scope keyword almost always is.

### Other causes of a bare `Error_ExpressionEval`

Ranked by how often they're the real culprit here:

1. **Wrong scope keyword / unresolvable property path** — by far the most
   common, and the one with the least helpful error text.
2. **A typo or case mismatch in the property name.** These paths are
   case-sensitive; `anyFault` ≠ `AnyFault`.
3. **`tag()` pointing at a path that doesn't resolve** — usually because
   the parameter feeding `Concat()` is empty at design time, or a member
   name is misspelled. Test by previewing just the
   `tag(Concat(...))` fragment alone.
4. **Type mismatch in `if()`** — a referenced property holding an
   Object/Dataset or `null` where a Boolean is expected.

**Free reliability win:** never hand-type these paths. The expression
binding editor has a **property-picker button** that inserts a
syntactically correct reference at the cursor, generated from the actual
view tree. It gets the `view.` vs `/root.` distinction right every time.

**8.1 vs 8.3:** no behavioral difference found. The View property
categories (`props`/`params`/`custom`), the one-root-container rule, and
the absolute-path operator are documented identically on both.

## Importing generated UDT definitions into Ignition Designer (verified 2026-09-07)

This is the receiving end of TASK_004 — the actual Designer steps for
getting a generated UDT definition JSON in. Written down because "Import
Tags" appearing greyed out cost real time mid-import on 2026-09-07.

**Use the Tag Browser toolbar, not the right-click menu.** The Tag
Browser's **More Options** menu (the hamburger / three-dots icon on the
Tag Browser toolbar) contains the Import and Export buttons, and that
path works in the UDT Definitions tab. The official docs describe both
routes — right-click a folder → `Import Tags > Direct`, *and* More
Options → Import Tags — but the context-menu route is the one that
intermittently comes up unavailable in the UDT Definitions tab. Reach
for the hamburger menu first and the problem never occurs.

**Why right-click → Import Tags shows greyed out.** Import is only
enabled when the selection is a **folder** (or the tag provider root).
A **UDT definition** is not a folder, even though in the UDT Definitions
tab it looks like one — it has an expand arrow and holds members. Select
a definition and you get the exact asymmetry seen on 2026-09-07: *Export
Tags* enabled (you can export a definition), *Import Tags* greyed out
(you cannot import *into* one). Confirmed by a forum thread on 8.1.27
where the fix was "select the folder it resides in, or the root."

Diagnostic order when Import is greyed out:
1. Is the selected node a UDT definition rather than a folder? Most
   likely cause. Click the parent folder — or just use the hamburger menu.
2. Is the Tag Provider Selector on **System** or **Client**? The Tag
   Browser's import/export tool does not work for System tags at all.
   **Confirmed in the field 2026-09-08** while importing MODVLV's UDT
   definition — the Provider Selector was the actual cause of a greyed-out
   Import that day, not a theoretical possibility. Check it early.
3. Does the provider allow editing? Tag provider **Tag Editing
   Permissions** (Gateway → Config → Tags → Realtime) gates edit/create/
   delete, a Standard provider has a **Read Only** checkbox, and a
   **Remote Tag Provider is read only by default** (Default Security
   Zone). Tell them apart in five seconds: if this is the cause, the
   toolbar **Add Tag** button is also unavailable and nothing in that
   provider can be created or renamed anywhere — not just here.

**Unrelated trap on the same operation — empty folders (IGN-2678).** An
import containing an **empty folder** fails with the misleading error
`Udt definitions can only be imported in the UDT Definitions tab`. The
message is wrong about the cause; the empty folder is the problem. Open
as a known bug since 8.1.5 (Jan 2022), still reproducing on 8.1.45 and
8.3.1. Worth knowing because generated JSON can easily carry an empty
folder — if that error appears while importing a TASK_004 output, check
for empty folders before believing the message.

## Replacing a UDT definition that already has instances (verified 2026-09-08)

Extends the import section above. That one covers *getting the JSON in*;
this covers *what happens to the existing instances* when the definition
they depend on is replaced — the regenerate-and-reimport loop TASK_004
creates every time a UDT is regenerated.

**The crux — two different binding mechanisms, and only one is by name.**

1. An instance finds its **definition by name**. The docs define the
   instance's `typeId` property as "The name of the UDT Definition this
   UDT is an instance of." There is no UUID or internal handle tying an
   instance to a *particular* definition object — just the type's name
   string. This is why structure changes reach instances at all, and why
   dropping a new definition in under the original name works.
2. An instance's **per-member overrides are keyed to member IDs**, not
   names. Inductive Automation staff, on the override-loss bug thread:
   overrides are "based on IDs of the members from the UDT Definition."
   Destroying the definition object destroys those IDs. A freshly
   imported definition carries new ones, and any override that pointed at
   an old ID is silently dropped.

**Consequence — rename-first and delete-first are NOT meaningfully
different for instance overrides.** Both destroy the name→definition
association and hand the instances a definition object they have never
seen. Renaming does not preserve overrides; it preserves a *copy of the
old definition* you can still look at. Do not treat the rename procedure
as the safe one and delete as the risky one — for overrides they are the
same operation with different cleanup. Rename's real and only advantages
are recoverability (the old definition is still there to diff or roll
back to) and that it is reversible mid-session; delete is not.

**Preferred procedure — replace in place, never delete or rename
first.** Import the new JSON straight over the existing definition of the
same name and set **Collision Policy = `MergeOverwrite`**, documented as
"Overwrites the tag with the exception of any properties that aren't
defined in the import folder. Those properties will be merged." The
definition object is never destroyed, so member IDs — and therefore
instance overrides — stay intact. This is strictly better than either of
the delete/rename variants and is the standing recommendation.

**⚠ Do NOT apply Doug's usual "zz delete" habit here (confirmed
2026-09-08).** Doug's normal practice elsewhere is to rename something to
a `zz delete ...` prefix before replacing it, as a safety margin. For a
UDT definition specifically, that habit is actively counterproductive:
renaming the old definition out of the way is the exact "rename-first"
procedure shown above to be no safer than deleting it outright. Every
future task that involves importing an updated UDT definition should
carry this reminder — overwrite the existing definition directly with
`MergeOverwrite`, don't rename or `zz delete` it first.

Two traps on that same operation:
- **`Overwrite` is not `MergeOverwrite`.** As of 8.1.8, `Overwrite`
  *completely* replaces a UDT definition, deleting any member not present
  in the import file. Regenerated JSON that is missing a hand-added
  member will silently remove it.
- **There is no selective-merge option for members.** Confirmed by staff
  on the forum — "keep existing members not included in the import file"
  is a feature request, not a setting. If the generated JSON must not be
  authoritative for the whole member list, the definition cannot be
  updated by import alone.

**⚠ Scope limit — `MergeOverwrite` is the right policy for THIS operation
only, not for every Ignition import (added 2026-09-09).** Everything above
is about replacing a **UDT definition that has live instances**, where the
risk being managed is destroying member IDs and losing per-instance
overrides. `MergeOverwrite` wins there precisely *because* it leaves
alone anything the import file doesn't mention.

That same property makes it the **wrong** choice when the goal is to
*remove* a property. `MergeOverwrite` treats a key absent from the import
file as "leave that property unchanged," so an import that deliberately
omits a key does not clear it — only plain `Overwrite` does. This matters
for TASK_010 (`fix_alarm_tags.py`), whose rule-9 fix works by removing
`sampleMode`/`historyMaxAge`/`historyMaxAgeUnits` from a plain alarm-tag
export: that file must be imported under **`Overwrite`**, and under
`MergeOverwrite` the removals silently do nothing. See
`PLCHelper_Tasks.md` TASK_010 for the full detail and sources — not
duplicated here (Lesson 9).

Rule of thumb: **changing or adding values → `MergeOverwrite` is safe;
removing a property or resetting one to its default → `Overwrite` is
required.**

**Where the config lives decides the exposure.** Read this before
worrying about override loss at all:
- Config set **on the definition** (History enabled on definition
  members, OPC Item Path templates on the definition) propagates to all
  instances automatically and is not at risk from any of this — but it
  *must be present in the regenerated JSON*, or the import removes it.
  That makes TASK_004's output completeness the real exposure, not the
  import procedure.
- Config **overridden per instance** is what the override-loss behavior
  destroys. UDT *parameter* values on instances survive; other tag
  property overrides do not.
- Practical rule: keep configuration on the definition wherever possible
  and treat per-instance overrides as fragile across any definition
  replacement. This also lines up with the History conventions earlier in
  this file, which are defined at the definition level.

**Pre-flight, every time (cheap, and the only real safety net).** Export
the current definition from the UDT Definitions tab *and* separately
export the instances — an instance export does **not** include the
definition, so one export is not a backup of both. For a production
gateway take a Gateway backup as well. There is no undo for a definition
replacement once instances have re-bound.

**Version notes.** Behavior above is 8.1.x. Override loss on
delete-and-re-add is long-standing and staff-described as intended
("always had that behavior"), reported from 8.1.0 through 8.1.25 and
observed as far back as 7.7.5 — do not expect a fix. Two version-specific
items: **8.1.6 had a critical UDT-import bug** triggered by exactly this
kind of `Overwrite`-policy definition modification (including JSON paste
into the Tag Browser, which uses Overwrite implicitly), fixed in
**8.1.7+** — historical only, but it is why Overwrite-policy definition
edits have a bad reputation. And **8.3.1 fixed** an issue where renaming
UDT instances or definition members "would flag existing values as
overrides on Memory tags" — so an 8.3 upgrade improves rename behavior
specifically, while the delete-and-re-add override loss is unchanged.

## Importing tag *instances* — `does not have item 'X' for overrides, and cannot accept children tags` (verified 2026-09-11)

Third entry in the import-troubleshooting run above. The first covers
*getting a definition JSON in*; the second covers *replacing a definition
that has instances*. This one is the **instance** side — TASK_005's
output, not TASK_004's — and it is a different failure with a different
cause, so do not reach for either of the answers above.

**The error.** Advanced Tag Import accepts the file, reports collisions,
then fails per target path with:

```
Bad_Unsupported("The target path '[default]<folder>/<TagName>' does not
have item 'EnableIn' for overrides, and cannot accept children tags.")
```

**What it actually means — and what it does not.** A `UdtInstance` node
can hold exactly two things: **parameter values**, and **overrides of
members its UDT definition already declares**. It cannot hold a child the
definition does not declare, because an instance is not a folder. The
message's two clauses map straight onto that: *"does not have item 'X'
for overrides"* = the definition declares no member named `X`; *"and
cannot accept children tags"* = and an instance can't take it as a new
child either. Decisive forum quote: **"Ignition doesn't support this at
all. You must change the definition to include more members... UDT
instances are not folders."** See `claude-workflow/TRUSTED_SOURCES.md`,
entry "Forum: `Bad_Unsupported(...does not have item 'X' for
overrides...)`", for the sources and the other reported forms.

**So it is a member-NAME mismatch between the import file and the UDT
definition.** Three things it is *not*, each ruled out rather than
assumed:

- **Not a Collision Policy problem.** No policy makes an instance accept
  an undeclared child. `Overwrite` vs `MergeOverwrite` changes what
  happens to properties that *do* resolve; it cannot conjure a member.
  `Ignore` only appears to help because it skips the colliding paths
  entirely — it imports nothing for them.
- **Not the `MergeOverwrite` guidance from the section above.** That
  guidance is scoped to **replacing a UDT definition that has live
  instances**. This is importing **instances** into a folder. Different
  operation, different failure; the two do not transfer.
- **Not a `--folder-mode flat` / `wrap` problem.** `flat` is correct and
  matches the shape of a real Ignition instance export. The error is
  raised *inside* a target tag, after the destination folder has already
  been resolved.

**Read the count correctly.** The error is reported **once per target
path**, and it names only the **first** offending child. "Error 1 of 9"
means nine target paths failed — not nine bad members, and not that the
other members are fine. Expect every undeclared member to be a problem.

**Diagnostic — one step, settles it.** Export the target type's
**definition** from the UDT Definitions tab and compare its member names
against the `name` values in the import file's per-instance `tags` array.
No overlap, or a missing name, is the whole answer. Do not start by
reading the tag at the failing path — the tag is usually fine; it is the
*definition behind it* that disagrees with the file.

**The structural trap this exposes, worth understanding once.** An
Ignition export of a UDT instance emits a **bare stub per member** —
`{"name": "...", "tagType": "AtomicTag"}` with no properties at all.
`generate_ignition_tags.py` mirrors that shape, taking the member names
from the **L5X AOI parameter list**. Those stubs carry **zero
information**: members are inherited from the definition, and a stub with
no properties overrides nothing. They are pure redundancy on a new
instance import — and they are the **only** part of the file that can
raise this error. Whenever the Ignition UDT was hand-built rather than
generated from the same L5X, the two name lists are free to disagree and
this is what it looks like.

**Fix, in order:**
1. Strip the per-instance `tags` array from the import file (or emit it
   empty). A `UdtInstance` object with just `name` / `tagType` / `typeId`
   / `parameters` is legal and imports cleanly on definition defaults.
2. Re-import. Use **`MergeOverwrite`**, not `Overwrite`, whenever the
   existing instances may carry parameter overrides the generated file
   does not mention — `Overwrite` is a complete overwrite of the tag and
   will drop them, and a generated blank `Description` will overwrite a
   hand-typed one under either policy.
3. Only if members genuinely need to exist on the instances, fix the
   **definition** (TASK_004 side) — never the instance file.

**Known live case: `INTERLOCK_AOI` (Blue Sky).** Confirmed 2026-09-11 by
reading Doug's own definition export. The real Ignition `INTERLOCK_AOI`
UDT (`tagType: UdtType`) declares **64 members** — `Interlock_00`..`_31`
and `Visibility_00`..`_31`, each an OPC tag bound per bit
(`...{InstanceName}.Interlocks.9`). The generated instance file declares
five — `EnableIn`, `EnableOut`, `Interlocks`, `Visibility`,
`OutputState`, straight from the L5X parameter list. **Zero overlap**, so
the import fails on the first of those five in document order,
`EnableIn`. Its top-level `parameters` (`DeviceName`, `Description`) are
correct and *do* exist on the definition. This is the manual bitfield
expansion already recorded in `BlueSky/BLUE_SKY_STATUS.md` (Open Work
Item 1, sub-item 5) and flagged in advance as watch-item 3 of
`PLCHelper_Tasks.md`'s "Fifth run — `INTERLOCK_AOI`" — the prediction was
right, and this is its confirmation.
