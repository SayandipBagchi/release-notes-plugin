---
name: collect
description: Pulls one window's evidence for a release-notes tenant from every configured source - tracker (Jira, Linear, Azure DevOps), deploy signal (GitHub or GitLab releases, Jira fixVersions) and comms (Outlook, Gmail, Slack, Teams) - with one source-puller agent per source, MCP connectors first and Chrome as a read-only fallback, applying the tenant's include and exclude filters, storing each record as evidence with a stable ID and a short excerpt, and proving completeness (fetched equals the source's reported total) for gate G3. Use it when a run needs its sources pulled, when someone asks to re-pull a partial source, or to check what a source returns for a window. Do not use it to tier, map or draft (reconcile, draft), to change a tenant's sources or filters (tenant-onboard), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Collect: every source, complete, as evidence

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`): G0 model, G1 tenant,
G2 window. You need the tenant slug, the run ID and the resolved window (start inclusive, end
exclusive, tenant timezone). Adapter detail: `references/source-adapters.md`. Completeness rules:
`references/completeness.md`.

## Steps

1. Read `sources` from `tenants/<name>/config.json`.
2. Start one `source-puller` agent per configured source, in parallel, each with only its own config
   block, the window and the run ID. Each returns records and `{fetched, reported_total}`.
3. For the tracker and each comms source, call rn-harness `apply_filters(tenant, source_kind,
   records)` (`tracker` or `comms:<index>`; the deploy signal has no filters beyond its repos) so
   include and exclude rules are applied the same way every run;
   keep the dropped list for the run report. Then `completeness_check(source, fetched,
   reported_total)` on the pre-filter counts.
4. Run rn-harness `injection_scan` on every excerpt; keep flagged spans for the run report.
5. Store records with rn-harness `evidence_put(tenant, run_id, records)`; keep the returned IDs.
6. Return to the router: per-source status (complete, partial, unknown, unreachable), counts, evidence
   IDs, injection flags.

## Rules

- **MCP first.** Use Chrome only when the tenant config says `mode: chrome` for that source.
- **Chrome is read-only.** Search and read; never click send, reply, forward, delete, archive, label,
  move or status controls. Confirm the signed-in account matches `accountHint` before reading; a
  mismatch aborts that source as `unreachable`.
- **Filters are the tenant's.** Apply include and exclude filters exactly as configured; excludes win
  on conflict. Never widen a filter to find more items.
- **Window is exact.** Start inclusive, end exclusive, tenant timezone (source quirk Q13).
- **Excerpts, not bodies.** At most 300 characters per record, chosen to support a possible line.
  Raw bodies stay in `runs/` only if needed for trace.
- **A partial source never reads as quiet.** Status partial or unknown blocks send (G3) and is
  named in the preview banner.
- **Read-only everywhere.** No writes to any source system.

## Evidence record

`{source, native_id, url, title, timestamp, author, excerpt, fields}` where `fields` holds structured
data: for tickets `key, status, status_changed_at, labels, components, project, fix_versions, creator`;
for releases `tag, date, refs`; for messages `subject, sender, channel, thread, ticket_keys_seen`.
