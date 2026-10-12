# Transfer V3 by pendrive

The finished ZIP includes source, existing SQL and React frontend, licensed assets and prebuilt frontend/dist. It excludes both .env files, Git history, virtual environments, node_modules, caches, logs and database dumps. It is an application archive, not a database backup.

1. Copy ZIP and SHA256 file to the pendrive. Verify checksum with `Get-FileHash .\DMS-V3-2026-10-12.zip -Algorithm SHA256` and compare it to the supplied checksum.
2. On the primary laptop, stop this project's API/frontend. Keep a backup of the existing source and a separate validated private MySQL backup. Keep root .env and backend/.env, including their actual existing credentials.
3. Extract the ZIP to a temporary directory for inspection. Merge `backend/app`, `backend/tests`, backend requirements/assets, `frontend`, `scripts` and `imp_instr` into `E:\CS\sarthak-disaster-management-system`. The ZIP has an enclosing `disaster-management-system-v3` folder: copy its CONTENTS, not the enclosing folder as a replacement checkout. Existing SQL scripts are included for reference; do not execute reset scripts.
4. Preserve the primary .git directory and private .env files. V3 did not change docker-compose.yml; keep the owner's existing copy and Compose project identity. Do not create a new MySQL container or volume from the temporary extraction directory. Start the existing disaster-mysql container; retain the actual mounted volume and disaster_management records.
5. Reuse or create a Python 3.10 virtual environment on this laptop and install backend requirements. Do not copy the secondary laptop's Python 3.12 virtual environment. Existing V2 database needs no V3 migration. If schema is older, follow V3_MIGRATION.md deliberately after backup.
6. Run API 8001 and prebuilt frontend 5500 using RUN_PROJECT_WINDOWS.md. Node is unnecessary unless rebuilding source. Use existing legitimate accounts or securely provision one through app.manage.
7. Perform the owner-run MySQL/end-to-end acceptance checklist. The development machine had no accessible running MySQL, so passing unit/UI fixture tests do not establish primary-laptop database verification.

Do not overwrite or reset any database using files from the ZIP. Do not remove disaster-mysql, its data volume or unrelated containers.


## Installing the cleaned frontend layout

Before copying this ZIP to a checkout that still has the V1/V2 frontend, move that existing frontend folder to a recovery folder outside the project. Copy the complete React frontend folder from the ZIP into its place; merging into the old folder would leave obsolete HTML/CSS/JS behind. If an earlier V3 web folder exists on the primary laptop, preserve any local edits in a recovery copy, then remove that obsolete web folder after the new frontend build is verified. Keep backend private .env, Git history, Docker configuration and existing MySQL data. Current server reads frontend/dist; npm commands run in frontend.
