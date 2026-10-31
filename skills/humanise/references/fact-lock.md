# Fact lock (G6)

Author: Sayandip Bagchi.

rn-harness `entity_ledger` extracts five categories from text:

| Category | Examples |
|---|---|
| ticket_keys | ACME-412 |
| versions | 4.18.0, v2.3 |
| dates | 2026-10-21, 21 Oct 2026, Oct 21, 2026 |
| numbers | 37, 2.5, 15% |
| urls | https://tracker.example/browse/ACME-412 |

`entity_diff(before, after)` returns `equal: true` only when all five sets match exactly.

## Common failures

- Writing a number as a word ("three" for 3): a removed number. Keep digits.
- Reformatting a date ("21 October" for "21 Oct 2026"): a changed date. Keep the original.
- Dropping a version from a line to shorten it: a removed version.
- "Fixing" a key's case or prefix: a removed and an added key.
- Adding a figure from general knowledge: an added number.

On any difference the pre-humanise draft wins. Never try a second rewrite to make the diff pass
without telling the owner; report what the first attempt would have changed.
