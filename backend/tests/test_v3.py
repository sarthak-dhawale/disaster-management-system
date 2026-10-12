"""V3 known-fixture tests never connect to the owner's database."""

from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from app.main import app
from app.security import current_user
from app.planning import Scenario, compare_plans
from app.routes import planning
from app.reporting import build_pdf, india_map
from conftest import ADMIN, PUBLIC


@pytest.fixture
def scenario():
    return dict(
        name="Assam flood exercise",
        disaster_type="FLOOD",
        region="Assam",
        population=2000,
        severity="HIGH",
        accommodation_required=2000,
        reserve_percent=20,
        demands=[
            dict(resource_id=1, quantity="30", region="District A", priority=5),
            dict(resource_id=1, quantity="90", region="District B", priority=3),
            dict(resource_id=2, quantity="3", region="District A", priority=3),
        ],
    )


@pytest.fixture
def snapshot():
    return dict(
        captured_at="2026-10-12T09:00:00+00:00",
        provenance="ISOLATED TEST FIXTURE",
        resources=[
            dict(
                resource_id=1,
                resource_name="Water",
                unit="litres",
                available_quantity="100",
                total_quantity="150",
                committed_quantity="50",
            ),
            dict(
                resource_id=2,
                resource_name="Blanket",
                unit="items",
                available_quantity="2",
                total_quantity="2",
                committed_quantity="0",
            ),
        ],
        shelters=[
            dict(
                shelter_id=i,
                name="Shelter " + str(i),
                status=status,
                capacity=capacity,
                current_occupancy=occupancy,
                latitude=lat,
                longitude=lon,
            )
            for i, status, capacity, occupancy, lat, lon in [
                (1, "AVAILABLE", 100, 20, 26, 92),
                (2, "FULL", 50, 50, 26, 92),
                (3, "CLOSED", 500, 0, 26, 92),
                (4, "AVAILABLE", 10, 0, None, None),
            ]
        ],
        disasters=[dict(disaster_id=1, title="Existing official record")],
    )


def test_same_snapshot_different_plans_no_mutation(scenario, snapshot):
    original = deepcopy(snapshot)
    result = compare_plans(Scenario(**scenario), snapshot)
    assert snapshot == original and result["snapshot"] == snapshot
    a, b, c = result["plans"]
    assert a["rows"][0]["proposed"] == "30"
    assert b["rows"][0]["region"] == "District B" and b["rows"][0]["proposed"] == "90"
    assert Decimal(c["resources"][0]["remaining"]) == 20
    assert result["shelters"]["eligible_capacity"] == 90
    assert result["shelters"]["gap"] == 1910
    assert len(result["shelters"]["items"]) == 2
    assert any("warehouse coordinates" in w for w in result["warnings"])


@pytest.mark.parametrize("reserve", [0, 20, 100])
def test_inventory_conservation_and_unit_separation(scenario, snapshot, reserve):
    scenario["reserve_percent"] = reserve
    for plan in compare_plans(Scenario(**scenario), snapshot)["plans"]:
        for resource in plan["resources"]:
            available = Decimal(resource["available"])
            proposed = Decimal(resource["proposed"])
            assert proposed + Decimal(resource["remaining"]) == available
            assert proposed <= available and Decimal(resource["remaining"]) >= Decimal(
                resource["reserve"]
            )
            assert Decimal(resource["required"]) == proposed + Decimal(resource["unmet"])
        assert {r["unit"] for r in plan["resources"]} == {"litres", "items"}


@pytest.mark.parametrize(
    "change",
    [
        {"population": -1},
        {"reserve_percent": 101},
        {"latitude": 26},
        {"latitude": float("nan"), "longitude": 92},
        {"accommodation_required": 2001},
        {"disaster_type": "UNKNOWN"},
        {"demands": []},
        {"demands": [{"resource_id": 1, "quantity": 0, "region": "A"}]},
    ],
)
def test_invalid_scenarios(scenario, change):
    with pytest.raises(ValidationError):
        Scenario(**{**scenario, **change})


def test_unknown_resource(scenario, snapshot):
    scenario["demands"][0]["resource_id"] = 999
    with pytest.raises(ValueError):
        compare_plans(Scenario(**scenario), snapshot)


