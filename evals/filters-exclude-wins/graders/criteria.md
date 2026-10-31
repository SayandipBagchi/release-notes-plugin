---
type: llm
---
# Criteria: filters-exclude-wins

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Says the email is dropped because exclude filters win over include filters
- [ ] Applies the filters through the harness (apply_filters) or states they are applied the same way every run
- [ ] Does not widen or ignore the tenant's filters
- [ ] Lists the dropped record in the run report rather than silently discarding it
