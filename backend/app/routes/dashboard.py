from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("/")
def get_dashboard(db: Session = Depends(get_db)):

    disaster_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_disasters,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_disasters,
                SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_disasters,
                SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_disasters
            FROM disasters
        """)
    ).mappings().first()

    shelter_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_shelters,
                SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_shelters,
                SUM(CASE WHEN status = 'FULL' THEN 1 ELSE 0 END) AS full_shelters,
                SUM(capacity) AS total_capacity,
                SUM(current_occupancy) AS total_occupancy
            FROM shelters
        """)
    ).mappings().first()

    volunteer_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_volunteers,
                SUM(CASE WHEN availability_status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_volunteers,
                SUM(CASE WHEN availability_status = 'ASSIGNED' THEN 1 ELSE 0 END) AS assigned_volunteers,
                SUM(CASE WHEN availability_status = 'UNAVAILABLE' THEN 1 ELSE 0 END) AS unavailable_volunteers
            FROM volunteers
        """)
    ).mappings().first()

    resource_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_resources,
                COALESCE(SUM(total_quantity), 0) AS total_quantity,
                COALESCE(SUM(available_quantity), 0) AS available_quantity
            FROM resources
        """)
    ).mappings().first()

    low_stock_resources = db.execute(
        text("""
            SELECT
                resource_id,
                resource_name,
                category,
                unit,
                total_quantity,
                available_quantity,
                minimum_required
            FROM resources
            WHERE available_quantity <= minimum_required
            ORDER BY available_quantity ASC
        """)
    ).mappings().all()

    emergency_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_reports,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending_reports,
                SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress_reports,
                SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_reports,
                SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_reports
            FROM emergency_reports
        """)
    ).mappings().first()

    registration_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_registrations,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_registrations,
                SUM(CASE WHEN status = 'CHECKED_OUT' THEN 1 ELSE 0 END) AS checked_out_registrations
            FROM shelter_registrations
        """)
    ).mappings().first()

    assignment_stats = db.execute(
        text("""
            SELECT
                COUNT(*) AS total_assignments,
                SUM(CASE WHEN status = 'ASSIGNED' THEN 1 ELSE 0 END) AS assigned,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
            FROM volunteer_assignments
        """)
    ).mappings().first()

    return {
        "disasters": {
            "total": disaster_stats["total_disasters"] or 0,
            "active": disaster_stats["active_disasters"] or 0,
            "critical": disaster_stats["critical_disasters"] or 0,
            "resolved": disaster_stats["resolved_disasters"] or 0
        },

        "shelters": {
            "total": shelter_stats["total_shelters"] or 0,
            "available": shelter_stats["available_shelters"] or 0,
            "full": shelter_stats["full_shelters"] or 0,
            "total_capacity": shelter_stats["total_capacity"] or 0,
            "total_occupancy": shelter_stats["total_occupancy"] or 0
        },

        "volunteers": {
            "total": volunteer_stats["total_volunteers"] or 0,
            "available": volunteer_stats["available_volunteers"] or 0,
            "assigned": volunteer_stats["assigned_volunteers"] or 0,
            "unavailable": volunteer_stats["unavailable_volunteers"] or 0
        },

        "resources": {
            "total_types": resource_stats["total_resources"] or 0,
            "total_quantity": resource_stats["total_quantity"] or 0,
            "available_quantity": resource_stats["available_quantity"] or 0,
            "low_stock_count": len(low_stock_resources),
            "low_stock_resources": [
                dict(resource)
                for resource in low_stock_resources
            ]
        },

        "emergency_reports": {
            "total": emergency_stats["total_reports"] or 0,
            "pending": emergency_stats["pending_reports"] or 0,
            "in_progress": emergency_stats["in_progress_reports"] or 0,
            "resolved": emergency_stats["resolved_reports"] or 0,
            "critical": emergency_stats["critical_reports"] or 0
        },

        "shelter_registrations": {
            "total": registration_stats["total_registrations"] or 0,
            "active": registration_stats["active_registrations"] or 0,
            "checked_out": registration_stats["checked_out_registrations"] or 0
        },

        "volunteer_assignments": {
            "total": assignment_stats["total_assignments"] or 0,
            "assigned": assignment_stats["assigned"] or 0,
            "active": assignment_stats["active"] or 0,
            "completed": assignment_stats["completed"] or 0
        }
    }