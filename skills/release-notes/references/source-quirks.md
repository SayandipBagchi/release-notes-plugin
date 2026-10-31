# Source quirks

Author: Sayandip Bagchi.

Numbered behaviours of source systems that cause wrong notes if ignored. Evidence for each, per
tenant, goes in `tenants/<name>/quirk-evidence.md` under the same number. Add new quirks at the end;
never renumber.

| # | Source | Quirk | Handling |
|---|---|---|---|
| Q1 | Jira | `resolutiondate` and the Done transition time can differ; reopen-then-close moves it | Use the last transition into a `doneStatuses` status inside the window |
| Q2 | Jira | A fixVersion can be marked released with a release date in the past or future | Tier on the version's release date, not the time it was marked released |
| Q3 | Jira | Search results paginate; `total` is the true count only for the same JQL | Paginate until fetched = total with identical JQL (G3) |
| Q4 | Jira | Components are often empty | Map by project, label or epic as well; empty-component items held if no rule matches |
| Q5 | GitHub/GitLab | Tags and releases are distinct; a release can be a draft or pre-release | Use published, non-draft releases; pre-releases only if the tenant config says so |
| Q6 | GitHub/GitLab | Release times are UTC | Convert to the tenant timezone before window comparison |
| Q7 | Email | Reply chains repeat the original; subject prefixes vary (RE:, FW:, AW:) | Dedupe by message ID and normalised subject; prefer the earliest message as evidence |
| Q8 | Email | Mail search in web clients caps results per page | Paginate; treat an unknown total as partial |
| Q9 | Slack | Search results omit thread replies unless asked | Fetch thread replies for any matching parent; cite the permalink of the message used |
| Q10 | Slack/Teams | Edited messages keep the original timestamp | Use the message timestamp for windowing; note the edit in the excerpt |
| Q11 | Chrome | Web UIs lazy-load; a scroll can stop early | Confirm the count shown by the UI matches the records read; else partial |
| Q12 | Chrome | A signed-in browser may be on a different account than expected | Check `accountHint` before reading (G3) |
| Q13 | Any | Times without a zone | Interpret in the tenant timezone, never the machine's |
