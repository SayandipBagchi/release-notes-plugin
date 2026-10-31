---
name: trace
description: Answers where any line of a release note came from - looks up the line's evidence IDs from the run's line map and returns each source with its link (tracker issue, release or fixVersion, email subject and date, chat permalink), the tier and why, whether it was single-source, and for held or missing items why they were held or dropped - without re-pulling sources. Use it when someone asks where a line came from, why an item is or is not in a note, why something was called released or pending, or to defend a note that was challenged. Do not use it to change a note (draft, humanise), to re-run collection (collect), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Trace: the evidence behind a line

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`) for tenant resolution.
Answer format: `references/answer-format.md`.

## Steps

1. Find the run: from the question, the latest run in `runs/run_log.jsonl`, or the message ID in the
   ledger.
2. Find the line in `runs/<run_id>/draft.md` (or the humanised draft) and its evidence IDs in the line
   map; for an item not in the note, find its ledger row (section and status).
3. `evidence_get(tenant, run_id, ids)` and return each source with its link and excerpt.
4. Explain the tier with the tenant's release definition and the structured fields that decided it.

## Rules

- Never re-pull to answer; answer from the run's evidence. If evidence is missing (`missing` from
  `evidence_get`), say so plainly.
- Show only this tenant's evidence.
- Quote at most a short excerpt per source; link to the rest.
