> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# V3 audit - 12 October 2026

Baseline: 177 unit/API tests passed; three opt-in MySQL integration tests skipped.

The existing application is FastAPI with SQLAlchemy/PyMySQL and plain HTML/CSS/JavaScript, not React/Vite as assumed by the V3 brief. V3 authorizes a new React/Vite frontend; retain legacy pages and all backend contracts. Existing V2 authentication, row-locked allocation approvals, inventory/capacity protection, report review, geography, audit history and movement ledger are implemented and covered by baseline tests.

| Issue                                                       | Severity | Correction                                                                               | Verification                                                 |
| ----------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| No React/Vite setup                                         | High     | Add reusable React application, retain legacy frontend                                   | Production build, route/browser checks                       |
| Exports are CSV plus browser printing                       | High     | Add server-generated ReportLab PDFs and shelter/overview CSV                             | PDF extraction, rendering, privacy and filter tests          |
| Demand analysis lacks cross-request stock contention totals | High     | Resource Intelligence with grouped resource shortages and distinct coverage/delivery     | Known demand fixtures and cancellation tests                 |
| No hypothetical planning tool                               | High     | Pure simulation engine, read-only consistent snapshot, bounded owner-scoped result cache | Known fixtures, no-DML checks, auth/expiry tests             |
| Two-laptop startup differs                                  | High     | Separate local MySQL and existing Docker instructions, prebuilt portable frontend        | Startup checks; primary laptop remains explicitly unverified |
| V2 operational interface crowded                            | Medium   | Overview map, consistent navigation, segmented Reports, light/dark themes                | Responsive browser review                                    |

No V3 database migration is planned. Preserve existing records, Docker container disaster-mysql and volume disaster_mysql_data. Do not run legacy reset scripts. Existing V1/V2 additive migration remains an explicit setup action only when needed. Never automatically initialize a populated database.

Primary: Python 3.10, Docker MySQL 8.4. Secondary: Python 3.12, local MySQL 8.4. Both API 8001/frontend 5500. No credentials or private environment files belong in the transfer archive.
