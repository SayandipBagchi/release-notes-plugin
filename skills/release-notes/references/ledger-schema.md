# Release ledger schema

Author: Sayandip Bagchi.

`tenants/<name>/release-ledger.csv` holds one row per item per window per run. It is written only
through rn-harness `ledger_append` and read by `history`, `draft` (carry-over) and `trace`.

| Column | Meaning |
|---|---|
| `window_start`, `window_end` | ISO timestamps in the tenant timezone; end exclusive |
| `run_id` | `<tenant>-<yyyymmdd>-<n>` |
| `item_key` | ticket key, or `<source>:<native id>` for items without one |
| `title` | short title as drafted (no PII) |
| `tier` | T1, T2, T3 or none |
| `section` | released, pending, mentioned, excluded, out_of_window |
| `status` | drafted, sent, held, dropped, carried |
| `evidence_ids` | `;`-separated evidence IDs |
| `message_id` | delivery message ID once sent |
| `carried_from` | window_start of the window the item was first reported as pending |

## Carry-over

`ledger_carry_over` returns items reported as `pending` in the last sent window that have no later
`released` row with status `sent` (a drafted or held run does not clear an item). `draft` lists them first in their section; when T1 evidence arrives they move to
Released with the note "previously reported as pending".

## Run log

`tenants/<name>/runs/run_log.jsonl` holds one record per run: run ID, status, model, window, sources
with counts and completeness, held count, approver, recipients count, message ID, and `edits` (lines
the owner changed before approving). `clean_run_count` reads it for auto-send eligibility.
