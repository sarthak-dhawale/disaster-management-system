# Disaster Management System

A database-driven platform for disaster reporting, incident monitoring, and coordinated emergency response.

The Disaster Management System is a full-stack college DBMS project that connects public emergency reporting with disaster-manager review and operational resource coordination. Built with **React, FastAPI, and MySQL 8.4**, it brings disaster records, shelters, volunteers, and resource allocation into one application.

Version 4 enhances the application with an interactive India disaster map, a chronological Disaster Replay Studio, Resource Intelligence, and a What-if Response Simulator.

## Features

### Interactive Disaster Overview
- View disaster locations on an interactive map of India.
- Explore disaster markers, clustering, filters, and incident details.
- Access disaster records even when valid map coordinates are unavailable.
- Review overview information derived from the application's database.

### Emergency Reporting
- Allow public users to submit suspected emergencies for review.
- Support pending, confirmed, and rejected report statuses.
- Enable authorized disaster managers to review reports and handle confirmed incidents.

### Disaster Replay Studio
- Explore available incident history through a chronological timeline.
- Navigate recorded events and review their details.
- Generate timeline reports where supported.
- Represent only available historical evidence; older incidents may have incomplete timelines.

### Resource Intelligence
- Examine resource availability, demand, shortages, and allocations.
- Review resource movement history where recorded.
- Support resource planning using existing inventory data.

### What-if Response Simulator
- Explore hypothetical disaster-response scenarios.
- Compare outcomes using the implemented simulation tools.
- Keep simulation results separate from live operational records.

### Reporting and Exports
- Generate PDF reports where supported.
- Export supported data to CSV.
- Review incident information and available operational records.

### Authentication and Access Control
The application supports four roles:

| Role | Primary responsibility |
|---|---|
| `ADMIN` | Administrative operations and account management |
| `DISASTER_MANAGER` | Incident review and disaster-response operations |
| `VOLUNTEER` | Volunteer-specific operations and permitted reporting workflows |
| `PUBLIC_USER` | Submit suspected emergencies and track permitted personal reports |

Backend authorization determines which operations each role can perform.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React 19, JavaScript, Vite 7 |
| Maps | Leaflet 1.9 |
| Backend | Python, FastAPI |
| Database | MySQL 8.4 |
| Database access | SQLAlchemy 2, PyMySQL |
| PDF generation | ReportLab, Pillow |
| Development tools | Git, Node.js, Docker Desktop |

## Prerequisites

Install the following before running the application:

- Python 3.10 for the primary development setup, or another version supported by the backend dependencies.
- Node.js compatible with the project's Vite version.
- MySQL 8.4.
- Docker Desktop if using the existing Docker-based database setup, or an existing local MySQL server.
- Git.

The primary development setup uses Python 3.10 and Docker-hosted MySQL. Python 3.12 may be used on another machine only if the installed dependencies are compatible.

## Getting Started

### 1. Configure the Environment

Open PowerShell in the repository root.

Create environment files from the examples **only if the corresponding private files do not already exist**:

```powershell
if (!(Test-Path backend\.env)) {
    Copy-Item backend\.env.example backend\.env
}

if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}
```

Configure the backend database connection in `backend/.env`, using the variable names supported by the project's configuration loader.

Typical settings may look like:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=disaster_management
DB_USER=your_database_user
DB_PASSWORD=your_private_password
```

Check the existing configuration loader before changing or adding variables. The root `.env` may be used by Docker Compose, while `backend/.env` contains backend configuration.

**Never commit passwords, session secrets, or private `.env` files.**

### 2. Start MySQL

On the primary development machine, start the existing Docker Compose services from the repository root:

```powershell
docker compose up -d
docker ps
```

Confirm that the existing MySQL container is running and that the database is reachable.

On a machine using local MySQL, start its existing MySQL service instead.

> **Database safety:** Preserve the existing `disaster-mysql` container, persistent volume, and populated `disaster_management` database. Do not delete the volume or execute destructive reset scripts against existing records.

### 3. Create the Python Environment

From the repository root:

```powershell
py -3.10 -m venv backend\.venv
```

Install the backend dependencies:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If `backend/.venv` already exists and is compatible, reuse it instead of recreating it.

### 4. Back Up and Migrate the Database

Before applying migrations or sample data:

1. Stop backend processes that could write to the database.
2. Create a database backup using the appropriate Docker or local MySQL procedure.
3. Verify that the backup completed successfully.
4. Review `database/V4_SAMPLE_DATA.md` for the detailed migration and safety instructions.

From the `backend` directory, run the documented migration:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.setup_db migrate
```

