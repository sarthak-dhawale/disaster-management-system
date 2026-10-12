# V3 troubleshooting

**Health 503 / connection refused:** verify the correct MySQL instance is actually listening at 127.0.0.1:3306. Installed software alone is insufficient. Primary: Docker Desktop, existing disaster-mysql container and logs. Secondary: actual local MySQL Windows service. Do not install Docker as a workaround on the secondary laptop.

**Access denied:** backend/.env must match an existing account and password. DATABASE*URL overrides DB*\*; check for stale environment values without printing the URL. Changing Docker .env does not reset stored account passwords. Use the account's actual host permissions; do not expose MySQL publicly.

**Unknown table/column:** V3 assumes the already compatible V2 schema. Do not reset it. Back up and use the existing explicit additive migration only if upgrading an older schema. Fresh init refuses existing tables.

**Frontend missing build:** restore frontend/dist from the ZIP or run npm ci then npm run build in frontend. Start scripts/serve_frontend.py from the project, then use http://127.0.0.1:5500. Do not launch raw JSX files with file:// or serve the legacy frontend expecting V3 navigation.

**Cannot reach API / CORS / missing cookie:** start API on 8001; frontend on 5500; use 127.0.0.1 consistently for both. Origin must be in CORS_ORIGINS. Secure cookies need HTTPS; local HTTP uses COOKIE_SECURE=false. VITE_API_URL is built into the frontend: changing it requires rebuild. CORS errors can also accompany an unavailable backend; read health/docs first. Write requests require X-DMS-Request:1, supplied by the application.

**Port in use:** inspect `Get-NetTCPConnection -LocalPort 8001,5500,3306`. Stop only a process identified as this project's previous server. Python frontend and Vite dev server cannot both use 5500. Do not kill unrelated services/containers.

**Login failure:** use an existing account or provision an administrator through app.manage with an interactive password. SQL sample hashes are not usable known credentials. Ten failed attempts trigger a temporary rate limit; passwords require 10 characters when registering. No secret is available in the ZIP.

**Blank map / tiles offline:** local boundary data and coordinate records are separate from optional internet tiles. Check frontend /data assets and optional MAP_TILE_URL. Refresh after network recovery. Unlocated records are counted and listed. Manual addresses/coordinates work without Photon. Plan A cannot calculate resource transport distance because the schema has no warehouse geography.

**PDF missing dependency/font:** reinstall backend requirements; retain backend/assets/fonts and its license. PDF supports bundled Latin/Devanagari font coverage; other scripts need a suitable licensed font configuration/extension, or export UTF-8 CSV. PDFs use no browser print prerequisite.

**Export 413:** PDF/analysis/planning are deliberately bounded to 10,000 records. Narrow search/region/resource/disaster filters. Operational CSV is streamed without that PDF cap. Overview global inventory sections remain global and are labeled accordingly.

**Simulation 404:** reference expired (one hour), belongs to another manager, was discarded, or backend restarted. Run again. **503 memory limit:** discard old results and retry. Use one API worker; cache is process-local. No simulation data is restored from MySQL because it is never persisted there.

**Approval conflict:** another request may have consumed stock; refresh and approve a valid smaller amount. Cancellation/delivery quantities and audit history must agree. Never update inventory manually in MySQL to bypass constraints.

**PowerShell activation blocked:** use the virtual environment's python.exe directly as documented. Python 3.10 is the primary target, 3.12 the secondary. Reinstall dependencies in a locally created environment instead of transferring venv folders.

**Unit-test tooling issue:** documented `--assert=plain` avoids assertion-rewrite crashes seen with the bundled development interpreter. Isolated tests do not require MySQL. Real tests require an explicitly named empty dedicated test database, not the owner's development database.
