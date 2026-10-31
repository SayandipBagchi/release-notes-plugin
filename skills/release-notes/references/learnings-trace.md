# Learnings trace

Author: Sayandip Bagchi.

Where each design learning landed. Each row names the primary file (relative to the plugin root) and
an **anchor**: a literal string in that file that `scripts/validate_skill.py` checks is still present,
so a later edit cannot silently drop a guardrail. Add a row whenever a live run teaches something new.

| # | Learning | Primary file | Anchor | Eval |
|---|---|---|---|---|
| L1 | Done is not shipped; the tenant defines "released" | `skills/release-notes/references/evidence-tiers.md` | `## Rules by release definition` | onboard-release-definition-required |
| L2 | Email and chat corroborate; they never promote an item to Released | `skills/release-notes/references/evidence-tiers.md` | `## Why email and chat never promote` | adv-mark-as-released |
| L3 | A partial pull must not read as a quiet window | `skills/release-notes/references/gates.md` | `## G3 in detail: completeness` | adv-partial-pull |
| L4 | Approval binds to this run's hash, in this session, from the owner | `skills/release-notes/references/gates.md` | `## G9 in detail: what counts as approval` | send-needs-in-session-approval |
| L5 | Humanise may change words, never entities | `skills/release-notes/references/gates.md` | `## G6 in detail: fact lock` | adv-humanise-drops-key |
| L6 | Recipients come only from tenant config | `skills/release-notes/references/security.md` | `## S2 · Recipients` | adv-recipient-injection |
| L7 | Items matching two tenants are held | `skills/release-notes/references/security.md` | `## S3 · Tenant isolation` | adv-two-tenant-item |
| L8 | Chrome is read-only and checks the account first | `skills/release-notes/references/security.md` | `## S6 · Read-only sources and Chrome` | adv-chrome-wrong-account |
| L9 | Chrome-sourced schedules need the local computer | `skills/schedule/SKILL.md` | `requires the local computer` | chrome-schedule-needs-computer |
| L10 | A sent window is never re-sent; corrections are versioned | `skills/release-notes/references/run-protocol.md` | `## Corrections` | adv-resend-sent-window |
| L11 | Times without a zone are read in the tenant timezone | `skills/release-notes/references/source-quirks.md` | `Q13` | adv-tz-window-edge |
| L12 | External audiences exclude security items and other customers' names | `skills/release-notes/references/security.md` | `## S4 · Disclosure (audience external)` | adv-cve-external |
