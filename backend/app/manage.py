import argparse, getpass
from sqlalchemy import text
from app.database import SessionLocal
from app.models import Register
from pydantic import ValidationError
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser(
        description="Provision accounts without passwords in source or shell history"
    )
    parser.add_argument("command", choices=["create-admin", "reset-password"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    password = getpass.getpass("Password (at least 10 characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        account = Register(full_name=args.name, email=args.email, password=password)
    except ValidationError as exc:
        # Default validation text includes input values, including passwords.
        fields = ", ".join(sorted({str(error["loc"][0]) for error in exc.errors()}))
        raise SystemExit(
            "Invalid account fields: "
            + fields
            + ". Check email/name and use a password of 10–128 characters."
        ) from None
    with SessionLocal() as db:
        try:
            existing = (
                db.execute(
                    text("SELECT user_id FROM users WHERE email=:email"),
                    {"email": str(account.email)},
                )
                .mappings()
                .first()
            )
            if args.command == "create-admin":
                if existing:
                    raise SystemExit(
                        "Email already exists. Use another email; reset-password preserves the existing role."
                    )
                db.execute(
                    text(
                        "INSERT INTO users(full_name,email,password_hash,role,status) VALUES(:name,:email,:hash,'ADMIN','ACTIVE')"
                    ),
                    {
                        "name": account.full_name,
                        "email": str(account.email),
                        "hash": hash_password(password),
                    },
                )
            else:
                if not existing:
                    raise SystemExit("Account not found")
                db.execute(
                    text("UPDATE users SET password_hash=:hash WHERE user_id=:id"),
                    {"hash": hash_password(password), "id": existing["user_id"]},
                )
                db.execute(
                    text("DELETE FROM auth_sessions WHERE user_id=:id"), {"id": existing["user_id"]}
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
    print("Account operation completed. No passwords or hashes displayed.")


if __name__ == "__main__":
    main()
