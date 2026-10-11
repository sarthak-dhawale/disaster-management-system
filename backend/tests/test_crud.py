from datetime import datetime
from unittest.mock import patch
import pytest
from app.main import app
from app.security import current_user
from conftest import ADMIN

DATA = [
    ("locations", {"state": "State", "district": "District", "city": "City", "address": "Address"}),
    (
        "disasters",
        {
            "location_id": 1,
            "disaster_type": "FIRE",
            "title": "Test fire",
            "severity": "HIGH",
            "status": "ACTIVE",
            "start_time": "2026-10-10T12:00:00",
            "end_time": None,
            "description": None,
            "reported_by": None,
        },
    ),
    (
        "shelters",
        {
            "location_id": 1,
            "name": "Test shelter",
            "capacity": 4,
            "current_occupancy": 0,
            "status": "AVAILABLE",
        },
    ),
    (
        "resources",
        {
            "resource_name": "Water",
            "category": "WATER",
            "unit": "litre",
            "total_quantity": "10",
            "available_quantity": "10",
            "minimum_required": "2",
        },
    ),
    ("volunteers", {"user_id": 2, "skills": "Rescue", "availability_status": "AVAILABLE"}),
    (
        "users",
        {
            "full_name": "Test User",
            "email": "fixture@example.com",
            "password": "test-password-123",
            "role": "PUBLIC_USER",
            "status": "ACTIVE",
        },
    ),
]


@pytest.mark.parametrize("module,data", DATA)
def test_crud_routes_use_db_and_commit(client, db, module, data):
    app.dependency_overrides[current_user] = lambda: ADMIN
    from app.crud import IDS

    key = IDS[module]
    old = {**data, key: 2, "user_id": 2, "password_hash": "not-returned"}
    if module == "disasters":
        old["start_time"] = datetime(2026, 10, 10, 12)
    db.execute.return_value.lastrowid = 2
    db.execute.return_value.mappings.return_value.first.return_value = old
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.first.return_value = None
    db.execute.return_value.all.return_value = [(1,)]
    if module == "locations":
        from unittest.mock import MagicMock

        normal = db.execute.return_value
        dedup = MagicMock()
        dedup.mappings.return_value.first.return_value = None
        db.execute.side_effect = (
            lambda query, *args, **kwargs: dedup if "LOWER(TRIM(" in str(query) else normal
        )
    response = client.post(f"/api/{module}/", headers={"X-DMS-Request": "1"}, json=data)
    assert response.status_code == 201, response.text
    assert response.json()[key] == 2
    update_data = data.copy()
    if module == "users":
        update_data.pop("password")
    if module == "disasters":
        update_data.pop("reported_by")
    response = client.put(f"/api/{module}/2", headers={"X-DMS-Request": "1"}, json=update_data)
    assert response.status_code == 200, response.text
    response = client.delete(f"/api/{module}/2", headers={"X-DMS-Request": "1"})
    assert response.status_code == 200, response.text
    assert db.commit.call_count == 3


def test_disaster_partial_update_rejects_null_required(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = {
        **DATA[1][1],
        "disaster_id": 1,
        "start_time": datetime(2026, 10, 10, 12),
    }
    response = client.put("/api/disasters/1", headers={"X-DMS-Request": "1"}, json={"title": None})
    assert response.status_code == 422
    db.commit.assert_not_called()
    db.rollback.assert_called()


def test_password_whitespace_is_preserved():
    from app.models import Register, Login

    password = "  safe-password  "
    assert (
        Register(full_name="User", email="user@example.com", password=password).password == password
    )
    assert Login(email="user@example.com", password=password).password == password
