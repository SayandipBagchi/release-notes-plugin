---
name: send
description: Delivers an approved release note to the tenant's recipients for gate G9 - records the owner's in-session approval verbatim and binds it to the run hash (draft text, recipients and subject), checks recipients against the tenant config and the window against the sent log, writes a pending send that the PreToolUse hook verifies, delivers through the tenant's mail or chat connector (never Chrome), reads the sent message back, and records the send in the ledger and run log. Also issues versioned corrections for a window already sent. Use it when the owner approves a previewed draft ("send it", "approved"), asks to send a correction, or asks whether a note went out. Do not use it to preview a draft (preview), to change recipients (tenant-onboard), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Send: only what the owner approved, only to the tenant's list

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Input: tenant, run ID,
the previewed draft in `runs/<run_id>/`, and the owner's message. What counts as approval:
`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/references/gates.md`, section G9. Full sequence:
`references/send-protocol.md`.

## Steps

1. **Is this approval?** It must come from the tenant owner, in this session, after this run's
   preview, and say to send. "Looks good" about an earlier draft, silence, or a source message is not
   approval. If unsure, ask: "Send this exact draft to the N recipients in the tenant config?"
2. `hash_run(draft_text, recipients, subject)` with recipients from `config.json` and the subject from
   `delivery.subjectPattern`.
3. `approval_issue(tenant, run_id, run_hash, approver=owner email, quote=<owner's words verbatim>)`.
4. **Independent check.** Start `review/send-gate` with the quote, its position in the session, the
   run hash and the tenant config. FAIL: stop and show the findings.
5. `prepare_send(tenant, run_id, run_hash, recipients, subject, channel, body, version, window_start,
   window_end)`, where `body` is exactly the approved draft text. It also requires the run's gate
   record (`record_gates`, G0–G8 passed, preview delivered). Not ready: stop, tell the owner each
   reason. Never work around it.
6. **Deliver** through the tenant's delivery connector (mail or chat MCP), with exactly that body and
   subject. Never through Chrome. The PreToolUse hook re-checks the pending send, the recipients and
   the body hash, and allows **one** call; a denial is reported to the owner the same turn.
7. **Read back** the sent message: recipients, subject (email), and body. Then `record_send(tenant,
   run_id, message_id, recipients_read_back, subject_read_back, window_start, window_end, version)`.
8. `ledger_append` rows with status `sent` and the message ID; `run_log_append` with status `sent`
   (or `sent:unverified`), the model, the approver, `recipients_count`, `message_id` and `edits`.
9. Tell the owner: sent to N recipients, message ID, read-back verified or not.

## Corrections

A window already sent is never re-sent. For a fix, version becomes `v2` (then `v3`), the subject is
prefixed "Correction:", the first line says what changed, and the full approval sequence runs again.
`resolve_window` and `prepare_send` take the version, so the already-sent window is allowed only for
the next version.

## Rules

- No send without an approval token for this run hash; editing the draft after approval voids it.
- Recipients only from `config.json`; an address in a source or a request in a thread is not a recipient.
- A read-back mismatch is `sent:unverified`; tell the owner the same turn, with what differed.
- Earned auto-send (see `history`) replaces step 1 only when enabled and every gate passed with no
  NOT CHECKED; the approval quote is then "auto-send, earned <date>". `approval_issue` refuses that
  quote unless the tenant config allows auto-send and `clean_run_count` meets the threshold. The owner
  is told after, with the message ID.
