# Disaster Management System V4

A local college DBMS application for suspected-emergency reporting, administrator review and coordinated operational records. React communicates with FastAPI and MySQL 8.4. V4 adds comprehensive incident-map retrieval and a read-only Disaster Replay Studio.

## Features

- Public reports with pending, confirmed and rejected review states; confirmation creates or links an official disaster.
- Disaster, location, shelter, volunteer, inventory, allocation, assignment and registration management.
- Overview with database metrics, India map, clustering, filters, marker selection and missing-location records.
- Advanced Tools: Disaster Replay Studio, Resource Intelligence and Response Simulator.
- Chronological audit replay, timeline PDFs, actual-data PDF/CSV exports and resource movement history.
- Four roles with backend authorization; Argon2 password hashes and expiring cookie sessions.
- Optional, explicitly fictional V4 sample batch that preserves existing records.

## Stack and requirements

React 19, Vite 7, Leaflet 1.9, Python/FastAPI, SQLAlchemy 2, PyMySQL, MySQL 8.4, ReportLab and Pillow. Windows Python 3.10 on the primary laptop or Python 3.12 on the secondary laptop. Node 20.19+ or 22.12+ is needed for source builds, but the included `frontend/dist` can run through Python without Node. Docker Desktop is required only for the primary laptop's Docker-hosted MySQL setup.

```text
backend/app/      API, validation, permissions, operational logic and replay
backend/tests/    Isolated tests and explicitly opt-in MySQL integration tests
database/         Schema, guarded migration guidance, optional V4 seed and verification
frontend/src/     React interface, maps and shared components
frontend/dist/    Prebuilt frontend
scripts/         Local frontend server
imp_instr/       Setup, troubleshooting and implementation handover
imp_docx/        Academic presentation, proposal, report and case study
```

## Environment

Preserve existing `.env` files. Only copy examples when private configuration does not already exist:

```powershell
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
# Docker laptop only:
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `backend/.env`: `DB_HOST=127.0.0.1`, `DB_PORT=3306`, `DB_NAME=disaster_management`, and the existing `DB_USER`/private `DB_PASSWORD`. Optional `DATABASE_URL` overrides these fields. `DB_TIME_ZONE` defaults to `+05:30`. Keep `CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500`, `COOKIE_SECURE=false` for local HTTP, and a finite `SESSION_HOURS`. Use secure cookies behind HTTPS for wider deployment. `VITE_API_URL` is a public build-time URL, defaulting to `http://127.0.0.1:8001`. It must never contain credentials.

## Database setup and backup

Open PowerShell at the project root. The primary laptop uses the existing container and volume:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
docker compose up -d
docker ps
docker logs disaster-mysql
```

Keep container `disaster-mysql` and volume `disaster_mysql_data`. Removing the persistent volume can permanently delete records. On the secondary laptop, start its existing local MySQL 8.4 service instead; Docker commands are unnecessary. Both setups expose MySQL to the directly running API at `127.0.0.1:3306`. An API inside Compose would use service hostname `mysql`.

Before any migration or seeding, stop backend writers and back up the configured database. Exact Docker/local commands are in [V4 sample-data instructions](database/V4_SAMPLE_DATA.md). For a local MySQL client:

```powershell
mysqldump -h 127.0.0.1 -P 3306 -u disaster_user -p --single-transaction --routines --triggers --no-tablespaces disaster_management --result-file=dms-before-v4.sql
```

Use the actual configured database/account and verify the dump succeeded. Credentials are entered at the prompt. Never use legacy reset scripts on a populated database.

## Python environment and explicit migration

```powershell
# Create only if absent; secondary laptop uses py -3.12.
py -3.10 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.\.venv\Scripts\python.exe -m app.setup_db migrate
```

V4 retains 14 tables and refreshes outdated owned audit triggers for future snapshots. DDL auto-commits; keep writers stopped and rerun if interrupted. For a genuinely empty database only, `python -m app.setup_db init --fresh` initializes and migrates it, refusing an existing schema. Never run initialization to repair a populated database.

Optional fictional data, still in `backend`:

```powershell
.\.venv\Scripts\python.exe ..\database\seed_v4.py --check
.\.venv\Scripts\python.exe ..\database\seed_v4.py --apply
```

The check does not connect to MySQL. Apply prompts for a new demo password and inserts an atomic batch: 12 disasters, 16 shelters, 20 resources, 12 volunteers, 10 public users, 2 role accounts and related records. Reruns preserve an intact batch; conflicts cause refusal. These are fictional scenarios, not verified emergencies. No sample account exists until the seed succeeds. Inspect `database/verify_v4.sql` and run its read-only queries afterward.

## Start the application

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

In a second PowerShell window at the root:

```powershell
.\backend\.venv\Scripts\python.exe scripts\serve_frontend.py
```

- Application: http://127.0.0.1:5500
- Health: http://127.0.0.1:8001/health
- API documentation: http://127.0.0.1:8001/docs

For React development, use `npm ci` once when dependencies are absent, then `npm run dev` in `frontend`. This replaces the Python frontend server on the same port. After editing React sources, `npm run build` refreshes the prebuilt interface.

Provision an administrator without a hardcoded password if no legitimate account exists:

```powershell
# In backend
.\.venv\Scripts\python.exe -m app.manage create-admin --email your-address@example.com --name "Your Name"
```

The command prompts privately. Seeded demonstration accounts use the password selected during `--apply`; the script prints their email references, never their password. Public self-registration remains available.

## Roles

| Role | Purpose |
|---|---|
| ADMIN | Response operations, Advanced Tools and account administration |
| DISASTER_MANAGER | Response operations and Advanced Tools |
| VOLUNTEER | Existing owned-report submission and tracking permissions |
| PUBLIC_USER | Submit suspected emergencies and track own reports |

## Verification and troubleshooting

Install development requirements only when running tests. Focused V4 checks:

```powershell
# In backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q tests/test_v4_overview.py tests/test_v4_replay.py tests/test_v4_seed.py
# In frontend
node --test tests/map-pages.test.js tests/replay.test.js tests/navigation.test.js
```

The V4 implementation recorded 16 new backend checks, 5 prior backend regression checks and 7 targeted frontend checks passing, plus production builds and an isolated UI review. This does not certify the owner database: migration, seed execution, stock/capacity verification and restart persistence still require the MySQL walkthrough. Timeline PDF API/content validation passed; a browser download wait did not complete in the isolated review; verify exports on the demonstration laptop. Earlier tests remain available and are not claimed as rerun in full for V4.

For API 503, check MySQL readiness, credentials and schema migration. For port conflicts, stop only the application's existing listener or choose/document a matching port and CORS configuration. For cookie/CORS failures, consistently use `127.0.0.1` in both URLs. Do not open source HTML through `file://`. Empty maps may reflect filters or absent coordinates; never replace database failures with fake data. External tiles/geocoding need internet, while the packaged boundary map and server PDF map use bundled data.

Replay history is partial for older incidents. It uses current geographic context and cannot recreate unknown historical states. Inventory has no warehouse-location field; resource map points represent allocation destinations. Shelter registrations have no direct disaster relationship. Simulation results are temporary and do not modify live records.

Stop frontend and API with Ctrl+C. Stop Docker MySQL with `docker stop disaster-mysql` when desired, preserving the volume. Keep `.env`, passwords, dumps, sessions, virtual environments and `node_modules` out of Git. Review sample accounts before any wider deployment.
