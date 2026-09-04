from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(
    prefix="/api/search",
    tags=["Search & Filters"]
)


@router.get("/disasters")
def search_disasters(
    disaster_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = """
        SELECT
            d.disaster_id,
            d.disaster_type,
            d.title,
            d.description,
            d.severity,
            d.status,
            d.start_time,
            d.end_time,
            l.state,
            l.district,
            l.city,
            l.address
        FROM disasters d
        JOIN locations l
            ON d.location_id = l.location_id
        WHERE 1 = 1
    """

    params = {}

    if disaster_type:
        query += " AND d.disaster_type = :disaster_type"
        params["disaster_type"] = disaster_type

    if severity:
        query += " AND d.severity = :severity"
        params["severity"] = severity

    if status:
        query += " AND d.status = :status"
        params["status"] = status

    if city:
        query += " AND l.city LIKE :city"
        params["city"] = f"%{city}%"

    query += " ORDER BY d.disaster_id DESC"

    result = db.execute(
        text(query),
        params
    ).mappings().all()

    return {
        "count": len(result),
        "disasters": [dict(row) for row in result]
    }


@router.get("/shelters")
def search_shelters(
    city: Optional[str] = None,
    status: Optional[str] = None,
    available_only: bool = False,
    db: Session = Depends(get_db)
):
    query = """
        SELECT
            s.shelter_id,
            s.name,
            s.capacity,
            s.current_occupancy,
            (s.capacity - s.current_occupancy) AS available_spaces,
            s.contact_phone,
            s.status,
            l.state,
            l.district,
            l.city,
            l.address
        FROM shelters s
        JOIN locations l
            ON s.location_id = l.location_id
        WHERE 1 = 1
    """

    params = {}

    if city:
        query += " AND l.city LIKE :city"
        params["city"] = f"%{city}%"

    if status:
        query += " AND s.status = :status"
        params["status"] = status

    if available_only:
        query += " AND s.current_occupancy < s.capacity"

    query += " ORDER BY available_spaces DESC"

    result = db.execute(
        text(query),
        params
    ).mappings().all()

    return {
        "count": len(result),
        "shelters": [dict(row) for row in result]
    }


@router.get("/resources")
def search_resources(
    category: Optional[str] = None,
    low_stock: bool = False,
    db: Session = Depends(get_db)
):
    query = """
        SELECT
            resource_id,
            resource_name,
            category,
            unit,
            total_quantity,
            available_quantity,
            minimum_required,
            CASE
                WHEN available_quantity <= minimum_required
                THEN 'LOW_STOCK'
                ELSE 'SUFFICIENT'
            END AS stock_status
        FROM resources
        WHERE 1 = 1
    """

    params = {}

    if category:
        query += " AND category = :category"
        params["category"] = category

    if low_stock:
        query += " AND available_quantity <= minimum_required"

    query += " ORDER BY available_quantity ASC"

    result = db.execute(
        text(query),
        params
    ).mappings().all()

    return {
        "count": len(result),
        "resources": [dict(row) for row in result]
    }


@router.get("/emergency-reports")
def search_emergency_reports(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    report_type: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = """
        SELECT
            er.report_id,
            er.disaster_id,
            er.location_id,
            er.report_type,
            er.description,
            er.severity,
            er.status,
            er.reported_at,
            er.resolved_at,
            l.state,
            l.district,
            l.city,
            l.address,
            u.full_name AS reported_by_name
        FROM emergency_reports er
        JOIN locations l
            ON er.location_id = l.location_id
        LEFT JOIN users u
            ON er.reported_by = u.user_id
        WHERE 1 = 1
    """

    params = {}

    if severity:
        query += " AND er.severity = :severity"
        params["severity"] = severity

    if status:
        query += " AND er.status = :status"
        params["status"] = status

    if report_type:
        query += " AND er.report_type = :report_type"
        params["report_type"] = report_type

    if city:
        query += " AND l.city LIKE :city"
        params["city"] = f"%{city}%"

    query += " ORDER BY er.report_id DESC"

    result = db.execute(
        text(query),
        params
    ).mappings().all()

    return {
        "count": len(result),
        "emergency_reports": [dict(row) for row in result]
    }