from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.security import current_user, ADMIN_ROLES
from app.listing import list_options, list_records
from app.routes import (
    disasters,
    shelters,
    resources,
    emergency_reports,
    locations,
    users,
    volunteers,
    resource_allocations,
    volunteer_assignments,
    shelter_registrations,
)

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("/{module}")
def search(
    module: str, db=Depends(get_db), options=Depends(list_options), user=Depends(current_user)
):
    modules = {
        "disasters": disasters,
        "shelters": shelters,
        "resources": resources,
        "emergency-reports": emergency_reports,
        "locations": locations,
        "users": users,
        "volunteers": volunteers,
        "resource-allocations": resource_allocations,
        "volunteer-assignments": volunteer_assignments,
        "shelter-registrations": shelter_registrations,
    }
    if module not in modules:
        raise HTTPException(404, "Search module not found")
    if module != "emergency-reports" and user["role"] not in ADMIN_ROLES:
        raise HTTPException(403, "Administrator access required")
    if module == "users" and user["role"] != "ADMIN":
        raise HTTPException(403, "Only an administrator can search accounts")
    if module == "emergency-reports":
        return emergency_reports.get_all(db, options, user)
    return list_records(db, modules[module].LIST_SQL, module.replace("-", "_"), options)
