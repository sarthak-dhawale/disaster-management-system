from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.exc import OperationalError
from app.main import app
from app.security import current_user
from app.history_schema import TABLES, VIEWS, audit_trigger, ledger_trigger, install_history
from app.database import clear_history_context
from conftest import ADMIN, PUBLIC

READ_PATHS = [
    "/api/audit-history/",
    "/api/resource-movements/",
    "/api/analytics/shelters",
    "/api/analytics/disasters",
    "/api/analytics/monthly-reports",
    "/api/analytics/resource-allocations",
]


@pytest.mark.parametrize("path", READ_PATHS)
def test_history_admin_only(client, db, path):
    assert client.get(path).status_code == 401
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert client.get(path).status_code == 403
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.mappings.return_value.all.return_value = []
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json() == dict(items=[], total=0, limit=25, offset=0)


@pytest.mark.parametrize(
    "path",
    [
        "/api/audit-history/?entity=users;DROP TABLE users",
        "/api/audit-history/?record_id=0",
        "/api/audit-history/?action=HACK",
        "/api/resource-movements/?movement_kind=INVALID",
        "/api/resource-movements/?limit=101",
        "/api/resource-movements/?offset=-1",
        "/api/audit-history/?start=2026-10-11&end=2026-10-10",
        "/api/resource-movements/?end=9999-12-31",
    ],
)
def test_invalid_filters_do_not_query_history(client, db, path):
    app.dependency_overrides[current_user] = lambda: ADMIN
    assert client.get(path).status_code == 422
    db.execute.assert_not_called()


def test_filters_and_inclusive_end_are_parameterized(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.scalar_one.return_value = 7
    db.execute.return_value.mappings.return_value.all.return_value = [{"audit_id": 3}]
    response = client.get(
        "/api/audit-history/?entity=disasters&record_id=4&action=UPDATE&start=2026-10-01&end=2026-10-11&limit=5&offset=2"
    )
    assert response.json()["items"] == [{"audit_id": 3}]
    query, params = db.execute.call_args.args
    assert params["until"] == date(2026, 10, 12)
    assert params["entity"] == "disasters" and params["record_id"] == 4 and params["offset"] == 2
    assert "disasters" not in str(query) and "created_at<:until" in str(query)


@pytest.mark.parametrize(
    "kind,qty,total,available",
    [("RESTOCK", "2.25", "12.25", "8.25"), ("WITHDRAW", "2.25", "7.75", "3.75")],
)
def test_stock_changes_are_locked_decimal_and_transactional(
    client, db, kind, qty, total, available
):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = {
        "resource_id": 1,
        "total_quantity": Decimal(10),
        "available_quantity": Decimal(6),
    }
    response = client.post(
        "/api/resources/1/stock",
        headers={"X-DMS-Request": "1"},
        json=dict(kind=kind, quantity=qty, note="Warehouse receipt"),
    )
    assert response.status_code == 201, response.text
    assert Decimal(response.json()["total_quantity"]) == Decimal(total)
    assert Decimal(response.json()["available_quantity"]) == Decimal(available)
    calls = db.execute.call_args_list
    assert "FOR UPDATE" in str(calls[0].args[0])
    assert calls[1].args[1]["kind"] == kind
    assert calls[2].args[1]["available_quantity"] == Decimal(available)
    assert "@dms_movement_kind=NULL" in str(calls[3].args[0])
    db.commit.assert_called_once()


def test_withdraw_cannot_consume_reserved_stock(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = {
        "total_quantity": Decimal(10),
        "available_quantity": Decimal(2),
    }
    response = client.post(
        "/api/resources/1/stock",
        headers={"X-DMS-Request": "1"},
        json=dict(kind="WITHDRAW", quantity=3, note="Damaged stock"),
    )
    assert response.status_code == 409
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_restock_overflow_rejected(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = {
        "total_quantity": Decimal("9999999999.99"),
        "available_quantity": Decimal(2),
    }
    assert (
        client.post(
            "/api/resources/1/stock",
            headers={"X-DMS-Request": "1"},
            json=dict(kind="RESTOCK", quantity=1, note="Receipt"),
        ).status_code
        == 422
    )
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "RESTOCK", "quantity": 0, "note": "Receipt"},
        {"kind": "RESTOCK", "quantity": -1, "note": "Receipt"},
        {"kind": "RESTOCK", "quantity": "0.001", "note": "Receipt"},
        {"kind": "RETURN", "quantity": 1, "note": "Receipt"},
        {"kind": "RESTOCK", "quantity": 1, "note": " "},
        {"kind": "RESTOCK", "quantity": 1, "note": "Receipt", "actor_id": 999},
    ],
)
def test_invalid_stock_input(client, db, data):
    app.dependency_overrides[current_user] = lambda: ADMIN
    assert (
        client.post("/api/resources/1/stock", headers={"X-DMS-Request": "1"}, json=data).status_code
        == 422
    )
    db.commit.assert_not_called()


