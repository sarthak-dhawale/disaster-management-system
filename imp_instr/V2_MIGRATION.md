> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# V2 migration and data safety

No migration has been applied to the primary database here. MySQL is unavailable. Validate in a disposable database before production use.

## Preconditions and commands

Stop application writes. Record MySQL 8.4 version and schema/account configuration. Take a complete private logical backup including routines/triggers; verify it can be restored. Restore a populated copy under a separate \*\_test name/account, never over disaster_management. Review backend/app/setup_db.py, v2_schema.py and history_schema.py.

Run from backend with the project environment active and explicitly configured for that disposable copy:

```powershell
python -m app.setup_db migrate
python -m app.setup_db migrate
```

Compare before/after row counts, foreign keys and existing coordinates/accounts. Repeated migration must not duplicate columns, indexes, tables or triggers. Check report confirmation, demand allocation/cancellation, ledger and history. Only after these pass, restore the primary private configuration and run `python -m app.setup_db migrate` once against the backed-up primary database. Normal FastAPI startup does not apply DDL.

For a genuinely empty fresh database only: `python -m app.setup_db init --fresh`. It refuses any existing tables and creates no demo data. Never use legacy schema/drop/sample deletion scripts on a populated database.

## Changes

- Locations gain coordinate_source (LEGACY for old records) and nullable SHA256 location_key with a unique index. Existing coordinates/text are untouched. Existing duplicates retain NULL keys; do not automatically merge referenced legacy locations.
- Emergency reports gain reported_location_text, reported_latitude/longitude and coordinate_source. location_id becomes nullable so unfamiliar public reports can remain outside the official directory. Its foreign key remains; confirmation requires a valid official location.
- resource_requests stores disaster/resource demand in the existing resource's units, quantity, note, status, creator and timestamps. FK constraints preserve existing inventory relationships.
- resource_allocations gains nullable request_id FK and nullable unique approval_key for idempotent manager approval. Existing allocations remain unlinked; no stock recalculation/reseeding occurs.
- Three resource-request audit triggers join the original 33 V1.2 history/ledger triggers. Existing views, audit records and movement entries are retained. Old report snapshots remain as originally recorded; new-location fields are also available from current records. There is no invented historical coordinate backfill.
- Existing V1.1 guarded report/session migration remains in the same command. Its legacy review classification is retained; historical reviews are never invented.

## Recovery limitations

MySQL DDL auto-commits. Guarded steps can be rerun after interruption, but a Python rollback cannot undo a partially applied schema. Do not drop V2 columns/tables to "roll back": new reports may have NULL official locations and request-linked allocations must retain their history. Recover from a tested private backup in a separate database, investigate the failed step and complete the guarded migration. Applying an older frontend/backend over V2 without compatibility checks is unsafe.

The opt-in integration test uses an empty dedicated _\_test database and refuses existing application records. To validate migration on a populated disposable copy, use the added populated-migration test with its own explicitly opted-in _\_migration_test database. Both must remain separate from the owner's database. See TEST_RESULTS and TESTING_CHECKLIST.
