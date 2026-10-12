from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from app.main import app
from app.security import (
    current_user,
    hash_password,
    verify_password,
    issue_session,
    check_write_request,
)
from app.models import (
    DisasterCreate,
    ResourceCreate,
    ShelterCreate,
    LocationCreate,
    AllocationCreate,
    AssignmentCreate,
    RegistrationCreate,
    EmergencyReportCreate,
    Register,
    UserCreate,
)
from app.crud import (
    allocation_save,
    allocation_delete,
    assignment_save,
    registration_save,
    registration_delete,
    simple_save,
    simple_delete,
    refresh_volunteer,
    refresh_shelter,
)
from app.listing import list_records
from app.routes.emergency_reports import review, owned_record
from app.routes.disasters import LIST_SQL
from conftest import ADMIN, PUBLIC

WRITE = {"X-DMS-Request": "1"}
MODULES = [
    "disasters",
    "shelters",
    "locations",
    "users",
    "volunteers",
    "resources",
    "resource-allocations",
    "volunteer-assignments",
    "shelter-registrations",
    "emergency-reports",
]


@pytest.mark.parametrize("connected,status", [(True, 200), (False, 503)])
def test_health(client, connected, status):
    with patch("app.main.test_database_connection", return_value=connected):
        r = client.get("/health")
        assert r.status_code == status
        assert r.json()["status"] == ("healthy" if connected else "degraded")


def test_real_connectivity_check_handles_failure():
    from app.database import test_database_connection

    with patch(
        "app.database.engine.connect",
        side_effect=OperationalError("SELECT 1", {}, Exception("test")),
    ):
        assert test_database_connection() is False


@pytest.mark.parametrize("module", MODULES)
def test_anonymous_lists_forbidden(client, db, module):
    assert client.get(f"/api/{module}/").status_code == 401
    db.execute.assert_not_called()


@pytest.mark.parametrize("module", MODULES[:-1])
def test_public_lists_forbidden(client, db, module):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert client.get(f"/api/{module}/").status_code == 403
    db.execute.assert_not_called()


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_public_cannot_mutate_administration(client, db, method):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    path = "/api/disasters/" if method == "post" else "/api/disasters/1"
    assert (
        getattr(client, method)(
            path, headers=WRITE, **({"json": {}} if method != "delete" else {})
        ).status_code
        == 403
    )


