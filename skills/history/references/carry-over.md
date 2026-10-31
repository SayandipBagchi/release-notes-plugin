# Carry-over and auto-send

Author: Sayandip Bagchi.

## Carry-over

An item reported as `pending` (T2) in a sent note stays on the carry-over list until a later window
has it as `released` (T1). `draft` puts carried items first in their section:

- Now T1: under Released, with "previously reported as pending on <date>".
- Still T2: under the pending section, with "pending since <date>".
- Pending for three or more windows: flagged in the run report so the owner can ask whether it shipped
  or was dropped.

An item the owner says was dropped is written to the ledger with status `dropped` and leaves the list.

## Clean run

A run counts as clean when its run-log record has status `sent`, `edits` = 0, every gate PASS (no
NOT CHECKED), no hook denial and read-back verified. `clean_run_count` counts consecutive clean runs
from the most recent backwards and stops at the first that is not clean.

## Why earned, not default

A release note goes to people who act on it. Owner previews catch the mistakes the gates do not.
Auto-send is a reward for a tenant whose sources, rules and template have proven stable, and it is
withdrawn the moment that stops being true.
