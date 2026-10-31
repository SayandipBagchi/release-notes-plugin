---
name: draft
description: Writes the release note for one tenant and window from reconciled, tiered items - fills the tenant's template section by section, one short line per item, every line carrying at least one evidence ID and a visible link (tracker issue, release, email subject and date, or chat permalink), carry-over items first, Released only for T1, Completed pending release for T2, and Mentioned unconfirmed for T3 on internal notes only - then proves every citation resolves for gate G5. Also parses an uploaded template into sections. Use it when a run's items are ready to be written up, when someone asks to redraft a section, or to turn an uploaded template into the tenant's template.md. Do not use it to rewrite for voice (humanise), to decide tiers or tenants (reconcile), to send (send), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Draft: every line cited

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Input: tenant, run ID,
window, items from `reconcile`. Template rules: `references/template-parsing.md`. Citation format:
`references/citation-format.md`.

## Steps

1. Read `tenants/<name>/template.md` and the audience from `config.json`.
2. Call rn-harness `ledger_carry_over(tenant)`. Carried items that are now T1 go first under Released
   with "previously reported as pending"; still-T2 carried items go first under the pending section.
3. Place each item in its template section by tier and type: Released (New, Improved, Fixed, Known
   issues by tracker issue type or label), pending (T2), mentioned (T3, internal only).
4. Write one line per item: what changed, for whom, in plain words, then the citation. Use the
   tracker title as the base; use comms excerpts only to clarify, never to add a claim the tracker or
   release does not support.
5. Fill `{{banner}}` with every partial, unknown or unreachable source and every excluded source,
   or remove it when all sources are complete.
6. Build `lines = {line_id: [evidence_ids]}` and call `citation_resolve(tenant, run_id, lines)`. Any
   uncited line or unknown ID fails G5: fix or remove the line.
7. Fill the trace appendix from `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/templates/trace-appendix.md`.
8. Save to `tenants/<name>/runs/<run_id>/draft.md` and `trace.md`, and return both with the line map.

## Rules

- **No line without evidence.** No summary sentences that make claims ("a big release for
  reliability") unless every item they summarise is cited in the same section.
- **No invented facts.** No dates, versions, owners, metrics or customer names that are not in the
  evidence. A missing fact stays missing.
- **T2 and T3 never under Released.**
- **Empty window:** a short note that says no items met the release definition in the window, with
  the trace appendix. No padding.
- **External audience:** no Mentioned block, no internal links (use public reference IDs or none),
  no internal people's names, no other customers' names.
- **Held items never appear** in the note; they appear only in the trace appendix's held table.
