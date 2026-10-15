import logging
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy import text
from app.database import test_database_connection, get_db
from app.config import ORIGINS
from app.security import check_write_request, current_user
from app.routes import (
    auth,
    disasters,
    shelters,
    locations,
    users,
    volunteers,
    resources,
    emergency_reports,
    resource_allocations,
    volunteer_assignments,
    shelter_registrations,
    dashboard,
    search,
    history,
    intelligence,
    demand,
    exports,
    planning,
    reports_v3,
    operations,
    replay,
)

app = FastAPI(
    title="Disaster Management System", version="4.0.0", dependencies=[Depends(check_write_request)]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    expose_headers=["Content-Disposition"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-DMS-Request"],
)
for module in [
    auth,
    disasters,
    shelters,
    locations,
    users,
    volunteers,
    resources,
    emergency_reports,
    resource_allocations,
    volunteer_assignments,
    shelter_registrations,
    dashboard,
    search,
    history,
    intelligence,
    demand,
    exports,
    planning,
    reports_v3,
    operations,
    replay,
]:
    app.include_router(module.router)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic error inputs can contain passwords. Return locations/messages only.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": "Please correct the highlighted fields", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "A duplicate, related record, or database constraint prevents this change"
        },
    )


@app.exception_handler(OperationalError)
async def operational_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable or not initialized. Check MySQL and the additive migration."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sql_error(request, exc):
    logging.getLogger("dms").error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed. Check schema setup and retry."},
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger("dms").error("Request failed: %s", type(exc).__name__)
    # ServerErrorMiddleware is outside CORS middleware; keep allowed clients able
    # to read the sanitized error rather than seeing a misleading network failure.
    origin = request.headers.get("origin")
    headers = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", "Vary": "Origin"} if origin in ORIGINS else {}
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error. Please retry."}, headers=headers)


@app.get("/")
def root():
    return {"message": "Disaster Management System API is running", "version": "4.0.0"}


@app.get("/health")
def health():
    connected = test_database_connection()
    return JSONResponse(
        status_code=200 if connected else 503,
        content={
            "status": "healthy" if connected else "degraded",
            "database": "connected" if connected else "disconnected",
        },
    )


@app.get("/api/lookups/{module}")
def lookups(
    module: str, db=Depends(get_db), user=Depends(current_user), q: str = "", offset: int = 0
):
    from app.security import ADMIN_ROLES
    from app.listing import IDS
    from fastapi import HTTPException

    if len(q) > 150 or offset < 0:
        raise HTTPException(422, "Invalid lookup query")
    labels = {
        "locations": "CONCAT(city, ', ', district, ', ', state, ' — ', address)",
        "disasters": "title",
        "shelters": "name",
        "resources": "resource_name",
        "users": "full_name",
        "volunteers": "(SELECT full_name FROM users u WHERE u.user_id=volunteers.user_id)",
    }
    if module not in labels:
        raise HTTPException(404, "Lookup not found")
    if module != "locations" and user["role"] not in ADMIN_ROLES:
        raise HTTPException(403, "Administrator access required")
    idfield = IDS[module]
    label = labels[module]
    params = {"q": "%" + q + "%", "offset": offset}
    rows = (
        db.execute(
            text(
                f"SELECT {idfield} AS id,{label} AS label FROM {module} WHERE {label} LIKE :q ORDER BY {idfield} LIMIT 200 OFFSET :offset"
            ),
            params,
        )
        .mappings()
        .all()
    )
    return {"items": [dict(r) for r in rows], "offset": offset, "has_more": len(rows) == 200}
