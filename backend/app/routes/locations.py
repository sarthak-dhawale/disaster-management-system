from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import LocationCreate, LocationUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import simple_save, simple_delete

router = APIRouter(
    prefix="/api/locations", tags=["Locations"], dependencies=[Depends(require_admin)]
)
LIST_SQL = """
SELECT location_id, state, district, city, address, latitude, longitude, created_at
FROM locations
ORDER BY location_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "locations", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT location_id, state, district, city, address, latitude, longitude, created_at
FROM locations
WHERE location_id=:id
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
def create(body: LocationCreate, db=Depends(get_db), user=Depends(require_admin)):
    return simple_save(db, "locations", body)


@router.put("/{id}")
def edit(
    body: LocationUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return simple_save(db, "locations", body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return simple_delete(db, "locations", id)
