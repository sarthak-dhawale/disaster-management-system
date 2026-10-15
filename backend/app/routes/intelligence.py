"""Database-backed India map, triage, shelter matching and recorded timelines."""

import json, os
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from app.database import get_db
from app.security import current_user, require_admin, ADMIN_ROLES
from app.crud import record
from app.routes.emergency_reports import owned_record
from app.geo import priority, india_extent, valid_coordinates, distance_km, priority_sql
from app.geocoding import geocode

router = APIRouter(prefix="/api/intelligence", tags=["Geography and response intelligence"])
INCIDENT_SQL = """
SELECT 'disaster' AS kind,d.disaster_id AS id,d.title,d.disaster_type,d.severity, d.status AS response_status,
       'OFFICIAL_RECORD' AS review_status,d.description,d.start_time AS incident_time,
       COALESCE(h.last_update, d.created_at) AS recorded_at,l.state,l.district,l.city,l.address,l.latitude,l.longitude, l.coordinate_source,
       d.location_id,NULL AS owner_id
FROM disasters d
JOIN locations l ON l.location_id=d.location_id
LEFT JOIN
  (SELECT record_id,MAX(created_at) AS last_update
   FROM audit_history
   WHERE entity='disasters'
   GROUP BY record_id) h ON h.record_id=d.disaster_id
UNION ALL
SELECT 'report',er.report_id,CONCAT('Emergency report #', er.report_id),er.disaster_type,
       er.severity, er.status,er.review_status,er.description,er.reported_at,
       COALESCE(rh.last_update, er.reviewed_at, er.reported_at), l.state,l.district,l.city,
       COALESCE(l.address, er.reported_location_text), COALESCE(l.latitude,
                                                         er.reported_latitude),
       COALESCE(l.longitude, er.reported_longitude), COALESCE(l.coordinate_source,
                                                       er.coordinate_source),er.location_id,er.reported_by
FROM emergency_reports er
LEFT JOIN locations l ON l.location_id=er.location_id
LEFT JOIN
  (SELECT record_id,MAX(created_at) AS last_update
   FROM audit_history
   WHERE entity='emergency_reports'
   GROUP BY record_id) rh ON rh.record_id=er.report_id
"""


