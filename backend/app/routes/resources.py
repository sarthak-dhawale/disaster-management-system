from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/api/resources", tags=["Resources"])


class ResourceCreate(BaseModel):
    resource_name: str
    category: str
    unit: str
    total_quantity: float = 0
    available_quantity: float = 0
    minimum_required: float = 0


class ResourceUpdate(BaseModel):
    resource_name: str
    category: str
    unit: str
    total_quantity: float
    available_quantity: float
    minimum_required: float


VALID_CATEGORIES = [
    "FOOD",
    "WATER",
    "MEDICINE",
    "CLOTHING",
    "EQUIPMENT",
    "SHELTER_SUPPLIES",
    "OTHER"
]


def validate_resource(resource):
    if resource.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid resource category"
        )

    if resource.total_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Total quantity cannot be negative"
        )

    if resource.available_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Available quantity cannot be negative"
        )

    if resource.available_quantity > resource.total_quantity:
        raise HTTPException(
            status_code=400,
            detail="Available quantity cannot exceed total quantity"
        )

    if resource.minimum_required < 0:
        raise HTTPException(
            status_code=400,
            detail="Minimum required cannot be negative"
        )


@router.get("/")
def get_all_resources(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            resource_id,
            resource_name,
            category,
            unit,
            total_quantity,
            available_quantity,
            minimum_required,
            updated_at
        FROM resources
        ORDER BY resource_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "resources": [dict(row) for row in result]
    }


@router.get("/{resource_id}")
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            resource_id,
            resource_name,
            category,
            unit,
            total_quantity,
            available_quantity,
            minimum_required,
            updated_at
        FROM resources
        WHERE resource_id = :resource_id
    """)

    result = db.execute(
        query,
        {"resource_id": resource_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    return dict(result)


@router.post("/")
def create_resource(
    resource: ResourceCreate,
    db: Session = Depends(get_db)
):
    validate_resource(resource)

    query = text("""
        INSERT INTO resources (
            resource_name,
            category,
            unit,
            total_quantity,
            available_quantity,
            minimum_required
        )
        VALUES (
            :resource_name,
            :category,
            :unit,
            :total_quantity,
            :available_quantity,
            :minimum_required
        )
    """)

    result = db.execute(
        query,
        {
            "resource_name": resource.resource_name,
            "category": resource.category,
            "unit": resource.unit,
            "total_quantity": resource.total_quantity,
            "available_quantity": resource.available_quantity,
            "minimum_required": resource.minimum_required
        }
    )

    db.commit()

    return {
        "message": "Resource created successfully",
        "resource_id": result.lastrowid
    }


@router.put("/{resource_id}")
def update_resource(
    resource_id: int,
    resource: ResourceUpdate,
    db: Session = Depends(get_db)
):
    resource_check = db.execute(
        text("""
            SELECT resource_id
            FROM resources
            WHERE resource_id = :resource_id
        """),
        {"resource_id": resource_id}
    ).first()

    if not resource_check:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    validate_resource(resource)

    query = text("""
        UPDATE resources
        SET
            resource_name = :resource_name,
            category = :category,
            unit = :unit,
            total_quantity = :total_quantity,
            available_quantity = :available_quantity,
            minimum_required = :minimum_required
        WHERE resource_id = :resource_id
    """)

    db.execute(
        query,
        {
            "resource_id": resource_id,
            "resource_name": resource.resource_name,
            "category": resource.category,
            "unit": resource.unit,
            "total_quantity": resource.total_quantity,
            "available_quantity": resource.available_quantity,
            "minimum_required": resource.minimum_required
        }
    )

    db.commit()

    return {
        "message": "Resource updated successfully",
        "resource_id": resource_id
    }


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db)
):
    resource_check = db.execute(
        text("""
            SELECT resource_id
            FROM resources
            WHERE resource_id = :resource_id
        """),
        {"resource_id": resource_id}
    ).first()

    if not resource_check:
        raise HTTPException(
            status_code=404,
            detail="Resource not found"
        )

    try:
        db.execute(
            text("""
                DELETE FROM resources
                WHERE resource_id = :resource_id
            """),
            {"resource_id": resource_id}
        )

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Resource cannot be deleted because it is being used by another record"
        )

    return {
        "message": "Resource deleted successfully",
        "resource_id": resource_id
    }