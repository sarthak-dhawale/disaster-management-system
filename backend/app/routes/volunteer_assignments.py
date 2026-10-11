from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import AssignmentCreate, AssignmentUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import assignment_save, assignment_delete

router = APIRouter(
    prefix="/api/volunteer-assignments",
    tags=["Volunteer Assignments"],
    dependencies=[Depends(require_admin)],
)
LIST_SQL = """
SELECT va.assignment_id, va.volunteer_id, u.full_name AS volunteer_name, va.disaster_id,
       d.title AS disaster_title, va.shelter_id, s.name AS shelter_name, va.assigned_by,
       a.full_name AS assigned_by_name, va.assignment_role, va.start_time, va.end_time, va.status
FROM volunteer_assignments va
JOIN volunteers v ON va.volunteer_id = v.volunteer_id
JOIN users u ON v.user_id = u.user_id
LEFT JOIN disasters d ON va.disaster_id = d.disaster_id
LEFT JOIN shelters s ON va.shelter_id = s.shelter_id
LEFT JOIN users a ON va.assigned_by = a.user_id
ORDER BY va.assignment_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "volunteer_assignments", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT va.assignment_id, va.volunteer_id, u.full_name AS volunteer_name, va.disaster_id,
       d.title AS disaster_title, va.shelter_id, s.name AS shelter_name, va.assigned_by,
       a.full_name AS assigned_by_name, va.assignment_role, va.start_time, va.end_time, va.status
FROM volunteer_assignments va
JOIN volunteers v ON va.volunteer_id = v.volunteer_id
JOIN users u ON v.user_id = u.user_id
LEFT JOIN disasters d ON va.disaster_id = d.disaster_id
LEFT JOIN shelters s ON va.shelter_id = s.shelter_id
LEFT JOIN users a ON va.assigned_by = a.user_id
WHERE assignment_id=:id
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
def create(body: AssignmentCreate, db=Depends(get_db), user=Depends(require_admin)):
    body.assigned_by = user["user_id"]
    return assignment_save(db, body)


@router.put("/{id}")
def edit(
    body: AssignmentUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    body.assigned_by = user["user_id"]
    return assignment_save(db, body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return assignment_delete(db, id)
