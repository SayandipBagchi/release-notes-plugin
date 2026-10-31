# Changelog

## 0.1.0 — 2026-10-31

First build from the PRD (Release Notes Agent — Plugin PRD, draft of 31 Oct 2026).

- Router skill `release-notes` with the model gate, tenant resolution and gates G0–G9.
- Worker skills: tenant-onboard, collect, reconcile, draft, humanise (bundled, fact-locked), preview,
  send, schedule, trace, history.
- Agents: source-puller, eval-runner, and review agents for grounding, tenant isolation, disclosure
  and the send gate.
- `rn-harness` local MCP server (standard library only) for window maths, evidence store, tiering,
  tenant mapping, injection scan, entity ledger, recipients, approval, idempotency and the ledger.
- PreToolUse send-gate hook (enforces only while a run is active or a send is pending; body-bound, single use) and SessionStart reminder.
- Tenant template, validators (`validate_skill.py`, `validate_tenant.py`), backtest scorer and the
  first L2/L4 eval cases.
