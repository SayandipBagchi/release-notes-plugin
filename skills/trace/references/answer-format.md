# Answer format

Author: Sayandip Bagchi.

```text
Line 3 · "Spend-category filters on the transactions list" · Completed, pending release (T2)

Why T2: tenant release definition is fixversion_released. ACME-405 moved to Done on 24 Oct (inside the
window) but is not in a released fixVersion yet.

Evidence
- Jira ACME-405 · status Done 24 Oct · https://tracker.example/browse/ACME-405
- Slack #cards-releases 24 Oct · "filters merged, going out with 4.19" · permalink

Run acme-cards-20261012-1 · window 12–26 Oct 2026 (Europe/London)
```

For an item not in the note:

```text
ACME-377 is not in the note: held. It matches mapping rules for two tenants (acme-cards: component
Cards; acme-lending: label lending). Tighten one rule in tenant-onboard to release it next run.
```
