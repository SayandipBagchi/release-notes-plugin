---
type: llm
---
# Criteria: onboard-window-required

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Refuses to save the tenant without a timezone
- [ ] Explains the window must be timezone-aware and why (items on the boundary)
- [ ] Offers to set the timezone and cadence now, or proposes a likely default for the owner to confirm
- [ ] Does not write a config that would fail validation
