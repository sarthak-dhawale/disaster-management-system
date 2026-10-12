"""Read-only planning endpoints; live approvals remain in the existing demand router."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from uuid import uuid4
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from app.database import engine, get_db
from app.security import require_admin
from app.planning import Scenario, compare_plans
from app.routes.demand import LIST

router = APIRouter(prefix="/api", tags=["Resource intelligence and hypothetical planning"])
MAX_RECORDS = 10000
TTL = 3600
MAX_CACHE_BYTES = 32 * 1024 * 1024
RESULTS = {}
LOCK = RLock()


def bounded_rows(db, sql, params=None):
    rows = [
        dict(row) for row in db.execute(text(sql + " LIMIT 10001"), params or {}).mappings().all()
    ]
    if len(rows) > MAX_RECORDS:
        raise HTTPException(
            413, "Planning scope exceeds 10,000 records. Narrow the filter before continuing."
        )
    return rows


def snapshot_inventory():
    # Separate connection avoids altering the authentication session's transaction.
    # First SELECT establishes one InnoDB repeatable-read snapshot; READ ONLY prohibits DML.
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        resources = bounded_rows(
            connection,
            """SELECT r.*,COALESCE(a.committed,0) AS committed_quantity
            FROM resources r LEFT JOIN (SELECT resource_id,SUM(quantity) AS committed
            FROM resource_allocations WHERE status!='CANCELLED' GROUP BY resource_id) a
            ON a.resource_id=r.resource_id ORDER BY r.resource_id""",
        )
        shelters = bounded_rows(
            connection,
            """SELECT s.shelter_id,s.name,s.status,s.capacity,s.current_occupancy,
            l.state,l.city,l.latitude,l.longitude FROM shelters s JOIN locations l ON l.location_id=s.location_id
            ORDER BY s.shelter_id""",
        )
        disasters = bounded_rows(
            connection, "SELECT disaster_id,title,status FROM disasters ORDER BY disaster_id"
        )
        for row in resources:
            for key in [
                "total_quantity",
                "available_quantity",
                "minimum_required",
                "committed_quantity",
            ]:
                row[key] = str(row[key])
            row.pop("updated_at", None)
        for row in shelters:
            for key in ["latitude", "longitude"]:
                row[key] = float(row[key]) if row[key] is not None else None
        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "provenance": "MySQL InnoDB repeatable-read, read-only transaction; live resources and shelters",
            "resources": resources,
            "shelters": shelters,
            "disasters": disasters,
        }


@router.get("/resource-intelligence")
def intelligence(
    db=Depends(get_db),
    user=Depends(require_admin),
    q: str = Query("", max_length=150),
    state: str = Query("", max_length=100),
    severity: str = Query("", max_length=30),
    status: str = Query("", pattern="^(|FULFILLED|PARTIAL|UNFULFILLED|CANCELLED)$"),
    resource_id: int | None = Query(None, gt=0),
    disaster_id: int | None = Query(None, gt=0),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    sql = LIST.replace("SELECT rr.*", "SELECT l.state,l.city,rr.*").replace(
        "JOIN resources r", "JOIN locations l ON l.location_id=d.location_id JOIN resources r"
    )
    clauses, params = [], {}
    for key, value, column in [
        ("state", state, "l.state"),
        ("severity", severity, "d.severity"),
        ("resource_id", resource_id, "rr.resource_id"),
        ("disaster_id", disaster_id, "rr.disaster_id"),
    ]:
        if value:
            clauses.append(column + "=:" + key)
            params[key] = value
    if q:
        clauses.append("CONCAT_WS(' ',d.title,r.resource_name,l.state,l.city,rr.note) LIKE :q")
        params["q"] = "%" + q + "%"
    rows = bounded_rows(
        db,
        sql
        + (" WHERE " + " AND ".join(clauses) if clauses else "")
        + " ORDER BY rr.request_id DESC",
        params,
    )
    from decimal import Decimal

    totals = {}
    for row in rows:
        row["fulfillment"] = (
            "CANCELLED"
            if row["status"] == "CANCELLED"
            else "FULFILLED"
            if row["outstanding_quantity"] == 0
            else "PARTIAL"
            if row["allocated_quantity"]
            else "UNFULFILLED"
        )
        row["recommended_quantity"] = (
            min(row["outstanding_quantity"], row["available_quantity"])
            if row["status"] == "OPEN"
            else Decimal(0)
        )
        row["recommendation_reason"] = (
            "Same resource ID and unit; stock is shared across requests. Approval revalidates live stock. No warehouse distance is available."
        )
        if row["status"] == "OPEN":
            group = totals.setdefault(
                row["resource_id"],
                {
                    "resource_id": row["resource_id"],
                    "resource_name": row["resource_name"],
                    "unit": row["unit"],
                    "outstanding": Decimal(0),
                    "available": row["available_quantity"],
                },
            )
            group["outstanding"] += row["outstanding_quantity"]
    for group in totals.values():
        group["shortage"] = max(Decimal(0), group["outstanding"] - group["available"])
    filtered = [r for r in rows if not status or r["fulfillment"] == status]
    return {
        "items": filtered[offset : offset + limit],
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "metrics": {
            "disasters_with_unmet_demand": len(
                {
                    r["disaster_id"]
                    for r in filtered
                    if r["status"] == "OPEN" and r["outstanding_quantity"] > 0
                }
            ),
            "outstanding_requests": sum(
                r["status"] == "OPEN" and r["outstanding_quantity"] > 0 for r in filtered
            ),
            "shortage_resource_types": sum(g["shortage"] > 0 for g in totals.values()),
            "fulfilled": sum(r["fulfillment"] == "FULFILLED" for r in filtered),
            "partial": sum(r["fulfillment"] == "PARTIAL" for r in filtered),
            "unallocated": sum(r["fulfillment"] == "UNFULFILLED" for r in filtered),
        },
        "resource_totals": list(totals.values()),
        "scope_note": "Request metrics respect all filters. Resource shortage groups respect search/region/severity/resource/disaster filters and include all OPEN requests before fulfillment filtering. Coverage means non-cancelled reserved or delivered allocations; delivery is displayed separately.",
    }


@router.get("/simulations/catalog")
def catalog(user=Depends(require_admin)):
    return snapshot_inventory()


@router.post("/simulations/run", status_code=201)
def run(body: Scenario, user=Depends(require_admin)):
    snapshot = snapshot_inventory()
    if body.disaster_id and not any(
        d["disaster_id"] == body.disaster_id for d in snapshot["disasters"]
    ):
        raise HTTPException(422, "Referenced official disaster does not exist")
    try:
        result = compare_plans(body, snapshot)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result["simulation_id"] = uuid4().hex
    result["expires_in_seconds"] = TTL
    with LOCK:
        now = monotonic()
        for key in list(RESULTS):
            if RESULTS[key][0] <= now:
                del RESULTS[key]
        if len(RESULTS) >= 100:
            raise HTTPException(
                503, "Simulation cache is full. Discard an older result or retry after expiry."
            )
        current_bytes = sum(
            len(json.dumps(saved[2], default=str).encode("utf-8")) for saved in RESULTS.values()
        )
        if current_bytes + len(json.dumps(result, default=str).encode("utf-8")) > MAX_CACHE_BYTES:
            raise HTTPException(
                503, "Simulation memory budget reached. Discard an older result and retry."
            )
        RESULTS[result["simulation_id"]] = (now + TTL, user["user_id"], result)
    return deepcopy(result)


def owned_result(id, user):
    with LOCK:
        saved = RESULTS.get(id)
        if not saved or saved[0] <= monotonic() or saved[1] != user["user_id"]:
            raise HTTPException(404, "Simulation expired or unavailable for this account")
        return deepcopy(saved[2])


@router.get("/simulations/{id}")
def retrieve(id: str, user=Depends(require_admin)):
    return owned_result(id, user)


@router.delete("/simulations/{id}")
def discard(id: str, user=Depends(require_admin)):
    owned_result(id, user)
    with LOCK:
        RESULTS.pop(id, None)
    return {"message": "Hypothetical result discarded; live records unchanged"}
