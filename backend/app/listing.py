from fastapi import Query
from sqlalchemy import text


def list_options(
    q: str = Query("", max_length=150),
    status: str = Query("", max_length=30),
    severity: str = Query("", max_length=30),
    category: str = Query("", max_length=30),
    disaster_type: str = Query("", max_length=30),
    report_type: str = Query("", max_length=40),
    review_status: str = Query("", max_length=30),
    city: str = Query("", max_length=100),
    role: str = Query("", max_length=30),
    availability_status: str = Query("", max_length=30),
    low_stock: bool = False,
    available_only: bool = False,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    record_id: int | None = Query(None, gt=0),
    request_id: int | None = Query(None, gt=0),
    sort: str = Query("desc", pattern="^(asc|desc|priority)$"),
):
    return locals()


SEARCH_FIELDS = {
    "disasters": ["title", "description", "disaster_type", "city"],
    "shelters": ["name", "city", "contact_phone"],
    "volunteers": ["full_name", "skills", "email"],
    "resources": ["resource_name", "category", "unit"],
    "locations": ["city", "district", "state", "address"],
    "users": ["full_name", "email", "phone"],
    "emergency_reports": [
        "description",
        "report_type",
        "city",
        "reported_by_name",
        "reported_location_text",
    ],
    "resource_allocations": ["resource_name", "disaster_title", "shelter_name"],
    "volunteer_assignments": [
        "volunteer_name",
        "assignment_role",
        "disaster_title",
        "shelter_name",
    ],
    "shelter_registrations": ["user_name", "shelter_name"],
}
FILTER_FIELDS = {
    "disasters": {"status", "severity", "disaster_type", "city"},
    "shelters": {"status", "city"},
    "volunteers": {"availability_status"},
    "resources": {"category"},
    "locations": {"city"},
    "users": {"role", "status"},
    "emergency_reports": {"status", "review_status", "severity", "report_type", "city"},
    "resource_allocations": {"status", "request_id"},
    "volunteer_assignments": {"status"},
    "shelter_registrations": {"status"},
}
IDS = dict(
    zip(
        SEARCH_FIELDS,
        [
            "disaster_id",
            "shelter_id",
            "volunteer_id",
            "resource_id",
            "location_id",
            "user_id",
            "report_id",
            "allocation_id",
            "assignment_id",
            "registration_id",
        ],
    )
)


def selection(sql, key, options, owner=None):
    # SQL/table/column identifiers are internal constants. User values are always bound.
    sql = sql.rsplit("ORDER BY", 1)[0].strip()
    where = ["1=1"]
    params = {}
    if options["q"]:
        where.append(
            "("
            + " OR ".join(f"CAST({f} AS CHAR) LIKE :q" for f in SEARCH_FIELDS[key])
            + f" OR CAST({IDS[key]} AS CHAR) LIKE :q)"
        )
        params["q"] = "%" + options["q"] + "%"
    for field in FILTER_FIELDS[key]:
        if options.get(field):
            where.append(f"{field} LIKE :{field}" if field == "city" else f"{field}=:{field}")
            params[field] = "%" + options[field] + "%" if field == "city" else options[field]
    if options["low_stock"] and key == "resources":
        where.append("available_quantity<=minimum_required")
    if options["available_only"] and key == "shelters":
        where.append("status='AVAILABLE' AND current_occupancy<capacity")
    if owner is not None:
        where.append("reported_by=:owner")
        params["owner"] = owner
    if options.get("record_id") is not None:
        where.append(f"{IDS[key]}=:record_id")
        params["record_id"] = options["record_id"]
    base = f"FROM ({sql}) AS records WHERE " + " AND ".join(where)
    return base, params


def list_records(db, sql, key, options, owner=None):
    from app.geo import priority, priority_sql

    base, params = selection(sql, key, options, owner)
    total = db.execute(text("SELECT COUNT(*) " + base), params).scalar_one()
    params.update(limit=options["limit"], offset=options["offset"])
    rank = priority_sql(key) if key in {"disasters", "emergency_reports"} else None
    extra = f", {rank} AS priority_score" if rank else ""
    order = (
        "priority_score DESC," + IDS[key] + " DESC"
        if options["sort"] == "priority" and rank
        else IDS[key] + (" ASC" if options["sort"] == "asc" else " DESC")
    )
    rows = (
        db.execute(
            text(f"SELECT *{extra} {base} ORDER BY {order} LIMIT :limit OFFSET :offset"), params
        )
        .mappings()
        .all()
    )
    rows = [{**dict(r), **priority(dict(r))} if rank else dict(r) for r in rows]
    return {
        "count": len(rows),
        "total": total,
        "limit": options["limit"],
        "offset": options["offset"],
        key: [dict(r) for r in rows],
    }
