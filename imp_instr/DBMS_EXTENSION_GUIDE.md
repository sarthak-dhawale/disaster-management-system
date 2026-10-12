> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# DMS V1.2: DBMS additions

Added to the existing project: administrative Audit history, Resource ledger and
Analytical reports pages. Plain HTML/CSS/JavaScript, FastAPI and MySQL 8.4 remain.

## Apply to the owner's database

1. Make a MySQL backup using the existing Docker setup and verify the backup file.
2. Stop FastAPI and pause other writers. Do not run schema.sql or sample_data.sql.
3. Start Docker Desktop and run `docker compose up -d` from
   `E:\CS\sarthak-disaster-management-system`.
4. In PowerShell, use the project's Python environment:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
.\.venv\Scripts\Activate.ps1
Set-Location backend
python -m pip install -r requirements.txt
python -m app.setup_db migrate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

If the existing venv is unusable, create one with an installed Python 3.12:
`py -3.12 -m venv .venv` from the project root. See RUN_PROJECT_WINDOWS.md for initial configuration.
In a second terminal:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Open http://127.0.0.1:5500/login.html and use a provisioned administrator account.
Public accounts cannot access the three new modules or change inventory.

The migration adds `audit_history`, `resource_movements`, three `dms_*` views,
30 versioned audit triggers and three resource ledger triggers. It does not
replace existing objects, drop tables, reset stock, or change Docker volumes.
MySQL DDL auto-commits: if interrupted, resolve the error and rerun the migration.
Existing names are preserved; future changes to these definitions need a new
versioned migration. The migration account needs CREATE, ALTER, INDEX, TRIGGER,
CREATE VIEW and ordinary data privileges. On binary-logged MySQL, trigger creation
may additionally require the server's configured trusted creator/admin privileges;
have the database owner handle that setting rather than weakening it automatically.

## History and transaction guarantees

Audit triggers run in the same InnoDB transaction as the operation. Rollback
also rolls back new history. INSERT, UPDATE and DELETE are recorded for the ten
management tables. UPDATE records are emitted only when the selected snapshot
fields change. History contains selected operational fields, not a full record:
passwords/hashes, session tokens, email, phone, emergency contacts and account
authentication events are intentionally excluded. Changing only an excluded field
does not generate a snapshot change.

Each authenticated request sets its actor ID/name on the database connection.
Connection checkout clears actor and movement context to prevent pooled identity
leaks. Maintenance scripts, public registration and direct SQL writes have an
unknown actor. Actor IDs are historical references, not proof of identity for
privileged direct SQL clients, which can set session variables themselves.

History has no foreign keys to source records: deleting a source/actor must not
delete its history. The API exposes read-only access; a database owner can still
alter/delete history. This is a college-project audit trail, not a tamper-proof log.
MySQL foreign-key cascades do not fire child triggers. Use the API's dependency
checks rather than deleting parent rows directly when complete child history matters.

## Resource ledger definitions

- OPENING: stock at resource creation, or a migration-time snapshot of existing stock.
  Earlier movements are unknown, never reconstructed. Rerunning migration creates
  no second opening when a resource already has ledger entries.
- RESTOCK: increase both total and available stock, with a required reason.
- WITHDRAW: decrease both totals using available stock only (loss, damage or removal).
- ALLOCATION_CHANGE: net available-stock change caused by allocation creation,
  editing or cancellation; references the allocation. Switching resources records
  restoration and allocation separately for their respective resource IDs.
- RETURN: allocation deletion restores its reserved stock.
- INVENTORY_ADJUSTMENT: quantity edits through the resource form or direct SQL.
- REMOVAL: resource deletion records negative balances and a zero resulting balance.

Restock and withdrawal lock the resource with FOR UPDATE, use Decimal arithmetic,
enforce inventory bounds, and commit once. Allocation operations retain existing
locking and reserved-stock checks. Cancellation returns stock; delivered allocations
remain reserved under the existing data model. The UI prevents editing resource
units; create a separate resource if the unit differs.

