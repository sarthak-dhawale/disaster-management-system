"""Explicit opt-in, empty disposable *_migration_test DB only; never reset tables."""

import os
import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app import setup_db


@pytest.mark.skipif(
    os.getenv("DMS_RUN_MIGRATION_TESTS") != "1",
    reason="Requires separately configured empty disposable *_migration_test MySQL database",
)
def test_populated_guarded_migration_twice():
    url = os.getenv("DMS_MIGRATION_DATABASE_URL")
    if not url:
        pytest.fail("DMS_MIGRATION_DATABASE_URL required")
    parsed = make_url(url)
    if (
        parsed.drivername != "mysql+pymysql"
        or not parsed.database
        or not parsed.database.endswith("_migration_test")
    ):
        pytest.fail("Refusing migration test: require mysql+pymysql and *_migration_test")
    engine = create_engine(url, hide_parameters=True, pool_pre_ping=True)
    tables = set(inspect(engine).get_table_names())
    base = {
        "locations",
        "users",
        "disasters",
        "shelters",
        "resources",
        "volunteers",
        "emergency_reports",
        "resource_allocations",
        "volunteer_assignments",
        "shelter_registrations",
        "resource_requests",
    }
    with engine.connect() as conn:
        for table in tables & base:
            if conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one():
                pytest.fail("Refusing: disposable DB contains existing application records")
    original = setup_db.engine
    setup_db.engine = engine
    token = uuid.uuid4().hex
    location = None
    try:
        if not tables:
            source = (Path(__file__).resolve().parents[2] / "database/init_safe.sql").read_text(
                encoding="utf-8"
            )
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                for statement in setup_db.sql_statements(source):
                    conn.exec_driver_sql(statement)
        with engine.begin() as conn:
            location = conn.execute(
                text(
                    "INSERT INTO locations(state,district,city,address,latitude,longitude) VALUES('Maharashtra','Pune',:city,'Disposable migration fixture',18.52,73.86)"
                ),
                dict(city=token),
            ).lastrowid
        setup_db.migrate()
        setup_db.migrate()
        with engine.connect() as conn:
            row = (
                conn.execute(
                    text("SELECT * FROM locations WHERE location_id=:id"), dict(id=location)
                )
                .mappings()
                .one()
            )
            assert row["city"] == token and float(row["latitude"]) == 18.52
            assert "resource_requests" in inspect(conn).get_table_names()
            columns = {c["name"]: c for c in inspect(conn).get_columns("emergency_reports")}
            assert columns["location_id"]["nullable"]
            triggers = (
                conn.execute(
                    text(
                        "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()"
                    )
                )
                .scalars()
                .all()
            )
            assert len([name for name in triggers if name.startswith("dms_")]) == 36
    finally:
        if location:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM locations WHERE location_id=:id"), dict(id=location))
        setup_db.engine = original
        engine.dispose()
