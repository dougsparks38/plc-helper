# PLCHelper — Executive Summary
*Prepared 2026-09-10 by Doug Sparks — personal reference for a phone update, not a formal report*

The idea behind PLCHelper: an AI agent that helps with the repetitive, error-prone parts of PLC/Ignition programming — the kind of work that's necessary but eats hours and is easy to get subtly wrong by hand. Here's where it actually stands.

## Working today

- **Generating Ignition tag definitions straight from PLC code.** Given an exported PLC program and one AOI (or native UDT) type, it automatically builds the matching Ignition UDT definition — every parameter, correct history settings, no manual re-typing. Already used for real client work (Blue Sky).
- **Finding and fixing alarm configuration problems automatically.** Built this week for a CPKCR client site (Weston): a tool audits every alarm tag in a site's export against 9 correctness rules and flags every problem; a companion tool applies the fix and produces a clean, ready-to-import file. First real run found 367 separate configuration problems across 143 alarm tags at one site — the kind of thing that would take hours to catch by hand, one alarm at a time. Both tools work against any site's export, not just the one they were built for.

## Spec'd, not yet built

- **A full PLC code audit** — cross-checking the IO list, the PLC's own tag database, and the actual ladder logic against each other to catch mismatches.
- **A rung-comment quality pass** — finding every unresolved "flag this later" comment and every filled-in instrument-scaling comment, and checking each one against the real instrument list.

## Ideas for later

- Auto-generating the individual Ignition tag *instances* that go with an already-built UDT definition, instead of building each by hand.
- The reverse check — finding Ignition tags that don't actually correspond to anything in the current PLC program anymore, so they can be cleaned up.
- Handling client-specific naming/config conventions in bulk instead of one field at a time.

## Bottom line

Two of the biggest wins so far both replace genuinely tedious, error-prone manual work — tag generation and alarm auditing — with something that runs in minutes and catches things a person would likely miss. Everything above is real, working tooling already used on live client jobs, not a prototype.
