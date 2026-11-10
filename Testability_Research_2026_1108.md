# Designing Logix programs for testability - research, 2026-11-08

Situation: ControlLogix/CompactLogix 5069-L320ER, Studio 5000 v38, ladder. Tested by Doug in Studio 5000 with I/O inhibited. Test-only routines (one step per scan, ZZ_ tags, ZZ pass-bit array). Pain: 60 s simulated valve travel, 60 s and 5-60 s timers, many states.

Source declaration (Lesson 11): Rockwell product and help pages were reachable only as search snippets (rockwellautomation.com returned HTTP 403 to fetch, so no Rockwell PDF was read in full). Everything marked "Doug-fit design" below is engineering practice from training knowledge plus lower-trust community material, not a Rockwell recommendation. **I found no official Rockwell document that tells programmers how to structure code for testability** (no style-guide section on test hooks, scalable presets or simulators). Rockwell does document the tools in section 5.

## Recommendations, ranked by value for Doug's workflow

1. **Timer presets in one config array, with a test scale factor.**
   Why: this removes the 60 s waits, the largest cost in every state-machine test.
   How: one UDT/array tag `Cfg_Tmr[n]` (DINT ms) holds every preset; each TON is preceded by a MUL/DIV rung `Cfg_Tmr[n] * Tmr_Scale / 100 -> Tmr_xxx.PRE` (or `MOV Cfg_Tmr[n] -> .PRE` when scale = 100). Tmr_Scale is a DINT percent, default 100, written only by the ZZ test routine (e.g. 2 = 50x faster). Never hard-code a preset in the timer instruction. Keep the unscaled values in Cfg_Tmr so "restore" is just writing Tmr_Scale back to 100 (never edit Cfg_Tmr itself).

2. **Simulated device with a speed parameter and an instant mode.**
   Why: a 60 s valve stroke is the other big wait; the sim must follow the same scale as the timers.
   How: each sim valve takes `Sim_TravelTime` (ms) from the config array and runs through the same scale (`Sim_TravelTime * Tmr_Scale / 100`); `Sim_Instant` = 1 makes the limit switches follow the command on the next scan (OTE open limit from the command bit). Keep the sim in its own ZZ-prefixed routine so deleting the routine and its JSR removes all of it.

3. **Fault injection bits per simulated device.**
   Why: transitions to fault/alarm states are untestable otherwise, and they are the ones most likely to be wrong.
   How: `ZZ_Valve1_FailOpen`, `_FailClose`, `_StuckMid`, `_NoFeedback` bits; each gates the sim's limit-switch rungs (XIO fail bit in series with the limit-switch OTE). The test routine sets a bit, steps until the program's travel-timeout alarm fires, checks the pass bit, clears the bit.

4. **Single test-mode bit and one set of override points, written in a fixed place in scan order.**
   Why: keeps all test writes in one routine, so nothing else in the program is "test aware" except a few clearly marked rungs.
   *Superseded 2026-11-10: the fixed "test first, sim last" placement below is replaced by item 5 of "Designing for testability" in `CLAUDE.md`.*
   How: `ZZ_TestMode` BOOL. Run the ZZ test routine FIRST in the main routine (before the logic under test) when it writes inputs, and the sim routine LAST (after the logic, so it reacts to commands from the same scan). Where a real input is read in ladder, read it through a mapped tag (alias or MOV from the I/O tag) so the test can substitute: `XIC(ZZ_TestMode) MOV ZZ_x -> Pump1_Run_FB`, `XIO(ZZ_TestMode) MOV Local:3:I.Data.0 -> Pump1_Run_FB`. With inhibited I/O the hardware input tags are inert, so writing mapped (non-I/O) tags is cleaner than forcing.

5. **State machines: one transition per scan, state number in an observable tag, no work done in the transition rung.**
   Why: the test routine can single-step, assert on `State` and `State_Prev` each scan, and detect an unintended jump.
   How: `State` (DINT) set by MOV in the transition rung gated by a one-shot (ONS) so only one transition fires per scan; transitions test the current state with EQU, never stack. Mirror state and step-timer accumulators into plainly named tags (`Seq_State`, `Seq_Tmr.ACC`). Do not write `State` directly from the test; drive the inputs, or use one named `ZZ_ForceState` rung during development only.

