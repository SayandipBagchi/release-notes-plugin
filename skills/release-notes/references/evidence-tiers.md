# Evidence tiers

Author: Sayandip Bagchi.

The tenant's `releaseDefinition.primary` decides what "released" means. rn-harness `tier_item` applies
it to structured fields: status, status change time, fix versions with release dates, deploy refs with
dates, labels and the list of sources that mention the item. It takes no free text, so nothing written
in a ticket or message can change a tier.

## Rules by release definition

| Definition | T1 (Released) | T2 (Completed, pending release) | T3 (Mentioned, unconfirmed) |
|---|---|---|---|
| `fixversion_released` | a fix version marked released with a release date inside the window | status in `doneStatuses`, changed inside the window, no released fix version | only comms sources mention it |
| `deploy_tag` | a deploy or release tag dated inside the window references it | as above, no deploy ref in window | only comms sources mention it |
| `done_in_window` | status in `doneStatuses`, changed inside the window | not used | only comms sources mention it |

Items with labels in `sources.tracker.exclude.labels` are `excluded`. For an external audience,
security, CVE and vulnerability labels are `excluded` too. Items with no signal inside the window are
`out_of_window` and are logged, not drafted.

## How each section is drafted

- **Released:** T1 only. Headings follow the template (New, Improved, Fixed, Known issues).
- **Completed, pending release:** T2. Label taken from `releaseDefinition.pendingLabel`.
- **Mentioned, unconfirmed:** T3, internal audience only, at the end, clearly marked. Dropped for
  external audiences.

## Why email and chat never promote

A chat message saying "shipped" is the most common false release. Comms add context (what changed,
for whom, links) to items the tracker or deploy signal already supports. They never create a Released
line on their own.
