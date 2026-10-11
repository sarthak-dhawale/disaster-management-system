from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import DisasterCreate, DisasterUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import simple_save, simple_delete

router = APIRouter(
    prefix="/api/disasters", tags=["Disasters"], dependencies=[Depends(require_admin)]
)
LIST_SQL = "SELECT d.*,l.city,l.district,l.state,l.address FROM disasters d JOIN locations l ON l.location_id=d.location_id ORDER BY d.disaster_id DESC"


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "disasters", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text(
                "SELECT d.*,l.city,l.district,l.state,l.address FROM disasters d JOIN locations l ON l.location_id=d.location_id  WHERE disaster_id=:id"
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
def create(body: DisasterCreate, db=Depends(get_db), user=Depends(require_admin)):
    return simple_save(db, "disasters", body)


@router.put("/{id}")
def edit(
    body: DisasterUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return simple_save(db, "disasters", body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return simple_delete(db, "disasters", id)