For each resource, opening plus subsequent available deltas should equal current
available stock (or zero after deletion). Total deltas similarly reconcile total
stock. Do not aggregate quantities across different resources/units.

## Analytical reports

- Shelter occupancy: reported current occupancy, capacity, remaining capacity,
  occupancy percentage, and active registration count. Closed shelters are included
  and visibly labelled; their remaining spaces are not necessarily usable.
- Disaster response: non-cancelled allocation count, distinct resource types,
  and distinct volunteers with ASSIGNED or ACTIVE assignments. Pre-aggregated joins
  prevent allocation/volunteer cross-products from inflating counts.
- Reports by month/location: submission month in the configured MySQL session
  timezone, exact location reference, and all four review-state counts. Reports at
  different addresses in one city remain separate groups.
- Allocated supplies: non-cancelled quantities per disaster/shelter target and
  resource/unit. Quantities in different units are never summed into a grand total.

All lists use bounded server pagination; history additionally supports date filters
(inclusive Through date), module/action/record or resource/movement filters. Refresh
loads the real API. Counts and rows can change during concurrent activity under the
existing READ COMMITTED isolation; these are operational reports, not frozen exports.

## Test and demonstrate

```powershell
Set-Location E:\CS\sarthak-disaster-management-system\backend
python -m pytest -q --assert=plain tests
Set-Location ..
node frontend/tests/check.cjs
```

`--assert=plain` retains Python assertions but avoids pytest's assertion rewriting;
the bundled Python runtime here crashed during rewriting. Ordinary pytest also
worked for the previous suite. No production database is used by these unit tests.

For the real integration test, create a dedicated, empty MySQL database whose name
ends `_test`, configure its own account and set these variables in PowerShell:

```powershell
$env:DMS_RUN_MYSQL_TESTS = '1'
# Set DMS_TEST_DATABASE_URL privately to the dedicated mysql+pymysql test URL.
python -m pytest -q --assert=plain tests/test_mysql_integration.py
```

The integration test refuses existing application records and never uses the owner's
DATABASE_URL. It applies the additive migration, checks actual history/ledger/view
results, verifies failed withdrawals create no ledger row, and cleans only fixture
IDs. History intentionally remains in the test database. Do not use your development
database even if its name is changed to end `_test`.

Manual demo: restock a resource with a receipt note; allocate supplies; cancel the
allocation; inspect the resulting ledger and audit snapshots; confirm a pending
report twice and verify one review change/official incident; open all four analytical
reports; verify public access receives 403. Compare counts directly with MySQL.

## Executed verification (2026-10-11)

134 unit/API tests passed; one real MySQL test skipped. Frontend source checks passed
for 16 HTML pages and 18 scripts. Browser checks used an isolated UI test API, never
installed in the project: all three pages rendered, the audit detail dialog escaped
script-like text, empty stock submission was blocked by four required fields,
analytics rendered, and no console errors were observed. At 390x844 the page width
remained 390px; wide tables scroll inside their containers.

Docker CLI/Desktop were absent and port 3306 was not listening. Therefore actual
MySQL trigger creation, migration repeatability, view output, concurrent operations
and persistence remain unverified. No owner database migration was executed. UI
fixtures were stopped after verification; they are not a working application demo.

Actual V1.2 startup verification: frontend login, API root and /docs returned HTTP 200 on ports 5500/8001. /health correctly returned HTTP 503 with database disconnected. Actual servers were started using the bundled Python runtime; no mock dependencies are installed in the project. MySQL remains unavailable.

## V2 integration

Resource requests extend the existing inventory with demand, not another stock table. Three additional request audit triggers bring the history/ledger trigger count to 36. Original 33 triggers and three reporting views are retained. Resource details expose the ledger, incident details expose history and Overview embeds analytics; standalone pages/endpoints remain available. Before migration see V2_MIGRATION.md. No V2 migration was executed on a real database in this environment.
