"""Administrative history and analytics; no history update/delete endpoints."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import Field
from sqlalchemy import text
from app.database import get_db
from app.security import require_admin
from app.models import Model
from app.crud import record, update
from app.history import movement_context
from app.history_schema import TABLES

router = APIRouter(
    prefix="/api", tags=["History and reports"], dependencies=[Depends(require_admin)]
)


def dates(start, end):
    if start and end and start > end:
        raise HTTPException(422, "Start date must not follow end date")
    if end and end == date.max:
        raise HTTPException(422, "End date is outside supported range")
    return end + timedelta(days=1) if end else None


def history_list(db, table, idfield, limit, offset, start, end, extra):
    until = dates(start, end)
    clauses = []
    params = {"limit": limit, "offset": offset}
    if start:
        clauses.append("created_at>=:start")
        params["start"] = start
    if until:
        clauses.append("created_at<:until")
        params["until"] = until
    for key, value in extra.items():
        if value is not None:
            clauses.append(key + "=:" + key)
            params[key] = value
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM {table}" + where), params).scalar_one()
    rows = (
        db.execute(
            text(
                f"SELECT * FROM {table}"
                + where
                + f" ORDER BY {idfield} DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        .mappings()
        .all()
    )
    return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/audit-history/")
def audit(
    db=Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    entity: str | None = None,
    action: Literal["INSERT", "UPDATE", "DELETE"] | None = None,
    record_id: int | None = Query(None, gt=0),
    start: date | None = None,
    end: date | None = None,
):
    if entity is not None and entity not in TABLES:
        raise HTTPException(422, "Unknown history module")
    return history_list(
        db,
        "audit_history",
        "audit_id",
        limit,
        offset,
        start,
        end,
        dict(entity=entity, action=action, record_id=record_id),
    )


@router.get("/resource-movements/")
def ledger(
    db=Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    resource_id: int | None = Query(None, gt=0),
    start: date | None = None,
    end: date | None = None,
    movement_kind: Literal[
        "OPENING",
        "RESTOCK",
        "WITHDRAW",
        "ALLOCATION_CHANGE",
        "RETURN",
        "INVENTORY_ADJUSTMENT",
        "REMOVAL",
    ]
    | None = None,
):
    return history_list(
        db,
        "resource_movements",
        "movement_id",
        limit,
        offset,
        start,
        end,
        dict(resource_id=resource_id, movement_kind=movement_kind),
    )


class StockMovement(Model):
    kind: Literal["RESTOCK", "WITHDRAW"]
    quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    note: Annotated[str, Field(min_length=3, max_length=500)]


@router.post("/resources/{id}/stock", status_code=201)
def stock(body: StockMovement, id: int = Path(gt=0), db=Depends(get_db)):
    resource = record(db, "resources", id, True)
    delta = body.quantity if body.kind == "RESTOCK" else -body.quantity
    total = resource["total_quantity"] + delta
    available = resource["available_quantity"] + delta
    if available < 0:
        raise HTTPException(409, "Cannot withdraw allocated or unavailable stock")
    if total > Decimal("9999999999.99"):
        raise HTTPException(422, "Result exceeds supported inventory quantity")
    with movement_context(db, body.kind, body.note):
        update(db, "resources", id, dict(total_quantity=total, available_quantity=available))
    db.commit()
    return {
        "message": "Stock movement recorded",
        "resource_id": id,
        "total_quantity": total,
        "available_quantity": available,
    }


REPORTS = {
    "shelters": ("dms_shelter_occupancy", "shelter_id"),
    "disasters": ("dms_disaster_allocations", "disaster_id"),
    "monthly-reports": ("dms_monthly_reports", "report_month DESC,location_id"),
    "resource-allocations": (None, None),
}


@router.get("/analytics/{section}")
def analytics(
    section: str,
    db=Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if section not in REPORTS:
        raise HTTPException(404, "Report not found")
    view, order = REPORTS[section]
    if view:
        source = f"SELECT * FROM {view}"
    else:
        # Never add quantities with incompatible units. Each row is one target/resource.
        source = """
SELECT a.disaster_id,a.shelter_id,
       COALESCE(d.title, s.name) AS target, r.resource_id,r.resource_name, r.unit,COUNT(*) AS allocation_count,
       SUM(a.quantity) AS allocated_quantity
FROM resource_allocations a
JOIN resources r ON r.resource_id=a.resource_id
LEFT JOIN disasters d ON d.disaster_id=a.disaster_id
LEFT JOIN shelters s ON s.shelter_id=a.shelter_id
WHERE a.status!='CANCELLED'
GROUP BY a.disaster_id,a.shelter_id,d.title,s.name,r.resource_id,r.resource_name,r.unit
"""
        order = "resource_id,disaster_id,shelter_id"
    total = db.execute(text("SELECT COUNT(*) FROM (" + source + ") report_rows")).scalar_one()
    rows = (
        db.execute(
            text(source + " ORDER BY " + order + " LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}
