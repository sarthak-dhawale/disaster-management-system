from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/shelter-registrations",
    tags=["Shelter Registrations"]
)


class RegistrationCreate(BaseModel):
    shelter_id: int
    user_id: int
    check_in: Optional[datetime] = None
    status: str = "ACTIVE"


class RegistrationUpdate(BaseModel):
    shelter_id: int
    user_id: int
    check_in: datetime
    check_out: Optional[datetime] = None
    status: str


VALID_STATUSES = [
    "ACTIVE",
    "CHECKED_OUT"
]


def validate_status(status: str):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status must be ACTIVE or CHECKED_OUT"
        )


def check_references(registration, db):
    shelter = db.execute(
        text("""
            SELECT
                shelter_id,
                capacity,
                current_occupancy,
                status
            FROM shelters
            WHERE shelter_id = :shelter_id
        """),
        {"shelter_id": registration.shelter_id}
    ).mappings().first()

    if not shelter:
        raise HTTPException(
            status_code=404,
            detail="Shelter not found"
        )

    user = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": registration.user_id}
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return shelter


@router.get("/")
def get_all_registrations(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            sr.registration_id,
            sr.shelter_id,
            s.name AS shelter_name,
            sr.user_id,
            u.full_name AS user_name,
            u.phone,
            sr.check_in,
            sr.check_out,
            sr.status
        FROM shelter_registrations sr
        JOIN shelters s
            ON sr.shelter_id = s.shelter_id
        JOIN users u
            ON sr.user_id = u.user_id
        ORDER BY sr.registration_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "shelter_registrations": [dict(row) for row in result]
    }


@router.get("/{registration_id}")
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            sr.registration_id,
            sr.shelter_id,
            s.name AS shelter_name,
            sr.user_id,
            u.full_name AS user_name,
            u.phone,
            sr.check_in,
            sr.check_out,
            sr.status
        FROM shelter_registrations sr
        JOIN shelters s
            ON sr.shelter_id = s.shelter_id
        JOIN users u
            ON sr.user_id = u.user_id
        WHERE sr.registration_id = :registration_id
    """)

    result = db.execute(
        query,
        {"registration_id": registration_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Shelter registration not found"
        )

    return dict(result)


@router.post("/")
def create_registration(
    registration: RegistrationCreate,
    db: Session = Depends(get_db)
):
    validate_status(registration.status)

    shelter = check_references(registration, db)

    if shelter["status"] == "CLOSED":
        raise HTTPException(
            status_code=400,
            detail="Cannot register a person in a closed shelter"
        )

    if registration.status == "ACTIVE":
        if shelter["current_occupancy"] >= shelter["capacity"]:
            raise HTTPException(
                status_code=400,
                detail="Shelter is full"
            )

    existing_registration = db.execute(
        text("""
            SELECT registration_id
            FROM shelter_registrations
            WHERE shelter_id = :shelter_id
            AND user_id = :user_id
            AND status = 'ACTIVE'
        """),
        {
            "shelter_id": registration.shelter_id,
            "user_id": registration.user_id
        }
    ).first()

    if existing_registration:
        raise HTTPException(
            status_code=400,
            detail="User is already registered in this shelter"
        )

    if registration.check_in is None:
        insert_query = text("""
            INSERT INTO shelter_registrations (
                shelter_id,
                user_id,
                status
            )
            VALUES (
                :shelter_id,
                :user_id,
                :status
            )
        """)

        result = db.execute(
            insert_query,
            {
                "shelter_id": registration.shelter_id,
                "user_id": registration.user_id,
                "status": registration.status
            }
        )
    else:
        insert_query = text("""
            INSERT INTO shelter_registrations (
                shelter_id,
                user_id,
                check_in,
                status
            )
            VALUES (
                :shelter_id,
                :user_id,
                :check_in,
                :status
            )
        """)

        result = db.execute(
            insert_query,
            {
                "shelter_id": registration.shelter_id,
                "user_id": registration.user_id,
                "check_in": registration.check_in,
                "status": registration.status
            }
        )

    if registration.status == "ACTIVE":
        db.execute(
            text("""
                UPDATE shelters
                SET current_occupancy = current_occupancy + 1
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": registration.shelter_id}
        )

    db.commit()

    db.execute(
        text("""
            UPDATE shelters
            SET status =
                CASE
                    WHEN current_occupancy >= capacity THEN 'FULL'
                    ELSE 'AVAILABLE'
                END
            WHERE shelter_id = :shelter_id
        """),
        {"shelter_id": registration.shelter_id}
    )

    db.commit()

    return {
        "message": "Shelter registration created successfully",
        "registration_id": result.lastrowid
    }