def test_stock_missing_and_public_permissions(client, db):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    data = dict(kind="RESTOCK", quantity=1, note="Receipt")
    assert (
        client.post("/api/resources/1/stock", headers={"X-DMS-Request": "1"}, json=data).status_code
        == 403
    )
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert (
        client.post("/api/resources/1/stock", headers={"X-DMS-Request": "1"}, json=data).status_code
        == 404
    )


def test_db_failure_rolls_back_stock(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.side_effect = OperationalError("query", {}, Exception("offline"))
    assert (
        client.post(
            "/api/resources/1/stock",
            headers={"X-DMS-Request": "1"},
            json=dict(kind="RESTOCK", quantity=1, note="Receipt"),
        ).status_code
        == 503
    )
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_analytics_avoids_unit_sums_and_join_multiplication(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.scalar_one.return_value = 0
    db.execute.return_value.mappings.return_value.all.return_value = []
    assert client.get("/api/analytics/resource-allocations").status_code == 200
    sql = str(db.execute.call_args.args[0])
    assert (
        "r.unit" in sql
        and "status!='CANCELLED'" in sql
        and "GROUP BY a.disaster_id,a.shelter_id" in sql
    )
    assert "COUNT(DISTINCT volunteer_id)" in VIEWS["dms_disaster_allocations"]
    import re

    assert re.search(r"LEFT\s+JOIN\s+\(\s*SELECT", VIEWS["dms_disaster_allocations"])
    assert client.get("/api/analytics/unknown").status_code == 404


@pytest.mark.parametrize("table", list(TABLES))
def test_trigger_snapshots_are_explicit_and_secret_free(table):
    for action in ["INSERT", "UPDATE", "DELETE"]:
        sql = audit_trigger(table, action)
        assert "AFTER " + action in sql and "@dms_actor_id" in sql
        for secret in ["password", "token_hash", "email", "phone", "emergency_contact"]:
            assert secret not in sql
        assert "DROP " not in sql


def test_ledger_only_logs_actual_stock_changes():
    assert (
        "NEW.total_quantity!=OLD.total_quantity OR NEW.available_quantity!=OLD.available_quantity"
        in ledger_trigger("UPDATE")
    )
    assert "NEW.available_quantity-OLD.available_quantity" in ledger_trigger("UPDATE")
    assert "'REMOVAL'" in ledger_trigger("DELETE")


def test_pooled_context_cannot_leak_actor_or_movement():
    connection = MagicMock()
    clear_history_context(connection, None, None)
    query = connection.cursor.return_value.__enter__.return_value.execute.call_args.args[0]
    for var in ["actor_id", "actor_name", "movement_kind", "movement_note", "allocation_id"]:
        assert "@dms_" + var + "=NULL" in query


def test_migration_does_not_replace_existing_triggers_or_views():
    conn = MagicMock()
    names = [
        (f"dms_v12_audit_{table}_{a.lower()}",)
        for table in TABLES
        for a in ["INSERT", "UPDATE", "DELETE"]
    ]
    names += [(f"dms_v12_ledger_{a.lower()}",) for a in ["INSERT", "UPDATE", "DELETE"]]
    conn.execute.return_value = names
    with patch("app.history_schema.inspect") as inspector:
        inspector.return_value.get_view_names.return_value = list(VIEWS)
        install_history(conn)
    sql = [c.args[0] for c in conn.exec_driver_sql.call_args_list]
    assert len(sql) == 3 and all("DROP " not in q for q in sql)
    assert "NOT EXISTS" in sql[-1] and "earlier movements unknown" in sql[-1]


def test_history_has_no_mutation_routes(client):
    app.dependency_overrides[current_user] = lambda: ADMIN
    for path in ["/api/audit-history/", "/api/resource-movements/"]:
        assert client.delete(path, headers={"X-DMS-Request": "1"}).status_code == 405
