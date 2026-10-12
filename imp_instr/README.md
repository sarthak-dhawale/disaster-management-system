# Disaster Management System V3

Start with RUN_PROJECT_WINDOWS.md and choose the laptop guide below. V3 is an incremental upgrade: existing FastAPI routes, MySQL tables, cookies, roles, approvals are retained. The frontend folder now contains only the React/Vite application, its assets, tests and production build. The earlier repository had no React setup; V3 adds it as requested.

| Layer          | Entry point                                                  | Local address         |
| -------------- | ------------------------------------------------------------ | --------------------- |
| React frontend | `frontend/src/main.jsx`; packaged `frontend/dist/index.html` | http://127.0.0.1:5500 |
| FastAPI        | `backend/app/main.py`                                        | http://127.0.0.1:8001 |
| MySQL 8.4      | Existing Docker container or local Windows installation      | 127.0.0.1:3306        |

The primary laptop uses Python 3.10 and Docker Desktop. The secondary laptop uses Python 3.12 and local MySQL. Both use `disaster_management`, the same compatible V2 schema and the same application ports. No Docker command is needed on the secondary laptop. Node is needed only when rebuilding the frontend, not to run the included build.

Folders: `backend/app` API/security/business logic; `backend/tests` isolated tests plus guarded MySQL integration; `backend/assets/fonts` licensed PDF fonts; `frontend/src` reusable React modules; `frontend/dist` runnable production build; `database` preserved SQL; `scripts` local frontend server; `imp_instr` setup, audit and verification documentation.

New features: embedded Overview map, consistent light/dark interface, live Resource Intelligence, explicitly hypothetical Response Simulator, ReportLab PDFs and filtered CSV. All actual operational data comes from the API. No fallback records are invented. Simulations do not write live records.

Read SETUP_WITH_DOCKER.md on the primary laptop, SETUP_WITHOUT_DOCKER.md on the secondary, ENV_CONFIGURATION.md for configuration, V3_FEATURE_GUIDE.md for behavior and limits, TRANSFER_TO_PRIMARY.md for ZIP installation, and TEST_RESULTS.md for actual verification. V1/V2 audit files remain historical records; these V3 guides define current startup.

Stop API and frontend with Ctrl+C. On the primary laptop, `docker stop disaster-mysql` stops MySQL without removing its volume. On the secondary laptop, stop the identified MySQL Windows service only when desired. Never remove the database volume or run legacy reset scripts.
