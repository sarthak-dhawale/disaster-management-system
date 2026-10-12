import hashlib
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy import text
from app.database import get_db
from app.models import Login, Register
from app.security import (
    current_user,
    issue_session,
    hash_password,
    verify_password,
    rate_limit,
    clear_attempts,
    COOKIE,
    DUMMY_HASH,
    hasher,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
def register(body: Register, request: Request, db=Depends(get_db)):
    rate_limit(request, str(body.email))
    data = body.model_dump()
    password = data.pop("password")
    data.update(password_hash=hash_password(password))
    result = db.execute(
        text("""INSERT INTO users(full_name,email,password_hash,phone,role,status)
        VALUES(:full_name,:email,:password_hash,:phone,'PUBLIC_USER','ACTIVE')"""),
        data,
    )
    db.commit()
    return {
        "message": "Account created. Sign in to report an emergency.",
        "user_id": result.lastrowid,
    }


@router.post("/login")
def login(body: Login, request: Request, response: Response, db=Depends(get_db)):
    key = rate_limit(request, str(body.email))
    user = (
        db.execute(text("SELECT * FROM users WHERE email=:email"), {"email": str(body.email)})
        .mappings()
        .first()
    )
    valid = verify_password(body.password, user["password_hash"] if user else DUMMY_HASH)
    if not user or not valid or user["status"] != "ACTIVE":
        raise HTTPException(401, "Invalid email or password")
    if hasher.check_needs_rehash(user["password_hash"]):
        db.execute(
            text("UPDATE users SET password_hash=:hash WHERE user_id=:id"),
            {"hash": hash_password(body.password), "id": user["user_id"]},
        )
    previous = request.cookies.get(COOKIE)
    if previous:
        db.execute(
            text("DELETE FROM auth_sessions WHERE token_hash=:token"),
            {"token": hashlib.sha256(previous.encode()).hexdigest()},
        )
    issue_session(db, response, user["user_id"])
    clear_attempts(key)
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.get("/me")
def me(user=Depends(current_user)):
    return user


@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        db.execute(
            text("DELETE FROM auth_sessions WHERE token_hash=:token"),
            {"token": hashlib.sha256(token.encode()).hexdigest()},
        )
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"message": "Signed out"}
