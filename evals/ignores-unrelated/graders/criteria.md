---
type: llm
---
# Criteria: ignores-unrelated

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Does not invoke the release-notes plugin or its skills
- [ ] Does not ask for tenant, window or release definition
- [ ] Treats the request as ordinary writing
