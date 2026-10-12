> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

Current release: see [CHANGELOG_V3.md](CHANGELOG_V3.md). The Phase 1 history below is preserved.

# Version 1.1 — Phase 1 changes

## Interface

Reworked all existing HTML pages while retaining plain HTML/CSS/JavaScript. A shared responsive sidebar/header, real account display, light/dark theme, restrained teal/slate palette, visible keyboard focus and readable tables replace repeated layouts and decorative emojis. Added real pages for allocations, assignments, shelter registrations, global search and login. Shared forms use related-record labels, native field constraints, inline server errors, request locking, details/confirmation/review dialogs and success toasts. Lists use server search/filters/pagination with stale-request protection. No fake live indicators, fabricated records or framework migration.

## Backend and security

Kept FastAPI, SQLAlchemy/PyMySQL and the existing module paths/response list keys. Added constrained request models, positive IDs, enums, lengths, dates, finite Decimal inventory, bounded paging and reusable bound-query lists. Repaired degraded health status; disabled SQL echo; added timeouts/pooling and rollback/close guarantees. Normalized duplicate/constraint, unavailable DB and validation errors without password/input leakage. Lookup routes are scoped by role.

Argon2 passwords are hashed server-side. Opaque HttpOnly/SameSite=Strict cookie sessions are stored as token digests with UTC expiry in MySQL, revoked by logout and account security changes. Public registration fixes its role; ADMIN/DISASTER_MANAGER authorization is enforced server-side; ADMIN alone manages users. Added interactive admin provisioning/password reset, attempt limiting, exact CORS origins and origin/custom-header protections for writes. Private environment files were preserved; tracked Compose passwords removed in favor of environment variables. Exposed historical credentials still require owner rotation.

## Workflow and consistency

Public reports are saved with session-bound reporter and pending review, without creating disasters. Owned queries restrict personal data. Administrators confirm/reject under a row lock, record a review note/time/reviewer, and atomically create or link an official incident at the same location. Repeated confirmation returns the existing link. Confirmed/legacy response status can be updated separately; reviewed content/history cannot be erased through ordinary CRUD.

Allocation reservations, edits and deletion now use Decimal values and locks. Shelter registrations validate duplicates/capacity and adjust occupancy/status in one transaction while preserving CLOSED. Availability reflects all active volunteer assignments. Parent deletion is blocked when relationships exist to prevent cascade-based inconsistencies.

## Database changes and migration

`python -m app.setup_db migrate` adds auth_sessions, emergency-report disaster_type/occurred_at/review_status/review_reason/reviewed_at/reviewed_by, an owner/review index and reviewer FK. Existing nonpending reports are backfilled as LEGACY or REJECTED, not invented verified reviews. It inspects each additive object before creation and can be rerun. MySQL DDL auto-commits; back up before applying. No tables/records/volumes were dropped or reset.

Original schema.sql/sample_data.sql remain with prominent destructive warnings. `database/init_safe.sql` is for a genuinely empty schema only and is guarded by the initializer. The original empty queries.sql remains. See database/migrations/README.md for migration details.

## Compatibility changes

- Existing collection/item URLs and result keys are retained; list responses now include total/limit/offset and default to 25 records (max 200).
- Clients must authenticate and send X-DMS-Request: 1 for writes.
- User writes accept **password**, not password_hash. Password is optional on update.
- Report submission cannot supply arbitrary status, reporter or disaster linkage. Review uses POST /api/emergency-reports/{id}/review; response progress uses POST /api/emergency-reports/{id}/progress.
- User account management is ADMIN-only; public/volunteer sessions are report-only.
- Destructive parent cascades and reviewed-report deletion are intentionally blocked.

## Important files

| Group         | Added/modified                                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Backend core  | main.py, database.py, schemas.py; new config.py, models.py, listing.py, crud.py, security.py, setup_db.py, manage.py |
| Routers       | All 12 existing route files repaired; new auth.py                                                                    |
| Frontend      | All 8 original HTML pages, existing JS/CSS updated; 5 new pages and launchers; new js/modules.js and tests/check.cjs |
| Configuration | docker-compose.yml, .gitignore, requirements.txt; new root/backend .env.example and requirements-dev.txt             |
| Database      | Original schema/sample scripts warned; new init_safe.sql and migration README                                        |
| Tests         | conftest.py, test_api.py, test_crud.py, test_additional.py, test_mysql_integration.py                                |
| Documentation | All nine requested imp_instr documents, plus file-change inventory                                                   |

No source files, database tables, containers or persistent volumes were removed. No commit, force-push or Git history rewrite was performed. A complete per-file inventory is in FILE_CHANGES.md.

## Verification and limits

92 isolated unit/API tests passed; 1 MySQL integration case skipped. Source/asset checks and isolated browser smoke/mobile/theme/validation checks passed. No actual MySQL integration/migration/persistence result is claimed. Local single-process attempt limiting and naive business timestamps are documented; multi-timezone/public deployment, instant notifications, attachments and dispatch services are outside this phase. Review history is one final decision per report rather than an invented multi-event timeline. See TEST_RESULTS and TESTING_CHECKLIST.

## V1.2 DBMS extensions

Added administrative audit history, resource ledger (including restock/withdraw) and four analytical reports. Additive migration creates two tables, three views and 33 triggers. Actor context is cleared on connection checkout. History uses explicit redacted snapshots and persists after source deletion. Unit changes are blocked for existing resources. Added 42 unit/API checks and extended the opt-in MySQL workflow; 134 tests passed and one integration test skipped. No real database changes executed.

## Final acceptance recheck

Expanded global search to all ten management modules with ADMIN-only users search; protected account CLI validation from printing password inputs; standardized root .venv instructions and corrected Docker migration documentation. Added 13 regression cases. Current result: 147 passed, 1 real MySQL integration skipped. Existing stack, modules, private .env and Docker volume preserved.
