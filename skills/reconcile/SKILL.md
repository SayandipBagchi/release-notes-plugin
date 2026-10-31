---
name: reconcile
description: Turns a run's evidence into release-note items for one tenant - joins email and chat mentions to tickets by extracting ticket keys, removes duplicates, maps every item to exactly one tenant with the deterministic mapping rules (items matching zero or two or more tenants are held, never guessed), and tiers each item against the tenant's own release definition (T1 released, T2 completed pending release, T3 mentioned only in comms) using structured fields only, for gate G4. Use it when a run's sources have been collected and need turning into items, or when someone asks why an item was held, tiered or excluded. Do not use it to pull sources (collect), write lines (draft), change mapping rules or the release definition (tenant-onboard), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Reconcile: one item, one tenant, one tier

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Input: tenant, run ID,
window, evidence IDs from `collect`. Tier rules: `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/references/evidence-tiers.md`.
Join and mapping detail: `references/tiering.md` and `references/mapping-rules.md`.

## Steps

1. **Load evidence** with rn-harness `evidence_get`.
2. **Join comms to tickets.** For each email or chat record, `extract_ticket_keys` on subject and
   excerpt with the tenant's project keys. Attach the record as supporting evidence to each key found.
   Comms records with no key stay as candidate T3 items keyed `<source>:<native_id>`.
3. **Join deploy to tickets.** Keys found in release names or bodies attach the release as a deploy
   ref (`{kind, tag, date}`); fixVersion membership attaches the version.
4. **Dedupe.** One item per ticket key; one item per comms thread for keyless items.
5. **Map.** For each item, call `map_tenant` with its flat fields (`jira.project`, `jira.component`,
   `jira.labels`, `slack.channel`, `email.toDl`, ...). Status `mapped` to this tenant: keep. `mapped`
   to another tenant: drop from this run and log. `unmapped` or `conflict`: **held**.
6. **Tier.** For each kept item, call `tier_item(tenant, run_id, item, window_start, window_end)`.
   The item carries its tracker `evidence_id`, and every fix version and deploy ref carries the
   `evidence_id` of the tracker or deploy record it came from; entries without one are ignored by the
   harness (a comms message cannot supply a deploy ref). Never override its result. Never pass free
   text to it.
7. **Return** items with `{key, title, tier, section, evidence_ids, single_source}` plus the held list
   with reasons and the excluded and out-of-window lists.

## Rules

- **Rules first, model never.** You may *suggest* a mapping rule for a held item in the run report;
  you may not assign the item.
- **Chat cannot promote.** A message saying "released" or "shipped" changes nothing; only structured
  fields count.
- **Titles come from the tracker** for keyed items; from the subject or first line for keyless T3 items.
- **Nothing outside the window** is drafted; out-of-window items are logged.
