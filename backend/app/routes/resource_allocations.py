from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/resource-allocations",
    tags=["Resource Allocations"]
)


class AllocationCreate(BaseModel):
    resource_id: int
    disaster_id: Optional[int] = None
    shelter_id: Optional[int] = None
    allocated_by: Optional[int] = None
    quantity: float
    status: str = "ALLOCATED"


class AllocationUpdate(BaseModel):
    resource_id: int
    disaster_id: Optional[int] = None
    shelter_id: Optional[int] = None
    allocated_by: Optional[int] = None
    quantity: float
    status: str


VALID_STATUSES = [
    "ALLOCATED",
    "DELIVERED",
    "CANCELLED"
]


def validate_target(allocation):
    if allocation.disaster_id is None and allocation.shelter_id is None:
        raise HTTPException(
            status_code=400,
            detail="Either disaster_id or shelter_id must be provided"
        )

    if allocation.disaster_id is not None and allocation.shelter_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either disaster_id or shelter_id, not both"
        )


def validate_status(status):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status must be ALLOCATED, DELIVERED, or CANCELLED"
        )


def check_references(allocation, db):
    resource_check = db.execute(
        text("""
            SELECT resource_id, available_quantity
            FROM resources
            WHERE resource_id = :resource_id
        """),
        {"resource_id": allocation.resource_id}
    ).mappings().first()

    if not resource_check:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    if allocation.disaster_id is not None:
        disaster_check = db.execute(
            text("""
                SELECT disaster_id
                FROM disasters
                WHERE disaster_id = :disaster_id
            """),
            {"disaster_id": allocation.disaster_id}
        ).first()

        if not disaster_check:
            raise HTTPException(
                status_code=404,
                detail="Disaster not found"
            )

    if allocation.shelter_id is not None:
        shelter_check = db.execute(
            text("""
                SELECT shelter_id
                FROM shelters
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": allocation.shelter_id}
        ).first()

        if not shelter_check:
            raise HTTPException(
                status_code=404,
                detail="Shelter not found"
            )

    if allocation.allocated_by is not None:
        user_check = db.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": allocation.allocated_by}
        ).first()

        if not user_check:
            raise HTTPException(
                status_code=404,
                detail="Allocating user not found"
            )


@router.get("/")
def get_all_allocations(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            ra.allocation_id,
            ra.resource_id,
            r.resource_name,
            ra.disaster_id,
            d.title AS disaster_title,
            ra.shelter_id,
            s.name AS shelter_name,
            ra.allocated_by,
            u.full_name AS allocated_by_name,
            ra.quantity,
            ra.allocation_date,
            ra.status
        FROM resource_allocations ra
        JOIN resources r
            ON ra.resource_id = r.resource_id
        LEFT JOIN disasters d
            ON ra.disaster_id = d.disaster_id
        LEFT JOIN shelters s
            ON ra.shelter_id = s.shelter_id
        LEFT JOIN users u
            ON ra.allocated_by = u.user_id
        ORDER BY ra.allocation_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "resource_allocations": [dict(row) for row in result]
    }


@router.get("/{allocation_id}")
def get_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            ra.allocation_id,
            ra.resource_id,
            r.resource_name,
            ra.disaster_id,
            d.title AS disaster_title,
            ra.shelter_id,
            s.name AS shelter_name,
            ra.allocated_by,
            u.full_name AS allocated_by_name,
            ra.quantity,
            ra.allocation_date,
            ra.status
        FROM resource_allocations ra
        JOIN resources r
            ON ra.resource_id = r.resource_id
        LEFT JOIN disasters d
            ON ra.disaster_id = d.disaster_id
        LEFT JOIN shelters s
            ON ra.shelter_id = s.shelter_id
        LEFT JOIN users u
            ON ra.allocated_by = u.user_id
        WHERE ra.allocation_id = :allocation_id
    """)

    result = db.execute(
        query,
        {"allocation_id": allocation_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Resource allocation not found"
        )

    return dict(result)


@router.post("/")
def create_allocation(
    allocation: AllocationCreate,
    db: Session = Depends(get_db)
):
    if allocation.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    validate_target(allocation)
    validate_status(allocation.status)
    check_references(allocation, db)

    resource = db.execute(
        text("""
            SELECT available_quantity
            FROM resources
            WHERE resource_id = :resource_id
        """),
        {"resource_id": allocation.resource_id}
    ).mappings().first()

    if allocation.status != "CANCELLED":
        if allocation.quantity > float(resource["available_quantity"]):
            raise HTTPException(
                status_code=400,
                detail="Insufficient available resource quantity"
            )

    query = text("""
        INSERT INTO resource_allocations (
            resource_id,
            disaster_id,
            shelter_id,
            allocated_by,
            quantity,
            status
        )
        VALUES (
            :resource_id,
            :disaster_id,
            :shelter_id,
            :allocated_by,
            :quantity,
            :status
        )
    """)

    result = db.execute(
        query,
        {
            "resource_id": allocation.resource_id,
            "disaster_id": allocation.disaster_id,
            "shelter_id": allocation.shelter_id,
            "allocated_by": allocation.allocated_by,
            "quantity": allocation.quantity,
            "status": allocation.status
        }
    )

    if allocation.status != "CANCELLED":
        db.execute(
            text("""
                UPDATE resources
                SET available_quantity = available_quantity - :quantity
                WHERE resource_id = :resource_id
            """),
            {
                "quantity": allocation.quantity,
                "resource_id": allocation.resource_id
            }
        )

    db.commit()

    return {
        "message": "Resource allocation created successfully",
        "allocation_id": result.lastrowid
    }


@router.put("/{allocation_id}")
def update_allocation(
    allocation_id: int,
    allocation: AllocationUpdate,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        text("""
            SELECT
                allocation_id,
                resource_id,
                quantity,
                status
            FROM resource_allocations
            WHERE allocation_id = :allocation_id
        """),
        {"allocation_id": allocation_id}
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Resource allocation not found"
        )

    if allocation.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    validate_target(allocation)
    validate_status(allocation.status)
    check_references(allocation, db)

    old_quantity = float(existing["quantity"])
    old_resource_id = existing["resource_id"]
    old_status = existing["status"]

    if old_status != "CANCELLED":
        db.execute(
            text("""
                UPDATE resources
                SET available_quantity = available_quantity + :quantity
                WHERE resource_id = :resource_id
            """),
            {
                "quantity": old_quantity,
                "resource_id": old_resource_id
            }
        )

    if allocation.status != "CANCELLED":
        new_resource = db.execute(
            text("""
                SELECT available_quantity
                FROM resources
                WHERE resource_id = :resource_id
            """),
            {"resource_id": allocation.resource_id}
        ).mappings().first()

        if allocation.quantity > float(new_resource["available_quantity"]):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Insufficient available resource quantity"
            )

    query = text("""
        UPDATE resource_allocations
        SET
            resource_id = :resource_id,
            disaster_id = :disaster_id,
            shelter_id = :shelter_id,
            allocated_by = :allocated_by,
            quantity = :quantity,
            status = :status
        WHERE allocation_id = :allocation_id
    """)

    db.execute(
        query,
        {
            "allocation_id": allocation_id,
            "resource_id": allocation.resource_id,
            "disaster_id": allocation.disaster_id,
            "shelter_id": allocation.shelter_id,
            "allocated_by": allocation.allocated_by,
            "quantity": allocation.quantity,
            "status": allocation.status
        }
    )

    if allocation.status != "CANCELLED":
        db.execute(
            text("""
                UPDATE resources
                SET available_quantity = available_quantity - :quantity
                WHERE resource_id = :resource_id
            """),
            {
                "quantity": allocation.quantity,
                "resource_id": allocation.resource_id
            }
        )

    db.commit()

    return {
        "message": "Resource allocation updated successfully",
        "allocation_id": allocation_id
    }


@router.delete("/{allocation_id}")
def delete_allocation(
    allocation_id: int,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        text("""
            SELECT
                allocation_id,
                resource_id,
                quantity,
                status
            FROM resource_allocations
            WHERE allocation_id = :allocation_id
        """),
        {"allocation_id": allocation_id}
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Resource allocation not found"
        )

    if existing["status"] != "CANCELLED":
        db.execute(
            text("""
                UPDATE resources
                SET available_quantity = available_quantity + :quantity
                WHERE resource_id = :resource_id
            """),
            {
                "quantity": existing["quantity"],
                "resource_id": existing["resource_id"]
            }
        )

    db.execute(
        text("""
            DELETE FROM resource_allocations
            WHERE allocation_id = :allocation_id
        """),
        {"allocation_id": allocation_id}
    )

    db.commit()

    return {
        "message": "Resource allocation deleted successfully",
        "allocation_id": allocation_id
    }