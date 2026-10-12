import hashlib, secrets, time, threading
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, Response, Header
from sqlalchemy import text
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from app.database import get_db
from app.config import COOKIE_SECURE, SESSION_HOURS, ORIGINS

hasher = PasswordHasher()
COOKIE = "dms_session"
ADMIN_ROLES = {"ADMIN", "DISASTER_MANAGER"}
PUBLIC_FIELDS = "user_id, full_name, email, phone, role, status, created_at"
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
_attempts = {}
_lock = threading.Lock()


def hash_password(password):
    return hasher.hash(password)


def verify_password(password, hashed):
    try:
        return hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def check_write_request(
    request: Request, x_dms_request: str | None = Header(default=None, alias="X-DMS-Request")
):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if x_dms_request != "1":
            raise HTTPException(403, "Missing request protection header")
        origin = request.headers.get("origin")
        if origin and origin not in ORIGINS:
            raise HTTPException(403, "Origin is not permitted")


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 256:
        raise HTTPException(401, "Please sign in")
    user = (
        db.execute(
            text("""
SELECT u.user_id,u.full_name,u.email,u.phone,u.role,u.status,u.created_at
FROM auth_sessions s
JOIN users u ON u.user_id=s.user_id
WHERE s.token_hash=:token
  AND s.expires_at>UTC_TIMESTAMP()
  AND u.status='ACTIVE'
"""),
            {"token": hashlib.sha256(token.encode()).hexdigest()},
        )
        .mappings()
        .first()
    )
    if not user:
        raise HTTPException(401, "Session expired or account inactive; please sign in")
    db.execute(
        text("SET @dms_actor_id=:id,@dms_actor_name=:name"),
        {"id": user["user_id"], "name": user["full_name"]},
    )
    return dict(user)


def require_admin(user=Depends(current_user)):
    if user["role"] not in ADMIN_ROLES:
        raise HTTPException(403, "Administrator access required")
    return user


def require_owner_admin(user=Depends(current_user)):
    if user["role"] != "ADMIN":
        raise HTTPException(403, "Only an administrator can manage accounts")
    return user


def issue_session(db, response: Response, user_id):
    token = secrets.token_urlsafe(48)
    db.execute(text("DELETE FROM auth_sessions WHERE expires_at<=UTC_TIMESTAMP()"))
    db.execute(
        text(
            "INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES(:token,:user,:expires)"
        ),
        {
            "token": hashlib.sha256(token.encode()).hexdigest(),
            "user": user_id,
            "expires": datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=SESSION_HOURS),
        },
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def rate_limit(request, email):
    # Local single-process demo protection; distributed deployment needs shared storage.
    key = (request.client.host if request.client else "unknown", email.lower())
    now = time.monotonic()
    with _lock:
        for k in list(_attempts):
            if _attempts[k][1] < now - 900:
                del _attempts[k]
        count, _ = _attempts.get(key, (0, now))
        if count >= 10:
            raise HTTPException(429, "Too many attempts; retry after 15 minutes")
        if len(_attempts) >= 10000:
            raise HTTPException(429, "Authentication is busy; retry later")
        _attempts[key] = (count + 1, now)
    return key


def clear_attempts(key):
    with _lock:
        _attempts.pop(key, None)
