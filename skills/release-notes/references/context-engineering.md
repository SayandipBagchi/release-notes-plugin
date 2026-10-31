# Context engineering

Author: Sayandip Bagchi.

The drafting context should hold what the note needs and nothing that can mislead it.

## The loading budget

| Context | Holds | Never holds |
|---|---|---|
| Router | settings, tenant `config.json`, gate table | raw sources |
| source-puller (one per source) | that source's config block, window, filters | other sources, other tenants |
| reconcile | evidence records (metadata + excerpts), mapping rules | full bodies |
| draft | template, voice, tiered items with excerpts, carry-over list, last 2 windows from the ledger | held items' bodies, raw sources |
| humanise | the draft, voice, entity ledger | evidence bodies |
| review agents | draft, evidence records for its lines, tenant config | drafting reasoning (so they are not anchored on it) |

## Per-task load table

| Task | Read |
|---|---|
| Any run | `config.json`, then `validate_tenant` |
| Draft | `template.md`, `voice.md`, `release-ledger.csv` (last 2 windows) |
| Onboard | `tenants/_template/*`, `references/onboarding-checklist.md` in tenant-onboard |
| Trace | `runs/<run_id>/evidence.jsonl` via `evidence_get` |

## Excerpts

Keep at most 300 characters of a source body per evidence record, chosen to support the line it backs.
Strip signatures, quoted replies and disclaimers.

## Eviction and re-read

After a source-puller returns, drop its working notes; keep only the records. Before send, re-read the
pending draft from `runs/` rather than from memory.

## The capsule as handover

Every session ends with [the capsule](../templates/context-capsule.md). A new session starts from it,
not from the old transcript.
