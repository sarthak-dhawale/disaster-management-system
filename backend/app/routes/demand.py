"""Demand requests reuse inventory and existing locked allocation mutations."""

from decimal import Decimal
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import Field
from sqlalchemy import text
from app.database import get_db
from app.security import require_admin
from app.models import Model, ID, AllocationCreate
from app.crud import record, insert, update, allocation_save

router = APIRouter(
    prefix="/api/resource-requests", tags=["Resource demand"], dependencies=[Depends(require_admin)]
)
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class DemandCreate(Model):
    disaster_id: ID
    resource_id: ID
    quantity: PositiveQuantity
    note: Annotated[str, Field(max_length=500)] | None = None


class DemandEdit(Model):
    quantity: PositiveQuantity
    note: Annotated[str, Field(max_length=500)] | None = None


class Approval(Model):
    quantity: PositiveQuantity
    idempotency_key: Annotated[str, Field(min_length=16, max_length=64, pattern="^[A-Za-z0-9-]+$")]


LIST = """
SELECT rr.*,d.title AS disaster_title,d.severity,r.resource_name,r.unit,r.available_quantity,
       COALESCE(a.allocated, 0) AS allocated_quantity,
       COALESCE(a.delivered, 0) AS delivered_quantity, GREATEST(0,

                                                         rr.quantity-COALESCE(a.allocated,
                                                                       0)) AS outstanding_quantity
FROM resource_requests rr
JOIN disasters d ON d.disaster_id=rr.disaster_id
JOIN resources r ON r.resource_id=rr.resource_id
LEFT JOIN
  (SELECT request_id,SUM(quantity) AS allocated,
          SUM(CASE WHEN status='DELIVERED' THEN quantity ELSE 0
              END) AS delivered
   FROM resource_allocations
   WHERE status!='CANCELLED'
   GROUP BY request_id) a ON a.request_id=rr.request_id
"""


@router.get("/")
def demand_list(
    db=Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    resource_id: int | None = Query(None, gt=0),
    disaster_id: int | None = Query(None, gt=0),
):
    clauses = []
    params = {"limit": limit, "offset": offset}
    for key, value in [("resource_id", resource_id), ("disaster_id", disaster_id)]:
        if value:
            clauses.append("rr." + key + "=:" + key)
            params[key] = value
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(
        text("SELECT COUNT(*) FROM resource_requests rr" + where), params
    ).scalar_one()
    rows = (
        db.execute(
            text(
                LIST
                + where
                + " ORDER BY CASE d.severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,rr.created_at,rr.request_id LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        .mappings()
        .all()
    )
    items = []
    for raw in rows:
        row = dict(raw)
        outstanding = row["outstanding_quantity"]
        available = row["available_quantity"]
        row["recommended_quantity"] = (
            min(outstanding, available) if row["status"] == "OPEN" else Decimal(0)
        )
        row["shortage_quantity"] = (
            max(Decimal(0), outstanding - available) if row["status"] == "OPEN" else Decimal(0)
        )
        row["fulfillment"] = (
            "CANCELLED"
            if row["status"] == "CANCELLED"
            else "FULFILLED"
            if outstanding == 0
            else "PARTIAL"
            if row["allocated_quantity"]
            else "UNFULFILLED"
        )
        row["recommendation_reason"] = (
            "Same inventory resource and unit; recommend min(outstanding demand, available stock). Manager approval required; other requests compete for this stock."
        )
        items.append(row)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/", status_code=201)
def create(body: DemandCreate, db=Depends(get_db), user=Depends(require_admin)):
    record(db, "disasters", body.disaster_id)
    record(db, "resources", body.resource_id)
    id = insert(db, "resource_requests", {**body.model_dump(), "created_by": user["user_id"]})
    db.commit()
    return {"request_id": id, "message": "Demand recorded; inventory unchanged"}


@router.put("/{id}")
def edit(body: DemandEdit, id: int = Path(gt=0), db=Depends(get_db)):
    old = record(db, "resource_requests", id, True)
    if old["status"] != "OPEN":
        raise HTTPException(409, "Cancelled requests cannot be edited")
    allocated = db.execute(
        text(
            "SELECT COALESCE(SUM(quantity),0) FROM resource_allocations WHERE request_id=:id AND status!='CANCELLED'"
        ),
        {"id": id},
    ).scalar_one()
    if body.quantity < allocated:
        raise HTTPException(409, "Requested quantity cannot be below existing allocations")
    update(db, "resource_requests", id, body.model_dump())
    db.commit()
    return {"message": "Demand updated", "request_id": id}


@router.post("/{id}/cancel")
def cancel(id: int = Path(gt=0), db=Depends(get_db)):
    record(db, "resource_requests", id, True)
    active = db.execute(
        text(
            "SELECT COUNT(*) FROM resource_allocations WHERE request_id=:id AND status!='CANCELLED'"
        ),
        {"id": id},
    ).scalar_one()
    if active:
        raise HTTPException(409, "Cancel linked allocations before cancelling this request")
    update(db, "resource_requests", id, {"status": "CANCELLED"})
    db.commit()
    return {"message": "Demand cancelled; stock unchanged"}


@router.post("/{id}/approve", status_code=201)
def approve(body: Approval, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)):
    request = record(db, "resource_requests", id, True)
    previous = (
        db.execute(
            text(
                "SELECT allocation_id,request_id,quantity,allocated_by FROM resource_allocations WHERE approval_key=:key"
            ),
            {"key": body.idempotency_key},
        )
        .mappings()
        .first()
    )
    if previous:
        if (
            previous["request_id"] != id
            or previous["quantity"] != body.quantity
            or previous["allocated_by"] != user["user_id"]
        ):
            raise HTTPException(409, "Approval reference already belongs to a different action")
        return {"message": "Approval already recorded", "allocation_id": previous["allocation_id"]}
    return allocation_save(
        db,
        AllocationCreate(
            resource_id=request["resource_id"],
            disaster_id=request["disaster_id"],
            request_id=id,
            quantity=body.quantity,
            allocated_by=user["user_id"],
        ),
        approval_key=body.idempotency_key,
    )
