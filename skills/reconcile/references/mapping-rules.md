# Mapping rules

Author: Sayandip Bagchi.

Each tenant's `config.json` holds `mappingRules`: a list of `{"match": {field: value}}`. A rule
matches an item when every field in it matches (a list value means any of). rn-harness `map_tenant`
checks the item against **every tenant's** rules, so a conflict between tenants is visible to both.

## Fields available to rules

| Field | From |
|---|---|
| `jira.project`, `jira.component`, `jira.labels`, `jira.epic` | tracker |
| `linear.team`, `linear.project`, `ado.areaPath` | tracker (v2) |
| `github.repo`, `gitlab.project` | deploy |
| `email.toDl`, `email.folder`, `email.sender` | email |
| `slack.channel`, `teams.channel` | chat |

## Outcomes

| `map_tenant` status | Meaning | Action |
|---|---|---|
| mapped (this tenant) | one tenant matches, and it is this one | keep |
| mapped (other tenant) | one tenant matches, another one | drop from this run, log |
| unmapped | no tenant matches | hold; suggest a rule in the run report |
| conflict | two or more tenants match | hold; name the tenants; owner resolves by tightening a rule |

## Writing good rules

Prefer the most specific stable field (component or label over project). Avoid rules on free-text
fields. A rule change is a config change: it goes through `tenant-onboard` with the owner's
confirmation and a revision entry.
