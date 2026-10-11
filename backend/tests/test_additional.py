from datetime import datetime
from unittest.mock import patch
import pytest
from app.main import app
from app.security import current_user, hash_password
from app.models import ReportProgress, Review
from app.routes.emergency_reports import progress, review
from conftest import ADMIN, PUBLIC


def test_valid_login_cookie_and_no_password_hash(client, db):
    from app.security import clear_attempts

    row = {
        **ADMIN,
        "email": "login@example.com",
        "password_hash": hash_password("login-password-123"),
    }
    db.execute.return_value.mappings.return_value.first.return_value = row
    response = client.post(
        "/api/auth/login",
        headers={"X-DMS-Request": "1"},
        json={"email": "login@example.com", "password": "login-password-123"},
    )
    assert response.status_code == 200 and "password_hash" not in response.json()
    assert "HttpOnly" in response.headers["set-cookie"]


def test_expired_session_cannot_access(client, db):
    client.cookies.set("dms_session", "an-expired-opaque-token")
    db.execute.return_value.mappings.return_value.first.return_value = None
    assert client.get("/api/auth/me").status_code == 401
    assert "expires_at>UTC_TIMESTAMP()" in str(db.execute.call_args.args[0])


def test_logout_deletes_db_session(client, db):
    client.cookies.set("dms_session", "temporary-token")
    response = client.post("/api/auth/logout", headers={"X-DMS-Request": "1"})
    assert response.status_code == 200 and "Max-Age=0" in response.headers["set-cookie"]
    assert "DELETE FROM auth_sessions" in str(db.execute.call_args.args[0])


def test_public_progress_forbidden(client):
    app.dependency_overrides[current_user] = lambda: PUBLIC
    assert (
        client.post(
            "/api/emergency-reports/1/progress",
            headers={"X-DMS-Request": "1"},
            json={"status": "RESOLVED"},
        ).status_code
        == 403
    )


def test_confirmed_progress_keeps_review_link(db):
    with (
        patch(
            "app.routes.emergency_reports.owned_record",
            return_value={"review_status": "CONFIRMED", "status": "IN_PROGRESS", "disaster_id": 21},
        ),
        patch("app.routes.emergency_reports.update") as update,
    ):
        progress(ReportProgress(status="RESOLVED"), 7, db, ADMIN)
        fields = update.call_args.args[3]
        assert fields["status"] == "RESOLVED" and isinstance(fields["resolved_at"], datetime)
        assert "review_status" not in fields and "disaster_id" not in fields


def test_pending_progress_cannot_bypass_review(db):
    with patch(
        "app.routes.emergency_reports.owned_record",
        return_value={"review_status": "PENDING_REVIEW", "status": "PENDING"},
    ):
        with pytest.raises(Exception) as e:
            progress(ReportProgress(status="RESOLVED"), 7, db, ADMIN)
        assert e.value.status_code == 409
        db.commit.assert_not_called()


def test_link_wrong_location_rejected(db):
    with (
        patch(
            "app.routes.emergency_reports.owned_record",
            return_value={"review_status": "PENDING_REVIEW", "location_id": 1},
        ),
        patch("app.routes.emergency_reports.record", return_value={"location_id": 2}),
    ):
        with pytest.raises(Exception) as e:
            review(Review(decision="CONFIRMED", disaster_id=21), 7, db, ADMIN)
        assert e.value.status_code == 422
        db.commit.assert_not_called()


def test_self_demotion_rejected(client, db):
    app.dependency_overrides[current_user] = lambda: ADMIN
    db.execute.return_value.all.return_value = [(1,)]
    db.execute.return_value.mappings.return_value.first.return_value = ADMIN
    response = client.put(
        "/api/users/1",
        headers={"X-DMS-Request": "1"},
        json={
            "full_name": "Owner",
            "email": "owner@example.com",
            "role": "PUBLIC_USER",
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 409
    db.commit.assert_not_called()


def test_database_session_rolls_back_and_closes():
    from app.database import get_db
    from unittest.mock import MagicMock

    db = MagicMock()
    with patch("app.database.SessionLocal", return_value=db):
        session = get_db()
        assert next(session) is db
        with pytest.raises(ValueError):
            session.throw(ValueError("test"))
        db.rollback.assert_called_once()
        db.close.assert_called_once()
