> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# DBMS extension audit

Scope approved: persistent audit history, resource movement ledger, analytical reports.
Inspected the existing CRUD transactions, session authorization, ten-table safe schema,
additive migration, frontend shared controller and tests before modifying application code.

| Finding                                                                           | Severity   | Correction                                                                      | Verification                                                 |
| --------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Reviewed reports retain only the latest state; other CRUD changes have no history | Medium     | Append audit rows through transactional MySQL triggers; no history mutation API | Trigger source tests and opt-in MySQL rollback/history test  |
| Stock is updated correctly but its movements cannot be traced                     | Medium     | Ledger triggers plus locked restock/withdraw endpoint                           | Quantity/rollback tests and MySQL reconciliation             |
| No analytical reports page                                                        | Medium     | Aggregate views, protected API, shared-layout page                              | SQL/source and API checks; MySQL results require integration |
| Credentials and pooled sessions must not enter history                            | High       | Explicit snapshot allowlist; clear connection actor/context on checkout         | Sensitive-field and actor-reset tests                        |
| Historical movements cannot be reconstructed                                      | Limitation | Record migration-time opening balances, never fabricate prior events            | Idempotent migration and documented opening semantics        |

No existing tables will be dropped or reset. Migration adds two tables, three views
and versioned triggers. Run with application stopped and a database backup.