@router.get("/incidents")
def incidents(
    db=Depends(get_db),
    user=Depends(current_user),
    q: str = Query("", max_length=150),
    disaster_type: str = Query("", max_length=30),
    severity: str = Query("", max_length=30),
    status: str = Query("", max_length=30),
    state: str = Query("", max_length=100),
    start: date | None = None,
    end: date | None = None,
    include_resolved: bool = False,
    include_rejected: bool = False,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    stable_order: bool = False,
):
    if start and end and start > end:
        raise HTTPException(422, "Start date must not follow end date")
    if end == date.max:
        raise HTTPException(422, "End date is outside supported range")
    clauses = []
    params = {"limit": limit, "offset": offset}
    if user["role"] not in ADMIN_ROLES:
        clauses.append("kind='report' AND owner_id=:owner")
        params["owner"] = user["user_id"]
    else:
        clauses.append("(kind='disaster' OR review_status IN ('PENDING_REVIEW','REJECTED'))")
    if not include_resolved and status != "RESOLVED":
        clauses.append("response_status!='RESOLVED'")
    if not include_rejected and status != "REJECTED":
        clauses.append("review_status!='REJECTED'")
    for field, value in [
        ("disaster_type", disaster_type),
        ("severity", severity),
        ("state", state),
    ]:
        if value:
            clauses.append(field + "=:" + field)
            params[field] = value
    if status:
        clauses.append("(response_status=:status OR review_status=:status)")
        params["status"] = status
    if q:
        clauses.append("CONCAT_WS(' ',id,title,disaster_type,description,city,address,state) LIKE :q")
        params["q"] = "%" + q + "%"
    if start:
        clauses.append("incident_time>=:start")
        params["start"] = start
    if end:
        clauses.append("incident_time<:until")
        params["until"] = end + timedelta(days=1)
    where = " AND ".join(clauses) or "1=1"
    base = f"FROM ({INCIDENT_SQL}) incidents WHERE {where}"
    total = db.execute(text("SELECT COUNT(*) " + base), params).scalar_one()
    score = "CASE WHEN response_status IN ('RESOLVED','REJECTED') THEN 0 ELSE CASE severity WHEN 'CRITICAL' THEN 100 WHEN 'HIGH' THEN 75 WHEN 'MEDIUM' THEN 50 WHEN 'LOW' THEN 25 ELSE 0 END + CASE WHEN response_status='ACTIVE' THEN 20 WHEN review_status='PENDING_REVIEW' THEN 15 WHEN response_status IN ('CONTAINED','IN_PROGRESS') THEN 10 ELSE 0 END + COALESCE(LEAST(15,GREATEST(0,TIMESTAMPDIFF(HOUR,incident_time,NOW()))),0) END"
    order = "kind,id" if stable_order else "priority_score DESC,incident_time DESC,kind,id DESC"
    rows = (
        db.execute(
            text(
                f"SELECT *,{score} AS priority_score {base} ORDER BY {order} LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        .mappings()
        .all()
    )
    items = []
    for raw in rows:
        row = dict(raw)
        row.pop("owner_id", None)
        row.update(priority(row))
        row["plottable"] = valid_coordinates(row.get("latitude"), row.get("longitude"))
        row["coordinate_note"] = (
            None
            if row["plottable"]
            else "Coordinates missing, invalid or outside the India map extent"
        )
        items.append(row)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


def incident_record(kind, id, db, user):
    if kind not in {"disaster", "report"}:
        raise HTTPException(404, "Incident type not found")
    if kind == "disaster":
        if user["role"] not in ADMIN_ROLES:
            raise HTTPException(403, "Administrator access required")
        return record(db, "disasters", id)
    return owned_record(db, id, user)


def incident_coordinates(kind, id, db, user):
    row = incident_record(kind, id, db, user)
    location = record(db, "locations", row["location_id"]) if row.get("location_id") else {}
    return (
        row,
        location,
        location.get("latitude", row.get("reported_latitude")),
        location.get("longitude", row.get("reported_longitude")),
    )


@router.get("/{kind}/{id}/shelters")
def nearby(
    kind: str,
    id: int,
    db=Depends(get_db),
    user=Depends(require_admin),
    limit: int = Query(5, ge=1, le=20),
):
    row, location, lat, lon = incident_coordinates(kind, id, db, user)
    if not valid_coordinates(lat, lon):
        return {
            "items": [],
            "reason": "Incident coordinates are missing or invalid; reliable distance unavailable",
        }
    candidates = (
        db.execute(
            text("""
SELECT s.shelter_id,s.name,s.capacity,s.current_occupancy,s.status,
       s.capacity-s.current_occupancy AS available_capacity,l.city,l.address,l.latitude,l.longitude
FROM shelters s
JOIN locations l ON l.location_id=s.location_id
WHERE s.status='AVAILABLE'
  AND s.current_occupancy<s.capacity
""")
        )
        .mappings()
        .all()
    )
    items = []
    excluded = 0
    for raw in candidates:
        candidate = dict(raw)
        if (
            candidate["status"] != "AVAILABLE"
            or candidate["capacity"] <= candidate["current_occupancy"]
        ):
            continue
        if not valid_coordinates(candidate.get("latitude"), candidate.get("longitude")):
            excluded += 1
            continue
        candidate["distance_km"] = round(
            distance_km(lat, lon, candidate["latitude"], candidate["longitude"]), 2
        )
        items.append(candidate)
    items.sort(key=lambda r: (r["distance_km"], r["shelter_id"]))
    return {
        "items": items[:limit],
        "excluded_missing_coordinates": excluded,
        "reason": None if items else "No eligible shelters with valid coordinates",
        "distance_method": "Straight-line Haversine distance, not travel distance; capacity can change before registration",
    }


@router.get("/{kind}/{id}/timeline")
def timeline(kind: str, id: int, db=Depends(get_db), user=Depends(current_user)):
    row = incident_record(kind, id, db, user)
    admin = user["role"] in ADMIN_ROLES
    table = "disasters" if kind == "disaster" else "emergency_reports"
    events = []
    created = row.get("created_at") if kind == "disaster" else row.get("reported_at")
    if created:
        events.append(
            {
                "timestamp": created,
                "action": "Official record created" if kind == "disaster" else "Report submitted",
                "actor_name": None,
                "description": f"{kind.title()} #{id} recorded",
                "source": "record timestamp",
            }
        )
    if kind == "report" and row.get("reviewed_at"):
        events.append(
            {
                "timestamp": row["reviewed_at"],
                "action": "Report " + row["review_status"].lower(),
                "actor_name": None,
                "description": row.get("review_reason") or "Administrator decision recorded",
                "source": "record review",
            }
        )
    if row.get("resolved_at") or (row.get("end_time") and row.get("status") == "RESOLVED"):
        events.append(
            {
                "timestamp": row.get("resolved_at") or row["end_time"],
                "action": "Resolution recorded",
                "actor_name": None,
                "description": "Recorded resolution time",
                "source": "record timestamp",
            }
        )
    disaster = id if kind == "disaster" else row.get("disaster_id")
    if admin:
        sql = """
SELECT audit_id,entity,record_id,action,actor_name,created_at,before_data,after_data
FROM audit_history
WHERE (entity=:table
       AND record_id=:id)
"""
        params = {"table": table, "id": id, "disaster": disaster}
        if disaster:
            sql += """ OR (entity='disasters' AND record_id=:disaster)
            OR (entity IN ('resource_allocations','volunteer_assignments','resource_requests','emergency_reports') AND
            (JSON_UNQUOTE(JSON_EXTRACT(after_data,'$.disaster_id'))=CAST(:disaster AS CHAR)
            OR JSON_UNQUOTE(JSON_EXTRACT(before_data,'$.disaster_id'))=CAST(:disaster AS CHAR)))"""
        sql += " ORDER BY created_at,audit_id"
        for raw in db.execute(text(sql), params).mappings().all():
            audit = dict(raw)
            if (
                audit["action"] == "INSERT"
                and audit["entity"] == table
                and audit["record_id"] == id
            ):
                continue
            for key in ["before_data", "after_data"]:
                if isinstance(audit[key], str):
                    audit[key] = json.loads(audit[key])
            events.append(
                {
                    "timestamp": audit["created_at"],
                    "action": audit["entity"].replace("_", " ") + " " + audit["action"].lower(),
                    "actor_name": audit["actor_name"],
                    "description": f"Record #{audit['record_id']}",
                    "source": "audit",
                    "audit_id": audit["audit_id"],
                    "before": audit["before_data"],
                    "after": audit["after_data"],
                }
            )
    events.sort(key=lambda e: str(e["timestamp"]))
    return {
        "items": events,
        "history_note": "Earlier state changes may be unavailable. Only stored timestamps and audit events are shown; public timelines omit administrative audit snapshots.",
    }


@router.get("/{kind}/{id}/report")
def printable(kind: str, id: int, db=Depends(get_db), user=Depends(current_user)):
    row, location, lat, lon = incident_coordinates(kind, id, db, user)
    admin = user["role"] in ADMIN_ROLES
    disaster = id if kind == "disaster" else row.get("disaster_id")
    allocations = []
    assignments = []
    if admin and disaster:
        allocations = [
            dict(r)
            for r in db.execute(
                text("""
SELECT a.allocation_id,a.status,a.quantity,a.allocation_date,r.resource_name,r.unit,
       s.name AS shelter_name
FROM resource_allocations a
JOIN resources r ON r.resource_id=a.resource_id
LEFT JOIN shelters s ON s.shelter_id=a.shelter_id
WHERE a.disaster_id=:id
ORDER BY a.allocation_id
"""),
                {"id": disaster},
            )
            .mappings()
            .all()
        ]
        assignments = [
            dict(r)
            for r in db.execute(
                text("""
SELECT a.assignment_id,a.assignment_role,a.status,a.start_time,a.end_time,u.full_name AS volunteer_name
FROM volunteer_assignments a
JOIN volunteers v ON v.volunteer_id=a.volunteer_id
JOIN users u ON u.user_id=v.user_id
WHERE a.disaster_id=:id
ORDER BY a.assignment_id
"""),
                {"id": disaster},
            )
            .mappings()
            .all()
        ]
    public_fields = [
        "report_id",
        "disaster_id",
        "location_id",
        "disaster_type",
        "report_type",
        "description",
        "severity",
        "status",
        "review_status",
        "review_reason",
        "reported_at",
        "occurred_at",
        "reviewed_at",
        "resolved_at",
        "reported_location_text",
    ]
    if not admin:
        row = {k: v for k, v in row.items() if k in public_fields}
    return {
        "application": "Disaster Management System",
        "version": "2.0",
        "generated_at": datetime.now().isoformat(),
        "kind": kind,
        "incident": row,
        "location": location or {"address": row.get("reported_location_text")},
        "latitude": lat,
        "longitude": lon,
        "timeline": timeline(kind, id, db, user),
        "allocations": allocations,
        "assignments": assignments,
        "shelters": nearby(kind, id, db, user, 5)
        if admin
        else {"items": [], "reason": "Administrative response information restricted"},
        "restricted_response_data": not admin,
    }


@router.get("/overview/summary", dependencies=[Depends(require_admin)])
def overview(db=Depends(get_db)):
    queries = {
        "types": "SELECT disaster_type AS label,COUNT(*) AS count FROM disasters GROUP BY disaster_type ORDER BY count DESC",
        "severity": "SELECT severity AS label,COUNT(*) AS count FROM disasters GROUP BY severity ORDER BY count DESC",
        "states": """
SELECT l.state AS label,COUNT(*) AS COUNT
FROM disasters d
JOIN locations l ON l.location_id=d.location_id
WHERE d.status='ACTIVE'
GROUP BY l.state
ORDER BY COUNT DESC
""",
        "trend": "SELECT DATE_FORMAT(start_time,'%Y-%m') AS label,COUNT(*) AS count FROM disasters GROUP BY DATE_FORMAT(start_time,'%Y-%m') ORDER BY label DESC LIMIT 12",
        "requests": """
SELECT rr.request_id,r.resource_name,r.unit,rr.quantity AS requested_quantity,
       COALESCE(a.allocated, 0) AS allocated_quantity,
       rr.quantity-COALESCE(a.allocated, 0) AS outstanding_quantity,r.available_quantity
FROM resource_requests rr
JOIN resources r ON r.resource_id=rr.resource_id
LEFT JOIN
  (SELECT request_id,SUM(quantity) AS allocated
   FROM resource_allocations
   WHERE status!='CANCELLED'
   GROUP BY request_id) a ON a.request_id=rr.request_id
WHERE rr.status='OPEN'
  AND rr.quantity>COALESCE(a.allocated, 0)
ORDER BY rr.created_at
LIMIT 10
""",
        "shelter_warnings": """
SELECT name,status,capacity,current_occupancy
FROM shelters
WHERE status IN ('FULL','CLOSED')
  OR current_occupancy>=capacity*0.9
ORDER BY current_occupancy DESC
LIMIT 10
""",
        "shortages": """
SELECT resource_id,resource_name,unit,available_quantity,minimum_required,
       GREATEST(0, minimum_required-available_quantity) AS shortage
FROM resources
WHERE available_quantity<=minimum_required
ORDER BY shortage DESC
LIMIT 10
""",
        "recent_confirmed": "SELECT report_id,disaster_id,severity,reviewed_at FROM emergency_reports WHERE review_status='CONFIRMED' ORDER BY reviewed_at DESC LIMIT 5",
    }
    return {
        key: [dict(row) for row in db.execute(text(sql)).mappings().all()]
        for key, sql in queries.items()
    }


@router.get("/places/search")
def places(q: str = Query(min_length=3, max_length=150), user=Depends(current_user)):
    return geocode(q)


@router.get("/map-config")
def map_config(user=Depends(current_user)):
    return {"tile_url": os.getenv("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")}
