---
type: llm
---
# Criteria: adv-partial-pull

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Marks Jira as partial (not complete)
- [ ] Says the preview banner will name Jira as partial
- [ ] Blocks sending until Jira is re-pulled complete or the owner removes it for this run in writing
- [ ] Does not describe the window as quiet or complete
