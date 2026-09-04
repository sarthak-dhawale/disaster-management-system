from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/emergency-reports",
    tags=["Emergency Reports"]
)


class EmergencyReportCreate(BaseModel):
    disaster_id: Optional[int] = None
    location_id: int
    reported_by: Optional[int] = None
    report_type: str
    description: str
    severity: str
    status: str = "PENDING"


class EmergencyReportUpdate(BaseModel):
    disaster_id: Optional[int] = None
    location_id: int
    reported_by: Optional[int] = None
    report_type: str
    description: str
    severity: str
    status: str
    resolved_at: Optional[str] = None


VALID_REPORT_TYPES = [
    "MEDICAL",
    "TRAPPED_PERSON",
    "MISSING_PERSON",
    "INFRASTRUCTURE_DAMAGE",
    "FIRE",
    "FLOODING",
    "OTHER"
]

VALID_SEVERITIES = [
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL"
]

VALID_STATUSES = [
    "PENDING",
    "IN_PROGRESS",
    "RESOLVED",
    "REJECTED"
]


def validate_report(report):
    if report.report_type not in VALID_REPORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid report type"
        )

    if report.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid severity"
        )

    if report.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid report status"
        )


def check_foreign_keys(report, db):
    location_check = db.execute(
        text("""
            SELECT location_id
            FROM locations
            WHERE location_id = :location_id
        """),
        {"location_id": report.location_id}
    ).first()

    if not location_check:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    if report.disaster_id is not None:
        disaster_check = db.execute(
            text("""
                SELECT disaster_id
                FROM disasters
                WHERE disaster_id = :disaster_id
            """),
            {"disaster_id": report.disaster_id}
        ).first()

        if not disaster_check:
            raise HTTPException(
                status_code=404,
                detail="Disaster not found"
            )

    if report.reported_by is not None:
        user_check = db.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": report.reported_by}
        ).first()

        if not user_check:
            raise HTTPException(
                status_code=404,
                detail="Reporting user not found"
            )


@router.get("/")
def get_all_reports(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            er.report_id,
            er.disaster_id,
            er.location_id,
            l.city,
            l.district,
            l.state,
            er.reported_by,
            u.full_name AS reported_by_name,
            er.report_type,
            er.description,
            er.severity,
            er.status,
            er.reported_at,
            er.resolved_at
        FROM emergency_reports er
        JOIN locations l
            ON er.location_id = l.location_id
        LEFT JOIN users u
            ON er.reported_by = u.user_id
        ORDER BY er.report_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "emergency_reports": [dict(row) for row in result]
    }


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            er.report_id,
            er.disaster_id,
            er.location_id,
            l.city,
            l.district,
            l.state,
            er.reported_by,
            u.full_name AS reported_by_name,
            er.report_type,
            er.description,
            er.severity,
            er.status,
            er.reported_at,
            er.resolved_at
        FROM emergency_reports er
        JOIN locations l
            ON er.location_id = l.location_id
        LEFT JOIN users u
            ON er.reported_by = u.user_id
        WHERE er.report_id = :report_id
    """)

    result = db.execute(
        query,
        {"report_id": report_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Emergency report not found"
        )

    return dict(result)


@router.post("/")
def create_report(
    report: EmergencyReportCreate,
    db: Session = Depends(get_db)
):
    validate_report(report)
    check_foreign_keys(report, db)

    query = text("""
        INSERT INTO emergency_reports (
            disaster_id,
            location_id,
            reported_by,
            report_type,
            description,
            severity,
            status
        )
        VALUES (
            :disaster_id,
            :location_id,
            :reported_by,
            :report_type,
            :description,
            :severity,
            :status
        )
    """)

    result = db.execute(
        query,
        {
            "disaster_id": report.disaster_id,
            "location_id": report.location_id,
            "reported_by": report.reported_by,
            "report_type": report.report_type,
            "description": report.description,
            "severity": report.severity,
            "status": report.status
        }
    )

    db.commit()

    return {
        "message": "Emergency report created successfully",
        "report_id": result.lastrowid
    }


@router.put("/{report_id}")
def update_report(
    report_id: int,
    report: EmergencyReportUpdate,
    db: Session = Depends(get_db)
):
    report_check = db.execute(
        text("""
            SELECT report_id
            FROM emergency_reports
            WHERE report_id = :report_id
        """),
        {"report_id": report_id}
    ).first()

    if not report_check:
        raise HTTPException(
            status_code=404,
            detail="Emergency report not found"
        )

    validate_report(report)
    check_foreign_keys(report, db)

    query = text("""
        UPDATE emergency_reports
        SET
            disaster_id = :disaster_id,
            location_id = :location_id,
            reported_by = :reported_by,
            report_type = :report_type,
            description = :description,
            severity = :severity,
            status = :status,
            resolved_at = :resolved_at
        WHERE report_id = :report_id
    """)

    db.execute(
        query,
        {
            "report_id": report_id,
            "disaster_id": report.disaster_id,
            "location_id": report.location_id,
            "reported_by": report.reported_by,
            "report_type": report.report_type,
            "description": report.description,
            "severity": report.severity,
            "status": report.status,
            "resolved_at": report.resolved_at
        }
    )

    db.commit()

    return {
        "message": "Emergency report updated successfully",
        "report_id": report_id
    }


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    report_check = db.execute(
        text("""
            SELECT report_id
            FROM emergency_reports
            WHERE report_id = :report_id
        """),
        {"report_id": report_id}
    ).first()

    if not report_check:
        raise HTTPException(
            status_code=404,
            detail="Emergency report not found"
        )

    db.execute(
        text("""
            DELETE FROM emergency_reports
            WHERE report_id = :report_id
        """),
        {"report_id": report_id}
    )

    db.commit()

    return {
        "message": "Emergency report deleted successfully",
        "report_id": report_id
    }