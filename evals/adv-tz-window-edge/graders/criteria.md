---
type: llm
---
# Criteria: adv-tz-window-edge

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Converts the UTC time to the tenant timezone before comparing
- [ ] Concludes correctly that 23:30 UTC on 18 Oct is 00:30 BST on 19 Oct, so it falls in the next window, not this one
- [ ] States the window is start-inclusive and end-exclusive
