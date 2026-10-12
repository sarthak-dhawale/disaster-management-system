# V3 changes - 12 October 2026

Added React/Vite frontend and a runnable prebuilt distribution while retaining legacy HTML/JS. New shared layout, restrained warm/light and navy/dark themes, account controls, responsive sidebar, reusable CRUD forms, validation, relation lookup, tables, dialogs, loading/error/empty states and stale-response-safe request caching. India map moved into Overview; Volunteers uses the simplified label; all existing modules remain accessible.

Added actual Resource Intelligence with competing stock totals, coverage/delivery distinctions, safe approval reuse, demand edits/cancellation and history/ledger detail. Added pure read-only hypothetical simulator, three plans from one server snapshot, owner-scoped bounded memory results, reserve/shortage/shelter calculations and clearly labeled exports.

Added ReportLab PDF generation, local Pillow India map, licensed Noto fonts, operational shelter CSV, Overview/Resource Intelligence/Detailed Reports exports and filter parity. Exposed safe Content-Disposition header, added request_id allocation filtering and fixed sanitized unexpected-error CORS visibility. Existing CRUD/auth/review/inventory/capacity logic remains in place.

V3 makes no database schema change, runs no migration automatically, changes no Compose configuration and does not touch live records, containers or volumes. No source file/module was removed. New unit/frontend tests and guarded owner-run V3 MySQL integration were added. Updated all current startup/transfer/security/testing guides; previous phase audit documents remain historical.

Verification limits and remaining owner-run checks are recorded in TEST_RESULTS.md. Source remains uncommitted; Git history was preserved. The ZIP excludes private/generated development material except the intentional runnable frontend build.

## Frontend folder cleanup — 12 October 2026

Moved React from web/ to frontend/. Removed the V1/V2 HTML/CSS/JS, legacy tests and bundled vendor directory from the project. Retained boundary data in frontend/public/data and updated PDF generation to read it. Updated the frontend server and current setup instructions. No backend operations or database files changed. A recovery copy of the removed UI is stored outside the project in the development workspace.
