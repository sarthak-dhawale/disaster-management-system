"""V4 operational summaries and layers, restricted to existing response roles."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from app.database import get_db
from app.security import require_admin
from app.geo import valid_coordinates
from app.routes.dashboard import get_dashboard

router = APIRouter(prefix="/api/operations", tags=["Operational overview"], dependencies=[Depends(require_admin)])


@router.get("/metrics")
def metrics(db=Depends(get_db)):
    stats = get_dashboard(db)
    shortage = db.execute(text("""
        SELECT COUNT(*) FROM resources r JOIN (
          SELECT rr.resource_id,SUM(GREATEST(0,rr.quantity-COALESCE(a.allocated,0))) AS outstanding
          FROM resource_requests rr LEFT JOIN (
            SELECT request_id,SUM(quantity) AS allocated FROM resource_allocations
            WHERE status!='CANCELLED' GROUP BY request_id
          ) a ON a.request_id=rr.request_id WHERE rr.status='OPEN' GROUP BY rr.resource_id
        ) demand ON demand.resource_id=r.resource_id WHERE demand.outstanding>r.available_quantity
    """)).scalar_one()
    spare = db.execute(text("SELECT COALESCE(SUM(capacity-current_occupancy),0) FROM shelters WHERE status='AVAILABLE'")).scalar_one()
    return {
        "active": stats["disasters"]["active"], "critical": stats["disasters"]["critical"],
        "pending": stats["emergency_reports"]["pending"], "shelter_places": spare,
        "shortage_types": shortage,
        "scope": "Countrywide. Active means ACTIVE; critical includes all CRITICAL official records. Spare places exclude FULL/CLOSED shelters. Shortages compare OPEN unmet demand with available stock per resource ID/unit.",
    }


@router.get("/map-layers")
def map_layers(db=Depends(get_db)):
    shelters = [dict(r) for r in db.execute(text("""
        SELECT 'shelter' AS kind,s.shelter_id AS id,s.name AS title,s.status AS response_status,
          s.capacity,s.current_occupancy,l.city,l.state,l.latitude,l.longitude
        FROM shelters s JOIN locations l ON l.location_id=s.location_id ORDER BY s.shelter_id
    """)).mappings()]
    # Inventory has no warehouse/location FK. These are real allocation destinations,
    # never inferred stock centres or evidence that reserved goods have been delivered.
    resources = [dict(r) for r in db.execute(text("""
        SELECT 'resource' AS kind,a.allocation_id AS id,r.resource_name AS title,r.unit,a.quantity,
          a.status AS response_status,a.disaster_id,a.shelter_id,
          l.city,l.state,l.latitude,l.longitude
        FROM resource_allocations a JOIN resources r ON r.resource_id=a.resource_id
        LEFT JOIN disasters d ON d.disaster_id=a.disaster_id
        LEFT JOIN shelters s ON s.shelter_id=a.shelter_id
        JOIN locations l ON l.location_id=COALESCE(d.location_id,s.location_id)
        WHERE a.status!='CANCELLED' ORDER BY a.allocation_id
    """)).mappings()]
    for row in shelters + resources:
        row["plottable"] = valid_coordinates(row["latitude"], row["longitude"])
    return {"shelters": shelters, "resources": resources,
            "resource_note": "Resource markers show allocation destinations, not warehouse stock. The schema does not store inventory locations; reserved allocations are not confirmed delivery."}
