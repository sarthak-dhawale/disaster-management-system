"""Safe fresh initialization and repeatable additive MySQL migration."""

import argparse
from pathlib import Path
from sqlalchemy import inspect
from app.database import engine

REPORT_COLUMNS = {
    "disaster_type": "ENUM('FLOOD','EARTHQUAKE','CYCLONE','LANDSLIDE','FIRE','DROUGHT','TSUNAMI','OTHER') NOT NULL DEFAULT 'OTHER'",
    "occurred_at": "DATETIME NULL",
    "review_status": "ENUM('PENDING_REVIEW','CONFIRMED','REJECTED','LEGACY') NOT NULL DEFAULT 'PENDING_REVIEW'",
    "review_reason": "VARCHAR(1000) NULL",
    "reviewed_at": "DATETIME NULL",
    "reviewed_by": "INT NULL",
}
SESSION_SQL = """
CREATE TABLE IF NOT EXISTS auth_sessions
  (token_hash CHAR(64) CHARACTER
   SET ascii COLLATE ascii_bin PRIMARY KEY, user_id INT NOT NULL, expires_at DATETIME NOT NULL, INDEX idx_sessions_expiry(expires_at),
                                                                                                      CONSTRAINT fk_session_user
   FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE) ENGINE=InnoDB
"""


def sql_statements(source):
    delimiter = ";"
    buffer = ""
    for line in source.splitlines():
        if line.strip().startswith("--"):
            continue
        if line.strip().upper().startswith("DELIMITER "):
            delimiter = line.strip().split()[1]
            continue
        buffer += line + "\n"
        if buffer.rstrip().endswith(delimiter):
            yield buffer.rstrip()[: -len(delimiter)].strip()
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete SQL statement")


def migrate():
    # MySQL DDL auto-commits. Each guarded step is safe to rerun after interruption.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        tables = set(inspect(conn).get_table_names())
        required = {
            "users",
            "locations",
            "disasters",
            "shelters",
            "volunteers",
            "resources",
            "emergency_reports",
            "resource_allocations",
            "volunteer_assignments",
            "shelter_registrations",
        }
        if not required.issubset(tables):
            raise RuntimeError(
                "Existing schema incomplete. Initialize only a fresh empty database, or restore missing tables from backup."
            )
        columns = {c["name"] for c in inspect(conn).get_columns("emergency_reports")}
        for name, definition in REPORT_COLUMNS.items():
            if name not in columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE emergency_reports ADD COLUMN {name} {definition}"
                )
        # Backfill only legacy states still carrying the default review status.
        conn.exec_driver_sql("""
UPDATE emergency_reports
SET review_status=CASE WHEN status='REJECTED' THEN 'REJECTED' ELSE 'LEGACY'
                  END
WHERE review_status='PENDING_REVIEW'
  AND status!='PENDING'
""")
        indexes = {i["name"] for i in inspect(conn).get_indexes("emergency_reports")}
        if "idx_reports_owner_review" not in indexes:
            conn.exec_driver_sql(
                "CREATE INDEX idx_reports_owner_review ON emergency_reports(reported_by,review_status,report_id)"
            )
        foreign = {f["name"] for f in inspect(conn).get_foreign_keys("emergency_reports")}
        if "fk_report_reviewer" not in foreign:
            conn.exec_driver_sql(
                "ALTER TABLE emergency_reports ADD CONSTRAINT fk_report_reviewer FOREIGN KEY(reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL"
            )
        conn.exec_driver_sql(SESSION_SQL)
        from app.v2_schema import install_v2

        install_v2(conn)
        from app.history_schema import install_history, install_v4_history

        install_history(conn)
        install_v4_history(conn)
    print("V4 additive migration complete. Existing records retained.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "migrate"])
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.command == "init":
        if not args.fresh:
            parser.error("Fresh initialization requires --fresh and refuses nonempty databases")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            if inspect(conn).get_table_names():
                raise RuntimeError(
                    "Refusing initialization: database already has tables. Use migrate."
                )
            source = (Path(__file__).resolve().parents[2] / "database/init_safe.sql").read_text(
                encoding="utf-8"
            )
            for statement in sql_statements(source):
                conn.exec_driver_sql(statement)
        print("Fresh schema initialized without demo records.")
    migrate()


if __name__ == "__main__":
    main()
