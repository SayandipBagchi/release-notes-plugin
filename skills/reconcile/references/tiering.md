# Joining and tiering

Author: Sayandip Bagchi.

## Join order

1. Tracker items are the spine: one item per key.
2. Deploy refs attach by key (release body, tag message, fixVersion membership).
3. Comms attach by key found with `extract_ticket_keys`. A message naming three keys supports three items.
4. Comms without any key become keyless items. Two messages in the same thread are one item.

## Single source

A Released item supported by one signal only (for example a released fixVersion with no deploy ref
and no comms) is marked `single_source: true`. That is allowed; the trace appendix shows it.

## What `tier_item` needs

```json
{
  "key": "ACME-412",
  "evidence_id": "jira:ACME-412:1a2b3c4d",
  "status": "Done",
  "status_changed_at": "2026-10-21T10:02:00+01:00",
  "labels": ["mobile"],
  "fix_versions": [{"name": "4.18.0", "released": true, "release_date": "2026-10-21",
                    "evidence_id": "jira_fixversion:4.18.0:5e6f7a8b"}],
  "deploy_refs": [{"kind": "github_release", "tag": "v4.18.0", "date": "2026-10-21T09:40:00Z",
                   "evidence_id": "github_release:v4.18.0:9f8e7d6c"}],
  "evidence_sources": ["jira", "github_release", "outlook"]
}
```

Keyless comms items pass `status: null`, no `evidence_id`, empty versions and refs, and their comms
sources; they tier as T3 when inside the window. The harness rejects a deploy ref or fix version
whose evidence record is not a tracker or deploy record, and lists it under `ignored`.

## Excluded and out of window

Excluded items (labels in the tenant's exclude list, or security labels for an external audience) and
out-of-window items are written to the ledger with that section and status `dropped`, never drafted.
