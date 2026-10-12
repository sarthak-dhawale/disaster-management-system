# Private configuration

Never commit or transfer `.env` files. `.env.example` contains placeholders only. Preserve existing root and backend `.env` on the primary laptop. This ZIP contains neither. Credentials previously exposed in archives or Git should be rotated deliberately; history is not rewritten by V3.

| Variable             | Purpose / safe example                                                                                   |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| DB_HOST              | 127.0.0.1 for API on Windows; mysql only for future API container                                        |
| DB_PORT              | 3306                                                                                                     |
| DB_NAME              | disaster_management                                                                                      |
| DB_USER              | Existing application account; normally disaster_user                                                     |
| DB_PASSWORD          | Private application password, never a real value in documentation                                        |
| DATABASE_URL         | Optional mysql+pymysql URL; overrides DB\_\*; URL-encode credentials                                     |
| DB_TIME_ZONE         | +05:30 for stored local incident datetimes                                                               |
| CORS_ORIGINS         | http://127.0.0.1:5500,http://localhost:5500; exact allowed origins                                       |
| COOKIE_SECURE        | false for local HTTP; true only with HTTPS                                                               |
| SESSION_HOURS        | 8; token expiry                                                                                          |
| GEOCODING_ENABLED    | true; optional place lookup can be disabled                                                              |
| GEOCODING_URL        | https://photon.komoot.io/api/                                                                            |
| GEOCODING_USER_AGENT | DMS-College-Project/3.0, no secret                                                                       |
| MAP_TILE_URL         | https://tile.openstreetmap.org/{z}/{x}/{y}.png; optional approved tile provider                          |
| VITE_API_URL         | Optional PUBLIC frontend build-time API URL, default http://127.0.0.1:8001; changing it requires rebuild |

Backend reads backend/.env independently of the terminal's working directory. Existing environment variables take precedence. SQL parameters and full URLs must not be logged. There is no V3 JWT/signing secret: existing random HttpOnly session cookies and hashed session tokens remain in use. The frontend stores only the theme preference, not passwords or bearer tokens.

Docker root `.env`: MYSQL_ROOT_PASSWORD (private), MYSQL_DATABASE (disaster_management), MYSQL_USER (existing app account), MYSQL_PASSWORD (private). Existing-volume passwords must match the actual stored MySQL accounts; changing Compose values alone does not reset them.

Tests use an intentionally invalid unit-test database URL and mocked dependencies. Optional integration uses DMS_RUN_MYSQL_TESTS=1 plus DMS_TEST_DATABASE_URL whose database ends `_test`; populated migration tests require DMS_RUN_MIGRATION_TESTS=1 plus DMS_MIGRATION_DATABASE_URL ending `_migration_test`. Never point either at disaster_management. All real-test safety guards must remain enabled.