def test_run_retrieve_owner_expiry_discard_no_db_writes(client, db, scenario, snapshot):
    app.dependency_overrides[current_user] = lambda: ADMIN
    planning.RESULTS.clear()
    with patch.object(planning, "snapshot_inventory", return_value=snapshot):
        response = client.post(
            "/api/simulations/run", json=scenario, headers={"X-DMS-Request": "1"}
        )
        assert response.status_code == 201, response.text
        id = response.json()["simulation_id"]
        assert client.get("/api/simulations/" + id).status_code == 200
        pdf = client.get("/api/simulations/" + id + "/export/pdf")
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        assert "HYPOTHETICAL" in "".join(
            p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages
        )
        assert client.get("/api/simulations/" + id + "/export/csv").content.startswith(
            b"\xef\xbb\xbf"
        )
        app.dependency_overrides[current_user] = lambda: {**ADMIN, "user_id": 999}
        assert client.get("/api/simulations/" + id).status_code == 404
        assert client.get("/api/simulations/" + id + "/export/pdf").status_code == 404
        app.dependency_overrides[current_user] = lambda: ADMIN
        assert (
            client.delete("/api/simulations/" + id, headers={"X-DMS-Request": "1"}).status_code
            == 200
        )
        assert client.get("/api/simulations/" + id).status_code == 404
        id = client.post(
            "/api/simulations/run", json=scenario, headers={"X-DMS-Request": "1"}
        ).json()["simulation_id"]
        _, owner, result = planning.RESULTS[id]
        planning.RESULTS[id] = (0, owner, result)
        assert client.get("/api/simulations/" + id).status_code == 404
    db.execute.assert_not_called()
    db.commit.assert_not_called()
    planning.RESULTS.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/api/resource-intelligence",
        "/api/simulations/catalog",
        "/api/simulations/unknown",
        "/api/simulations/unknown/export/pdf",
        "/api/reports/overview/pdf",
        "/api/reports/resource-intelligence/pdf",
        "/api/exports/resources.pdf",
    ],
)
def test_public_cannot_access_planning_or_admin_exports(client, path):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert client.get(path).status_code == 403


