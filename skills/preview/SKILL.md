---
name: preview
description: Runs the review agents on a release-note draft (grounding, tenant isolation, and disclosure when the audience is external) for gate G7, then delivers the draft, the trace appendix, the held list and the run report to the tenant owner only for gate G8, and records the run as drafted. Every run, manual or scheduled, previews before anything can be sent. Use it when a draft has been humanised and needs checking and showing to the owner, when the owner asks to see the latest draft again, or when a scheduled run reaches its draft. Do not use it to send to recipients (send), to rewrite lines (draft, humanise), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Preview: checked, then shown to the owner only

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Input: tenant, run ID,
the humanised (or reverted) draft, the trace appendix, the held list, gate results so far. Review
dispatch: `references/review-dispatch.md`.

## Steps

1. **Review (G7).** Start, each in a fresh context with only the draft, its evidence records and the
   tenant config: `review/grounding`, `review/tenant-isolation`, and `review/disclosure` when audience
   is external. They report; they never fix.
2. Any review failure: status `held`. Show the findings to the owner with the draft; do not hide them.
3. **Deliver to the owner only (G8).** Include: banner, draft, trace appendix, held list, and the run
   report from `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/templates/run-report.md`.
   - Owner present in the session: show it here. Nothing is mailed.
   - Owner not present (scheduled run): call rn-harness `prepare_preview(tenant, run_id, subject,
     body)` with the subject prefixed `[DRAFT · needs your approval]` and the exact preview text as
     body, then send it through the tenant's delivery connector to the owner only
     (`owner.previewTo`, default `owner.email`). The PreToolUse hook allows a preview only to the
     owner and only with that body. Then `record_send` with the read-back (no window needed).
4. `record_gates(tenant, run_id, gates, preview_delivered=true)` with G0–G8 as PASS, FAIL,
   NOT CHECKED (or REVERTED for G6). `send` cannot proceed without it.
5. Write ledger rows: drafted items with status `drafted`, held items with status `held`,
   excluded and out-of-window items with status `dropped` (`ledger_append`). Then `run_log_append`
   with status `drafted` (or `held`), the model, `sources` (each with status, fetched and
   reported total) and `held_count`.
6. End the turn by asking the owner to approve this exact draft or say what to change.

## Rules

- The preview goes to the owner only. Never to recipients, never cc.
- Show NOT CHECKED gates as NOT CHECKED.
- If the owner edits lines, count them (`edits`) for the run log; an edit changes the run hash, so the
  next approval covers the edited draft.