@router.put("/{registration_id}")
def update_registration(
    registration_id: int,
    registration: RegistrationUpdate,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        text("""
            SELECT
                registration_id,
                shelter_id,
                user_id,
                check_in,
                check_out,
                status
            FROM shelter_registrations
            WHERE registration_id = :registration_id
        """),
        {"registration_id": registration_id}
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Shelter registration not found"
        )

    validate_status(registration.status)

    shelter = check_references(registration, db)

    if registration.check_out is not None:
        if registration.check_out <= registration.check_in:
            raise HTTPException(
                status_code=400,
                detail="Check-out must be after check-in"
            )

    old_active = existing["status"] == "ACTIVE"
    new_active = registration.status == "ACTIVE"

    if new_active:
        if shelter["status"] == "CLOSED":
            raise HTTPException(
                status_code=400,
                detail="Cannot register a person in a closed shelter"
            )

        if not old_active or existing["shelter_id"] != registration.shelter_id:
            if shelter["current_occupancy"] >= shelter["capacity"]:
                raise HTTPException(
                    status_code=400,
                    detail="Shelter is full"
                )

    query = text("""
        UPDATE shelter_registrations
        SET
            shelter_id = :shelter_id,
            user_id = :user_id,
            check_in = :check_in,
            check_out = :check_out,
            status = :status
        WHERE registration_id = :registration_id
    """)

    db.execute(
        query,
        {
            "registration_id": registration_id,
            "shelter_id": registration.shelter_id,
            "user_id": registration.user_id,
            "check_in": registration.check_in,
            "check_out": registration.check_out,
            "status": registration.status
        }
    )

    if old_active:
        db.execute(
            text("""
                UPDATE shelters
                SET current_occupancy = GREATEST(current_occupancy - 1, 0)
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": existing["shelter_id"]}
        )

    if new_active:
        db.execute(
            text("""
                UPDATE shelters
                SET current_occupancy = current_occupancy + 1
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": registration.shelter_id}
        )

    db.execute(
        text("""
            UPDATE shelters
            SET status =
                CASE
                    WHEN current_occupancy >= capacity THEN 'FULL'
                    ELSE 'AVAILABLE'
                END
            WHERE shelter_id IN (:old_shelter_id, :new_shelter_id)
        """),
        {
            "old_shelter_id": existing["shelter_id"],
            "new_shelter_id": registration.shelter_id
        }
    )

    db.commit()

    return {
        "message": "Shelter registration updated successfully",
        "registration_id": registration_id
    }


@router.delete("/{registration_id}")
def delete_registration(
    registration_id: int,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        text("""
            SELECT
                registration_id,
                shelter_id,
                status
            FROM shelter_registrations
            WHERE registration_id = :registration_id
        """),
        {"registration_id": registration_id}
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Shelter registration not found"
        )

    db.execute(
        text("""
            DELETE FROM shelter_registrations
            WHERE registration_id = :registration_id
        """),
        {"registration_id": registration_id}
    )

    if existing["status"] == "ACTIVE":
        db.execute(
            text("""
                UPDATE shelters
                SET current_occupancy = GREATEST(current_occupancy - 1, 0)
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": existing["shelter_id"]}
        )

        db.execute(
            text("""
                UPDATE shelters
                SET status =
                    CASE
                        WHEN current_occupancy >= capacity THEN 'FULL'
                        ELSE 'AVAILABLE'
                    END
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": existing["shelter_id"]}
        )

    db.commit()

    return {
        "message": "Shelter registration deleted successfully",
        "registration_id": registration_id
    }