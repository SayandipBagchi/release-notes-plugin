# Connectors

What each skill needs to reach, and how. MCP connectors are always preferred. Chrome (a signed-in
browser) is a **read-only** fallback for reading sources; it is never used to deliver.

| Need | Preferred (MCP) | Fallback | Skills | Notes |
|---|---|---|---|---|
| Tracker: Jira | Atlassian MCP (JQL search, issue fetch, versions) | Chrome: Jira issue navigator with JQL | collect, tenant-onboard | fixVersion release dates come from the project's versions |
| Tracker: Linear, Azure DevOps | Their MCP connectors | Chrome: saved views | collect | v2 adapters; same evidence shape |
| Deploy: GitHub / GitLab releases | GitHub / GitLab MCP (releases, tags) | Chrome: Releases page | collect | Tag dates converted to the tenant timezone |
| Email: Outlook | Microsoft 365 MCP mail search | Chrome: Outlook web search | collect | Signed-in account checked against `accountHint` before reading |
| Email: Gmail | Gmail MCP search | Chrome: Gmail search operators | collect | |
| Chat: Slack | Slack MCP channel history | Chrome: Slack search | collect | Permalinks are the citation |
| Chat: Teams | Microsoft 365 MCP chats and channels | Chrome: Teams web | collect | v2 |
| Delivery: email | Outlook or Gmail MCP send | none | send | Never through Chrome. Read back after sending |
| Delivery: Slack / Teams | Slack / Teams MCP post | none | send | Same gate and read-back |
| Delivery: doc | Docs connector | none | send | v2: not accepted by `validate_tenant` in v1 |
| Deterministic checks | `rn-harness` (bundled, local) | none | all | Standard-library Python; no network |
| Scheduling | The host's scheduled tasks | none | schedule | Chrome-sourced tenants need the local computer |

Each tenant's `config.json` names which connector and mode it uses per source. This file names none of
a tenant's systems, accounts or addresses.

## Chrome fallback rules

- Read only. No clicks on send, reply, forward, delete, archive, label, move or status controls.
- Confirm the signed-in account matches `accountHint` before reading. Mismatch aborts the pull.
- Record what was read as evidence with its URL or permalink, like any MCP source.
- A Chrome-sourced scheduled run needs the local computer awake with Chrome open; if it is not, the run
  ends `failed:source_unreachable` and tells the owner. It never drafts from a partial pull.
