# V3 verification — 12 October 2026

Status: implementation delivered; full acceptance with the owner's existing MySQL records remains unverified. No production SQL, database initialization, migration, Docker command or database reset was executed.

Environment: Windows, bundled CPython 3.12.14, Node 22.23.1, Vite 7.3.7. Primary laptop Python 3.10 runtime and Docker MySQL 8.4 were not available for end-to-end testing. TCP 127.0.0.1:3306 had no listener. The image describes the intended laptops, not proof of this environment's installed software.

## Executed checks

| Check                                                 | Actual result                                                                                                                                                      |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Before V3 baseline                                    | 177 passed, 3 opt-in MySQL tests skipped                                                                                                                           |
| V3 regression suite before final CSV expansion        | 208 passed, 4 opt-in tests skipped; 3.22 seconds                                                                                                                   |
| Final V3 test file, including expanded simulation CSV | 32 passed; 0.77 seconds                                                                                                                                            |
| Final individual unchanged regression files           | additional 9, CRUD 8, history 43, V2 29 passed                                                                                                                     |
| Final individual MySQL files                          | 3 integration tests and 1 migration test skipped                                                                                                                   |
| Final combined rerun and two individual older files   | Bundled Windows Python access-violation crash; not a passed final full-suite run                                                                                   |
| Frontend Node tests                                   | 4 passed: shared cache, cancellation, field errors/no fake fallback, filter encoding                                                                               |
| Production frontend build                             | Passed; default API 8001; no fixture API URL in build                                                                                                              |
| Python 3.10 syntax check                              | 49 application/test/script files accepted; not a 3.10 runtime test                                                                                                 |
| ReportLab PDF checks                                  | Valid PDFs, escaped text, accented Latin, Devanagari visual inspection, empty results, multi-page headers, map/legend and page footers                             |
| Browser fixture checks                                | All 17 destinations loaded; ten create dialogs opened/closed without saving; navigation, search, theme and simulator checked                                       |
| Observed browser sizes                                | CSS widths 2560, 1440 and 480; no page-level horizontal overflow. 375 CSS pixels could not be produced by the browser tool and remains unverified                  |
| Simulator browser fixture                             | Demand 150 litres vs available 100: Plan A proposes 100, leaves 50 unmet; shelter demand 2000 vs spare 80: gap 1920. Clearly labelled isolated QA, never real data |
| Live production startup                               | Frontend 5500: 200; API 8001 root/docs: 200; health: 503 disconnected. Backend subsequently stopped at user's request                                              |

The last browser download check was interrupted; no successful browser download is claimed. Export endpoint/PDF/CSV tests passed against fixtures. Browser fixtures and overrides are outside the project and excluded from the ZIP. Browser CRUD mutations, actual data persistence, concurrent MySQL locking, primary-laptop transfer and performance with realistic records remain unverified.

The bundled Python runtime intermittently crashes with Windows access violations, including unchanged test files. An earlier complete 208-test run passed. Do not treat the later crash as a successful run or hide it. Rerun the final full suite in the owner's freshly installed Python environment. One Starlette/AnyIO deprecation warning was observed; it did not fail successful runs.

## Owner commands — unit tests

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Set-Location backend
.\.venv\Scripts\python.exe -m pytest --assert=plain -q tests
```

## Owner commands — dedicated MySQL integration

Create a separate empty MySQL database named `dms_v3_test` and a test account restricted to it. Do not use disaster_management or its credentials/database URL. Never point these tests at an existing populated database. The fixture rejects database names without `_test` and pre-existing application records; it removes only IDs it created, and keeps dedicated audit rows.

```powershell
$env:DMS_RUN_MYSQL_TESTS='1'
$env:DMS_TEST_DATABASE_URL='mysql+pymysql://TEST_USER:URL_ENCODED_PRIVATE_PASSWORD@127.0.0.1:3306/dms_v3_test'
.\.venv\Scripts\python.exe -m pytest --assert=plain -q tests/test_mysql_integration.py
Remove-Item Env:DMS_RUN_MYSQL_TESTS
Remove-Item Env:DMS_TEST_DATABASE_URL
```

Replace placeholders privately. Test credentials must never be committed. These opt-in tests cover real CRUD/auth/review, request approval/cancellation, geography/exports, and V3 no-change simulation signatures including inventory, occupancy, audit and ledger counts. They are provided, not executed here.

Populated additive V1/V2 migration verification requires another separate disposable empty `dms_migration_test` database. Set `DMS_RUN_MIGRATION_TESTS=1` and `DMS_MIGRATION_DATABASE_URL` to its dedicated URL, then run `tests/test_populated_migration.py`. V3 itself adds no schema change. Follow TESTING_CHECKLIST.md for existing-record persistence and primary Docker-volume verification.


## Frontend cleanup verification — 12 October 2026

After moving React from web to frontend and removing the old UI: production build passed (49 modules, 1.49 seconds reported), four frontend tests passed, and six relevant PDF tests passed with 26 deselected. Local map boundary assets and attribution were preserved in frontend/public/data; PDF renderer uses that path. No database connection or backend service startup was needed for these tests.
