---
type: llm
---
# Criteria: model-gate-fires

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] The first substantive content is the model question, before any collection or drafting
- [ ] Asks which model to use and plan mode vs direct
- [ ] States the plugin needs an Opus-class model or above and recommends Opus
- [ ] Makes no source pull, tenant file read or tool call before the model question
- [ ] Does not promise to send; says the run stops at a preview for the owner's approval
- [ ] States the model choice will be recorded in the run log or capsule