def test_public_cannot_review(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert (
        client.post(
            "/api/emergency-reports/1/review", headers=WRITE, json={"decision": "CONFIRMED"}
        ).status_code
        == 403
    )
    db.execute.assert_not_called()


def test_manager_cannot_manage_accounts(client):
    app.dependency_overrides[current_user] = lambda: {**ADMIN, "role": "DISASTER_MANAGER"}
    assert client.get("/api/users/").status_code == 403


def test_write_origin_and_header(client):
    assert client.post("/api/auth/login", json={}).status_code == 403
    assert (
        client.post(
            "/api/auth/login", headers={**WRITE, "Origin": "https://untrusted.example"}, json={}
        ).status_code
        == 403
    )


def test_cors_restricted(client):
    headers = {
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-DMS-Request",
    }
    assert client.options("/api/auth/login", headers=headers).status_code == 200
    headers["Origin"] = "https://untrusted.example"
    assert client.options("/api/auth/login", headers=headers).status_code == 400


def test_passwords_and_invalid_legacy_hash():
    hashed = hash_password("Very private pass 123")
    assert hashed.startswith("$argon2id$") and verify_password("Very private pass 123", hashed)
    assert not verify_password("incorrect", hashed)
    assert not verify_password("anything", "legacy_fake_hash")


def test_session_cookie_and_db_token(db):
    from starlette.responses import Response

    response = Response()
    issue_session(db, response, 1)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Max-Age=" in cookie
    token = cookie.split(";")[0].split("=", 1)[1]
    params = db.execute.call_args_list[-1].args[1]
    assert params["token"] != token and len(params["token"]) == 64


def test_invalid_login_does_not_expose_hash(client, db):
    db.execute.return_value.mappings.return_value.first.return_value = None
    r = client.post(
        "/api/auth/login",
        headers=WRITE,
        json={"email": "missing@example.com", "password": "secret"},
    )
    assert r.status_code == 401 and "hash" not in r.text


def test_registration_cannot_escalate(client, db):
    r = client.post(
        "/api/auth/register",
        headers=WRITE,
        json={
            "email": "public@example.com",
            "full_name": "Public",
            "password": "long-password",
            "role": "ADMIN",
        },
    )
    assert r.status_code == 422
    db.execute.assert_not_called()
    assert "long-password" not in r.text


def test_registration_hashes_and_fixes_role(client, db):
    db.execute.return_value.lastrowid = 10
    r = client.post(
        "/api/auth/register",
        headers=WRITE,
        json={"email": "new@example.com", "full_name": "New Public", "password": "long-password"},
    )
    assert r.status_code == 201
    sql = str(db.execute.call_args.args[0])
    data = db.execute.call_args.args[1]
    assert (
        "'PUBLIC_USER'" in sql
        and "password" not in data
        and verify_password("long-password", data["password_hash"])
    )


def test_db_constraint_is_safe_and_rolls_back(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.side_effect = IntegrityError(
        "private query", {"secret": "secret-value"}, Exception("duplicate")
    )
    r = client.post(
        "/api/locations/",
        headers=WRITE,
        json={"state": "S", "district": "D", "city": "C", "address": "A"},
    )
    assert r.status_code == 409 and "secret-value" not in r.text
    db.rollback.assert_called()


def test_db_unavailable_is_safe(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.side_effect = OperationalError("private query", {}, Exception("private password"))
    r = client.get("/api/disasters/")
    assert r.status_code == 503 and "private password" not in r.text


def test_invalid_pagination(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    assert client.get("/api/disasters/?limit=201&offset=-1").status_code == 422
    assert client.get("/api/disasters/?sort=drop").status_code == 422


@pytest.mark.parametrize("module", MODULES)
def test_missing_records(client, db, module):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert client.get(f"/api/{module}/999").status_code == 404


@pytest.mark.parametrize(
    "model,data",
    [
        (LocationCreate, {"city": " ", "state": "S", "district": "D", "address": "A"}),
        (
            LocationCreate,
            {"city": "C", "state": "S", "district": "D", "address": "A", "latitude": 91},
        ),
        (
            ResourceCreate,
            {
                "resource_name": "Food",
                "category": "FOOD",
                "unit": "kg",
                "total_quantity": 2,
                "available_quantity": 3,
            },
        ),
        (ResourceCreate, {"resource_name": "Food", "category": "NOPE", "unit": "kg"}),
        (
            ResourceCreate,
            {"resource_name": "Food", "category": "FOOD", "unit": "kg", "total_quantity": "NaN"},
        ),
        (
            ShelterCreate,
            {"location_id": 1, "name": "Shelter", "capacity": 2, "current_occupancy": 3},
        ),
        (AllocationCreate, {"resource_id": 1, "quantity": 1, "disaster_id": 1, "shelter_id": 1}),
        (AllocationCreate, {"resource_id": 1, "quantity": "0.001", "disaster_id": 1}),
        (
            AssignmentCreate,
            {
                "volunteer_id": 1,
                "assignment_role": "Rescue",
                "start_time": "2026-10-10T12:00",
                "end_time": "2026-10-10T11:00",
                "shelter_id": 1,
            },
        ),
        (
            RegistrationCreate,
            {
                "user_id": 1,
                "shelter_id": 1,
                "check_in": "2026-10-10T12:00",
                "check_out": "2026-10-10T11:00",
                "status": "CHECKED_OUT",
            },
        ),
        (
            EmergencyReportCreate,
            {
                "location_id": 1,
                "report_type": "FIRE",
                "description": "too short",
                "severity": "HIGH",
            },
        ),
        (
            DisasterCreate,
            {
                "location_id": 0,
                "title": "Fire",
                "disaster_type": "FIRE",
                "severity": "HIGH",
                "start_time": "2026-10-10T12:00",
            },
        ),
        (Register, {"full_name": "Person", "email": "invalid", "password": "long-password"}),
        (UserCreate, {"full_name": "Person", "email": "user@example.com", "password_hash": "hash"}),
    ],
)
def test_invalid_models(model, data):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        model.model_validate(data)


def options(**kw):
    data = dict(
        q="",
        status="",
        severity="",
        category="",
        disaster_type="",
        report_type="",
        review_status="",
        city="",
        role="",
        availability_status="",
        low_stock=False,
        available_only=False,
        limit=25,
        offset=0,
        sort="desc",
    )
    data.update(kw)
    return data


def test_search_is_bound_and_paginated(db):
    db.execute.return_value.scalar_one.return_value = 8
    db.execute.return_value.mappings.return_value.all.return_value = []
    query = "%' OR 1=1 --"
    result = list_records(db, LIST_SQL, "disasters", options(q=query, status="ACTIVE", offset=25))
    sql, params = db.execute.call_args.args
    assert query not in str(sql) and params["q"] == "%" + query + "%" and params["offset"] == 25
    assert "LIMIT :limit OFFSET :offset" in str(sql) and result["total"] == 8


def test_public_reports_are_owned(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.mappings.return_value.all.return_value = []
    r = client.get("/api/emergency-reports/?status=PENDING_REVIEW")
    assert r.status_code == 200
    sql, params = db.execute.call_args.args
    assert (
        "reported_by=:owner" in str(sql)
        and params["owner"] == 2
        and params["review_status"] == "PENDING_REVIEW"
    )


def test_report_creation_fixes_identity_and_pending(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.mappings.return_value.first.return_value = {"location_id": 1}
    db.execute.return_value.lastrowid = 7
    r = client.post(
        "/api/emergency-reports/",
        headers=WRITE,
        json={
            "location_id": 1,
            "report_type": "FIRE",
            "description": "Smoke coming from building",
            "severity": "HIGH",
            "disaster_type": "FIRE",
        },
    )
    assert r.status_code == 201 and r.json()["status"] == "PENDING_REVIEW"
    data = db.execute.call_args.args[1]
    assert data["reported_by"] == 2 and data["status"] == "PENDING" and "disaster_id" not in data


def test_spoofed_reporter_rejected(client):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    r = client.post(
        "/api/emergency-reports/",
        headers=WRITE,
        json={
            "location_id": 1,
            "report_type": "FIRE",
            "description": "Smoke coming from building",
            "severity": "HIGH",
            "reported_by": 1,
        },
    )
    assert r.status_code == 422


def pending():
    return {
        "report_id": 7,
        "location_id": 1,
        "reported_by": 2,
        "disaster_type": "FIRE",
        "severity": "HIGH",
        "description": "Smoke in a building",
        "occurred_at": None,
        "reported_at": datetime(2026, 10, 10, 12),
        "review_status": "PENDING_REVIEW",
        "disaster_id": None,
    }


def test_confirm_and_retry_no_duplicate(db):
    from app.models import Review

    row = pending()
    with (
        patch("app.routes.emergency_reports.owned_record", return_value=row),
        patch("app.routes.emergency_reports.insert", return_value=21) as create,
        patch("app.routes.emergency_reports.update") as update,
    ):
        result = review(Review(decision="CONFIRMED"), 7, db, ADMIN)
        assert result["disaster_id"] == 21 and create.call_count == 1
        assert update.call_args.args[3]["review_status"] == "CONFIRMED"
        db.commit.assert_called_once()
    with (
        patch(
            "app.routes.emergency_reports.owned_record",
            return_value={**row, "review_status": "CONFIRMED", "disaster_id": 21},
        ),
        patch("app.routes.emergency_reports.insert") as create,
    ):
        assert review(Review(decision="CONFIRMED"), 7, db, ADMIN)["disaster_id"] == 21
        create.assert_not_called()


def test_reject_no_disaster(db):
    from app.models import Review

    with (
        patch("app.routes.emergency_reports.owned_record", return_value=pending()),
        patch("app.routes.emergency_reports.insert") as create,
        patch("app.routes.emergency_reports.update") as update,
    ):
        review(Review(decision="REJECTED", reason="Unable to verify"), 7, db, ADMIN)
        create.assert_not_called()
        assert update.call_args.args[3]["review_reason"] == "Unable to verify"


def test_owner_lookup_has_predicate(db):
    db.execute.return_value.mappings.return_value.first.return_value = None
    with pytest.raises(Exception) as e:
        owned_record(db, 7, PUBLIC)
    assert e.value.status_code == 404 and "reported_by=:owner" in str(db.execute.call_args.args[0])


def test_allocation_insufficient_leaves_no_writes(db):
    data = AllocationCreate(resource_id=1, disaster_id=1, quantity=6)
    with (
        patch("app.crud.references"),
        patch(
            "app.crud.record",
            return_value={"available_quantity": Decimal(5), "total_quantity": Decimal(10)},
        ),
        patch("app.crud.insert") as insert,
    ):
        with pytest.raises(Exception) as e:
            allocation_save(db, data)
        assert e.value.status_code == 409
        insert.assert_not_called()
        db.commit.assert_not_called()


def test_allocation_adjustment_same_resource(db):
    old = {"allocation_id": 1, "resource_id": 1, "quantity": Decimal(4), "status": "ALLOCATED"}
    resource = {"available_quantity": Decimal(6), "total_quantity": Decimal(10)}
    data = AllocationCreate(resource_id=1, disaster_id=1, quantity=7)
    with (
        patch("app.crud.references"),
        patch("app.crud.record", side_effect=[old, resource]),
        patch("app.crud.update") as update,
    ):
        allocation_save(db, data, 1)
        assert update.call_args_list[-1].args[3]["available_quantity"] == Decimal(3)
        db.commit.assert_called_once()


def test_volunteer_still_assigned_with_other_work(db):
    db.execute.return_value.scalar_one.return_value = 1
    with patch("app.crud.update") as update:
        refresh_volunteer(db, 1)
    assert update.call_args.args[3]["availability_status"] == "ASSIGNED"


def test_closed_shelter_preserved(db):
    refresh_shelter(db, 1)
    assert "WHEN status='CLOSED' THEN 'CLOSED'" in str(db.execute.call_args.args[0])


def test_registration_full_and_duplicate(db):
    data = RegistrationCreate(user_id=2, shelter_id=1)
    full = {"current_occupancy": 2, "capacity": 2, "status": "FULL"}
    with (
        patch("app.crud.references"),
        patch("app.crud.record", side_effect=[full, {"user_id": 2}]),
        patch("app.crud.insert") as insert,
    ):
        db.execute.return_value.first.return_value = None
        with pytest.raises(Exception) as e:
            registration_save(db, data)
        assert e.value.status_code == 409
        insert.assert_not_called()


def test_dependency_blocks_parent_delete(db):
    db.execute.return_value.first.return_value = (1,)
    with patch("app.crud.record"), patch("app.crud.remove") as remove:
        with pytest.raises(Exception) as e:
            simple_delete(db, "disasters", 1)
        assert e.value.status_code == 409
        remove.assert_not_called()
        db.commit.assert_not_called()


def test_dashboard_values_are_db_backed(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    values = {
        "total_disasters": 3,
        "active_disasters": 2,
        "critical_disasters": 1,
        "resolved_disasters": 1,
        "total_shelters": 4,
        "available_shelters": 3,
        "full_shelters": 1,
        "total_capacity": 100,
        "total_occupancy": 50,
        "total_volunteers": 6,
        "available_volunteers": 4,
        "assigned_volunteers": 2,
        "unavailable_volunteers": 0,
        "total_resources": 7,
        "available_types": 5,
        "total_quantity": 30,
        "available_quantity": 20,
        "total_reports": 8,
        "pending_reports": 2,
        "in_progress_reports": 3,
        "resolved_reports": 1,
        "critical_reports": 2,
        "total_registrations": 9,
        "active_registrations": 5,
        "checked_out_registrations": 4,
        "total_assignments": 10,
        "assigned": 2,
        "active": 3,
        "completed": 5,
    }
    db.execute.return_value.mappings.return_value.first.return_value = values
    db.execute.return_value.mappings.return_value.all.return_value = []
    r = client.get("/api/dashboard/")
    assert r.status_code == 200
    assert r.json()["disasters"]["total"] == 3 and r.json()["resources"]["available_types"] == 5
    assert r.json()["emergency_reports"]["pending"] == 2
