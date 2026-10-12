"""Single-query streaming CSV exports with explicit field allowlists."""

import csv, io
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from app.database import get_db
from app.security import current_user, ADMIN_ROLES
from app.listing import list_options, selection, IDS
from app.geo import priority_sql
from app.routes import disasters, emergency_reports, resources, resource_allocations, shelters

router = APIRouter(prefix="/api/exports", tags=["CSV reports"])
MODULES = {
    "disasters": disasters,
    "emergency-reports": emergency_reports,
    "resources": resources,
    "resource-allocations": resource_allocations,
    "shelters": shelters,
}
COLUMNS = {
    "shelters": ["shelter_id", "name", "city", "state", "status", "capacity", "current_occupancy", "contact_phone"],
    "disasters": [
        "disaster_id",
        "title",
        "disaster_type",
        "severity",
        "status",
        "location_id",
        "city",
        "district",
        "state",
        "description",
        "start_time",
        "end_time",
    ],
    "emergency-reports": [
        "report_id",
        "disaster_id",
        "disaster_type",
        "report_type",
        "description",
        "severity",
        "status",
        "review_status",
        "review_reason",
        "reported_at",
        "reviewed_at",
        "location_id",
        "city",
        "address",
        "reported_location_text",
        "reported_latitude",
        "reported_longitude",
    ],
    "resources": [
        "resource_id",
        "resource_name",
        "category",
        "unit",
        "total_quantity",
        "available_quantity",
        "minimum_required",
        "updated_at",
    ],
    "resource-allocations": [
        "allocation_id",
        "resource_name",
        "quantity",
        "unit",
        "disaster_id",
        "disaster_title",
        "shelter_id",
        "shelter_name",
        "status",
        "allocation_date",
    ],
}


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    value = str(value)
    # Leading control characters/whitespace must not hide a spreadsheet formula.
    if value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or value.startswith(
        ("\t", "\r", "\n")
    ):
        value = "'" + value
    return value


def csv_rows(rows, columns):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    yield "\ufeff"
    writer.writerow([name.replace("_", " ").title() for name in columns])
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    for row in rows:
        writer.writerow([csv_value(row.get(name)) for name in columns])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


@router.get("/{module}.csv")
def export(
    module: str, db=Depends(get_db), options=Depends(list_options), user=Depends(current_user)
):
    if module not in MODULES:
        raise HTTPException(404, "Export module not found")
    if module != "emergency-reports" and user["role"] not in ADMIN_ROLES:
        raise HTTPException(403, "Administrator access required")
    opts = options.copy()
    key = module.replace("-", "_")
    if module == "emergency-reports" and opts["status"] in {
        "PENDING_REVIEW",
        "CONFIRMED",
        "REJECTED",
        "LEGACY",
    }:
        opts["review_status"] = opts["status"]
        opts["status"] = ""
    owner = (
        user["user_id"]
        if module == "emergency-reports" and user["role"] not in ADMIN_ROLES
        else None
    )
    base, params = selection(MODULES[module].LIST_SQL, key, opts, owner)
    order = IDS[key] + (" ASC" if opts["sort"] == "asc" else " DESC")
    if opts["sort"] == "priority" and key in {"disasters", "emergency_reports"}:
        order = priority_sql(key) + " DESC," + IDS[key] + " DESC"
    # One database statement reads all matching rows. limit/offset intentionally ignored.
    rows = db.execute(
        text(f"SELECT * {base} ORDER BY {order}"),
        params,
        execution_options={"stream_results": True, "yield_per": 500},
    ).mappings()
    filename = f"dms-{module}-{datetime.now():%Y%m%d-%H%M%S}.csv"
    return StreamingResponse(
        csv_rows(rows, COLUMNS[module]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
