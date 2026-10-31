# Portability

Author: Sayandip Bagchi.

## The minimum runtime contract

- A host that loads `SKILL.md` skills with YAML frontmatter and resolves `${CLAUDE_PLUGIN_ROOT}`.
- Python 3.11+ for `rn-harness`, the hook and the scripts (standard library only).
- An Opus-class model.
- A tracker connector (MCP) or a signed-in browser for the Chrome fallback.
- A delivery connector (mail or chat MCP). Without one, the plugin drafts and previews but cannot send.

## The travelling set

`skills/`, `agents/`, `mcp/rn-harness/`, `scripts/`, `hooks/hooks.json`, `settings.json`,
`tenants/_template/`, `evals/`. Real tenant folders do not travel; they are per installation.

## What degrades

| Missing | Effect |
|---|---|
| Hooks not supported by the host | Send gate is enforced only by the send skill and rn-harness `prepare_send`; say so in the run report |
| No MCP support | No rn-harness: the plugin must refuse to run, because gates G2–G6 and G9 depend on it |
| No scheduled tasks | On-demand only |
| No subagents | Review runs in the same context; label the review "same-context" in the run report |

## Tenants directory

Defaults to `${CLAUDE_PLUGIN_ROOT}/tenants`. Set `RN_TENANTS_DIR` to keep tenant folders outside the
plugin so updates never overwrite them.

## Validation

Run `python3 scripts/validate_skill.py` after any change; run the evals before a release.
