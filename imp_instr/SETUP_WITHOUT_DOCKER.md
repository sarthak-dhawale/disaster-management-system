# Secondary laptop: Python 3.12 and local MySQL 8.4

Docker Desktop is not required. Use the existing local MySQL 8.4 installation. Identify its actual Windows service in Services; do not assume it is named MySQL84. Start that service and confirm 127.0.0.1:3306 is listening. A non-listening port means the database is unavailable even if MySQL was installed.

```powershell
Get-Service *mysql*
Get-NetTCPConnection -LocalPort 3306 -ErrorAction SilentlyContinue
```

Use MySQL Workbench or the installed MySQL client. If its executable is on PATH:

```powershell
mysql -u root -p
```

The password is prompted. Use the existing database/account if available. ONLY when preparing a new development instance, an administrator may create the database and application account:

```sql
CREATE DATABASE IF NOT EXISTS disaster_management CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'disaster_user'@'localhost' IDENTIFIED BY 'CHOOSE_A_PRIVATE_PASSWORD';
GRANT ALL PRIVILEGES ON disaster_management.* TO 'disaster_user'@'localhost';
```

Choose a real private password locally; the text above is a placeholder. CREATE USER IF NOT EXISTS does not reset an existing password. Grants are restricted to this project database. Your installation may require a matching 127.0.0.1 account; use an account that can connect through the actual TCP configuration rather than widening network access.

Create `backend\.venv` with `py -3.12 -m venv backend\.venv`, install backend requirements, and configure `backend\.env` as in RUN_PROJECT_WINDOWS.md. DB_HOST=127.0.0.1, DB_PORT=3306, DB_NAME=disaster_management; keep credentials private. Do not create root Docker `.env` on this laptop merely to run the app.

For an existing V2 schema: no V3 migration is required. For an older existing schema, back up then explicitly run `python -m app.setup_db migrate` from backend. For a genuinely new EMPTY schema only, from backend:

```powershell
.\.venv\Scripts\python.exe -m app.setup_db init --fresh
```

Initialization refuses existing tables and adds no fake demonstration records. Never run this against the owner's populated primary database. Provision an administrator interactively using app.manage. Run the API on 8001 and included frontend on 5500 using RUN_PROJECT_WINDOWS.md. Rebuild the frontend only when changing source; no Docker is involved.

The development session verified Python 3.12, but no listener was available on 3306 and the specifically named MySQL84 service was absent. This does not establish that every possible MySQL installation is absent. Real MySQL integration remains an owner-run verification step.
