# V3 database compatibility

V3 creates no table, column, trigger or view and performs no automatic migration on startup. Existing V2 schema and records are reused. New analysis uses resource_requests, resource_allocations, resources, disasters, locations, shelters and the existing history/ledger. Simulations reside temporarily in process memory, not MySQL.

If V2 already runs, install dependencies/source/frontend only. The existing app.setup_db migrate command remains available for an older schema. Back up first; MySQL DDL auto-commits and cannot be rolled back like ordinary CRUD. From backend:

```powershell
.\.venv\Scripts\python.exe -m app.setup_db migrate
```

This is the previously implemented additive V1/V2 migration, not a new V3 migration. It retains records, adds missing authentication/review/geography/request/history objects and does not invent legacy review events. Do not run database reset/demo scripts. Fresh initialization is restricted to a genuinely empty secondary database.

Example primary backup (password prompt, no secret on command line):

```powershell
docker exec -it disaster-mysql mysqldump -u root -p --routines --triggers disaster_management --result-file=/tmp/dms-before-v3.sql
docker cp disaster-mysql:/tmp/dms-before-v3.sql .\dms-before-v3.sql
```

Keep this private backup outside the transfer ZIP. Validate backup completion before migration. Local MySQL can use mysqldump with `--result-file=PATH` and a password prompt. The V3 development session did not run any migration or MySQL write.
