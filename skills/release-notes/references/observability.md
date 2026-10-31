# Observability

Author: Sayandip Bagchi.

## Layer 1 · Watching the notes

| Signal | Source | Watch for |
|---|---|---|
| Items per window by section | release ledger | sudden drop to zero (source broken, not a quiet week) |
| Held items per run | run log | rising share means mapping rules have drifted |
| T3 share | release ledger | a rising share means comms are carrying news the tracker misses |
| Carry-over age | release ledger | items pending for 3+ windows: ask the owner whether they shipped |

### Triangulation

Each Released line should be supported by two independent signals where the tenant has them: a
tracker status and a deploy or fixVersion record. A Released item with only one is fine under the
tenant definition but is flagged in the trace appendix as single-source.

### Drift

Compare this window's sources and counts with the last three. A source whose count falls by more than
80% with no change in config is reported as possible drift in the run report.

## Layer 2 · Watching the agent

| Signal | Source | Watch for |
|---|---|---|
| Gate failures by gate | run log | repeated G3: connector or Chrome reader broken; repeated G5: template mismatch |
| Owner edit rate | run log `edits` | above 15% of lines means voice or template rules need work |
| Hook denials | hook stderr, run report | any denial is reported to the owner |
| Injection flags | run report | patterns per source |
| Model per run | run log | any run below Opus is a defect |
