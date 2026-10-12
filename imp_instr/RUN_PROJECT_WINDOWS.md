# Run V3 on Windows

Project root on the primary laptop: `E:\CS\sarthak-disaster-management-system`. If installed elsewhere on the secondary laptop, replace that path with its actual checkout. Use PowerShell terminals.

1. Primary: start Docker Desktop and follow DOCKER_MYSQL_SETUP.md to start the existing database. Secondary: start the existing local MySQL 8.4 service; follow SETUP_WITHOUT_DOCKER.md. Both must make port 3306 available to the API at 127.0.0.1.
2. Open the project root:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system
```

3. Create a virtual environment only if it does not already exist. Primary:

```powershell
py -3.10 -m venv backend\.venv
```

Secondary uses `py -3.12 -m venv backend\.venv`. Do not transfer a virtual environment between laptops.

4. Install dependencies (activation is optional):

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Optional activation: `.\backend\.venv\Scripts\Activate.ps1`. If Windows blocks activation, use the executable commands shown here instead of changing system execution policy.

5. Preserve existing private environment files. Only if `backend\.env` is missing:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set the existing application's DB username/password, host 127.0.0.1, port 3306 and database disaster_management. No real password is included in the ZIP. Keep root `.env` (Docker) separate from `backend\.env` (API). Use the same hostname in both browser URLs: 127.0.0.1.

6. V3 adds no database migration. If V2 already works, do not initialize it. If upgrading an older schema, back up first and explicitly run the existing additive migration as described in V3_MIGRATION.md. Fresh initialization is only for a new, empty secondary database.

7. Start the API from the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/health and http://127.0.0.1:8001/docs. Healthy means database connected; 503 means unavailable. The server can start while MySQL is offline, but operational features then remain unavailable.

8. In a second terminal at the root, serve the included React build:

```powershell
.\backend\.venv\Scripts\python.exe scripts\serve_frontend.py
```

Open http://127.0.0.1:5500. This does not require Node. Do not open `frontend/index.html` as a file or serve the source directory directly.

9. Sign in using an existing legitimately provisioned account. If no administrator exists, in a third terminal:

```powershell
Set-Location E:\CS\sarthak-disaster-management-system\backend
.\.venv\Scripts\python.exe -m app.manage create-admin --email your-address@example.com --name "Your Name"
```

Replace the example email. The command prompts privately for your chosen password; none is hardcoded. Public accounts use Create a public account on the login page. Passwords require at least 10 characters for registration. Do not invent or reuse a demo password from old SQL samples.

10. Verify: public user submits a suspected emergency; administrator sees pending review, selects a verified location if needed, confirms or rejects; confirmed status persists and repeated confirmation does not duplicate disasters. Test resource demand approval and cancellation; run a hypothetical Assam flood simulation; verify no inventory, disaster, audit or ledger writes from the simulation. Follow TESTING_CHECKLIST.md.
11. Stop frontend/API with Ctrl+C. Primary: `docker stop disaster-mysql`; secondary: stop the actual MySQL service if wanted. No volume removal is needed.

Optional source rebuild (Node 22.12+ or 20.19+):

```powershell
Set-Location E:\CS\sarthak-disaster-management-system\frontend
npm ci
npm run build
```

For frontend development use `npm run dev` instead of the Python frontend server; both bind 5500, so run only one. `VITE_API_URL` is an optional public build-time URL, never a secret. The distributed build uses http://127.0.0.1:8001.
