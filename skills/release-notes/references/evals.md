# Evals

Author: Sayandip Bagchi.

Four layers. The `eval-runner` agent runs all of them and returns a dated score sheet; anything it
could not run is NOT RUN, never passed.

| Layer | What | Command | Pass bar |
|---|---|---|---|
| L1 structural | package, frontmatter, links, purity, secrets, learnings trace, tenant configs | `python3 scripts/validate_skill.py`; `python3 scripts/validate_tenant.py <tenant>` | 100% |
| L1 harness | rn-harness unit tests | `python3 -m unittest discover -s mcp/rn-harness/tests` | 100% |
| L2 behavioural | routing and gate behaviour | `claude plugin eval .` | every criteria item |
| L3 quantitative | accuracy against human-written notes | `python3 scripts/backtest.py --fixtures evals/fixtures` | recall ≥ 0.90, precision ≥ 0.95, false released 0, uncited 0, duplicates 0, entities preserved |
| L4 adversarial | attacks and edge cases (`adv-*` cases) | `claude plugin eval . --case 'adv-*'` | 0 unsafe actions |

## What each case tests

The case table with target skill and should-fire lives in `evals/README.md`. Each case folder holds
`prompt.md` and `graders/criteria.md` (type llm) and `graders/skill-fired.md` (type tool_used, or llm
for should-not-fire cases).

## Scoring

Score each criteria item independently. An item that cannot be checked from the output is a fail, not
a pass. Use the runner's default of 3 runs; do not read one run as a verdict. Do not pass
`--ablation none`.

## Adding a case

1. Create `evals/<case-name>/prompt.md` and both graders.
2. Add a row to the case table in `evals/README.md`.
3. If the case comes from a live learning, add a row to [learnings-trace.md](learnings-trace.md).

## The golden set

3–5 past windows from 2–3 teams in `evals/fixtures/<org>-<window>/`: frozen source pulls, the
human-written note as `answer-key.json`, and the agent's output as `agent-output.json`. Fixtures are
redacted; no real addresses or names.
