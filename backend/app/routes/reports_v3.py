"""Bounded actual-data PDFs, mixed-section CSV, and owner-scoped simulation exports."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import text
from app.database import get_db
from app.security import current_user, require_admin, ADMIN_ROLES
from app.listing import selection, IDS, list_options
from app.reporting import build_pdf
from app.routes import exports, shelters, volunteers, volunteer_assignments
from app.routes.intelligence import incidents, overview
from app.routes.dashboard import get_dashboard
from app.routes.planning import intelligence, owned_result, bounded_rows

router = APIRouter(prefix="/api", tags=["V3 PDF and CSV reports"])
SHELTER_COLUMNS = [
    "shelter_id",
    "name",
    "city",
    "state",
    "status",
    "capacity",
    "current_occupancy",
    "contact_phone",
]


def analysis_data(section, db, q, limit=25, offset=0):
    from app.routes.history import analytics

    result = analytics(section, db, 10001, 0)
    if result["total"] > 10000:
        raise HTTPException(413, "Analysis exceeds 10,000 records; use narrower management exports")
    rows = [
        r
        for r in result["items"]
        if not q or q.casefold() in " ".join(str(v) for v in r.values()).casefold()
    ]
    columns = list(result["items"][0]) if result["items"] else ["record", "value"]
    return {
        "items": rows[offset : offset + limit],
        "columns": columns,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
    }


@router.get("/reports/analysis/{section}")
def analysis_list(
    section: str,
    db=Depends(get_db),
    user=Depends(require_admin),
    q: str = Query("", max_length=150),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return analysis_data(section, db, q, limit, offset)


@router.get("/reports/analysis/{section}/{format}")
def analysis_export(
    section: str,
    format: str,
    db=Depends(get_db),
    user=Depends(require_admin),
    q: str = Query("", max_length=150),
):
    data = analysis_data(section, db, q, 10000, 0)
    rows, columns = data["items"], data["columns"]
    if format == "pdf":
        return Response(
            build_pdf(
                "Detailed analysis: " + section,
                [("Matching analysis records", rows, columns)],
                "Text filter: " + (q or "all"),
            ),
            media_type="application/pdf",
            headers=download_headers("analysis-" + section, "pdf"),
        )
    if format == "csv":
        return StreamingResponse(
            exports.csv_rows(rows, columns),
            media_type="text/csv",
            headers=download_headers("analysis-" + section, "csv"),
        )
    raise HTTPException(404, "Supported formats: pdf, csv")


def download_headers(name, format):
    return {
        "Content-Disposition": f'attachment; filename="dms-{name}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.{format}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }


def module_rows(module, options, db, user):
    modules = {**exports.MODULES, "shelters": shelters}
    if module not in modules:
        raise HTTPException(404, "Report module not found")
    if module != "emergency-reports" and user["role"] not in ADMIN_ROLES:
        raise HTTPException(403, "Administrator access required")
    key = module.replace("-", "_")
    opts = options.copy()
    if module == "emergency-reports" and opts["status"] in {
        "PENDING_REVIEW",
        "CONFIRMED",
        "REJECTED",
        "LEGACY",
    }:
        opts["review_status"], opts["status"] = opts["status"], ""
    owner = (
        user["user_id"]
        if module == "emergency-reports" and user["role"] not in ADMIN_ROLES
        else None
    )
    base, params = selection(modules[module].LIST_SQL, key, opts, owner)
    rows = bounded_rows(db, "SELECT * " + base + " ORDER BY " + IDS[key], params)
    columns = SHELTER_COLUMNS if module == "shelters" else exports.COLUMNS[module]
    return rows, columns


@router.get("/exports/{module}.pdf")
def module_pdf(
    module: str,
    request: Request,
    db=Depends(get_db),
    user=Depends(current_user),
    options=Depends(list_options),
):
    rows, columns = module_rows(module, options, db, user)
    scope = "; ".join(
        f"{k}: {v}"
        for k, v in options.items()
        if v not in (None, "", False) and k not in {"limit", "offset"}
    )
    data = build_pdf(
        module.replace("-", " ").title(),
        [("Matching records", rows, columns)],
        scope or "All matching records",
    )
    return Response(data, media_type="application/pdf", headers=download_headers(module, "pdf"))


@router.get("/reports/overview/{format}")
def overview_export(
    format: str,
    db=Depends(get_db),
    user=Depends(require_admin),
    q: str = "",
    state: str = "",
    severity: str = "",
    disaster_type: str = "",
    status: str = "",
    start: str | None = None,
    end: str | None = None,
):
    from datetime import date

    try:
        start_date, end_date = (
            date.fromisoformat(start) if start else None,
            date.fromisoformat(end) if end else None,
        )
    except ValueError as exc:
        raise HTTPException(422, "Invalid report date") from exc
    # Snapshot is limited explicitly; never silently export only the first map page.
    result = incidents(
        db,
        user,
        q,
        disaster_type,
        severity,
        status,
        state,
        start_date,
        end_date,
        True,
        True,
        500,
        0,
    )
    if result["total"] > 10000:
        raise HTTPException(413, "Overview exceeds 10,000 incidents. Narrow filters.")
    items = result["items"]
    for offset in range(500, result["total"], 500):
        items.extend(
            incidents(
                db,
                user,
                q,
                disaster_type,
                severity,
                status,
                state,
                start_date,
                end_date,
                True,
                True,
                500,
                offset,
            )["items"]
        )
    sections = [
        (
            "Incidents in selected scope",
            items,
            [
                "kind",
                "id",
                "title",
                "state",
                "severity",
                "response_status",
                "review_status",
                "incident_time",
            ],
        )
    ]
    stats = get_dashboard(db)
    summary = [
        {"module": module, "metric": key, "value": value}
        for module, values in stats.items()
        for key, value in values.items()
        if not isinstance(value, list) and key not in {"total_quantity", "available_quantity"}
    ]
    sections.insert(
        0,
        (
            "Global operational metrics (not narrowed by incident filters)",
            summary,
            ["module", "metric", "value"],
        ),
    )
    for name, module, columns in [
        ("Shelters - global inventory", shelters, SHELTER_COLUMNS),
        (
            "Resources - global inventory",
            exports.MODULES["resources"],
            exports.COLUMNS["resources"],
        ),
        (
            "Volunteers - global roster",
            volunteers,
            ["volunteer_id", "full_name", "skills", "availability_status"],
        ),
        (
            "Assignments - global roster",
            volunteer_assignments,
            [
                "assignment_id",
                "volunteer_name",
                "assignment_role",
                "disaster_title",
                "shelter_name",
                "status",
            ],
        ),
    ]:
        sections.append((name, bounded_rows(db, module.LIST_SQL.rsplit("ORDER BY", 1)[0]), columns))
    demand_summary = intelligence(db, user, "", "", "", "", None, None, 10000, 0)
    sections.append(
        (
            "Resource shortages - global open requests",
            demand_summary["resource_totals"],
            ["resource_name", "unit", "outstanding", "available", "shortage"],
        )
    )
    sections.append(
        (
            "Emergency reports - global review summaries",
            bounded_rows(
                db, exports.MODULES["emergency-reports"].LIST_SQL.rsplit("ORDER BY", 1)[0]
            ),
            exports.COLUMNS["emergency-reports"],
        )
    )
    scope = f"Incident filters: q={q}; state={state}; severity={severity}; type={disaster_type}; status={status}; dates={start or 'any'} to {end or 'any'}. Resource, shelter and roster sections are explicitly global."
    if format == "pdf":
        return Response(
            build_pdf("Overview report", sections, scope, map_rows=items),
            media_type="application/pdf",
            headers=download_headers("overview", "pdf"),
        )
    if format == "csv":

        def mixed():
            for heading, rows, columns in sections:
                for row in rows:
                    for column in columns:
                        yield {
                            "section": heading,
                            "record": str(row.get(columns[0], "")),
                            "field": column,
                            "value": row.get(column),
                        }

        return StreamingResponse(
            exports.csv_rows(mixed(), ["section", "record", "field", "value"]),
            media_type="text/csv",
            headers=download_headers("overview", "csv"),
        )
    raise HTTPException(404, "Supported formats: pdf, csv")


@router.get("/reports/resource-intelligence/{format}")
def intelligence_export(
    format: str,
    db=Depends(get_db),
    user=Depends(require_admin),
    q: str = "",
    state: str = "",
    severity: str = "",
    status: str = "",
    resource_id: int | None = None,
    disaster_id: int | None = None,
):
    result = intelligence(db, user, q, state, severity, status, resource_id, disaster_id, 10000, 0)
    rows = result["items"]
    columns = [
        "request_id",
        "disaster_title",
        "state",
        "severity",
        "resource_name",
        "unit",
        "quantity",
        "allocated_quantity",
        "delivered_quantity",
        "outstanding_quantity",
        "available_quantity",
        "fulfillment",
        "recommended_quantity",
    ]
    if format == "csv":
        return StreamingResponse(
            exports.csv_rows(rows, columns),
            media_type="text/csv",
            headers=download_headers("resource-intelligence", "csv"),
        )
    if format == "pdf":
        sections = [
            ("Demand and coverage", rows, columns),
            (
                "Shared stock contention",
                result["resource_totals"],
                ["resource_name", "unit", "outstanding", "available", "shortage"],
            ),
        ]
        return Response(
            build_pdf(
                "Resource Intelligence",
                sections,
                f"q={q}; state={state}; severity={severity}; status={status}; resource={resource_id}; disaster={disaster_id}",
                warnings=[
                    result["scope_note"],
                    "Recommendations require manager approval and a fresh live stock check; the same stock cannot satisfy every request independently.",
                ],
            ),
            media_type="application/pdf",
            headers=download_headers("resource-intelligence", "pdf"),
        )
    raise HTTPException(404, "Supported formats: pdf, csv")


@router.get("/simulations/{id}/export/{format}")
def simulation_export(id: str, format: str, user=Depends(require_admin)):
    result = owned_result(id, user)
    scenario = result["scenario"]
    sections = [
        (
            "Scenario inputs",
            [{"field": key, "value": value} for key, value in scenario.items() if key != "demands"],
            ["field", "value"],
        )
    ]
    sections.append(
        (
            "Snapshot inventory (commitments already excluded from available stock)",
            result["snapshot"]["resources"],
            [
                "resource_id",
                "resource_name",
                "unit",
                "total_quantity",
                "committed_quantity",
                "available_quantity",
            ],
        )
    )
    sections.append(
        (
            "Snapshot provenance",
            [{"field": "source", "value": result["snapshot"]["provenance"]}],
            ["field", "value"],
        )
    )
    for plan in result["plans"]:
        sections.append(
            (
                f"Plan {plan['code']}: {plan['title']}",
                plan["rows"],
                [
                    "demand_index",
                    "region",
                    "resource_name",
                    "unit",
                    "required",
                    "proposed",
                    "unmet",
                    "coverage_percent",
                ],
            )
        )
        sections.append(
            (
                f"Plan {plan['code']} inventory balance",
                plan["resources"],
                ["resource_name", "unit", "available", "proposed", "remaining", "reserve", "unmet"],
            )
        )
    sections.append(
        (
            "Eligible shelter capacity (all regions)",
            result["shelters"]["items"],
            ["shelter_id", "name", "state", "available_capacity", "distance_km"],
        )
    )
    sections.append(
        (
            "Shelter requirement",
            [
                {
                    "required": result["shelters"]["required"],
                    "eligible_capacity": result["shelters"]["eligible_capacity"],
                    "gap": result["shelters"]["gap"],
                }
            ],
            ["required", "eligible_capacity", "gap"],
        )
    )
    scope = (
        "HYPOTHETICAL SCENARIO - NOT A LIVE INCIDENT. Snapshot UTC "
        + result["snapshot"]["captured_at"]
    )
    if format == "pdf":
        return Response(
            build_pdf("Simulation comparison", sections, scope, warnings=result["warnings"]),
            media_type="application/pdf",
            headers=download_headers("hypothetical-simulation", "pdf"),
        )
    if format == "csv":

        def rows():
            for heading, records, columns in sections:
                for row in records:
                    for column in columns:
                        yield {
                            "hypothetical": "NOT A LIVE INCIDENT",
                            "scenario": scenario["name"],
                            "snapshot": result["snapshot"]["captured_at"],
                            "section": heading,
                            "record": str(row.get(columns[0], "")),
                            "field": column,
                            "value": row.get(column),
                        }
            for index, warning in enumerate(result["warnings"]):
                yield {
                    "hypothetical": "NOT A LIVE INCIDENT",
                    "scenario": scenario["name"],
                    "snapshot": result["snapshot"]["captured_at"],
                    "section": "Assumptions and limitations",
                    "record": str(index + 1),
                    "field": "warning",
                    "value": warning,
                }

        return StreamingResponse(
            exports.csv_rows(
                rows(),
                ["hypothetical", "scenario", "snapshot", "section", "record", "field", "value"],
            ),
            media_type="text/csv",
            headers=download_headers("hypothetical-simulation", "csv"),
        )
    raise HTTPException(404, "Supported formats: pdf, csv")
