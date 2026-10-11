"""Isolated V2 tests: every database dependency is mocked, never the owner's DB."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
import csv
import io
import pytest
from pydantic import ValidationError
from app.geo import priority, distance_km, india_extent, valid_coordinates
from app.models import EmergencyReportCreate, LocationCreate
from app.routes.exports import csv_rows, csv_value
from app.routes.demand import demand_list, approve, Approval
from app.security import current_user, require_admin
from app.main import app
from conftest import ADMIN, PUBLIC


@pytest.mark.parametrize(
    "lat,lon,expected",
    [
        (28.6, 77.2, True),
        (None, 77, False),
        (float("nan"), 77, False),
        (91, 77, False),
        (28, 181, False),
    ],
)
def test_coordinate_validity(lat, lon, expected):
    assert valid_coordinates(lat, lon) is expected


def test_distances_and_india_extent():
    assert distance_km(28.6, 77.2, 28.6, 77.2) == 0
    assert 110 < distance_km(28, 77, 29, 77) < 112
    assert india_extent(28, 77) and not india_extent(0, 0)
    with pytest.raises(ValueError):
        distance_km(None, None, 28, 77)


def test_priority_transparent_and_missing_values():
    now = datetime(2026, 10, 11, 12)
    result = priority(
        dict(severity="CRITICAL", status="ACTIVE", start_time=datetime(2026, 10, 11, 10)), now
    )
    assert result["priority_score"] == 122
    assert result["priority_factors"]["elapsed_hours_bonus"] == 2
    assert priority(dict(severity="CRITICAL", status="RESOLVED"), now)["priority_score"] == 0
    assert (
        priority(dict(severity="HIGH", review_status="PENDING_REVIEW"), now)["priority_score"] == 90
    )
    assert not priority({}, now)["priority_factors"]["time_known"]


def test_public_unfamiliar_location_model():
    data = dict(
        report_type="FIRE",
        description="A suspected fire near the market",
        severity="HIGH",
        reported_location_text="Near market, Pune",
    )
    report = EmergencyReportCreate(**data, reported_latitude=18.5, reported_longitude=73.8)
    assert report.location_id is None
    for extra in [dict(location_id=1), dict(reported_latitude=18.5)]:
        with pytest.raises(ValidationError):
            EmergencyReportCreate(**data, **extra)
    with pytest.raises(ValidationError):
        LocationCreate(state="A", city="B", district="C", address="D", latitude=18)


@pytest.mark.parametrize(
    "value", ["=SUM(1,2)", "  +SUM(1,2)", "-1+1", "@cmd", "\tformula", "\nformula"]
)
def test_csv_formula_protection(value):
    assert csv_value(value).startswith("'")


def test_csv_unicode_multiline_quotes_empty_and_large():
    rows = [dict(description='पुणे, "flood"\nsecond line', id=i) for i in range(1200)]
    rendered = "".join(csv_rows(iter(rows), ["id", "description"]))
    parsed = list(csv.reader(io.StringIO(rendered.lstrip("\ufeff"))))
    assert len(parsed) == 1201 and parsed[-1][1] == rows[-1]["description"]
    assert len(list(csv.reader(io.StringIO("".join(csv_rows([], ["id"])).lstrip("\ufeff"))))) == 1


@pytest.mark.parametrize(
    "path",
    [
        "/api/intelligence/incidents",
        "/api/intelligence/disaster/1/timeline",
        "/api/exports/resources.csv",
        "/api/resource-requests/",
    ],
)
def test_v2_requires_authentication(client, db, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/intelligence/disaster/1/report",
        "/api/intelligence/report/1/shelters",
        "/api/intelligence/overview/summary",
        "/api/exports/resources.csv",
        "/api/resource-requests/",
    ],
)
def test_v2_public_permission_boundaries(client, db, path):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert client.get(path).status_code == 403


def test_public_map_owner_scope_and_missing_coordinates(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.scalar_one.return_value = 1
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(
            kind="report",
            id=4,
            owner_id=2,
            review_status="PENDING_REVIEW",
            severity="HIGH",
            response_status="PENDING",
            latitude=None,
            longitude=None,
        )
    ]
    response = client.get("/api/intelligence/incidents?q=Pune&severity=HIGH")
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert not item["plottable"] and "owner_id" not in item
    calls = db.execute.call_args_list
    assert all(c.args[1]["owner"] == 2 for c in calls)
    assert "owner_id=:owner" in str(calls[-1].args[0])


def test_recommendation_does_not_change_stock():
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = 1
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(
            status="OPEN",
            outstanding_quantity=Decimal(8),
            available_quantity=Decimal(3),
            allocated_quantity=Decimal(2),
        )
    ]
    result = demand_list(db, 25, 0, None, None)["items"][0]
    assert (
        result["recommended_quantity"] == 3
        and result["shortage_quantity"] == 5
        and result["fulfillment"] == "PARTIAL"
    )
    db.commit.assert_not_called()
    assert all("UPDATE" not in str(c.args[0]) for c in db.execute.call_args_list)


def test_approval_retry_is_idempotent():
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = dict(
        allocation_id=8, request_id=2, quantity=Decimal(3), allocated_by=1
    )
    with patch("app.routes.demand.record", return_value=dict(resource_id=1, disaster_id=1)):
        with patch("app.routes.demand.allocation_save") as allocate:
            result = approve(
                Approval(quantity=3, idempotency_key="test-action-key-1234"), 2, db, ADMIN
            )
            assert result["allocation_id"] == 8
            allocate.assert_not_called()
            db.commit.assert_not_called()


def test_csv_all_matching_and_owner_filter(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.mappings.return_value.__iter__.return_value = iter(
        [dict(report_id=i, description="Unicode पुणे") for i in range(4)]
    )
    response = client.get("/api/exports/emergency-reports.csv?limit=1&offset=9&q=Pune")
    assert response.status_code == 200, response.text
    assert len(list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))) == 5
    call = db.execute.call_args
    assert "LIMIT" not in str(call.args[0]) and call.args[1]["owner"] == 2
    assert call.args[1]["q"] == "%Pune%"


def test_shelter_matching_excludes_closed_full_and_unlocated():
    from app.routes.intelligence import nearby

    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(
            shelter_id=i,
            name="Shelter",
            capacity=10,
            current_occupancy=occupancy,
            status=status,
            latitude=latitude,
            longitude=77,
            available_capacity=10 - occupancy,
        )
        for i, status, occupancy, latitude in [
            (1, "AVAILABLE", 2, 29),
            (2, "CLOSED", 0, 28),
            (3, "FULL", 10, 28),
            (4, "AVAILABLE", 0, None),
        ]
    ]
    with patch("app.routes.intelligence.incident_coordinates", return_value=({}, {}, 28, 77)):
        result = nearby("disaster", 1, db, ADMIN, 5)
        assert [r["shelter_id"] for r in result["items"]] == [1]
        assert 110 < result["items"][0]["distance_km"] < 112
    db.commit.assert_not_called()
