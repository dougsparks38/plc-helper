# Ignition Data Storage Tips

General lessons from investigating a stored-value problem in Ignition
daily/monthly data storage at a rail client. All client, site, tag and
device detail has been removed; the patterns are described in general
terms so they apply anywhere.

Labels used below:

- **CONFIRMED** — seen directly in the exported Ignition files or checked
  live during the investigation.
- **INFERENCE / THEORY** — reasoning that fits the evidence but was not
  proven.

Added 2026-10-05.

---

## 1. Current and "Last" transactions, and mixed clocks

- **CONFIRMED.** Daily and monthly storage is often split into four
  transactions in one transaction group: a current daily, a "Last" daily
  (yesterday), a current monthly, and a "Last" monthly (last month).
- **CONFIRMED.** One transaction group can mix two clocks for its row key
  (the row index and year):
  - some transactions build the key from **PLC date tags** read over OPC;
  - others build it from **Ignition expressions on the gateway clock**
    (`now()`, e.g. `getYear(addDays(now(), -1))` for the year of yesterday's
    date).
- In the case investigated, the "Last" daily transaction used gateway time
  and the other three used PLC time. This was true at **both** sites
  compared, so the mix on its own did not explain why only one site had
  the problem.

## 2. Server and PLC time zones

- **CONFIRMED.** The Ignition gateway was in a different time zone from the
  PLCs (one hour apart). No time sync ran between Ignition and the PLCs.
- **CONFIRMED.** The PLC clocks themselves matched real time to within a
  few seconds, so clock drift was ruled out.
- **INFERENCE.** When a transaction keyed on gateway time sits next to one
  keyed on PLC time, the two roll over to a new day and a new month at
  different moments (an hour apart here). Any logic that assumes both
  sides change date together can write into the wrong row in that window.
- Check the gateway's configured time zone directly; do not assume it
  from where the server is located.

## 3. Duplicate, similarly named tag folders

- **CONFIRMED.** Over time people create near-duplicate tag folders, such
  as a folder name and the same name with a "2" added. Both can be in live
  use **by the same transaction group at the same time** (for example the
  current transactions reading one folder and the "Last" transactions
  reading the other).
- **CONFIRMED.** Item labels in a transaction group can disagree with the
  tag path the item actually points to (a label naming one folder or tag,
  the real path pointing somewhere else). The item's path is what runs;
  the label is not.
- Before changing or comparing anything, open each item and check which
  folder and tag it really reads.

## 4. Tag event script that picks the month for "yesterday"

- **CONFIRMED (at both sites, identical script).** A tag event script on a
  "last day" tag set the month for the "yesterday" data instances. It chose
  the month by testing whether **the previous day = 1**, rather than
  whether **today is the 1st**.
- **INFERENCE.** On the 1st of the month the previous day is the last day
  of the prior month, so the script takes the "current month" tag. If that
  tag has already rolled to the new month, yesterday's values are pointed
  at the wrong month (e.g. new month with last month's final day).
- **CONFIRMED.** A separate expression tag that tests "today = 1" existed
  in the project but nothing used it. Look for an unused correct version
  before writing a new one.
- **CONFIRMED.** The script rewrote the data instances' configuration
  (separately for day and month). **INFERENCE:** a transaction that fires
  during that rewrite may read an unsettled value.

## 5. Differences to check between sites with "the same" setup

Two sites built from the same template still differed in these settings.
All **CONFIRMED** from the exports:

- **Auto-insert row** — off for both monthly transactions at one site, on
  at the other. With it off, a missing row is never created.
- **Tag group** — the PLC date tags (last day, last month, current month)
  were scanned in different tag groups at each site. At the problem site
  the "last day" and "current month" tags shared one group; at the other
  they were in different groups. **INFERENCE:** that changes the order in
  which the values arrive at rollover, which matters to the script in
  section 4.
- **Trigger tag** — the "Last" daily transaction used a different trigger
  tag (and different handshake settings) at each site.
- **Other group options** — execution flags and "store timestamp" differed.
- **Export age** — several exports were years old. **Not confirmed** that
  the live gateway still matched them; re-export before relying on an old
  copy.

## 6. A stored zero in a minimum column after a rollover

**INFERENCE / THEORY — not confirmed.**

- Symptom: a minimum column stored 0 for each month while the matching
  maximum and average looked normal.
- The PLC value feeding it was checked and nothing in the PLC set it to
  zero (CONFIRMED).
- Working theory 1 (midnight race): the gateway polls the PLC every few
  seconds. Right after midnight there may be a short window where Ignition
  has the new date but has not yet read new data, so a null or zero gets
  stored. Once the real values arrive, the stored zero remains the lowest
  value of the period.
- Working theory 2: a PLC running minimum that restarts at 0 on a reset.
  Max and average recover as soon as real values arrive; a minimum does
  not. A minimum column is therefore where a rollover glitch shows first.
- CONFIRMED wiring that makes this possible: a monthly "Last" transaction
  that fires on the month change and writes the **current day's** value
  into **last month's** row. Check whether monthly transactions read daily
  tags instead of monthly ones.

## 7. How to compare two sites

1. Export each site's transaction groups and the relevant tag folders.
2. For every date, year and row-key item, trace it to its real source:
   - OPC read from the PLC, or
   - an Ignition expression on gateway time.
3. Follow the item's actual tag path, not its label or the folder name it
   seems to belong to.
4. Open the tag definition itself (OPC item path, expression, tag group,
   event scripts) rather than trusting the transaction view.
5. Check the UDT definition too, if data members are built from
   parameters such as month and day. Without it, which PLC slot a member
   reads is only an inference.
6. Find the database rows around the first of a month (and the last day
   of the previous month) to see which row holds the bad value, and
   whether it is 0 or null.
7. Separate what you saw (CONFIRMED) from what you reason (INFERENCE) in
   the write-up. In this case two early assumptions were contradicted by
   the files once traced.
8. Back up the transaction group (export it) before changing anything.

## 8. Check the client's other sites

- **CONFIRMED.** The same transaction group layout, tag folder structure
  and event script were found at more than one of the client's sites.
- When this problem appears at one site, check the others built from the
  same template, even if nobody has reported it there yet.
