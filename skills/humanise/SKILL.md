---
name: humanise
description: Rewrites a release-note draft in the tenant's voice - first or third person, tone, banned words, house copy rules and an optional sample paragraph to imitate - removing generic AI-sounding phrasing (filler, hype, vague claims, formulaic structure) while locking every fact - ticket keys, versions, dates, numbers and URLs must be identical before and after, checked with the entity ledger for gate G6; on any difference the rewrite is discarded and the pre-humanise draft is used and flagged. Also audits a draft for those patterns without rewriting. Use it when a draft is ready for voice and copy rules, when the owner says a note sounds robotic or off-brand, or to audit a note's wording. Do not use it to add, remove or re-tier items (draft, reconcile), to change voice rules (tenant-onboard), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Humanise: the tenant's voice, the same facts

This is a bundled, pinned copy, so the rewrite behaves the same in every installation.

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Input: the draft from
`runs/<run_id>/draft.md` and `tenants/<name>/voice.md`. Patterns: `references/patterns.md`. Fact lock:
`references/fact-lock.md`.

## Steps

1. `entity_ledger(draft_text, project_keys)` → keep as **before**.
2. Rewrite line by line, applying `voice.md` (person, tone, banned words, house rules) and removing
   the patterns in `references/patterns.md`. Keep every line's citation exactly as it is.
3. `entity_diff(before, after, project_keys)` with the pre- and post-humanise text.
4. **Equal:** save as `runs/<run_id>/draft.humanised.md` and return it.
5. **Not equal:** discard the rewrite, return the pre-humanise draft, and add to the run report which
   entities would have been added or removed. G6 is recorded as "reverted".
6. Audit mode: report pattern hits per 500 words with line references; change nothing.

## Rules

- Change words, never claims. Do not add benefits, numbers, adjectives of scale ("major", "huge") or
  outcomes the evidence does not state.
- Never touch citations, ticket keys, versions, dates, numbers or URLs, including their formatting.
- Never move a line to another section or merge two items into one line.
- Keep lines short: one sentence each where possible.
- First person ("we shipped") or third person ("the team shipped", or passive) exactly as `voice.md`
  says; do not mix.
