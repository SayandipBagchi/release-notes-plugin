# Review dispatch

Author: Sayandip Bagchi.

| Agent | Runs when | Gets | Fails on |
|---|---|---|---|
| `review/grounding` | every run | draft, line map, evidence records, tenant release definition | uncited line; citation that does not support its line; T2 or T3 under Released; invented date, version, number or name; claim words with no evidence |
| `review/tenant-isolation` | every run | draft, trace appendix, `map_tenant` results, tenant config | any item or evidence mapped to another tenant or held; any recipient or address not in config; any other tenant's name or term |
| `review/disclosure` | audience external | draft, tenant config | security or CVE item; internal link; internal person's name; other customer's name; PII; Mentioned block present |
| `review/send-gate` | at send time (send skill) | run hash, approval record, pending send, config | see the send skill |

Each agent returns `PASS` or `FAIL` with findings as `line · rule · why`, quoting at most 15 words of
the line. Reviewers never edit the draft and never see the drafting reasoning.

If an agent cannot run (no subagents on the host), the review runs in the same context and the run
report labels G7 "same-context review".
