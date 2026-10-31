# release-notes

Release notes that compile themselves, cite every line, and never send without you.

`release-notes` is a Claude plugin that builds a release note for one **tenant** (an org, client,
product, BU or OU) from your tracker, your deploy signal and the email or chat threads you point it
at. It drafts to you first, every time. You approve, and only then does it go to the recipient list.

## What it does

| Step | What happens |
| --- | --- |
| Collect | Pulls Jira (or Linear / Azure DevOps), a deploy signal (GitHub/GitLab releases or Jira fixVersions) and comms (Outlook, Gmail, Slack, Teams) for one time window. MCP connectors first; Chrome as a read-only fallback. |
| Reconcile | Joins email and chat mentions to tickets, removes duplicates, maps each item to exactly one tenant, and tiers it against **your** definition of "released". |
| Draft | Fills your template. Every line carries a link to the ticket, release, email or chat message it came from. |
| Humanise | Rewrites for your voice (first or third person, tone, banned words) without touching a single ticket key, version, date, number or link. |
| Review | Independent checks for grounding and tenant isolation (plus disclosure for external audiences). Any failure blocks the draft. |
| Preview | Sends the draft and a trace appendix to you only. |
| Send | After your approval in the session, delivers to the tenant's recipients through a connector, then reads the sent message back. |

## How "released" is decided

Each tenant chooses one definition at setup: a fixVersion marked released, a deploy or release tag,
or Done within the window. Evidence is tiered:

| Tier | Evidence | Shown as |
| --- | --- | --- |
| T1 | Meets the tenant's release definition inside the window | Released |
| T2 | Done in the window but no release record | Completed, pending release |
| T3 | Only mentioned in email or chat | Internal "Mentioned, unconfirmed" block, or dropped |

Email and chat add context. They never make an item Released on their own.

## Install and first run

1. Install the plugin. It needs Python 3.11+ for the bundled `rn-harness` server (standard library only).
2. Use an Opus-class model. The plugin refuses to run below Opus.
3. Say "set up release notes for <team or product>". The `tenant-onboard` skill asks for the tenant
   classification, audience (internal by default), release definition, sources and filters, time
   window and timezone, template, voice rules, recipients and cadence. Each connector is tested with a
   live read before it is saved.
4. It finishes with a dry run of the last completed window, sent to you only.

After that: "draft this fortnight's release notes for acme-cards", or let the scheduled task run it.
Scheduled runs stop at the preview and wait for your approval.

## Safety, in one table

| Risk | Guard |
| --- | --- |
| Announcing something that did not ship | Tenant release definition; T3 never Released; uncited lines block the draft |
| One client's changes reaching another | Rules-first tenant mapping; ambiguous items held; recipients only from the tenant's own config |
| Sending without sign-off | Preview every run; approval bound to the exact draft; PreToolUse hook blocks unapproved sends |
| Instructions hidden in emails or tickets | Source text is data; injection scan; tiers read structured fields only |
| The rewrite changing facts | Entity ledger before and after humanise must match exactly |
| A broken source read as a quiet week | Completeness check names the missing source and blocks send |

## Layout

```text
.claude-plugin/plugin.json   manifest and MCP server
settings.json                plugin-wide policy (model gate, approval, send gate, session)
hooks/hooks.json             SessionStart reminder and PreToolUse send gate
CONNECTORS.md                which connector each skill uses, and the Chrome fallback
skills/                      router (release-notes) and one skill per job
agents/                      source puller, eval runner, review agents
mcp/rn-harness/              deterministic tools and their tests
scripts/                     validators, send gate, backtest
tenants/_template/           copy this for a new tenant (tenant-onboard does it for you)
evals/                       behavioural and adversarial cases, fixtures for the backtest
docs/PRD.md                  the product requirements this build follows
```

## Checks

```bash
python3 scripts/validate_skill.py                         # package structure, purity, secrets
python3 scripts/validate_tenant.py <tenant>               # one tenant's config
python3 -m unittest discover -s mcp/rn-harness/tests      # harness unit tests
python3 scripts/backtest.py --fixtures evals/fixtures     # accuracy against human-written notes
claude plugin eval .                                      # behavioural and adversarial cases
```

## Licence

MIT. See LICENSE.
