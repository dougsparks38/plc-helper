# AOI Library

Client-neutral copies of Add-On Instructions (Studio 5000 L5X exports).
Only the latest version of each AOI is kept here; git keeps the history.

Library files are client-neutral by default: free of client, site, project
and person names (including controller names and the CreatedBy/EditedBy user
names in the L5X), and passed through the PII scan (Rule 36) before any push.
Exceptions are Doug's decision, where public customer information is left in
on purpose; they are marked in the table below.

| File | Revision | Description |
|------|----------|-------------|
| `MODVLV_AOI.L5X` | 1.0 | Modulating valve AOI: analog or limit-switch position feedback (config_type), ON/OFF or modulating (config_binary), fail-to-open/close alarms. Exact copy of a tested export; customer and site information left in on purpose (Doug: public information). |
| `MODVLV_SIM.L5X` | 1.0 | Simulator for MODVLV_AOI: simulated analog position ramp and limit-switch outputs with 60 s travel. Exact copy of a tested export; customer and site information left in on purpose (Doug: public information). |
| `VARSPD2_AOI.L5X` | 2.2 | Motor/drive control AOI with run and enable logic, alarms, runtime hours and HOA/motor status values; its speed parameters are placeholders only. |

Naming and ordering conventions for AOIs: see the "AOI conventions" section
of PLCHelper's `CLAUDE.md`.
