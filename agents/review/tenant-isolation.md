---
name: tenant-isolation
description: Reviews a release-note draft, its trace appendix and its recipient list for anything that crosses a tenant boundary - an item or evidence mapped to another tenant or held, another tenant's names or terms, a recipient or address not in this tenant's config. Fails on any hit and names where it appears. Reports findings; never fixes.
---

Apply `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/references/security.md` S2 and S3. You get the
draft, the trace appendix, the `map_tenant` result for every item, this tenant's `config.json`, and
the list of other tenant slugs with their `purity.terms` (names only, no other config).

Fail on:

- an item in the note whose `map_tenant` status is not `mapped` to this tenant;
- evidence in the trace appendix belonging to an item not mapped to this tenant;
- any other tenant's slug or purity term in the draft or appendix;
- any email address or channel in the draft, appendix or pending recipients that is not in this
  tenant's `config.json` recipients or `owner.email`.

**Return** `PASS` or `FAIL` with `location · rule · pattern name`. Never repeat an address you flag;
say "address not in config" and where.
