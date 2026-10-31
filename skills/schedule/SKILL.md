---
name: schedule
description: Sets up how a release-notes tenant runs - a fixed cadence (weekly, fortnightly, monthly) as a scheduled task that runs collect through preview and then waits for the owner's approval, or on demand - with the window anchor and timezone from the tenant config; a tenant with any Chrome-sourced input gets a schedule that requires the local computer and fails as source unreachable rather than drafting from a partial pull. Use it when someone asks to schedule release notes, change the cadence, pause or resume a schedule, or run a tenant now. Do not use it to change sources, recipients or the window definition (tenant-onboard), to send (send), or for routing and gates (release-notes).
metadata:
  author: Sayandip Bagchi
---

# Schedule: cadence without unattended sends

## Before anything else

The router runs first (`${CLAUDE_PLUGIN_ROOT}/skills/release-notes/SKILL.md`). Cadence rules:
`references/cadence.md`.

## Steps

1. Read `window` and `sources` from `tenants/<name>/config.json`.
2. **On demand:** nothing to schedule. "Run it now" goes to the router with an explicit window or the
   last completed window from `resolve_window`.
3. **Fixed cadence:** find the host's scheduling tool. Create one scheduled task per tenant that fires
   shortly after each window closes (anchor time plus 2 hours, in the tenant timezone). Its prompt is
   standalone: tenant slug, "run release notes for the window that just closed; stop at preview unless
   the tenant has earned auto-send enabled (the harness decides)", and the instruction to use an
   Opus-class model.
4. **Chrome sources:** if any source has `mode: chrome`, the task **requires the local computer**.
   Tell the owner it will fail as `failed:source_unreachable` when the computer is asleep or Chrome is
   closed, and that it will never draft from a partial pull.
5. Set the task's model to Opus where the host allows; the run still checks G0.
6. Record the task name and cadence in `profile.md` and the change in `revisions.md`.

## Rules

- A scheduled run stops at preview. It never sends unless earned auto-send is enabled (see `history`),
  and the harness refuses an auto-send the tenant has not earned.
- One task per tenant. Never one task for several tenants.
- Pausing a schedule is fine without ceremony; deleting it needs the owner's word.
