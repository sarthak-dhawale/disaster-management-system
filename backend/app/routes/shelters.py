from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(
    prefix="/api/shelters",
    tags=["Shelters"]
)


class ShelterCreate(BaseModel):
    location_id: int
    name: str
    capacity: int
    current_occupancy: int = 0
    contact_phone: Optional[str] = None
    status: str = "AVAILABLE"


class ShelterUpdate(BaseModel):
    location_id: int
    name: str
    capacity: int
    current_occupancy: int
    contact_phone: Optional[str] = None
    status: str


@router.get("/")
def get_all_shelters(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            shelter_id,
            location_id,
            name,
            capacity,
            current_occupancy,
            contact_phone,
            status,
            created_at
        FROM shelters
        ORDER BY shelter_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "shelters": [dict(row) for row in result]
    }


@router.post("/")
def create_shelter(
    shelter: ShelterCreate,
    db: Session = Depends(get_db)
):
    # Check whether location exists
    location_check = db.execute(
        text("""
            SELECT location_id
            FROM locations
            WHERE location_id = :location_id
        """),
        {"location_id": shelter.location_id}
    ).first()

    if not location_check:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    # Validate capacity
    if shelter.capacity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Capacity must be greater than 0"
        )

    # Validate occupancy
    if shelter.current_occupancy < 0:
        raise HTTPException(
            status_code=400,
            detail="Current occupancy cannot be negative"
        )

    if shelter.current_occupancy > shelter.capacity:
        raise HTTPException(
            status_code=400,
            detail="Current occupancy cannot exceed capacity"
        )

    # Validate status
    valid_statuses = ["AVAILABLE", "FULL", "CLOSED"]

    if shelter.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be AVAILABLE, FULL, or CLOSED"
        )

    query = text("""
        INSERT INTO shelters
        (
            location_id,
            name,
            capacity,
            current_occupancy,
            contact_phone,
            status
        )
        VALUES
        (
            :location_id,
            :name,
            :capacity,
            :current_occupancy,
            :contact_phone,
            :status
        )
    """)

    result = db.execute(
        query,
        {
            "location_id": shelter.location_id,
            "name": shelter.name,
            "capacity": shelter.capacity,
            "current_occupancy": shelter.current_occupancy,
            "contact_phone": shelter.contact_phone,
            "status": shelter.status
        }
    )

    db.commit()

    shelter_id = result.lastrowid

    return {
        "message": "Shelter created successfully",
        "shelter_id": shelter_id
    }


@router.get("/{shelter_id}")
def get_shelter(
    shelter_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            shelter_id,
            location_id,
            name,
            capacity,
            current_occupancy,
            contact_phone,
            status,
            created_at
        FROM shelters
        WHERE shelter_id = :shelter_id
    """)

    result = db.execute(
        query,
        {"shelter_id": shelter_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Shelter not found"
        )

    return dict(result)


@router.put("/{shelter_id}")
def update_shelter(
    shelter_id: int,
    shelter: ShelterUpdate,
    db: Session = Depends(get_db)
):
    # Check whether shelter exists
    shelter_check = db.execute(
        text("""
            SELECT shelter_id
            FROM shelters
            WHERE shelter_id = :shelter_id
        """),
        {"shelter_id": shelter_id}
    ).first()

    if not shelter_check:
        raise HTTPException(
            status_code=404,
            detail="Shelter not found"
        )

    # Check whether location exists
    location_check = db.execute(
        text("""
            SELECT location_id
            FROM locations
            WHERE location_id = :location_id
        """),
        {"location_id": shelter.location_id}
    ).first()

    if not location_check:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    # Validate capacity
    if shelter.capacity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Capacity must be greater than 0"
        )

    # Validate occupancy
    if shelter.current_occupancy < 0:
        raise HTTPException(
            status_code=400,
            detail="Current occupancy cannot be negative"
        )

    if shelter.current_occupancy > shelter.capacity:
        raise HTTPException(
            status_code=400,
            detail="Current occupancy cannot exceed capacity"
        )

    # Validate status
    valid_statuses = ["AVAILABLE", "FULL", "CLOSED"]

    if shelter.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be AVAILABLE, FULL, or CLOSED"
        )

    query = text("""
        UPDATE shelters
        SET
            location_id = :location_id,
            name = :name,
            capacity = :capacity,
            current_occupancy = :current_occupancy,
            contact_phone = :contact_phone,
            status = :status
        WHERE shelter_id = :shelter_id
    """)

    db.execute(
        query,
        {
            "shelter_id": shelter_id,
            "location_id": shelter.location_id,
            "name": shelter.name,
            "capacity": shelter.capacity,
            "current_occupancy": shelter.current_occupancy,
            "contact_phone": shelter.contact_phone,
            "status": shelter.status
        }
    )

    db.commit()

    return {
        "message": "Shelter updated successfully",
        "shelter_id": shelter_id
    }


@router.delete("/{shelter_id}")
def delete_shelter(
    shelter_id: int,
    db: Session = Depends(get_db)
):
    # Check whether shelter exists
    shelter_check = db.execute(
        text("""
            SELECT shelter_id
            FROM shelters
            WHERE shelter_id = :shelter_id
        """),
        {"shelter_id": shelter_id}
    ).first()

    if not shelter_check:
        raise HTTPException(
            status_code=404,
            detail="Shelter not found"
        )

    query = text("""
        DELETE FROM shelters
        WHERE shelter_id = :shelter_id
    """)

    db.execute(
        query,
        {"shelter_id": shelter_id}
    )

    db.commit()

    return {
        "message": "Shelter deleted successfully",
        "shelter_id": shelter_id
    }