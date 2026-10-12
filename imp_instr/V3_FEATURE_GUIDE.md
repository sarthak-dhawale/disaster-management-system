# V3 behavior and architecture

React uses hash routes (`#/overview`, `#/resources`, etc.), so the portable Python HTTP server needs no route fallback. The original frontend remains in frontend/ for reference and compatibility; V3's entry point is frontend/dist. Shared layout, fields, relation lookup, tables, dialogs, status messages and API hooks reduce page duplication. Cookies and role rules remain enforced by FastAPI. Administrators and disaster managers manage response data; only ADMIN manages user accounts; public accounts see and submit their own emergency reports.

Overview places the real India map above metrics. It fetches priority-ranked actual incidents, with filters for search, state, type, severity, status and dates. At most 500 markers are loaded and the scope count is displayed; narrow filters for larger datasets. Missing coordinates remain in the record list and count. There is no fabricated live indicator. Confirmed reports are not double-counted as official disasters on the administrative map. Nearby shelters use Haversine distance, not road routing. Boundaries are local; optional OSM tiles and Photon lookup need internet. Manual addresses and coordinates continue to work without the provider.

Metrics: recorded disasters = official disaster records; active = status ACTIVE; pending = reports PENDING_REVIEW; available shelters = AVAILABLE plus spare capacity; volunteers = registered volunteer records; stocked resources = distinct resource IDs with available_quantity > 0. Quantities in different units are never presented as a combined stock KPI. Detailed Reports uses segmented database-view analyses with text filtering/pagination and matching PDF/CSV exports.

Resource Intelligence computes required, non-cancelled allocated/reserved, delivered and outstanding quantities separately. Shared-resource shortage = max(0, summed OPEN outstanding demand - available stock), grouped by the same resource ID/unit. Request metrics respect fulfillment filters; stock-contention groups are calculated before the fulfillment filter, as explained on screen. Recommendations are min(request outstanding, available stock), are not independent promises of stock, and require approval through the existing locked/idempotent endpoint. No warehouse geography exists, so no resource-source distance is invented. Demand details show linked allocations and recorded history/ledger; old historical events may be unavailable.

Response Simulator inputs are hypothetical. The Assam / FLOOD / 2,000 / HIGH default is not saved as a disaster. Managers enter resource quantities using actual catalog items/units, shelter demand, priorities, optional coordinates and an optional official reference. That reference is context; it does not import live demand automatically. Available inventory already reflects live commitments, which are shown in the server snapshot rather than subtracted twice. Each run uses a separate MySQL REPEATABLE READ, READ ONLY transaction. All plans share that exact immutable snapshot.

Plan A: nearest resource supply is unavailable because inventory has no warehouse coordinates; explicit fallback prioritizes demand then input order. Plan B: highest unmet quantity first WITHIN each compatible resource, with priority/input tie-breaks. Plan C: Plan A order while preserving the selected percentage of each resource's available stock, rounded down to 0.01. Results never overallocate a resource or sum incompatible units. Per-resource coverage = proposed / required. Regional demand rows expose the distribution. Eligible shelters exclude CLOSED/FULL/no-space records; all-region spare capacity is only an upper bound, not a local accommodation guarantee. Valid coordinates give straight-line distance; missing distance is labeled. These are heuristics, not optimal plans.

There is no Apply live action. Run, compare, edit, rerun, export and discard do not write disasters, allocations, resources, shelters, audit or ledger. Result references are random, owner-scoped, expire after one hour, disappear on restart, and are limited to 100 results / 32 MiB per process. Use one API worker. A rerun captures a new timestamped snapshot; changing live inventory cannot silently alter an existing result. There are no simulations in operational dashboard totals.

New endpoints:

| Endpoint                                         | Behavior                                                                |
| ------------------------------------------------ | ----------------------------------------------------------------------- |
| GET /api/resource-intelligence                   | Actual demand metrics/groups, filtering and pagination                  |
| GET /api/simulations/catalog                     | Read-only actual resources/shelters/official reference catalog          |
| POST /api/simulations/run                        | Validates assumptions, captures stock, returns three hypothetical plans |
| GET /api/simulations/{id}                        | Owner-scoped cached comparison                                          |
| DELETE /api/simulations/{id}                     | Discards memory result only                                             |
| GET /api/simulations/{id}/export/{pdf,csv}       | Hypothetical export with snapshot and warning                           |
| GET /api/exports/{module}.pdf                    | Allowlisted filtered actual-record PDF                                  |
| GET /api/exports/shelters.csv                    | Adds shelter streaming CSV; old CSV routes retained                     |
| GET /api/reports/overview/{pdf,csv}              | Incident scope plus explicitly global capacity/inventory/rosters        |
| GET /api/reports/resource-intelligence/{pdf,csv} | Filtered demand/coverage and stock contention                           |
| GET /api/reports/analysis/{section}              | Filtered/paged detailed database-view analysis                          |
| GET /api/reports/analysis/{section}/{pdf,csv}    | Same analysis/filter exported                                           |

All planning and operational aggregate exports are manager-only; public emergency-report exports remain owner-filtered. Password hashes and approval keys are excluded. CSV escapes formula prefixes. PDFs use ReportLab, local boundary polygons rendered with Pillow and actual incident coordinates; no tile scraping or screenshot map. Tables repeat headers and paginate; Noto Latin/Devanagari fonts are bundled with SIL OFL license. Other scripts require additional appropriate fonts; CSV preserves UTF-8 for those data.

PDF/analysis/planning scope is explicitly capped at 10,000 records with a 413 response rather than silent truncation. Operational CSV routes stream all matching rows in batches. Overview incident filters apply to its incident/map section; inventory/shelter/roster sections and metrics are global and labeled. Mixed overview CSV is long-form `Section, Record, Field, Value`, not incompatible wide tables. Simulation CSV is distinctly hypothetical and resource/unit aware. Exports use generated timestamps and no-store headers. They are not browser print dialogs.

Performance: map code is lazy-loaded; existing map instance survives filter changes and only marker layers change. Requests have shared in-memory 15-second caches, deduplicate concurrent subscribers, cancel abandoned fetches and ignore stale hook responses. Search is debounced 300ms; management lists paginate 25 records. Successful mutations invalidate related read caches. Refresh is explicit, not falsely real-time. PERF_AND_TEST_RESULTS.md records measured build/browser checks and their limits.

Simulation CSV schema: hypothetical, scenario, snapshot, section, record, field, value. It includes scenario inputs, snapshot inventory/provenance, all three plans, shelter analysis and assumptions. Overview adds explicitly global emergency-report and open-demand shortage sections.
