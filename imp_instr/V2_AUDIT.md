> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# V2 pre-change audit

Source checkpoint: separate source backup with SHA-256 inventory made before edits.
103 eligible repository files read, including all imp_instr guides and migrations.
Private .env, Git internals, venvs, dependencies and caches excluded and preserved.

Present: working V1.2 CRUD, authentication, owned-report review, transactional stock,
registrations/assignments, audit triggers, movement ledger and three reporting views.
Partial: theme/nav must change; analytics exists separately; coordinates already exist
on locations; report history has latest review plus audit snapshots, not a timeline.
Missing: map/picker, geographic matching, demand requests, recommendations, CSV/print
reports, embedded analytics, local-MySQL setup and repository-wide readable formatting.
No intermediate V2 files were found in the actual repository.

Baseline: 147 tests passed, one opt-in MySQL integration skipped. Docker/MySQL absent.
Real migration/locking/persistence/map queries cannot be verified here. No real schema
change will be executed until a disposable MySQL environment validates it.

Plan: retain API contracts; add V2 endpoints and nullable report-specific location
fields, location deduplication key, demand rows linking existing inventory/allocations.
No automatic migration, seeding, stock mutation from suggestions or location invention.
Vendor Leaflet/cluster assets and attributed boundary data; use lightweight SVG charts.
Keep geocoding optional, cached, explicitly submitted, rate-limited and replaceable.
