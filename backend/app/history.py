from contextlib import contextmanager
from sqlalchemy import text


@contextmanager
def movement_context(db, kind, note, allocation_id=None):
    db.execute(
        text(
            "SET @dms_movement_kind=:kind,@dms_movement_note=:note,@dms_allocation_id=:allocation"
        ),
        {"kind": kind, "note": note, "allocation": allocation_id},
    )
    try:
        yield
    finally:
        db.execute(
            text("SET @dms_movement_kind=NULL,@dms_movement_note=NULL,@dms_allocation_id=NULL")
        )
