"""Opt-in real MySQL test. Never uses DATABASE_URL or resets tables/volumes."""

import os, secrets, uuid
from importlib import import_module
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database import get_db
from app.security import hash_password
from app import setup_db

pytestmark = pytest.mark.skipif(
    os.getenv("DMS_RUN_MYSQL_TESTS") != "1",
    reason="Real MySQL integration requires explicit opt-in and a dedicated *_test database",
)


@pytest.fixture
def mysql_clients():
    url = os.getenv("DMS_TEST_DATABASE_URL")
    if not url:
        pytest.fail("DMS_TEST_DATABASE_URL is required")
    parsed = make_url(url)
    if (
        parsed.drivername != "mysql+pymysql"
        or not parsed.database
        or not parsed.database.endswith("_test")
    ):
        pytest.fail("Refusing integration: require mysql+pymysql and a database name ending _test")
    from app.config import DB_TIME_ZONE

    engine = create_engine(
        url,
        hide_parameters=True,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={"init_command": f"SET time_zone = '{DB_TIME_ZONE}'"},
    )
    from sqlalchemy import event
    from app.database import clear_history_context

    event.listen(engine, "checkout", clear_history_context)
    tables = set(inspect(engine).get_table_names())
    required = {
        "users",
        "locations",
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
        # Refuse any pre-existing application records, even in a database named *_test.
        for table in required & tables:
            if conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one():
                pytest.fail(
                    "Refusing integration: test database contains existing application records"
                )
    original = setup_db.engine
    setup_db.engine = engine
    try:
        if not tables:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                from pathlib import Path

                source = (
                    Path(__file__).resolve().parents[2] / "database/init_safe.sql"
                ).read_text()
                for statement in setup_db.sql_statements(source):
                    conn.exec_driver_sql(statement)
        setup_db.migrate()
    finally:
        setup_db.engine = original
    from sqlalchemy.orm import sessionmaker

    sessions = sessionmaker(bind=engine)
    tracked = {table: [] for table in required}
    token = uuid.uuid4().hex[:10]
    password = secrets.token_urlsafe(20)
    with sessions() as db:
        for name, role in [("admin", "ADMIN"), ("public", "PUBLIC_USER")]:
            id = db.execute(
                text(
                    "INSERT INTO users(full_name,email,password_hash,role) VALUES(:name,:email,:hash,:role)"
                ),
                {
                    "name": name,
                    "email": f"{name}-{token}@example.com",
                    "hash": hash_password(password),
                    "role": role,
                },
            ).lastrowid
            tracked["users"].append(id)
        db.commit()

    def isolated_db():
        db = sessions()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = isolated_db
    main = import_module("app.main")
    original_health = main.test_database_connection

    def health():
        with engine.connect() as conn:
            return conn.execute(text("SELECT 1")).scalar_one() == 1

    main.test_database_connection = health
    admin = TestClient(app)
    public = TestClient(app)
    for client, name in [(admin, "admin"), (public, "public")]:
        response = client.post(
            "/api/auth/login",
            headers={"X-DMS-Request": "1"},
            json={"email": f"{name}-{token}@example.com", "password": password},
        )
        assert response.status_code == 200, response.text
    try:
        yield admin, public, tracked, token
    finally:
        admin.close()
        public.close()
        app.dependency_overrides.clear()
        main.test_database_connection = original_health
        # Delete only IDs created by this test, in FK-safe order. Never reset the test DB.
        order = [
            "shelter_registrations",
            "volunteer_assignments",
            "resource_allocations",
            "resource_requests",
            "emergency_reports",
            "volunteers",
            "shelters",
            "resources",
            "disasters",
            "locations",
            "users",
        ]
        from app.crud import IDS

        with sessions() as db:
            for table in order:
                for id in tracked[table]:
                    db.execute(text(f"DELETE FROM {table} WHERE {IDS[table]}=:id"), {"id": id})
            db.commit()
        engine.dispose()


def test_real_mysql_crud_auth_review_search_and_persistence(mysql_clients):
    admin, public, tracked, token = mysql_clients
    headers = {"X-DMS-Request": "1"}

    def create(module, data):
        response = admin.post(f"/api/{module}/", headers=headers, json=data)
        assert response.status_code == 201, response.text
        from app.crud import IDS

        table = module.replace("-", "_")
        id = response.json()[IDS[table]]
        tracked[table].append(id)
        assert admin.get(f"/api/{module}/{id}").status_code == 200
        return id

    assert admin.get("/health").status_code == 200
    loc = create(
        "locations",
        dict(
            state="Test",
            district="Test",
            city="Test " + token,
            address="Disposable integration fixture",
        ),
    )
    disaster = create(
        "disasters",
        dict(
            location_id=loc,
            disaster_type="FIRE",
            title="Test incident " + token,
            severity="HIGH",
            start_time="2026-10-10T12:00:00",
        ),
    )
    shelter = create(
        "shelters",
        dict(location_id=loc, name="Test shelter " + token, capacity=2, current_occupancy=0),
    )
    resource = create(
        "resources",
        dict(
            resource_name="Test water " + token,
            category="WATER",
            unit="litre",
            total_quantity=10,
            available_quantity=10,
            minimum_required=2,
        ),
    )
    volunteer = create("volunteers", dict(user_id=tracked["users"][1], skills="Rescue"))
    alloc_data = dict(resource_id=resource, disaster_id=disaster, quantity=4)
    allocation = create("resource-allocations", alloc_data)
    assert DecimalValue(admin.get(f"/api/resources/{resource}").json()["available_quantity"]) == 6
    assert (
        admin.put(
            f"/api/resource-allocations/{allocation}",
            headers=headers,
            json={**alloc_data, "quantity": 3, "status": "DELIVERED"},
        ).status_code
        == 200
    )
    assert DecimalValue(admin.get(f"/api/resources/{resource}").json()["available_quantity"]) == 7
    assign_data = dict(
        volunteer_id=volunteer,
        shelter_id=shelter,
        assignment_role="Rescue",
        start_time="2026-10-10T12:00:00",
    )
    assignment = create("volunteer-assignments", assign_data)
    assert admin.get(f"/api/volunteers/{volunteer}").json()["availability_status"] == "ASSIGNED"
    assert (
        admin.put(
            f"/api/volunteer-assignments/{assignment}",
            headers=headers,
            json={**assign_data, "status": "COMPLETED"},
        ).status_code
        == 200
    )
    registration = create(
        "shelter-registrations", dict(shelter_id=shelter, user_id=tracked["users"][1])
    )
    assert admin.get(f"/api/shelters/{shelter}").json()["current_occupancy"] == 1
    newuser = create(
        "users",
        dict(
            full_name="Test extra",
            email=f"extra-{token}@example.com",
            password=secrets.token_urlsafe(16),
        ),
    )
    assert "password_hash" not in admin.get(f"/api/users/{newuser}").json()
    for module, id, data in [
        (
            "locations",
            loc,
            dict(state="Test", district="Test", city="Updated " + token, address="Test address"),
        ),
        ("disasters", disaster, dict(title="Updated " + token, status="CONTAINED")),
        (
            "shelters",
            shelter,
            dict(
                location_id=loc,
                name="Updated shelter",
                capacity=3,
                current_occupancy=1,
                status="AVAILABLE",
            ),
        ),
        (
            "resources",
            resource,
            dict(
                resource_name="Updated water",
                category="WATER",
                unit="litre",
                total_quantity=12,
                available_quantity=9,
                minimum_required=2,
            ),
        ),
        (
            "volunteers",
            volunteer,
            dict(user_id=tracked["users"][1], skills="Medical", availability_status="AVAILABLE"),
        ),
        (
            "users",
            newuser,
            dict(
                full_name="Updated Person",
                email=f"extra-{token}@example.com",
                role="PUBLIC_USER",
                status="ACTIVE",
            ),
        ),
        (
            "shelter-registrations",
            registration,
            dict(shelter_id=shelter, user_id=tracked["users"][1], status="CHECKED_OUT"),
        ),
    ]:
        response = admin.put(f"/api/{module}/{id}", headers=headers, json=data)
        assert response.status_code == 200, response.text
    assert admin.get(f"/api/shelters/{shelter}").json()["current_occupancy"] == 0
    reportdata = dict(
        location_id=loc,
        disaster_type="FIRE",
        report_type="FIRE",
        description="Disposable test report for integration verification",
        severity="HIGH",
    )
    response = public.post("/api/emergency-reports/", headers=headers, json=reportdata)
    assert response.status_code == 201, response.text
    report = response.json()["report_id"]
    tracked["emergency_reports"].append(report)
    assert (
        public.post(
            f"/api/emergency-reports/{report}/review",
            headers=headers,
            json={"decision": "CONFIRMED"},
        ).status_code
        == 403
    )
    response = admin.post(
        f"/api/emergency-reports/{report}/review", headers=headers, json={"decision": "CONFIRMED"}
    )
    assert response.status_code == 200, response.text
    official = response.json()["disaster_id"]
    tracked["disasters"].append(official)
    assert (
        admin.post(
            f"/api/emergency-reports/{report}/review",
            headers=headers,
            json={"decision": "CONFIRMED"},
        ).json()["disaster_id"]
        == official
    )
    assert public.get(f"/api/emergency-reports/{report}").json()["review_status"] == "CONFIRMED"
    response = public.post("/api/emergency-reports/", headers=headers, json=reportdata)
    rejected = response.json()["report_id"]
    tracked["emergency_reports"].append(rejected)
    assert (
        admin.put(
            f"/api/emergency-reports/{rejected}",
            headers=headers,
            json={**reportdata, "severity": "MEDIUM"},
        ).status_code
        == 200
    )
    assert (
        admin.post(
            f"/api/emergency-reports/{rejected}/review",
            headers=headers,
            json={"decision": "REJECTED", "reason": "Test rejection"},
        ).status_code
        == 200
    )
    assert (
        public.get(f"/api/emergency-reports/{rejected}").json()["review_reason"] == "Test rejection"
    )
    assert public.get("/api/users/").status_code == 403
    assert public.get("/api/emergency-reports/999999").status_code == 404
    assert admin.get("/api/search/disasters?status=CONTAINED&q=" + token).json()["total"] == 1
    assert admin.get("/api/disasters/?limit=1&offset=1").json()["count"] == 1
    assert admin.get("/api/dashboard/").json()["emergency_reports"]["pending"] == 0
    assert (
        admin.post(
            "/api/volunteers/", headers=headers, json={"user_id": tracked["users"][1]}
        ).status_code
        == 409
    )
    assert (
        admin.post(
            "/api/shelters/",
            headers=headers,
            json={"location_id": 999999, "name": "Missing", "capacity": 1},
        ).status_code
        == 404
    )
    assert (
        admin.post(
            "/api/resources/",
            headers=headers,
            json={
                "resource_name": "Invalid",
                "category": "WATER",
                "unit": "litre",
                "available_quantity": -1,
            },
        ).status_code
        == 422
    )
    # Exercise actual triggers, views and stock endpoint with dedicated fixture IDs.
    assert public.get("/api/audit-history/").status_code == 403
    stock = admin.post(
        f"/api/resources/{resource}/stock",
        headers=headers,
        json=dict(kind="RESTOCK", quantity="2.25", note="Integration receipt"),
    )
    assert stock.status_code == 201, stock.text
    movements = admin.get(f"/api/resource-movements/?resource_id={resource}").json()["items"]
    assert (
        movements[0]["movement_kind"] == "RESTOCK"
        and movements[0]["actor_id"] == tracked["users"][0]
    )
    assert sum(DecimalValue(m["available_delta"]) for m in movements) == DecimalValue(
        stock.json()["available_quantity"]
    )
    failed = admin.post(
        f"/api/resources/{resource}/stock",
        headers=headers,
        json=dict(kind="WITHDRAW", quantity="99999", note="Invalid withdrawal"),
    )
    assert failed.status_code == 409
    assert len(
        admin.get(f"/api/resource-movements/?resource_id={resource}").json()["items"]
    ) == len(movements)
    history = admin.get(f"/api/audit-history/?entity=emergency_reports&record_id={report}").json()[
        "items"
    ]
    import json

    def parsed(value):
        return json.loads(value) if isinstance(value, str) else value

    review_changes = [
        h
        for h in history
        if h["action"] == "UPDATE" and parsed(h["after_data"])["review_status"] == "CONFIRMED"
    ]
    assert len(review_changes) == 1 and review_changes[0]["actor_id"] == tracked["users"][0]
    rows = admin.get("/api/analytics/disasters").json()["items"]
    assert next(r for r in rows if r["disaster_id"] == disaster)["allocation_count"] == 1
    assert admin.get("/api/analytics/monthly-reports").json()["total"] == 1
    for section in ["shelters", "resource-allocations"]:
        assert admin.get("/api/analytics/" + section).status_code == 200
    # Unreviewed reports support delete; reviewed ones deliberately retain history.
    response = public.post("/api/emergency-reports/", headers=headers, json=reportdata)
    pending = response.json()["report_id"]
    tracked["emergency_reports"].append(pending)
    assert admin.delete(f"/api/emergency-reports/{pending}", headers=headers).status_code == 200
    for module, id in [
        ("shelter-registrations", registration),
        ("volunteer-assignments", assignment),
        ("resource-allocations", allocation),
        ("volunteers", volunteer),
        ("shelters", shelter),
        ("resources", resource),
        ("users", newuser),
        ("disasters", disaster),
    ]:
        response = admin.delete(f"/api/{module}/{id}", headers=headers)
        assert response.status_code == 200, response.text
        assert admin.get(f"/api/{module}/{id}").status_code == 404
    assert admin.delete(f"/api/locations/{loc}", headers=headers).status_code == 409
    assert public.post("/api/auth/logout", headers=headers).status_code == 200
    assert public.get("/api/auth/me").status_code == 401


def DecimalValue(value):
    from decimal import Decimal

    return Decimal(str(value))


def test_real_mysql_v2_request_reporting_and_geography(mysql_clients):
    admin, public, tracked, token = mysql_clients
    headers = {"X-DMS-Request": "1"}

    def create(module, data):
        from app.crud import IDS

        response = admin.post(f"/api/{module}/", headers=headers, json=data)
        assert response.status_code == 201, response.text
        table = module.replace("-", "_")
        key = response.json()[IDS[table]]
        tracked[table].append(key)
        return key

    location = create(
        "locations",
        dict(
            state="Maharashtra",
            district="Pune",
            city="Test " + token,
            address="Integration only " + token,
            latitude="18.5200000",
            longitude="73.8600000",
        ),
    )
    disaster = create(
        "disasters",
        dict(
            location_id=location,
            title="Integration V2 " + token,
            disaster_type="FIRE",
            severity="CRITICAL",
            start_time="2026-10-11T10:00:00",
        ),
    )
    resource = create(
        "resources",
        dict(
            resource_name="Integration water " + token,
            category="WATER",
            unit="litre",
            total_quantity=10,
            available_quantity=10,
        ),
    )
    shelter = create(
        "shelters", dict(location_id=location, name="Integration shelter " + token, capacity=2)
    )
    request = create(
        "resource-requests", dict(disaster_id=disaster, resource_id=resource, quantity=8)
    )
    assert DecimalValue(admin.get(f"/api/resources/{resource}").json()["available_quantity"]) == 10
    approval = dict(quantity=3, idempotency_key="approval-" + token + "-first")
    result = admin.post(f"/api/resource-requests/{request}/approve", headers=headers, json=approval)
    assert result.status_code == 201, result.text
    allocation = result.json()["allocation_id"]
    tracked["resource_allocations"].append(allocation)
    assert (
        admin.post(
            f"/api/resource-requests/{request}/approve", headers=headers, json=approval
        ).json()["allocation_id"]
        == allocation
    )
    assert DecimalValue(admin.get(f"/api/resources/{resource}").json()["available_quantity"]) == 7
    assert (
        admin.post(
            f"/api/resource-requests/{request}/approve",
            headers=headers,
            json=dict(quantity=8, idempotency_key="approval-" + token + "-bad"),
        ).status_code
        == 409
    )
    assert (
        public.post(
            f"/api/resource-requests/{request}/approve", headers=headers, json=approval
        ).status_code
        == 403
    )
    assert (
        admin.put(
            f"/api/resource-allocations/{allocation}",
            headers=headers,
            json=dict(resource_id=resource, disaster_id=disaster, quantity=3, status="CANCELLED"),
        ).status_code
        == 200
    )
    assert DecimalValue(admin.get(f"/api/resources/{resource}").json()["available_quantity"]) == 10
    assert (
        admin.post(f"/api/resource-requests/{request}/cancel", headers=headers).status_code == 200
    )
    data = dict(
        reported_location_text="Integration unfamiliar locality",
        reported_latitude="18.52",
        reported_longitude="73.86",
        report_type="FIRE",
        disaster_type="FIRE",
        description="Integration suspected incident only",
        severity="HIGH",
    )
    result = public.post("/api/emergency-reports/", headers=headers, json=data)
    assert result.status_code == 201, result.text
    report = result.json()["report_id"]
    tracked["emergency_reports"].append(report)
    assert public.get(f"/api/emergency-reports/{report}").json()["location_id"] is None
    assert (
        admin.post(
            f"/api/emergency-reports/{report}/review",
            headers=headers,
            json=dict(decision="CONFIRMED"),
        ).status_code
        == 422
    )
    decision = dict(decision="CONFIRMED", location_id=location, disaster_id=disaster)
    assert (
        admin.post(
            f"/api/emergency-reports/{report}/review", headers=headers, json=decision
        ).json()["disaster_id"]
        == disaster
    )
    assert (
        admin.post(
            f"/api/emergency-reports/{report}/review", headers=headers, json=decision
        ).json()["disaster_id"]
        == disaster
    )
    mapped = admin.get("/api/intelligence/incidents?q=" + token).json()["items"]
    assert any(
        row["kind"] == "disaster" and row["id"] == disaster and row["plottable"] for row in mapped
    )
    nearest = admin.get(f"/api/intelligence/disaster/{disaster}/shelters").json()["items"]
    assert any(row["shelter_id"] == shelter and row["distance_km"] == 0 for row in nearest)
    assert admin.get(f"/api/intelligence/disaster/{disaster}/report").status_code == 200
    assert admin.get(f"/api/exports/disasters.csv?record_id={disaster}").status_code == 200
    assert public.get("/api/exports/resources.csv").status_code == 403
