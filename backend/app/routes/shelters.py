from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import ShelterCreate, ShelterUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import simple_save, simple_delete

router = APIRouter(prefix="/api/shelters", tags=["Shelters"], dependencies=[Depends(require_admin)])
LIST_SQL = "SELECT s.*,l.city,l.district,l.state,l.address FROM shelters s JOIN locations l ON l.location_id=s.location_id ORDER BY s.shelter_id DESC"


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "shelters", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text(
                "SELECT s.*,l.city,l.district,l.state,l.address FROM shelters s JOIN locations l ON l.location_id=s.location_id  WHERE shelter_id=:id"
            ),
            {"id": id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(404, "Record not found")
    return dict(row)


@router.post("/", status_code=201)
def create(body: ShelterCreate, db=Depends(get_db), user=Depends(require_admin)):
    return simple_save(db, "shelters", body)


@router.put("/{id}")
def edit(
    body: ShelterUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return simple_save(db, "shelters", body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return simple_delete(db, "shelters", id)