6. **Test routine as its own step-sequencer, pass bits in one ZZ array (already Doug's pattern).**
   Why: it is repeatable and visible; one array shows pass/fail at a glance in a Studio 5000 watch window.
   How: `ZZ_Step` DINT; one step per scan; each step is EQU(ZZ_Step, n) -> set stimulus, wait for condition or a ZZ timeout, compare result -> set `ZZ_Pass[n]`, advance. Add a `ZZ_Timeout` timer per step that sets `ZZ_Fail[n]` so a stuck test never hangs. Add `ZZ_Run`, `ZZ_Done`, `ZZ_AllPass` (a COP/loop, or a compare of the array to expected). Leave test timers on their own unscaled preset (they are wall-clock; the program under test is what is scaled). *Added 2026-11-10: the tag names here are illustrative; for how test tags are named see item 10 of "Designing for testability" in `CLAUDE.md`.*

7. **A safe-restore and "test code left in" guard.**
   Why: the worst failure is shipping with Tmr_Scale not at 100, Sim_Instant on, or ZZ rungs enabled.
   How: put Tmr_Scale, Sim_Instant, ZZ_TestMode in one tag UDT so a single watch shows everything; add a rung `ZZ_TestMode OR Tmr_Scale<>100 -> TestActive_Alm`, shown on the HMI. Final release step: a Studio 5000 search (Find All) for `ZZ_` returns nothing outside the test routine, and the JSR to the test routine is removed or its rung disabled (by Doug). Initialise Tmr_Scale to 100 in the tag's default value so a fresh download is safe.

8. **Small unit routines with their own inputs/outputs, so each can be tested on its own.**
   Why: a routine that only reads its own tags and writes its own tags can be exercised without running the rest of the program.
   How: AOI per device (as with ModValve) with config values as Visible parameters (already your standing rule); give the AOI a built-in `Sim_` input for test if the AOI owns timing (e.g. `Test_Scale`), or keep timers in the config array and pass the scaled preset in.

9. **Use Echo for full-cycle runs if licence allows (see section 5).**
   Why: Echo emulates the controller on a PC, so tests do not touch the physical controller and presets can still be scaled the same way; its slow-down/pause/reset-to-point features and snapshots fit state-machine testing.
   How: only worth adding if Casne already licenses Echo; it replaces nothing above.

## 5. What Rockwell's own tools offer (and fit with inhibited I/O)

- **FactoryTalk Logix Echo** (official, medium confidence on details from the product page and snippet only): emulates ControlLogix 5580/5590, GuardLogix 5580, CompactLogix 5380 (the 5069-L3xx family) and Compact GuardLogix 5380 on a PC. Rockwell's Getting Results guide says a project at v33 or later needs no modification to run on 5580/5380 emulated controllers. Version 3 is described as able to pause or slow time and reset to a point, and to take and restore snapshots; it connects to Emulate3D for a mechanical model. Limitations from the Getting Results guide as snippeted: remove License-Based Source Protection first; Echo and FactoryTalk Linx both use port 44818, so Linx's "listen on EtherNet/IP encapsulation ports" must be disabled. Needs a separate licence and a feature-compatible Logix Designer (30-day trial exists). I could not confirm from an official page how it presents I/O modules for stimulus; it needs checking in the Echo user manual.
- **Studio 5000 Logix Emulate** (official): older emulator, listed by Rockwell as the predecessor; I could not confirm it supports 5069 (5380) controllers; the comparison page "Echo versus Logix Emulate" is on Rockwell's support site and was not readable here.
- **Force** (official, the Logix Designer help page for Force describes it as overriding an I/O module's values in the controller). From training knowledge, to be confirmed in 1756-PM004/Logix Designer help: forces need the controller online, apply to I/O tags (not ordinary tags), and must be enabled with Enable All I/O Forces. Third-party posts (low trust) say forces on input tags can be overwritten if logic writes the tag, and are overwritten by the RPI update unless the module is inhibited. For your inhibited-I/O workflow the dependable method is writing a mapped (non-I/O) tag, which needs no force.
- **Compare** (Logix Designer Tools > Compare): offline project-vs-project compare. Useful to prove that test-only changes are gone before release: compare the release project with the last-known-good file. The only descriptions found were third-party (low trust); no Rockwell page located.
- **Test Edits / Test Accepted Program Edits** (official Logix Designer help): online-edit stage where edited logic runs in Test state before Assemble. Not a test framework; relevant only when changing logic while the controller is running. Rockwell's Logix Designer 38.01 note (already in LESSONS_AND_RULES) applies to multi-rung online edits.
- **Trends**: Logix Designer's built-in trend (tag-based, runs while online) is a good way to plot Seq_State, valve position and timer ACC during a long test. I found no Rockwell page on it in this research (training knowledge).
- **Rockwell testing/commissioning guidance**: none found. 1756-RM094 (Logix 5000 Controllers Design Considerations) exists at literature.rockwellautomation.com but the PDF returned 403 and no snippet touched testing. PlantPAx documentation showed no test-hook conventions. Nothing found stating a Rockwell-recommended test-mode or timer-scale pattern.

## 6. Pitfalls

- **Force vs write:** a force overrides the I/O value every scan and survives program writes; a written value is overwritten by the next logic rung or input update. Use writes on mapped tags; use forces only on real I/O tags and remove them after (check Controller Properties and the force-enabled LED).
- **Scan order:** a test write placed after the logic under test is seen one scan late; a sim placed before the logic makes feedback arrive instantly. Decide the order once (tests first, sim last) and keep it. Do not let two routines write the same tag (OTE twice). *Superseded 2026-11-10: for placement see item 5 of "Designing for testability" in `CLAUDE.md`.*
- **Test code or short presets left in:** see recommendation 7. Never edit a preset in place to shorten it; scale it.
- **Unscaled test timers:** if the test routine's own timeouts are scaled with the program's, a fast test will time out the wrong way. Keep test timeouts on real time.
- **HMI/SCADA exposure:** keep ZZ_ tags out of any HMI/Ignition tag import and do not expose Tmr_Scale/ZZ_TestMode to operators (Ignition imports and tag-based writes: make sure the tag provider only imports named tags). Add the TestActive alarm so a left-on test mode is visible.
- **Retentive state:** with a scaled timer, a restore to 100 while a timer is running can leave the ACC above the new PRE; the timer then completes immediately. Restore only with the state machine idle (and reset the state machine after).
- **One-shot test steps:** a test step that relies on ONS misses if the step is held across a scan; use state latches for the ZZ_Step advance.
- **Inhibited I/O:** with modules inhibited, I/O tags read as zero and faults are suppressed, so I/O fault and "module comm loss" logic (GSV tests) cannot be exercised that way; test those separately.

## Proposed standing practices (rules PLCHelper could adopt)

1. Every timer preset in generated or edited ladder comes from a config array/tag, never a literal in the instruction; the rung that loads .PRE applies `Tmr_Scale`.
2. Every program with a state machine ships with `Tmr_Scale` (default 100), `ZZ_TestMode` and a `TestActive` alarm bit.
3. Every simulator routine is ZZ-prefixed and has a speed parameter and an instant mode; every simulated device has fail bits.
4. State machines make one transition per scan and expose the state number in a plain DINT tag.
5. Test inputs go through mapped tags, never forces; tests run first in the main routine, simulators last. *Superseded 2026-11-10: placement is worked out per test; see item 5 of "Designing for testability" in `CLAUDE.md`.*
6. Test routines write pass/fail bits in one ZZ array with a per-step timeout on real time.
7. Before release: Find All `ZZ_` and `Tmr_Scale` outside the test routine, confirm Tmr_Scale = 100, remove the JSR to the test routine (Doug does the removal).
8. Design for testability is part of the build request: the plan for any new state machine states the test hooks (scale tag, sim, fail bits, observable state) before the code is written.

## Sources and trust

Official Rockwell (highest trust; read as search snippets only, 403 on fetch):
- FactoryTalk Logix Echo product page: https://www.rockwellautomation.com/en-us/products/software/factorytalk/designsuite/logix-echo.html
- Echo 3.0 blog: https://www.rockwellautomation.com/en-us/company/news/blogs/factorytalk-logix-echo-30.html
- FactoryTalk Logix Echo Getting Results Guide, 9310-GR001: https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/9310-gr001_-en-p.pdf
- Studio 5000 Logix Emulate page: https://www.rockwellautomation.com/en-us/products/software/factorytalk/designsuite/studio-5000/studio-5000-logix-emulate.html
- Logix Designer v37 help, Force: https://rockwellautomation.com/en-se/docs/studio-5000-logix-designer/37-00/contents-ditamap/studio-5000-logix-designer/force.html
- Logix Designer v37 help, Test Accepted Program/Phase Edits: https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-00/contents-ditamap/studio-5000-logix-designer/navigating-the-application/-product_name_rsl5k--application-main-window/-product_name_rsl5k--application-commands/test-accepted-program-phase-edits-command.html
- 1756-RM094 Design Considerations (exists; no testing content seen): https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1756-rm094_-en-p.pdf
- 1756-PM004 I/O and Tag Data (candidate for the force rules, not read): https://literature.rockwellautomation.com/idc/groups/literature/documents/pm/1756-pm004_-en-p.pdf

Lower trust (vendor or third-party blogs and forums; support only):
- industrialmonitordirect.com knowledgebase (Compare tool, forcing, test-bit and sim-mode posts): conflicting posts, lowest trust.
- DMC Inc. Logix Echo case study (mentioned only): https://www.dmcinfo.com/our-work/advanced-process-control-using-rockwell-plantpax-processors-and-factorytalk-suite/
- ESE Co. Echo v3 blog (integrator): https://ese-co.com/blog/revolutionize-design-and-testing-with-factorytalk-logix-echo-v3
- MrPLC thread "How do you test PLC logic": https://mrplc.com/forums/topic/38992-how-do-you-test-plc-logic/ (forum, snippet only)

Question for Doug: which official Rockwell sources do you want logged in claude-workflow\TRUSTED_SOURCES.md (candidates: Logix Echo page, Echo Getting Results Guide 9310-GR001, Logix Designer Force help, 1756-PM004)? I have not edited that file.
