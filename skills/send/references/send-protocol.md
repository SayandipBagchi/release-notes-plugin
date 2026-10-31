# Send protocol

Author: Sayandip Bagchi.

```text
owner says "send it"
  → hash_run(draft, recipients, subject)              run_hash
  → approval_issue(..., quote)                        runs/<run_id>/approval.json
  → review/send-gate agent                            PASS required
  → prepare_send(..., body)                           needs runs/<run_id>/gates.json (G0–G8, preview delivered)
                                                      writes runs/pending-send.json (mode send, 30 min TTL)
  → connector send tool                               PreToolUse hook: scripts/send_gate.py
        hook allows ONE call only if: pending send not expired and unused, approval valid for
        run_hash, recipients in the call ⊆ pending recipients, body hash = approved draft,
        subject matches (email), window not already sent
  → read back the sent message
  → record_send(...)                                  runs/sent.jsonl, approval consumed, pending removed
  → ledger_append, run_log_append
```

## Why three checks

The send skill checks, rn-harness `prepare_send` checks, and the hook checks again at the moment of
the tool call. The hook is the one the model cannot talk its way past: it runs outside the model and
fails closed.

## Idempotency key

`<tenant>|<window_start>|<window_end>|<version>`. Used once. A correction uses the next version.

## Read-back

| Channel | Read back |
|---|---|
| Email | fetch the sent message by ID; compare To/Cc/Bcc set and subject |
| Slack / Teams | fetch the posted message; compare channel (no subject) |

## Hook denials

Common reasons: no pending send (prepare_send not called or expired), an extra recipient, approval for
a different draft, window already sent. Fix the cause; never retry with a different tool to avoid the
hook.
