> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# Phase 1 audit — baseline, 10 October 2026

## Architecture and verified page/API/table map

FastAPI entry: `backend/app/main.py`, launched from `backend` as `app.main:app`.
SQLAlchemy sessions with parameterized SQL/PyMySQL; no ORM models. Frontend is static HTML/CSS/JavaScript, calling port 8001, served on 5500. Compose database: MySQL 8.4, service `mysql`, container `disaster-mysql`, volume `disaster_mysql_data`.

| Page / module                 | API                                     | Tables                                                        |
| ----------------------------- | --------------------------------------- | ------------------------------------------------------------- |
| index.html                    | /api/dashboard/, disasters/, resources/ | All dashboard management tables                               |
| disasters.html                | /api/disasters/                         | disasters, locations, users                                   |
| shelters.html                 | /api/shelters/                          | shelters, locations                                           |
| volunteers.html               | /api/volunteers/                        | volunteers, users                                             |
| resources.html                | /api/resources/                         | resources                                                     |
| emergency-reports.html        | /api/emergency-reports/                 | emergency_reports, locations, users, disasters                |
| locations.html                | /api/locations/                         | locations                                                     |
| users.html                    | /api/users/                             | users                                                         |
| API only; no existing UI      | /api/resource-allocations/              | resource_allocations, resources, disasters, shelters, users   |
| API only; no existing UI      | /api/volunteer-assignments/             | volunteer_assignments, volunteers, disasters, shelters, users |
| API only; no existing UI      | /api/shelter-registrations/             | shelter_registrations, shelters, users                        |
| API only; no global search UI | /api/search/{module}                    | disasters, shelters, resources, emergency_reports + joins     |

## Findings and acceptance checks

| Severity | Verified problem                                                                                               | Correction                                                                                                | Verification                                                           |
| -------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Critical | All CRUD/list/search routes unauthenticated; private reporters and users exposed                               | Session auth, role dependencies, owned-report predicates                                                  | Anonymous 401, public admin calls 403, other report 404                |
| Critical | Users accept client password_hash; no genuine login; arbitrary role/status assignment                          | Argon2 server hashing; public registration fixed role; secure admin CLI                                   | Hash verification, rejected role escalation, no hashes returned        |
| Critical | schema.sql drops every table; sample_data.sql deletes all records                                              | Preserve legacy scripts with prominent warning; add non-destructive initialization and additive migration | Never run legacy scripts against owner DB                              |
| High     | Compose includes plaintext DB passwords; private backend .env exists                                           | Placeholders/env Compose; document rotation, preserve private file                                        | No secret values emitted or included in docs                           |
| High     | Emergency creation accepts arbitrary reporter, status and disaster link; no review workflow                    | Identity from session, pending creation, locked transactional confirm/reject                              | Owned status, repeat review cannot duplicate official disasters        |
| High     | Assignment writes and availability changes commit separately; completing one ignores other assignments         | One transaction, volunteer locks, derived availability                                                    | Multiple assignments completion retains ASSIGNED                       |
| High     | Registration create commits occupancy before status; update misses duplicate check and reopens CLOSED shelters | Locks, duplicate checks, preserve CLOSED, one commit                                                      | Capacity race, checkout/transfer consistency                           |
| High     | Allocations use float and unlocked stock reads; cascaded parent deletion bypasses stock restoration            | Decimal amounts, row locks, dependency-blocked deletion                                                   | Insufficient stock rolls back, concurrent allocations do not overspend |
| High     | /health always healthy even disconnected; SQL echo=True                                                        | 503 degraded health, SQL echo off, safe errors                                                            | Connected/disconnected health tests                                    |
| Medium   | Disaster schemas lack enum, length, positive-ID and date validation                                            | Shared constrained request models + merged update validation                                              | Invalid enum/null/date returns 422/400                                 |
| Medium   | Lists/search unbounded; frontend loads all data then filters; no pagination                                    | Server search/filters/pagination with bound values                                                        | Count/limit/offset correctness, clearing filters                       |
| Medium   | Frontend raw IDs in forms; no UI for three supported relation modules                                          | Shared lookup selectors; relation pages                                                                   | Labels and all related CRUD reachable                                  |
| Medium   | Repeated markup/scripts, alert/confirm interactions, inconsistent loading/errors, no dark mode                 | Shared plain-JS controller, accessible dialogs, coherent theme/responsive layout                          | Link/assets, syntax, browser checks                                    |
| Medium   | Hardcoded Administrator, System Online, Live System before backend check                                       | Real account/health/last-refresh state                                                                    | Disconnection cannot display fabricated success                        |
| Medium   | Resource dashboard sums quantities of incompatible units; low-stock threshold differs between UI/API           | Count available resource types, per-row units, consistent <= threshold                                    | No misleading mixed-unit total                                         |
| Low      | database/queries.sql empty, unversioned dependencies, no project tests/docs                                    | Keep script, explicit ranges, isolated unit and gated MySQL tests                                         | Test run results + Windows run guide                                   |

