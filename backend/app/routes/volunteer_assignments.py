from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/volunteer-assignments",
    tags=["Volunteer Assignments"]
)


class AssignmentCreate(BaseModel):
    volunteer_id: int
    disaster_id: Optional[int] = None
    shelter_id: Optional[int] = None
    assigned_by: Optional[int] = None
    assignment_role: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "ASSIGNED"


class AssignmentUpdate(BaseModel):
    volunteer_id: int
    disaster_id: Optional[int] = None
    shelter_id: Optional[int] = None
    assigned_by: Optional[int] = None
    assignment_role: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str


VALID_STATUSES = [
    "ASSIGNED",
    "ACTIVE",
    "COMPLETED",
    "CANCELLED"
]


def validate_target(assignment):
    if assignment.disaster_id is None and assignment.shelter_id is None:
        raise HTTPException(
            status_code=400,
            detail="Either disaster_id or shelter_id must be provided"
        )

    if assignment.disaster_id is not None and assignment.shelter_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either disaster_id or shelter_id, not both"
        )


def validate_status(status):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status must be ASSIGNED, ACTIVE, COMPLETED, or CANCELLED"
        )


def check_references(assignment, db):
    volunteer_check = db.execute(
        text("""
            SELECT volunteer_id
            FROM volunteers
            WHERE volunteer_id = :volunteer_id
        """),
        {"volunteer_id": assignment.volunteer_id}
    ).first()

    if not volunteer_check:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )

    if assignment.disaster_id is not None:
        disaster_check = db.execute(
            text("""
                SELECT disaster_id
                FROM disasters
                WHERE disaster_id = :disaster_id
            """),
            {"disaster_id": assignment.disaster_id}
        ).first()

        if not disaster_check:
            raise HTTPException(
                status_code=404,
                detail="Disaster not found"
            )

    if assignment.shelter_id is not None:
        shelter_check = db.execute(
            text("""
                SELECT shelter_id
                FROM shelters
                WHERE shelter_id = :shelter_id
            """),
            {"shelter_id": assignment.shelter_id}
        ).first()

        if not shelter_check:
            raise HTTPException(
                status_code=404,
                detail="Shelter not found"
            )

    if assignment.assigned_by is not None:
        user_check = db.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": assignment.assigned_by}
        ).first()

        if not user_check:
            raise HTTPException(
                status_code=404,
                detail="Assigning user not found"
            )


@router.get("/")
def get_all_assignments(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            va.assignment_id,
            va.volunteer_id,
            u.full_name AS volunteer_name,
            va.disaster_id,
            d.title AS disaster_title,
            va.shelter_id,
            s.name AS shelter_name,
            va.assigned_by,
            a.full_name AS assigned_by_name,
            va.assignment_role,
            va.start_time,
            va.end_time,
            va.status
        FROM volunteer_assignments va
        JOIN volunteers v
            ON va.volunteer_id = v.volunteer_id
        JOIN users u
            ON v.user_id = u.user_id
        LEFT JOIN disasters d
            ON va.disaster_id = d.disaster_id
        LEFT JOIN shelters s
            ON va.shelter_id = s.shelter_id
        LEFT JOIN users a
            ON va.assigned_by = a.user_id
        ORDER BY va.assignment_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "volunteer_assignments": [dict(row) for row in result]
    }


