from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter(prefix="/api/users", tags=["Users"])


class UserCreate(BaseModel):
    full_name: str
    email: str
    password_hash: str
    phone: Optional[str] = None
    role: str = "PUBLIC_USER"
    status: str = "ACTIVE"


class UserUpdate(BaseModel):
    full_name: str
    email: str
    password_hash: str
    phone: Optional[str] = None
    role: str
    status: str


@router.get("/")
def get_all_users(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            user_id,
            full_name,
            email,
            phone,
            role,
            status,
            created_at
        FROM users
        ORDER BY user_id DESC
    """)

    result = db.execute(query).mappings().all()

    return {
        "count": len(result),
        "users": [dict(row) for row in result]
    }


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            user_id,
            full_name,
            email,
            phone,
            role,
            status,
            created_at
        FROM users
        WHERE user_id = :user_id
    """)

    result = db.execute(
        query,
        {"user_id": user_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return dict(result)


@router.post("/")
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    valid_roles = [
        "ADMIN",
        "DISASTER_MANAGER",
        "VOLUNTEER",
        "PUBLIC_USER"
    ]

    valid_statuses = [
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED"
    ]

    if user.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    if user.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid user status"
        )

    existing_user = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE email = :email
        """),
        {"email": user.email}
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    query = text("""
        INSERT INTO users (
            full_name,
            email,
            password_hash,
            phone,
            role,
            status
        )
        VALUES (
            :full_name,
            :email,
            :password_hash,
            :phone,
            :role,
            :status
        )
    """)

    result = db.execute(
        query,
        {
            "full_name": user.full_name,
            "email": user.email,
            "password_hash": user.password_hash,
            "phone": user.phone,
            "role": user.role,
            "status": user.status
        }
    )

    db.commit()

    return {
        "message": "User created successfully",
        "user_id": result.lastrowid
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db)
):
    user_check = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).first()

    if not user_check:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    valid_roles = [
        "ADMIN",
        "DISASTER_MANAGER",
        "VOLUNTEER",
        "PUBLIC_USER"
    ]

    valid_statuses = [
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED"
    ]

    if user.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role"
        )

    if user.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid user status"
        )

    duplicate_email = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE email = :email
            AND user_id != :user_id
        """),
        {
            "email": user.email,
            "user_id": user_id
        }
    ).first()

    if duplicate_email:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    query = text("""
        UPDATE users
        SET
            full_name = :full_name,
            email = :email,
            password_hash = :password_hash,
            phone = :phone,
            role = :role,
            status = :status
        WHERE user_id = :user_id
    """)

    db.execute(
        query,
        {
            "user_id": user_id,
            "full_name": user.full_name,
            "email": user.email,
            "password_hash": user.password_hash,
            "phone": user.phone,
            "role": user.role,
            "status": user.status
        }
    )

    db.commit()

    return {
        "message": "User updated successfully",
        "user_id": user_id
    }


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user_check = db.execute(
        text("""
            SELECT user_id
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).first()

    if not user_check:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    try:
        db.execute(
            text("""
                DELETE FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )

        db.commit()

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="User cannot be deleted because the user is being used by another record"
        )

    return {
        "message": "User deleted successfully",
        "user_id": user_id
    }