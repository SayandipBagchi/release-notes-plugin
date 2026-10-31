# Run protocol

Author: Sayandip Bagchi.

## Standard run

1. **Router:** G0 model, G1 tenant (`validate_tenant`), G2 window (`resolve_window`). Create a run ID:
   `<tenant>-<window start yyyymmdd>-<n>` and call `run_start(tenant, run_id)`. While a run is active
   the PreToolUse send gate enforces on every outbound tool; outside a run it stays out of the way.
2. **collect:** one `source-puller` agent per configured source, in parallel. Each returns evidence
   records and counts; `evidence_put` stores them; `completeness_check` per source (G3).
3. **reconcile:** `extract_ticket_keys` on comms excerpts to join them to tickets; dedupe by key;
   `map_tenant` per item; `tier_item` per item (G4). Held items go to the held list.
4. **draft:** fill the tenant template from the tiered items, one line per item, each with evidence
   IDs; `citation_resolve` (G5). Carry-over items from `ledger_carry_over` go first in their section.
5. **humanise:** `entity_ledger` before, rewrite with the tenant voice, `entity_diff` after (G6).
6. **preview:** review agents (G7), then deliver the draft, trace appendix, held list and run report
   to the owner only (G8). `record_gates`. Ledger rows: `drafted`, `held` or `dropped`.
   `run_log_append` status `drafted` with sources and counts and `held_count`.
7. **send** (after approval only): `hash_run`, `approval_issue`, review/send-gate, `prepare_send`
   with the approved body, deliver through the tenant connector (the hook allows one call), read back,
   `record_send`, ledger rows status `sent`, `run_log_append` status `sent` with `edits` = lines the
   owner changed.
8. **End:** `run_end(tenant, run_id)` when the run reaches `sent`, `held` or `failed:*`, or when the
   owner closes it. A run left at `drafted` keeps its marker until approval or its 12-hour expiry.

## Corrections

A window already sent is never re-sent. If the owner wants to fix it, the send skill issues a
**correction**: version `v2` (then `v3`), subject prefixed "Correction:", a one-line note of what
changed at the top, same recipients unless the owner changes them in config first.

## Backfill

For a first-time history, `tenant-onboard` or `history` runs past windows in order, owner-only
delivery, never to recipients. Each window still passes G0–G8.

## Scheduled runs

A scheduled run executes steps 1–6 and stops. It notifies the owner that a draft is ready. Send
happens only when the owner opens the session and approves. The one exception is earned auto-send
(see `history`): when the tenant config has it enabled and every gate passed with no NOT CHECKED,
the run continues to step 7 with the auto-send quote, which the harness refuses unless the tenant has
earned it. Any gate failure or owner edit revokes it.

## Session hygiene

- Read `config.json` first and only the tenant files the step needs.
- Do not paste raw source bodies into chat; cite excerpts.
- After 8 prompts, offer a new session; end with the capsule.
