from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import UserCreate, UserUpdate
from app.security import require_owner_admin, PUBLIC_FIELDS, hash_password
from app.listing import list_options, list_records
from app.crud import record, insert, update, simple_delete

router = APIRouter(prefix="/api/users", tags=["Users"], dependencies=[Depends(require_owner_admin)])
LIST_SQL = "SELECT " + PUBLIC_FIELDS + " FROM users ORDER BY user_id DESC"


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options)):
    return list_records(db, LIST_SQL, "users", options)


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db)):
    user = record(db, "users", id)
    user.pop("password_hash")
    return user


@router.post("/", status_code=201)
def create(body: UserCreate, db=Depends(get_db)):
    data = body.model_dump()
    data["password_hash"] = hash_password(data.pop("password"))
    id = insert(db, "users", data)
    db.commit()
    return {"message": "User created", "user_id": id}


@router.put("/{id}")
def edit(
    body: UserUpdate, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_owner_admin)
):
    # Serialize account changes to protect the last active administrator.
    admins = db.execute(
        text(
            "SELECT user_id FROM users WHERE role='ADMIN' AND status='ACTIVE' ORDER BY user_id FOR UPDATE"
        )
    ).all()
    old = record(db, "users", id, True)
    if id == user["user_id"] and (body.status != "ACTIVE" or body.role != "ADMIN"):
        raise HTTPException(409, "You cannot disable or demote your own administrator account")
    if (
        old["role"] == "ADMIN"
        and old["status"] == "ACTIVE"
        and len(admins) <= 1
        and (body.role != "ADMIN" or body.status != "ACTIVE")
    ):
        raise HTTPException(409, "Keep at least one active administrator")
    data = body.model_dump()
    password = data.pop("password")
    if password:
        data["password_hash"] = hash_password(password)
    update(db, "users", id, data)
    if password or old["role"] != body.role or old["status"] != body.status:
        db.execute(text("DELETE FROM auth_sessions WHERE user_id=:id"), {"id": id})
    db.commit()
    return {"message": "User updated", "user_id": id}


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_owner_admin)):
    admins = db.execute(
        text(
            "SELECT user_id FROM users WHERE role='ADMIN' AND status='ACTIVE' ORDER BY user_id FOR UPDATE"
        )
    ).all()
    old = record(db, "users", id, True)
    if id == user["user_id"]:
        raise HTTPException(409, "You cannot delete your own account")
    if old["role"] == "ADMIN" and old["status"] == "ACTIVE" and len(admins) <= 1:
        raise HTTPException(409, "Keep at least one active administrator")
    return simple_delete(db, "users", id)