## Baseline execution

Read all source pages, scripts, styles, route files, schema, sample data, Compose and requirement files. All nine existing JS files passed `node --check`; all backend source files parsed with Python AST. All referenced local HTML assets exist. No application test suite was present (test files inside the copied virtual environment are dependency files). Docker executable unavailable; installed system Python launcher has no Python runtime. Bundled Python 3.12 is available but initially has none of the app/test dependencies. Backend runtime baseline will be attempted after installing isolated workspace dependencies. Existing Git directory is present; default Git command incorrectly reports not a work tree and is being investigated without changing Git history.

No database initialization, reset, sample-data import or Docker mutation has been performed.

## Final disposition

The baseline backend imported successfully when executed from its actual backend working directory. Read-only Git status succeeded with normal local access; no repository settings/history needed changes. V1.1 addresses the listed application/authentication/UI issues with shared constrained routes, transactional services and additive schema setup. See CHANGELOG_PHASE1 for compatibility changes and TEST_RESULTS for the precise proof: 92 unit tests passed, one real MySQL integration case skipped, browser smoke/mobile checks used an explicitly isolated fixture. MySQL migration, locking, persistence and full real-data workflow remain owner-run acceptance checks. Historical credential rotation is still required; private environment files were retained.

Implementation references: [FastAPI password hashing guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [SQLAlchemy connection pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html), [MySQL 8.4 SELECT and locking reads](https://dev.mysql.com/doc/refman/8.4/en/select.html). These describe password hashing, pre-ping/pool cleanup and row-locking behavior; they do not substitute for the unexecuted MySQL integration tests.

## Repeat acceptance audit — 11 October 2026

Existing V1.1 repairs and authorized DBMS extensions were inspected rather than
replaced. Entry points remain backend/app/main.py and frontend/login.html.

| Severity | Remaining finding                                                       | Fix                                                            | Verification                                                             |
| -------- | ----------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------ |
| High     | Account CLI validation exceptions could include entered password values | Report invalid field names only; suppress validation traceback | Invalid-password create/reset tests verify no secret output or DB access |
| Medium   | Global search omitted locations, users, volunteers and relation modules | All ten allowlisted modules; restrict users search to ADMIN    | Anonymous/public/admin search tests per module; manager users search 403 |
| Low      | Extension guide referenced a different venv from main Windows guide     | Standardize root .venv and current migration documentation     | Read exact paths/commands against implementation                         |

Current UI/API map additions: login.html -> /api/auth/\* -> users/auth_sessions;
resource-allocations.html -> resource_allocations/resources; volunteer-assignments.html
-> volunteer_assignments/volunteers; shelter-registrations.html -> shelter_registrations/shelters;
search.html -> /api/search/{module} -> all ten management modules with role restrictions.
audit-history.html -> /api/audit-history/ -> audit_history; resource-movements.html
-> /api/resource-movements/ and /api/resources/{id}/stock -> resource_movements/resources;
analytics.html -> /api/analytics/{section} -> three reporting views and allocation joins.

No database reset, legacy SQL execution, credential provisioning or Docker volume
mutation was performed. The actual /health remains degraded when MySQL is unavailable.
The previously authorized DBMS additions remain included; app version is V1.2.
