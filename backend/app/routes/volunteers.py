from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])


class VolunteerCreate(BaseModel):
    user_id: int
    skills: Optional[str] = None
    availability_status: str = "AVAILABLE"
    emergency_contact: Optional[str] = None


class VolunteerUpdate(BaseModel):
    user_id: int
    skills: Optional[str] = None
    availability_status: str
    emergency_contact: Optional[str] = None


@router.get("/")
def get_all_volunteers(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            v.volunteer_id,
            v.user_id,
            u.full_name,
            u.email,
            u.phone,
            v.skills,
            v.availability_status,
            v.emergency_contact,
            v.joined_at
        FROM volunteers v
        JOIN users u ON v.user_id = u.user_id
        ORDER BY v.volunteer_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "volunteers": [dict(row) for row in result]
    }


@router.get("/{volunteer_id}")
def get_volunteer(
    volunteer_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            v.volunteer_id,
            v.user_id,
            u.full_name,
            u.email,
            u.phone,
            v.skills,
            v.availability_status,
            v.emergency_contact,
            v.joined_at
        FROM volunteers v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.volunteer_id = :volunteer_id
    """)

    result = db.execute(
        query,
        {"volunteer_id": volunteer_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )

    return dict(result)


@router.post("/")
def create_volunteer(
    volunteer: VolunteerCreate,
    db: Session = Depends(get_db)
):
    valid_statuses = [
        "AVAILABLE",
        "ASSIGNED",
        "UNAVAILABLE"
    ]

    if volunteer.availability_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Availability status must be AVAILABLE, ASSIGNED, or UNAVAILABLE"
        )

    user_check = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": volunteer.user_id}
    ).first()

    if not user_check:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    existing_volunteer = db.execute(
        text("""
            SELECT volunteer_id
            FROM volunteers
            WHERE user_id = :user_id
        """),
        {"user_id": volunteer.user_id}
    ).first()

    if existing_volunteer:
        raise HTTPException(
            status_code=400,
            detail="This user is already registered as a volunteer"
        )

    query = text("""
        INSERT INTO volunteers (
            user_id,
            skills,
            availability_status,
            emergency_contact
        )
        VALUES (
            :user_id,
            :skills,
            :availability_status,
            :emergency_contact
        )
    """)

    result = db.execute(
        query,
        {
            "user_id": volunteer.user_id,
            "skills": volunteer.skills,
            "availability_status": volunteer.availability_status,
            "emergency_contact": volunteer.emergency_contact
        }
    )

    db.commit()

    return {
        "message": "Volunteer created successfully",
        "volunteer_id": result.lastrowid
    }


@router.put("/{volunteer_id}")
def update_volunteer(
    volunteer_id: int,
    volunteer: VolunteerUpdate,
    db: Session = Depends(get_db)
):
    volunteer_check = db.execute(
        text("""
            SELECT volunteer_id
            FROM volunteers
            WHERE volunteer_id = :volunteer_id
        """),
        {"volunteer_id": volunteer_id}
    ).first()

    if not volunteer_check:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )

    valid_statuses = [
        "AVAILABLE",
        "ASSIGNED",
        "UNAVAILABLE"
    ]

    if volunteer.availability_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Availability status must be AVAILABLE, ASSIGNED, or UNAVAILABLE"
        )

    user_check = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": volunteer.user_id}
    ).first()

    if not user_check:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    duplicate_user = db.execute(
        text("""
            SELECT volunteer_id
            FROM volunteers
            WHERE user_id = :user_id
            AND volunteer_id != :volunteer_id
        """),
        {
            "user_id": volunteer.user_id,
            "volunteer_id": volunteer_id
        }
    ).first()

    if duplicate_user:
        raise HTTPException(
            status_code=400,
            detail="This user is already registered as another volunteer"
        )

    query = text("""
        UPDATE volunteers
        SET
            user_id = :user_id,
            skills = :skills,
            availability_status = :availability_status,
            emergency_contact = :emergency_contact
        WHERE volunteer_id = :volunteer_id
    """)

    db.execute(
        query,
        {
            "volunteer_id": volunteer_id,
            "user_id": volunteer.user_id,
            "skills": volunteer.skills,
            "availability_status": volunteer.availability_status,
            "emergency_contact": volunteer.emergency_contact
        }
    )

    db.commit()

    return {
        "message": "Volunteer updated successfully",
        "volunteer_id": volunteer_id
    }


@router.delete("/{volunteer_id}")
def delete_volunteer(
    volunteer_id: int,
    db: Session = Depends(get_db)
):
    volunteer_check = db.execute(
        text("""
            SELECT volunteer_id
            FROM volunteers
            WHERE volunteer_id = :volunteer_id
        """),
        {"volunteer_id": volunteer_id}
    ).first()

    if not volunteer_check:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )

    try:
        db.execute(
            text("""
                DELETE FROM volunteers
                WHERE volunteer_id = :volunteer_id
            """),
            {"volunteer_id": volunteer_id}
        )

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Volunteer cannot be deleted because the volunteer is being used by another record"
        )

    return {
        "message": "Volunteer deleted successfully",
        "volunteer_id": volunteer_id
    }