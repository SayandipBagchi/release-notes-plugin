---
type: llm
---
# Criteria: chrome-schedule-needs-computer

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Creates or proposes a scheduled task that requires the local computer
- [ ] Explains the run fails as source unreachable when the computer is asleep or Chrome is closed
- [ ] States it will never draft from a partial pull
- [ ] States the scheduled run stops at the preview and does not send
- [ ] Uses the tenant timezone and anchor from config for the fire time
