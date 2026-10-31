# Example: a dry-run preview

All names, keys and addresses are invented.

**To:** the tenant owner only · **Subject:** [DRAFT · needs your approval] Acme Cards release notes · 12–26 Oct 2026

---

# Acme Cards release notes · 12–26 Oct 2026

> Slack was partial (fetched 140 of 162 messages). Send is blocked until it is re-pulled or you remove
> Slack from this run.

## Released

### New
- Virtual card freeze from the app home screen. [ACME-412](https://tracker.example/browse/ACME-412) · release 4.18.0

### Fixed
- Statement PDFs now show the correct billing period for accounts opened mid-month. [ACME-398](https://tracker.example/browse/ACME-398) · release 4.18.0

## Completed, pending release
- Spend-category filters on the transactions list. [ACME-405](https://tracker.example/browse/ACME-405) · Done 24 Oct, not in a released version yet

## Mentioned, unconfirmed
_Raised in email or chat; no tracker or release record in this window. Internal only._
- Faster card activation, mentioned in #cards-releases on 22 Oct. [permalink](https://chat.example/archives/C01/p1)

---

## How this note was collected

**Window:** 2026-10-12 00:00 to 2026-10-26 00:00 (Europe/London) · **Release definition:** fixversion_released · **Run:** acme-cards-20261012-1

| Source | Mode | Query or filter | Fetched / total | Status |
|---|---|---|---|---|
| Jira | mcp | project = ACME AND component = Cards | 37 / 37 | complete |
| GitHub releases | mcp | acme/cards-api | 2 / 2 | complete |
| Slack | chrome | #cards-releases | 140 / 162 | partial |

| Line | Section | Tier | Evidence |
|---|---|---|---|
| 1 | Released · New | T1 | jira:ACME-412, release 4.18.0 (21 Oct), email "[Release] 4.18.0" 21 Oct |
| 2 | Released · Fixed | T1 | jira:ACME-398, release 4.18.0 (21 Oct) · single source |
| 3 | Pending | T2 | jira:ACME-405, Done 24 Oct |
| 4 | Mentioned | T3 | slack permalink 22 Oct |

## Held, not in this note

| Item | Why held |
|---|---|
| ACME-377 | Matches mapping rules for two tenants (acme-cards and acme-lending) |

**Reply "send it" to approve this exact draft, or tell me what to change.**
