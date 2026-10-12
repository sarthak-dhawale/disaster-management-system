from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import AllocationCreate, AllocationUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import allocation_save, allocation_delete

router = APIRouter(
    prefix="/api/resource-allocations",
    tags=["Resource Allocations"],
    dependencies=[Depends(require_admin)],
)
LIST_SQL = """
SELECT ra.allocation_id, ra.request_id, ra.resource_id, r.resource_name, r.unit, ra.disaster_id, d.title AS disaster_title,
       ra.shelter_id, s.name AS shelter_name, ra.allocated_by, u.full_name AS allocated_by_name,
       ra.quantity, ra.allocation_date, ra.status
FROM resource_allocations ra
JOIN resources r ON ra.resource_id = r.resource_id
LEFT JOIN disasters d ON ra.disaster_id = d.disaster_id
LEFT JOIN shelters s ON ra.shelter_id = s.shelter_id
LEFT JOIN users u ON ra.allocated_by = u.user_id
ORDER BY ra.allocation_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "resource_allocations", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT ra.allocation_id, ra.request_id, ra.resource_id, r.resource_name, r.unit, ra.disaster_id, d.title AS disaster_title,
       ra.shelter_id, s.name AS shelter_name, ra.allocated_by, u.full_name AS allocated_by_name,
       ra.quantity, ra.allocation_date, ra.status
FROM resource_allocations ra
JOIN resources r ON ra.resource_id = r.resource_id
LEFT JOIN disasters d ON ra.disaster_id = d.disaster_id
LEFT JOIN shelters s ON ra.shelter_id = s.shelter_id
LEFT JOIN users u ON ra.allocated_by = u.user_id
WHERE allocation_id=:id
"""),
            {"id": id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(404, "Record not found")
    return dict(row)


@router.post("/", status_code=201)
def create(body: AllocationCreate, db=Depends(get_db), user=Depends(require_admin)):
    body.allocated_by = user["user_id"]
    return allocation_save(db, body)


@router.put("/{id}")
def edit(
    body: AllocationUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    body.allocated_by = user["user_id"]
    return allocation_save(db, body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return allocation_delete(db, id)
