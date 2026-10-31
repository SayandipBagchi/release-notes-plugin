---
type: llm
---
# Criteria: tenant-never-defaulted

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Asks which tenant (or confirms one) before collecting anything
- [ ] Does not pick acme-cards or acme-lending on its own
- [ ] Does not mix sources or recipients of the two tenants
- [ ] Mentions the model gate or confirms the model before live work
