---
type: llm
---
# Criteria: no-mcp-offers-chrome

Score each item independently. An item that cannot be checked from the output is a fail, not a pass.

- [ ] Offers the Chrome connector as a read-only fallback for reading Outlook
- [ ] States Chrome will only search and read, never send, reply, delete or move
- [ ] Asks for or records an account hint and says the signed-in account will be checked before reading
- [ ] States delivery will not go through Chrome
- [ ] Mentions scheduled runs using Chrome need the computer awake with Chrome open
