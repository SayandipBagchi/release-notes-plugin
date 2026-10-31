# Patterns to remove

Author: Sayandip Bagchi.

Count hits per 500 words in audit mode. The tenant passes at no more than 2 (settings
`humanise.maxPatternHitsPer500Words`).

| # | Pattern | Example | Fix |
|---|---|---|---|
| P1 | Hype adjectives | "a game-changing, seamless experience" | say what changed |
| P2 | Empty intensifiers | "significantly improved", "greatly enhanced" | drop, or use the number the evidence gives |
| P3 | Filler openers | "We're excited to announce that…" | start with the change |
| P4 | Vague benefit | "to improve the user experience" | name who can now do what |
| P5 | Stacked abstractions | "leveraging robust capabilities to empower users" | plain verb and object |
| P6 | Rule of three by habit | "faster, smarter and more reliable" | keep only what the evidence supports |
| P7 | Hedge chains | "may potentially help to" | one hedge or none |
| P8 | Self-reference | "this release note covers…" | delete |
| P9 | Em-dash asides everywhere | "the fix — finally — lands" | a full stop |
| P10 | Formulaic closers | "Stay tuned for more!" | delete |
| P11 | Passive fog where the voice is active | "improvements were made to" | active, if voice.md allows |
| P12 | Jargon the audience will not know | internal code names | the product name the audience uses |

Banned words from `voice.md` count as hits too.
