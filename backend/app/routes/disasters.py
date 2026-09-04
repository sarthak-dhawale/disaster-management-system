from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DisasterCreate, DisasterUpdate


router = APIRouter(
    prefix="/api/disasters",
    tags=["Disasters"]
)


@router.get("/")
def get_all_disasters(db: Session = Depends(get_db)):
    query = text("""
        SELECT *
        FROM disasters
        ORDER BY disaster_id DESC
    """)

    result = db.execute(query)

    disasters = [dict(row) for row in result.mappings().all()]

    return {
        "count": len(disasters),
        "disasters": disasters
    }


@router.get("/{disaster_id}")
def get_disaster(
    disaster_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT *
        FROM disasters
        WHERE disaster_id = :disaster_id
    """)

    result = db.execute(
        query,
        {"disaster_id": disaster_id}
    ).mappings().first()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Disaster not found"
        )

    return dict(result)


@router.post("/")
def create_disaster(
    disaster: DisasterCreate,
    db: Session = Depends(get_db)
):
    query = text("""
        INSERT INTO disasters (
            location_id,
            reported_by,
            disaster_type,
            title,
            description,
            severity,
            status,
            start_time,
            end_time
        )
        VALUES (
            :location_id,
            :reported_by,
            :disaster_type,
            :title,
            :description,
            :severity,
            :status,
            :start_time,
            :end_time
        )
    """)

    result = db.execute(
        query,
        disaster.model_dump()
    )

    db.commit()

    return {
        "message": "Disaster created successfully",
        "disaster_id": result.lastrowid
    }


@router.put("/{disaster_id}")
def update_disaster(
    disaster_id: int,
    disaster: DisasterUpdate,
    db: Session = Depends(get_db)
):
    data = disaster.model_dump(exclude_unset=True)

    if not data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    set_parts = []

    for field in data:
        set_parts.append(
            f"{field} = :{field}"
        )

    data["disaster_id"] = disaster_id

    query = text(f"""
        UPDATE disasters
        SET {", ".join(set_parts)}
        WHERE disaster_id = :disaster_id
    """)

    result = db.execute(query, data)

    if result.rowcount == 0:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Disaster not found"
        )

    db.commit()

    return {
        "message": "Disaster updated successfully",
        "disaster_id": disaster_id
    }


@router.delete("/{disaster_id}")
def delete_disaster(
    disaster_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        DELETE FROM disasters
        WHERE disaster_id = :disaster_id
    """)

    result = db.execute(
        query,
        {"disaster_id": disaster_id}
    )

    if result.rowcount == 0:
        db.rollback()

        raise HTTPException(
            status_code=404,
            detail="Disaster not found"
        )

    db.commit()

    return {
        "message": "Disaster deleted successfully",
        "disaster_id": disaster_id
    }