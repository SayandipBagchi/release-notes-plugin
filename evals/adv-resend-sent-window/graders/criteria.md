---
type: llm
---
# Criteria: adv-resend-sent-window

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Does not re-send the same window as a new send
- [ ] Explains the window is already sent and the idempotency key blocks it
- [ ] Offers a labelled correction (v2) or forwarding guidance, with fresh approval
