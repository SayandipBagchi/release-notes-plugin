# Tenant files

Author: Sayandip Bagchi.

Everything in this directory is **live state for one tenant's release notes**. A tenant is one org,
client, product, BU or OU. Nothing here belongs in a skill, agent, hook or setting, and
`scripts/validate_skill.py` fails the package if a tenant's distinctive names appear in generic files.

Create a tenant with the `tenant-onboard` skill, which copies `_template/`. Never copy another tenant.
To keep tenants outside the plugin (so updates never touch them), set `RN_TENANTS_DIR`.

| File | Holds | Read it when |
|---|---|---|
| `config.json` | classification, owner, audience, release definition, window, sources and filters, mapping rules, **recipients (the only place addresses live)**, delivery, auto-send, purity terms | every run, first |
| `profile.md` | the tenant in plain words: what "released" means here, known gaps | onboarding, review |
| `voice.md` | person, tone, banned words, house rules, sample paragraph | humanise |
| `template.md` | the note template with `{{section:<id>}}` placeholders | draft |
| `release-ledger.csv` | one row per item per window per run (written by rn-harness) | draft (carry-over), history, trace |
| `quirk-evidence.md` | evidence behind each numbered source quirk, keyed by number | when a quirk is disputed |
| `open-items.md` | unresolved questions with an owner | every session start |
| `revisions.md` | dated config changes with the owner's words | after any change |
| `source/` | uploaded templates, sample past notes, capsules | onboarding, backfill |
| `runs/` | evidence, drafts, approvals, pending send, sent log, run log (git-ignored) | trace, send, history |
