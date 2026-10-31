# Citation format

Author: Sayandip Bagchi.

Every line ends with its citation. Readers must be able to click through or find the source.

| Evidence | Shown as |
|---|---|
| Tracker issue | `[ACME-412](issue url)` |
| Release or tag | `release 4.18.0` linked to the release page when the audience can open it |
| fixVersion | `version 4.18.0` |
| Email | `email "<subject>" <d Mon>` (no addresses) |
| Chat | `[thread](permalink)` or `#channel <d Mon>` when the link is internal and the audience external |

Multiple evidence items: tracker first, then release, then comms, separated by ` · `.

The line map passed to `citation_resolve` uses evidence IDs, not display text:
`{"L1": ["jira:ACME-412:1a2b3c4d", "github_release:v4.18.0:9f8e7d6c"]}`.

For external audiences, links that require internal access are replaced by the reference ID alone
(for example `ACME-412`), never removed silently: the trace appendix to the owner keeps the full link.
