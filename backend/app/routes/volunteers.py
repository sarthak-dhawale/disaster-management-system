from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import VolunteerCreate, VolunteerUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import simple_save, simple_delete

router = APIRouter(
    prefix="/api/volunteers", tags=["Volunteers"], dependencies=[Depends(require_admin)]
)
LIST_SQL = """
SELECT v.volunteer_id, v.user_id, u.full_name, u.email, u.phone, v.skills, v.availability_status,
       v.emergency_contact, v.joined_at
FROM volunteers v
JOIN users u ON v.user_id = u.user_id
ORDER BY v.volunteer_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "volunteers", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT v.volunteer_id, v.user_id, u.full_name, u.email, u.phone, v.skills, v.availability_status,
       v.emergency_contact, v.joined_at
FROM volunteers v
JOIN users u ON v.user_id = u.user_id
WHERE volunteer_id=:id
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
def create(body: VolunteerCreate, db=Depends(get_db), user=Depends(require_admin)):
    return simple_save(db, "volunteers", body)


@router.put("/{id}")
def edit(
    body: VolunteerUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return simple_save(db, "volunteers", body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return simple_delete(db, "volunteers", id)