def test_report_pdf_owner_filter_and_no_hashes(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    db.execute.return_value.mappings.return_value.all.return_value = [
        dict(report_id=1, description="José report", password_hash="NEVER_EXPORT")
    ]
    response = client.get("/api/exports/emergency-reports.pdf?q=Pune&limit=1&offset=9")
    assert response.status_code == 200, response.text
    text = "".join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
    assert "José" in text and "NEVER_EXPORT" not in text
    assert db.execute.call_args.args[1]["owner"] == PUBLIC["user_id"]
    assert db.execute.call_args.args[1]["q"] == "%Pune%"
    assert "OFFSET" not in str(db.execute.call_args.args[0])


def test_readonly_repeatable_snapshot_protocol():
    engine = MagicMock()
    connection = engine.connect.return_value.execution_options.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.all.return_value = []
    with patch.object(planning, "engine", engine):
        snapshot = planning.snapshot_inventory()
    engine.connect.return_value.execution_options.assert_called_once_with(
        isolation_level="REPEATABLE READ"
    )
    sql = [str(c.args[0]).strip() for c in connection.execute.call_args_list]
    assert sql[0] == "SET TRANSACTION READ ONLY"
    assert all(s.startswith("SELECT") for s in sql[1:])
    assert len(sql) == 4 and snapshot["resources"] == []
    connection.commit.assert_not_called()


def test_intelligence_shared_stock_cancellation_delivery(db):
    rows = []
    for id, status, required, allocated, delivered in [
        (1, "OPEN", 10, 2, 0),
        (2, "OPEN", 10, 3, 3),
        (3, "CANCELLED", 100, 0, 0),
        (4, "OPEN", 2, 2, 0),
    ]:
        rows.append(
            dict(
                request_id=id,
                disaster_id=id,
                resource_id=1,
                status=status,
                quantity=Decimal(required),
                allocated_quantity=Decimal(allocated),
                delivered_quantity=Decimal(delivered),
                outstanding_quantity=Decimal(required - allocated),
                available_quantity=Decimal(6),
                resource_name="Water",
                unit="litres",
            )
        )
    db.execute.return_value.mappings.return_value.all.return_value = rows
    result = planning.intelligence(db, ADMIN, "", "", "", "", None, None, 25, 0)
    assert result["metrics"]["outstanding_requests"] == 2
    assert result["resource_totals"][0]["outstanding"] == 15
    assert result["resource_totals"][0]["shortage"] == 9
    assert (
        result["items"][3]["fulfillment"] == "FULFILLED"
        and result["items"][3]["delivered_quantity"] == 0
    )
    assert result["items"][2]["recommended_quantity"] == 0
    db.commit.assert_not_called()
    assert all(str(c.args[0]).lstrip().startswith("SELECT") for c in db.execute.call_args_list)


def test_pdf_empty_unicode_escaped_multiline_map_pagination():
    rows = [
        {
            "id": i,
            "name": "José & <script> harmless",
            "description": "Long description\n" + "Text " * 30,
        }
        for i in range(100)
    ]
    data = build_pdf(
        "Fixture report",
        [("Records", rows, ["id", "name", "description"]), ("Empty", [], ["id", "name"])],
        map_rows=[
            dict(kind="disaster", latitude=26, longitude=92),
            dict(kind="report", latitude=None, longitude=None),
        ],
    )
    reader = PdfReader(BytesIO(data))
    texts = [p.extract_text() for p in reader.pages]
    assert len(texts) > 3
    normalized = " ".join("".join(texts).split())
    assert "Legend:" in normalized and "missing/invalid/outside map coordinates 1" in normalized
    assert "José" in "".join(texts) and "<script>" in "".join(texts)
    assert "No matching records" in "".join(texts)
    assert all("Page " + str(i + 1) in t for i, t in enumerate(texts))
    assert any(p.images for p in reader.pages)


def test_simulator_stock_not_client_controlled(client, scenario):
    app.dependency_overrides[current_user] = lambda: ADMIN
    response = client.post(
        "/api/simulations/run",
        json={**scenario, "available_quantity": 999999},
        headers={"X-DMS-Request": "1"},
    )
    assert response.status_code == 422


def test_bound_exceeds_not_silently_truncated(db):
    db.execute.return_value.mappings.return_value.all.return_value = [{}] * 10001
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        planning.bounded_rows(db, "SELECT resource_id FROM resources")
    assert exc.value.status_code == 413


def test_analysis_filters_pagination_and_export_match(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    with patch(
        "app.routes.history.analytics",
        return_value={
            "items": [{"id": 1, "state": "Assam"}, {"id": 2, "state": "Kerala"}],
            "total": 2,
        },
    ):
        response = client.get("/api/reports/analysis/disasters?q=Assam")
        assert response.status_code == 200 and response.json()["total"] == 1
        assert response.json()["items"][0]["id"] == 1
        csv = client.get("/api/reports/analysis/disasters/csv?q=Assam")
        assert csv.status_code == 200 and "Assam" in csv.text and "Kerala" not in csv.text
        pdf = client.get("/api/reports/analysis/disasters/pdf?q=Assam")
        assert pdf.status_code == 200
        text = "".join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        assert "Assam" in text and "Kerala" not in text


def test_unexpected_errors_keep_restricted_cors(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.side_effect = RuntimeError("Private implementation detail")
    response = client.get("/api/dashboard/", headers={"Origin": "http://127.0.0.1:5500"})
    assert response.status_code == 500
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"
    assert "Private implementation detail" not in response.text
    response = client.get("/api/dashboard/", headers={"Origin": "https://untrusted.invalid"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_allocation_request_filter_parameterized(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.mappings.return_value.all.return_value = []
    assert client.get("/api/resource-allocations/?request_id=7").status_code == 200
    assert db.execute.call_args.args[1]["request_id"] == 7
    assert "request_id=:request_id" in str(db.execute.call_args.args[0])


def test_simulation_cache_capacity_and_reference(client, scenario, snapshot):
    app.dependency_overrides[current_user] = lambda: ADMIN
    planning.RESULTS.clear()
    with patch.object(planning, "snapshot_inventory", return_value=snapshot):
        response = client.post(
            "/api/simulations/run",
            json={**scenario, "disaster_id": 999},
            headers={"X-DMS-Request": "1"},
        )
        assert response.status_code == 422
        with patch.object(planning, "MAX_CACHE_BYTES", 1):
            response = client.post(
                "/api/simulations/run", json=scenario, headers={"X-DMS-Request": "1"}
            )
            assert response.status_code == 503
    assert not planning.RESULTS


def test_simulation_csv_contains_inputs_inventory_and_shelters(client, scenario, snapshot):
    app.dependency_overrides[current_user] = lambda: ADMIN
    planning.RESULTS.clear()
    with patch.object(planning, "snapshot_inventory", return_value=snapshot):
        response = client.post(
            "/api/simulations/run", json=scenario, headers={"X-DMS-Request": "1"}
        )
        identifier = response.json()["simulation_id"]
        csv = client.get(f"/api/simulations/{identifier}/export/csv")
        assert csv.status_code == 200
        assert "Scenario inputs" in csv.text and "Snapshot inventory" in csv.text
        assert "Shelter requirement" in csv.text and "Plan C" in csv.text
        assert "NOT A LIVE INCIDENT" in csv.text and "ISOLATED TEST FIXTURE" in csv.text
    planning.RESULTS.clear()
