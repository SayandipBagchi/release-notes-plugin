# Cadence

Author: Sayandip Bagchi.

| Cadence | Window | Needs |
|---|---|---|
| weekly | the 7 days ending at the most recent anchor (for example Mon 00:00) | `anchor` |
| fortnightly | 14-day periods aligned to `anchorDate` at the anchor time | `anchor`, `anchorDate` |
| monthly | the previous calendar month, starting on the anchor day | `anchor` as "01 00:00" |
| on_demand | explicit start and end | given per run |

All windows are start-inclusive, end-exclusive, in the tenant timezone, so daylight-saving changes
shorten or lengthen a window by an hour rather than dropping or doubling items.

## Fire time

Fire the scheduled task a little after the window closes, so late transitions land: anchor plus 2
hours by default. If the team closes tickets late, the owner can move it.

## Missed runs

If a scheduled run fails (model, source unreachable), the next run does not widen its window to catch
up. The owner runs the missed window on demand.

## Backfill

Past windows run one at a time, oldest first, owner-only, through `history`.