This workflow is intended for an existing supported schema. Use the documented fresh-initialization procedure only for a genuinely empty database.

**Never use destructive initialization scripts to repair or reset a populated database.**

## Optional: Add V4 Demonstration Data

The optional V4 dataset contains fictional disaster scenarios and related operational records. These are demonstration records, not verified current emergencies.

After backing up the database and applying the required migration, open a terminal in `backend` with the Python environment active.

First validate the seed plan:

```powershell
python ..\database\seed_v4.py --check
```

This check does not connect to MySQL or write records.

If the check succeeds and you want to add the demonstration dataset, run:

```powershell
python ..\database\seed_v4.py --apply
```

Choose a demonstration-account password when prompted.

The seed script is designed to insert the dataset transactionally, preserve existing records, and refuse conflicting or incomplete demonstration namespaces. Review `database/verify_v4.sql` for read-only verification queries.

For the complete procedure, including backups, migration, and verification, see [`database/V4_SAMPLE_DATA.md`](database/V4_SAMPLE_DATA.md).

## Running the Application

### 1. Start the Backend

From the `backend` directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Keep this terminal open.

Once the backend is running, the following endpoints should be available if configured as documented:

- API health: `http://127.0.0.1:8001/health`
- FastAPI documentation: `http://127.0.0.1:8001/docs`

### 2. Start the Frontend

**Option A: Serve the prebuilt frontend**

Open a second terminal at the repository root:

```powershell
python .\scripts\serve_frontend.py
```

If the serving script and build output are present and configured for port `5500`, open:

`http://127.0.0.1:5500`

**Option B: Run React in development mode**

Open another terminal in `frontend`:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite.

After changing React source files, build the frontend when the deployment workflow requires the production output:

```powershell
npm run build
```

Do not run two frontend servers on the same port simultaneously.

## Database and Project Structure

The repository contains the main application and database-related resources:

| Path | Purpose |
|---|---|
| `frontend/` | React frontend and its build configuration |
| `backend/` | FastAPI application and Python dependencies |
| `database/` | SQL scripts, migration-related resources, sample-data utilities, and verification queries |
| `scripts/` | Project utility scripts, including the frontend serving script where present |
| `README.md` | Project overview and setup instructions |

Database scripts have different purposes. Review a script before executing it, particularly if it contains table drops, deletes, or other destructive operations.

## Testing

Run tests available in your checkout and review their actual results.

Backend tests, if the development requirements and test suite are present, can be run from `backend`:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Frontend or Node.js tests should be run using the scripts and test files present in the repository. For example, where these files exist:

```powershell
node --test tests/map-pages.test.js tests/replay.test.js tests/navigation.test.js
```

A successful build alone does not establish that the entire application works end to end. Before a demonstration, verify the database migration, login and role permissions, incident reporting, persistence after restart, map behavior, and report downloads in the intended environment.

## Known Limitations

- Historical replay depends on recorded audit data. Older incidents may have incomplete histories.
- Demonstration records are fictional and must not be treated as verified emergencies.
- Map visibility depends on available coordinates and active filters.
- Resource map locations depend on the locations supported by the current data model.
- Shelter registrations may not have a direct disaster relationship in the existing schema.
- Simulation results are hypothetical and must remain separate from live operational records.
- External map tiles and geocoding services may require internet access.

## Security and Data Safety

- Keep credentials, private environment files, database backups, virtual environments, and dependency folders out of Git.
- Back up the database before applying migrations or demonstration data.
- Never execute destructive legacy SQL scripts against a populated database.
- Change or disable demonstration accounts before any wider deployment.
- Use HTTPS and secure cookie settings outside local development.
- Treat backend authorization—not frontend visibility—as the security boundary.

## Project Status

This is a college DBMS project demonstrating database design, full-stack application development, role-based access, incident reporting, and disaster-response workflows.

The verification status should reflect the code, test results, and database walkthrough for the version being demonstrated.
