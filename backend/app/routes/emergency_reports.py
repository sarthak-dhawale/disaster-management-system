from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import text
from app.database import get_db
from app.models import EmergencyReportCreate, Review, ReportProgress
from app.security import current_user, require_admin, ADMIN_ROLES
from app.listing import list_options, list_records
from app.crud import record, insert, update, remove

router = APIRouter(prefix="/api/emergency-reports", tags=["Emergency reports"])
LIST_SQL = """
SELECT er.*,l.city,l.district,l.state,l.address,u.full_name AS reported_by_name
FROM emergency_reports er
LEFT JOIN locations l ON l.location_id=er.location_id
LEFT JOIN users u ON u.user_id=er.reported_by
ORDER BY er.report_id DESC
"""


def owned_record(db, id, user, lock=False):
    owner = "" if user["role"] in ADMIN_ROLES else " AND reported_by=:owner"
    r = (
        db.execute(
            text(
                "SELECT * FROM emergency_reports WHERE report_id=:id"
                + owner
                + (" FOR UPDATE" if lock else "")
            ),
            {"id": id, "owner": user["user_id"]},
        )
        .mappings()
        .first()
    )
    if not r:
        raise HTTPException(404, "Report not found")
    return dict(r)


@router.get("/")
def get_all(db=Depends(get_db), options=Depends(list_options), user=Depends(current_user)):
    opts = options.copy()
    if opts["status"] in {"PENDING_REVIEW", "CONFIRMED", "REJECTED", "LEGACY"}:
        opts["review_status"] = opts.pop("status")
        opts["status"] = ""
    return list_records(
        db,
        LIST_SQL,
        "emergency_reports",
        opts,
        None if user["role"] in ADMIN_ROLES else user["user_id"],
    )


@router.get("/{id}")
def get_one(id: int = Path(gt=0), db=Depends(get_db), user=Depends(current_user)):
    owned_record(db, id, user)
    return dict(
        db.execute(text(LIST_SQL.rsplit("ORDER BY", 1)[0] + " WHERE er.report_id=:id"), {"id": id})
        .mappings()
        .one()
    )


@router.post("/", status_code=201)
def create(body: EmergencyReportCreate, db=Depends(get_db), user=Depends(current_user)):
    if body.location_id:
        record(db, "locations", body.location_id)
    data = body.model_dump()
    data.update(reported_by=user["user_id"], status="PENDING", review_status="PENDING_REVIEW")
    id = insert(db, "emergency_reports", data)
    db.commit()
    return {
        "message": "Report submitted for administrator review",
        "report_id": id,
        "status": "PENDING_REVIEW",
    }


@router.put("/{id}")
def edit(
    body: EmergencyReportCreate,
    id: int = Path(gt=0),
    db=Depends(get_db),
    user=Depends(require_admin),
):
    old = owned_record(db, id, user, True)
    if old["review_status"] != "PENDING_REVIEW":
        raise HTTPException(409, "Reviewed reports are immutable")
    if body.location_id:
        record(db, "locations", body.location_id)
    update(db, "emergency_reports", id, body.model_dump())
    db.commit()
    return {"message": "Pending report updated", "report_id": id}


@router.post("/{id}/review")
def review(body: Review, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)):
    old = owned_record(db, id, user, True)
    if old["review_status"] != "PENDING_REVIEW":
        if old["review_status"] == body.decision:
            return {
                "message": "Report already reviewed",
                "report_id": id,
                "status": old["review_status"],
                "disaster_id": old["disaster_id"],
            }
        raise HTTPException(409, "Report has already been reviewed")
    disaster_id = None
    if body.decision == "CONFIRMED":
        location_id = body.location_id or old["location_id"]
        if not location_id:
            raise HTTPException(422, "Select an official saved location before confirmation")
        record(db, "locations", location_id)
        if body.disaster_id:
            linked = record(db, "disasters", body.disaster_id, True)
            if linked["location_id"] != location_id:
                raise HTTPException(422, "Linked disaster must use the report location")
            disaster_id = body.disaster_id
        else:
            disaster_id = insert(
                db,
                "disasters",
                {
                    "location_id": location_id,
                    "reported_by": old["reported_by"],
                    "disaster_type": old["disaster_type"],
                    "title": body.title or f"Emergency report #{id}",
                    "description": old["description"],
                    "severity": old["severity"],
                    "status": "ACTIVE",
                    "start_time": old["occurred_at"] or old["reported_at"],
                },
            )
    elif body.disaster_id:
        raise HTTPException(422, "Rejected reports cannot link an official disaster")
    update(
        db,
        "emergency_reports",
        id,
        {
            **({"location_id": location_id} if body.decision == "CONFIRMED" else {}),
            "disaster_id": disaster_id,
            "review_status": body.decision,
            "status": "IN_PROGRESS" if body.decision == "CONFIRMED" else "REJECTED",
            "reviewed_by": user["user_id"],
            "reviewed_at": datetime.now(),
            "review_reason": body.reason,
        },
    )
    db.commit()
    return {
        "message": "Report reviewed",
        "report_id": id,
        "status": body.decision,
        "disaster_id": disaster_id,
    }


@router.post("/{id}/progress")
def progress(
    body: ReportProgress, id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)
):
    old = owned_record(db, id, user, True)
    if old["review_status"] not in {"CONFIRMED", "LEGACY"} or old["status"] == "REJECTED":
        raise HTTPException(
            409, "Only confirmed or existing legacy reports can change response progress"
        )
    update(
        db,
        "emergency_reports",
        id,
        {
            "status": body.status,
            "resolved_at": datetime.now() if body.status == "RESOLVED" else None,
        },
    )
    db.commit()
    return {"message": "Response progress updated", "report_id": id, "status": body.status}


@router.delete("/{id}")
def delete(id: int = Path(gt=0), db=Depends(get_db), user=Depends(require_admin)):
    old = owned_record(db, id, user, True)
    if old["review_status"] != "PENDING_REVIEW":
        raise HTTPException(409, "Retain reviewed reports as an audit trail")
    remove(db, "emergency_reports", id)
    db.commit()
    return {"message": "Pending report deleted", "report_id": id}
