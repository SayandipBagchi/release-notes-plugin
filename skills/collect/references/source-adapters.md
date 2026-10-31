# Source adapters

Author: Sayandip Bagchi.

Each adapter returns the evidence record shape in the collect skill and `{fetched, reported_total}`.

## Tracker: Jira

- **MCP:** JQL search with `project in (...) AND component in (...)` plus include and exclude labels,
  creators and `jqlExtra`, bounded by `updated >= start AND updated < end`. Page until fetched equals
  `total` for the same JQL (Q3). For each issue: status, last transition into a Done status (Q1), fix
  versions with `released` and `releaseDate` (Q2), labels, components, creator.
- **Chrome:** the issue navigator with the same JQL; read the result count shown; page through.
- **Citation:** the issue URL.

## Tracker: Linear, Azure DevOps (v2)

Same shape. Linear: team, project, labels, `completedAt`. Azure DevOps: area path, iteration, state,
`Microsoft.VSTS.Common.ClosedDate`.

## Deploy: GitHub / GitLab releases

- **MCP:** list releases for each repo; keep published, non-draft releases dated inside the window
  (Q5, Q6). Extract ticket keys from the release name and body with `extract_ticket_keys`.
- **Chrome:** the Releases page.
- **Citation:** the release URL.

## Deploy: Jira fixVersions

Project versions with `released = true` and `releaseDate` inside the window, plus the issues in each.

## Email: Outlook, Gmail

- **MCP:** search with the include filters (subject patterns, senders, folders, headers) and the
  window; then drop anything matching exclude filters. Dedupe reply chains (Q7).
- **Chrome:** the web client search; confirm `accountHint` first (Q12); page until the shown count is
  read (Q8, Q11).
- **Citation:** subject, sender and date, plus a message link if the client gives one.

## Chat: Slack, Teams

- **MCP:** channel history for the configured channels inside the window; fetch thread replies for
  matching parents (Q9).
- **Chrome:** channel search; confirm `accountHint`.
- **Citation:** the message permalink.
