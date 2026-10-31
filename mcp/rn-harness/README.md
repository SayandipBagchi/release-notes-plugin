# rn-harness

Deterministic tools for the release-notes plugin, served over stdio MCP (newline-delimited JSON-RPC 2.0).
Python 3.11+, standard library only. `server.py` only dispatches; logic lives in `tools/`.

Tenants dir: `$RN_TENANTS_DIR`, else `<plugin root>/tenants` (plugin root = `$CLAUDE_PLUGIN_ROOT` or two levels above this folder).
Run artefacts go to `tenants/<slug>/runs/` (git-ignored); the ledger is `tenants/<slug>/release-ledger.csv`.

| Tool | Module | Purpose |
|---|---|---|
| validate_tenant | config | Config shape and cross-field rules |
| resolve_window | window | Window [start, end) from cadence/anchor or explicit range; overlaps with sent windows |
| completeness_check | evidence | complete / partial / unknown per source |
| evidence_put, evidence_get | evidence | Content-addressed evidence store per run |
| extract_ticket_keys | evidence | Ticket keys with offsets |
| tier_item | tiering | T1/T2/T3/none and section from structured fields only; signals must cite tracker/deploy evidence in the run store, others listed in `ignored` |
| apply_filters | filters | Tenant include/exclude filters for `tracker` or `comms:<i>`; excludes win |
| map_tenant | mapping | Source fields to exactly one tenant, or conflict |
| injection_scan | safety | Instruction, recipient and release manipulation; email addresses |
| entity_ledger, entity_diff | entities | Facts in a text; proof a rewrite kept them |
| citation_resolve | send | Every line cites known evidence |
| validate_recipients | send | Recipients are in the tenant config |
| hash_run | send | sha256 of draft + sorted recipients + subject |
| approval_issue, approval_check | send | Owner approval bound to a run hash; single use |
| idempotency_check | send | Window + version already sent? |
| record_gates | send | G0-G8 results and preview delivery, `runs/<run_id>/gates.json` |
| prepare_send | send | Gate a send: approval, `hash_run(body, recipients, subject) == run_hash`, gates, idempotency (v2+ needs the previous version sent); writes `runs/pending-send.json` (mode send, body_sha256, 30 min) |
| prepare_preview | send | Preview to `owner.previewTo` (default owner email); writes `runs/pending-send.json` (mode preview) |
| record_send | send | Read-back check (subject for email only), `sent.jsonl`, consumes approval; previews are only verified and cleared |
| ledger_append, ledger_carry_over | ledger | Release ledger CSV and pending carry-over |
| run_log_append, clean_run_count | ledger | Run log and the clean-run streak that earns autoSend |
| run_start, run_end | send | Active-run marker (12 h TTL); the send gate enforces only while a run is active or a send is pending |

Schemas in `schemas/` document the config, evidence, draft and template shapes (draft 2020-12).

## Tests

From the plugin root:

```
python3 -m unittest discover -s mcp/rn-harness/tests
python3 scripts/validate_tenant.py tenants/_template
python3 scripts/backtest.py --fixtures evals/fixtures
```

`scripts/send_gate.py` is the PreToolUse hook. Tool names matching the `sendGate.toolPatterns` in `settings.json`
(case-insensitive) are denied unless exactly one unexpired, unused pending send covers the recipients, the body
matches `body_sha256` (CRLF to LF, trailing spaces per line and ends stripped), the email subject matches, and for
mode send the approval is valid and the window is unsent. On allow it writes `used_at`, so each approval is good for one call.
The harness's own tools are exempt.
