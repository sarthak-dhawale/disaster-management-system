# Migrations

Explicit safe CLI: from backend run `python -m app.setup_db migrate` after backup and disposable validation. Fresh empty database only: `python -m app.setup_db init --fresh`. V2 guarded implementation is app/v2_schema.py; history installation is app/history_schema.py. See ../../imp_instr/V2_MIGRATION.md for prerequisites, additive changes, idempotency and MySQL DDL recovery limitations.

Legacy SQL migrations/scripts remain reference material. Never execute reset/drop/sample scripts on a populated database. Normal application startup runs no migration.
