# Completeness (G3)

Author: Sayandip Bagchi.

| Situation | `completeness_check` status | Effect |
|---|---|---|
| fetched equals reported total | complete | none |
| fetched less than total | partial | banner names the source; send blocked |
| fetched more than total | partial (note: duplicates or query drift) | banner; send blocked |
| source gives no total | unknown | treated as partial |
| connector error, Chrome account mismatch, computer offline | unreachable | banner; send blocked; scheduled run ends `failed:source_unreachable` if the tracker is unreachable |

## Recovering

Re-pull the source with the identical query. If it still cannot complete, the owner may remove that
source **for this run only**, in writing in the session; record their words in the run report. The
note then says which source was excluded and why.

## Zero results

Zero records with a reported total of zero is complete. Compare with the last three windows; a fall
from a steady count to zero is reported as possible drift (see the router's observability reference).
