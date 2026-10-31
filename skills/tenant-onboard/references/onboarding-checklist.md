# Onboarding checklist

Author: Sayandip Bagchi.

Tick each before the dry run. An unticked item is an open item in `open-items.md` with an owner.

## Folder

- [ ] `tenants/<slug>/` created from `tenants/_template/`, not from another tenant
- [ ] `config.json` field `tenant` equals the folder name
- [ ] `profile.md`, `voice.md`, `template.md`, `open-items.md`, `revisions.md`, `quirk-evidence.md` present
- [ ] `release-ledger.csv` absent or header only

## Decisions (owner's words recorded in revisions.md)

- [ ] Audience: internal or external
- [ ] Release definition and Done statuses
- [ ] Owner is the sole approver (D2)
- [ ] Cadence, timezone, anchor (and anchor date if fortnightly)

## Sources (each proven with a live read)

- [ ] Tracker: connector or Chrome; projects; components; include and exclude; count for last 14 days
- [ ] Deploy: kind; repos or versions; count for last 14 days; or `none` with `done_in_window`
- [ ] Each comms source: connector or Chrome; `accountHint` for Chrome; include and exclude filters; count
- [ ] For every Chrome source: owner told scheduled runs need the computer awake with Chrome open

## Mapping

- [ ] At least one mapping rule
- [ ] `map_tenant` on 20 sample items: conflicts listed and resolved with the owner
- [ ] Unmapped share noted; above 20% means the owner should add a label or field (release-note label path)

## Content

- [ ] Template chosen or uploaded and parsed into sections
- [ ] Voice rules: person, tone, banned words
- [ ] `purity.terms` filled with tenant-unique names

## Delivery

- [ ] Recipients in `config.json` only; each valid
- [ ] Delivery connector present and able to send (MCP), never Chrome
- [ ] Subject pattern previewed with the next window's dates

## Close

- [ ] `scripts/validate_tenant.py <slug>` passes
- [ ] Dry run sent to the owner only
- [ ] Capsule written
