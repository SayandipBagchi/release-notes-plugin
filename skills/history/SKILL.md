---
name: history
description: Manages a release-notes tenant's record over time - reads the release ledger and run log to list past notes, carries pending items forward until they are released, prepares versioned corrections for a sent window, runs owner-only backfills of past windows, and decides earned auto-send (offered only after the configured number of consecutive approved runs with no owner edits, switched on only by the owner, revoked on any edit or gate failure). Use it when someone asks what was sent before, what is still pending, to correct a past note, to backfill history, or whether auto-send can be turned on. Do not use it to draft or send this window (draft, send), to change tenant settings other than auto-send (tenant-onboard), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# History: the ledger, carry-over and earned trust

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Ledger columns:
`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/references/ledger-schema.md`. Auto-send rules:
`references/carry-over.md`.

## Jobs

| Ask | Do |
|---|---|
| What was sent before? | Read `release-ledger.csv` and `runs/run_log.jsonl`; list windows, message IDs, counts |
| What is still pending? | `ledger_carry_over(tenant)`; list with the window first reported |
| Correct a sent note | Prepare a `v2` run for the same window; it goes through draft, preview and send like any run |
| Backfill | Run past windows oldest first through the router, owner-only previews, never to recipients |
| Can we auto-send? | `clean_run_count(tenant)` against `autoSend.earnedAfterCleanRuns` |

## Earned auto-send

1. Offer it only when `clean_run_count` is at least `earnedAfterCleanRuns` (default 3).
2. The owner switches it on in their own words; record them in `revisions.md` and set
   `autoSend.enabled: true` through `tenant-onboard`. `validate_tenant` rejects it otherwise.
3. While on: a scheduled run that passes every gate with no NOT CHECKED may send without the owner's
   message; the owner is told after, with the message ID.
4. Revoked automatically by any owner edit to a sent note, any gate failure, any hook denial or any
   read-back mismatch: set `enabled: false` and tell the owner.
