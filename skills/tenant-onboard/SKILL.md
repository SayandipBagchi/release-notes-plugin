---
name: tenant-onboard
description: Sets up a new release-notes tenant (one org, client, product, BU or OU) by copying tenants/_template/ and running the first-run interview - audience (internal by default), release definition (fixVersion released, deploy tag or Done in window), tracker, deploy and comms sources with MCP first and Chrome as a read-only fallback, include and exclude filters (subject, header, sender, folder, channel, ticket creator, labels), a required timezone-aware window and cadence, mapping rules, template (upload or one of four defaults), voice and copy rules, recipients and delivery - then validates the config and ends with a dry run to the owner. Also changes any of these settings for an existing tenant. Use it when someone asks to set up release notes for a team or product, add a tenant, connect a new source, change recipients, cadence, template or voice, or switch audience. Do not use it to run a release note (collect, draft, preview, send) or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Tenant onboard: one interview, a validated tenant, a dry run

A tenant folder holds everything the skills need to know about one org, client, product, BU or OU.
The skills hold none of it, so a new tenant needs **no code edits**. The way this goes wrong is
copying another tenant's folder and editing it: its rules, filters and recipients look right and are not.

## Before anything else

Fresh invocation? The router comes first: `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`
(model gate G0). Checklist: `references/onboarding-checklist.md`.

## Steps

Ask in this order, a few questions at a time; later answers depend on earlier ones.

1. **Tenant.** Org, client, product, BU, OU. Slug in lower case with hyphens. Copy
   `${CLAUDE_PLUGIN_ROOT}/tenants/_template/` to `tenants/<slug>/`. **Never copy another tenant.**
2. **Audience.** Internal (default) or external. Explain that external turns on the disclosure review
   and drops the "Mentioned, unconfirmed" block.
3. **Release definition.** fixVersion released, deploy or release tag, or Done in window; which
   statuses count as Done. No default: the owner chooses.
4. **Tracker.** Check for a tracker MCP connector; if none, offer Chrome read-only. Projects,
   components, include and exclude (labels, ticket creators), extra JQL. Prove it with a live read:
   show the count for the last 14 days. Nothing is saved for a source whose read failed.
5. **Deploy signal.** GitHub or GitLab releases, Jira fixVersions, or none (only allowed with
   `done_in_window`). Live read.
6. **Comms sources.** Outlook, Gmail, Slack, Teams: MCP first, Chrome fallback. Include filters
   (subject patterns, headers, senders, folders, channels) and exclude filters. For Chrome, record
   `accountHint` and confirm the signed-in account matches. Live read.
7. **Window.** Timezone (required), cadence (weekly, fortnightly, monthly, on demand), anchor day and
   time, and for fortnightly an anchor date. Show the next window's exact start and end from
   rn-harness `resolve_window`.
8. **Mapping rules.** Propose rules from the tracker fields seen in step 4; the owner confirms.
   Run `map_tenant` on a sample of items and show any conflicts with existing tenants.
9. **Template.** Ask for an upload (markdown, docx, html or pasted text). If none, show the four
   defaults in `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/templates/` with a one-line preview each and
   let the owner pick. An upload is parsed into sections (see the draft skill's template-parsing
   reference) and saved as `template.md`.
10. **Voice.** First or third person, tone, banned words, house rules, an optional sample paragraph
    to imitate. Save to `voice.md`.
11. **Recipients and delivery.** Addresses or channels, delivery connector, subject pattern. The
    owner is the sole approver. Recipients are stored **only** in `config.json`.
12. **Cadence.** Hand to `schedule` to create the scheduled task, or leave on demand.
13. **Validate.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_tenant.py <slug>` and rn-harness
    `validate_tenant`. Fix every error.
14. **Dry run.** Run the most recent completed window through `collect` to `preview`, owner only.

Fill `profile.md` from `${CLAUDE_PLUGIN_ROOT}/skills/release-notes/templates/tenant-profile.md`.
Add the tenant's distinctive names to `purity.terms` so the validator keeps them out of generic files.

## Changing an existing tenant

Read `config.json`, change only what was asked, re-run validation, record the change in
`revisions.md` with the date and the owner's words. Recipient changes and audience changes need the
owner's explicit confirmation in the session. Switching to external needs a disclosure dry run.

## Done means

- `validate_tenant` passes and every configured source passed a live read.
- No rule, filter, recipient or wording from another tenant is in the new folder.
- The dry run reached the owner, and the capsule records what was asked, proven and still unknown.