@router.get("/{assignment_id}")
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            va.assignment_id,
            va.volunteer_id,
            u.full_name AS volunteer_name,
            va.disaster_id,
            d.title AS disaster_title,
            va.shelter_id,
            s.name AS shelter_name,
            va.assigned_by,
            a.full_name AS assigned_by_name,
            va.assignment_role,
            va.start_time,
            va.end_time,
            va.status
        FROM volunteer_assignments va
        JOIN volunteers v
            ON va.volunteer_id = v.volunteer_id
        JOIN users u
            ON v.user_id = u.user_id
        LEFT JOIN disasters d
            ON va.disaster_id = d.disaster_id
        LEFT JOIN shelters s
            ON va.shelter_id = s.shelter_id
        LEFT JOIN users a
            ON va.assigned_by = a.user_id
        WHERE va.assignment_id = :assignment_id
    """)

    result = db.execute(
        query,
        {"assignment_id": assignment_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Volunteer assignment not found"
        )

    return dict(result)


@router.post("/")
def create_assignment(
    assignment: AssignmentCreate,
    db: Session = Depends(get_db)
):
    validate_target(assignment)
    validate_status(assignment.status)
    check_references(assignment, db)

    if assignment.end_time is not None:
        if assignment.end_time <= assignment.start_time:
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time"
            )

    query = text("""
        INSERT INTO volunteer_assignments (
            volunteer_id,
            disaster_id,
            shelter_id,
            assigned_by,
            assignment_role,
            start_time,
            end_time,
            status
        )
        VALUES (
            :volunteer_id,
            :disaster_id,
            :shelter_id,
            :assigned_by,
            :assignment_role,
            :start_time,
            :end_time,
            :status
        )
    """)

    result = db.execute(
        query,
        {
            "volunteer_id": assignment.volunteer_id,
            "disaster_id": assignment.disaster_id,
            "shelter_id": assignment.shelter_id,
            "assigned_by": assignment.assigned_by,
            "assignment_role": assignment.assignment_role,
            "start_time": assignment.start_time,
            "end_time": assignment.end_time,
            "status": assignment.status
        }
    )

    db.commit()

    if assignment.status in ["ASSIGNED", "ACTIVE"]:
        db.execute(
            text("""
                UPDATE volunteers
                SET availability_status = 'ASSIGNED'
                WHERE volunteer_id = :volunteer_id
            """),
            {"volunteer_id": assignment.volunteer_id}
        )
        db.commit()

    return {
        "message": "Volunteer assignment created successfully",
        "assignment_id": result.lastrowid
    }


@router.put("/{assignment_id}")
def update_assignment(
    assignment_id: int,
    assignment: AssignmentUpdate,
    db: Session = Depends(get_db)
):
    assignment_check = db.execute(
        text("""
            SELECT assignment_id
            FROM volunteer_assignments
            WHERE assignment_id = :assignment_id
        """),
        {"assignment_id": assignment_id}
    ).first()

    if not assignment_check:
        raise HTTPException(
            status_code=404,
            detail="Volunteer assignment not found"
        )

    validate_target(assignment)
    validate_status(assignment.status)
    check_references(assignment, db)

    if assignment.end_time is not None:
        if assignment.end_time <= assignment.start_time:
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time"
            )

    query = text("""
        UPDATE volunteer_assignments
        SET
            volunteer_id = :volunteer_id,
            disaster_id = :disaster_id,
            shelter_id = :shelter_id,
            assigned_by = :assigned_by,
            assignment_role = :assignment_role,
            start_time = :start_time,
            end_time = :end_time,
            status = :status
        WHERE assignment_id = :assignment_id
    """)

    db.execute(
        query,
        {
            "assignment_id": assignment_id,
            "volunteer_id": assignment.volunteer_id,
            "disaster_id": assignment.disaster_id,
            "shelter_id": assignment.shelter_id,
            "assigned_by": assignment.assigned_by,
            "assignment_role": assignment.assignment_role,
            "start_time": assignment.start_time,
            "end_time": assignment.end_time,
            "status": assignment.status
        }
    )

    db.commit()

    if assignment.status in ["ASSIGNED", "ACTIVE"]:
        db.execute(
            text("""
                UPDATE volunteers
                SET availability_status = 'ASSIGNED'
                WHERE volunteer_id = :volunteer_id
            """),
            {"volunteer_id": assignment.volunteer_id}
        )
    else:
        db.execute(
            text("""
                UPDATE volunteers
                SET availability_status = 'AVAILABLE'
                WHERE volunteer_id = :volunteer_id
            """),
            {"volunteer_id": assignment.volunteer_id}
        )

    db.commit()

    return {
        "message": "Volunteer assignment updated successfully",
        "assignment_id": assignment_id
    }


@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db)
):
    existing = db.execute(
        text("""
            SELECT
                assignment_id,
                volunteer_id,
                status
            FROM volunteer_assignments
            WHERE assignment_id = :assignment_id
        """),
        {"assignment_id": assignment_id}
    ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Volunteer assignment not found"
        )

    db.execute(
        text("""
            DELETE FROM volunteer_assignments
            WHERE assignment_id = :assignment_id
        """),
        {"assignment_id": assignment_id}
    )

    db.commit()

    db.execute(
        text("""
            UPDATE volunteers
            SET availability_status = 'AVAILABLE'
            WHERE volunteer_id = :volunteer_id
            AND NOT EXISTS (
                SELECT 1
                FROM volunteer_assignments
                WHERE volunteer_id = :volunteer_id
                AND status IN ('ASSIGNED', 'ACTIVE')
            )
        """),
        {"volunteer_id": existing["volunteer_id"]}
    )

    db.commit()

    return {
        "message": "Volunteer assignment deleted successfully",
        "assignment_id": assignment_id
    }