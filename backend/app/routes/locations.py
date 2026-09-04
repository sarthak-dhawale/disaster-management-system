from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/api/locations", tags=["Locations"])


class LocationCreate(BaseModel):
    state: str
    district: str
    city: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LocationUpdate(BaseModel):
    state: str
    district: str
    city: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.get("/")
def get_all_locations(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            location_id,
            state,
            district,
            city,
            address,
            latitude,
            longitude,
            created_at
        FROM locations
        ORDER BY location_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "locations": [dict(row) for row in result]
    }


@router.get("/{location_id}")
def get_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            location_id,
            state,
            district,
            city,
            address,
            latitude,
            longitude,
            created_at
        FROM locations
        WHERE location_id = :location_id
    """)

    result = db.execute(
        query,
        {"location_id": location_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    return dict(result)


@router.post("/")
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db)
):
    if location.latitude is not None:
        if location.latitude < -90 or location.latitude > 90:
            raise HTTPException(
                status_code=400,
                detail="Latitude must be between -90 and 90"
            )

    if location.longitude is not None:
        if location.longitude < -180 or location.longitude > 180:
            raise HTTPException(
                status_code=400,
                detail="Longitude must be between -180 and 180"
            )

    query = text("""
        INSERT INTO locations (
            state,
            district,
            city,
            address,
            latitude,
            longitude
        )
        VALUES (
            :state,
            :district,
            :city,
            :address,
            :latitude,
            :longitude
        )
    """)

    result = db.execute(
        query,
        {
            "state": location.state,
            "district": location.district,
            "city": location.city,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude
        }
    )

    db.commit()

    return {
        "message": "Location created successfully",
        "location_id": result.lastrowid
    }


@router.put("/{location_id}")
def update_location(
    location_id: int,
    location: LocationUpdate,
    db: Session = Depends(get_db)
):
    location_check = db.execute(
        text("""
            SELECT location_id
            FROM locations
            WHERE location_id = :location_id
        """),
        {"location_id": location_id}
    ).first()

    if not location_check:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    if location.latitude is not None:
        if location.latitude < -90 or location.latitude > 90:
            raise HTTPException(
                status_code=400,
                detail="Latitude must be between -90 and 90"
            )

    if location.longitude is not None:
        if location.longitude < -180 or location.longitude > 180:
            raise HTTPException(
                status_code=400,
                detail="Longitude must be between -180 and 180"
            )

    query = text("""
        UPDATE locations
        SET
            state = :state,
            district = :district,
            city = :city,
            address = :address,
            latitude = :latitude,
            longitude = :longitude
        WHERE location_id = :location_id
    """)

    db.execute(
        query,
        {
            "location_id": location_id,
            "state": location.state,
            "district": location.district,
            "city": location.city,
            "address": location.address,
            "latitude": location.latitude,
            "longitude": location.longitude
        }
    )

    db.commit()

    return {
        "message": "Location updated successfully",
        "location_id": location_id
    }


@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    location_check = db.execute(
        text("""
            SELECT location_id
            FROM locations
            WHERE location_id = :location_id
        """),
        {"location_id": location_id}
    ).first()

    if not location_check:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    query = text("""
        DELETE FROM locations
        WHERE location_id = :location_id
    """)

    try:
        db.execute(
            query,
            {"location_id": location_id}
        )
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Location cannot be deleted because it is being used by another record"
        )

    return {
        "message": "Location deleted successfully",
        "location_id": location_id
    }