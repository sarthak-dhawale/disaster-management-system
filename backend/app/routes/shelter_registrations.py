from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import RegistrationCreate, RegistrationUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import registration_save, registration_delete

router = APIRouter(
    prefix="/api/shelter-registrations",
    tags=["Shelter Registrations"],
    dependencies=[Depends(require_admin)],
)
LIST_SQL = """
SELECT sr.registration_id, sr.shelter_id, s.name AS shelter_name, sr.user_id, u.full_name AS user_name, u.phone,
       sr.check_in, sr.check_out, sr.status
FROM shelter_registrations sr
JOIN shelters s ON sr.shelter_id = s.shelter_id
JOIN users u ON sr.user_id = u.user_id
ORDER BY sr.registration_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "shelter_registrations", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT sr.registration_id, sr.shelter_id, s.name AS shelter_name, sr.user_id, u.full_name AS user_name, u.phone,
       sr.check_in, sr.check_out, sr.status
FROM shelter_registrations sr
JOIN shelters s ON sr.shelter_id = s.shelter_id
JOIN users u ON sr.user_id = u.user_id
WHERE registration_id=:id
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
def create(body: RegistrationCreate, db=Depends(get_db), user=Depends(require_admin)):
    return registration_save(db, body)


@router.put("/{id}")
def edit(
    body: RegistrationUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return registration_save(db, body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return registration_delete(db, id)
