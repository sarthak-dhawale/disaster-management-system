"""Deterministic geographic helpers; no guessed coordinates or predictions."""

import math
from datetime import datetime, timezone, timedelta
from app.config import DB_TIME_ZONE


def valid_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
        return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


def india_extent(latitude, longitude):
    return (
        valid_coordinates(latitude, longitude)
        and 6 <= float(latitude) <= 38
        and 68 <= float(longitude) <= 98
    )


def distance_km(lat1, lon1, lat2, lon2):
    if not valid_coordinates(lat1, lon1) or not valid_coordinates(lat2, lon2):
        raise ValueError("Valid coordinates required")
    a, b, c, d = map(math.radians, map(float, [lat1, lon1, lat2, lon2]))
    h = math.sin((c - a) / 2) ** 2 + math.cos(a) * math.cos(c) * math.sin((d - b) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def business_now():
    sign = 1 if DB_TIME_ZONE[0] == "+" else -1
    offset = sign * (int(DB_TIME_ZONE[1:3]) * 60 + int(DB_TIME_ZONE[4:6]))
    return datetime.now(timezone(timedelta(minutes=offset))).replace(tzinfo=None)


def priority(row, now=None):
    severity = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}.get(row.get("severity"), 0)
    state = row.get("response_status", row.get("status"))
    review = row.get("review_status")
    inactive = state in {"RESOLVED", "REJECTED"} or review == "REJECTED"
    response = (
        0
        if inactive
        else 20
        if state == "ACTIVE"
        else 15
        if review == "PENDING_REVIEW"
        else 10
        if state in {"CONTAINED", "IN_PROGRESS"}
        else 0
    )
    timestamp = row.get("incident_time") or row.get("reported_at") or row.get("start_time")
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            timestamp = None
    hours = (
        max(0, ((now or business_now()) - timestamp).total_seconds() / 3600)
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None
        else None
    )
    age = 0 if inactive or hours is None else min(15, int(hours))
    calculated = 0 if inactive else severity + response + age
    return {
        "priority_score": row.get("priority_score", calculated),
        "priority_factors": {
            "severity": 0 if inactive else severity,
            "response": response,
            "elapsed_hours_bonus": age,
            "time_known": hours is not None,
        },
        "priority_note": "Human review required; deterministic triage, not disaster prediction",
    }


def priority_sql(key):
    timestamp = "start_time" if key == "disasters" else "reported_at"
    pending = "WHEN review_status='PENDING_REVIEW' THEN 15 " if key == "emergency_reports" else ""
    return f"CASE WHEN status IN ('RESOLVED','REJECTED') THEN 0 ELSE CASE severity WHEN 'CRITICAL' THEN 100 WHEN 'HIGH' THEN 75 WHEN 'MEDIUM' THEN 50 WHEN 'LOW' THEN 25 ELSE 0 END + CASE WHEN status='ACTIVE' THEN 20 {pending}WHEN status IN ('CONTAINED','IN_PROGRESS') THEN 10 ELSE 0 END + COALESCE(LEAST(15,GREATEST(0,TIMESTAMPDIFF(HOUR,{timestamp},NOW()))),0) END"
