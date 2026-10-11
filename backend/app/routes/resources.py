from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import ResourceCreate, ResourceUpdate
from app.security import require_admin
from app.listing import list_options, list_records
from app.crud import simple_save, simple_delete

router = APIRouter(
    prefix="/api/resources", tags=["Resources"], dependencies=[Depends(require_admin)]
)
LIST_SQL = """
SELECT resource_id, resource_name, category, unit, total_quantity, available_quantity, minimum_required,
       updated_at
FROM resources
ORDER BY resource_id DESC
"""


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "resources", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    row = (
        db.execute(
            text("""
SELECT resource_id, resource_name, category, unit, total_quantity, available_quantity, minimum_required,
       updated_at
FROM resources
WHERE resource_id=:id
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
def create(body: ResourceCreate, db=Depends(get_db), user=Depends(require_admin)):
    return simple_save(db, "resources", body)


@router.put("/{id}")
def edit(
    body: ResourceUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    return simple_save(db, "resources", body, id)


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db)):
    return simple_delete(db, "resources", id)
