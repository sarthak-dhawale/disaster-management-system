from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from app.models import DisasterCreate, RegistrationCreate
from app.history import movement_context

IDS = {
    "locations": "location_id",
    "disasters": "disaster_id",
    "shelters": "shelter_id",
    "users": "user_id",
    "volunteers": "volunteer_id",
    "resources": "resource_id",
    "resource_allocations": "allocation_id",
    "volunteer_assignments": "assignment_id",
    "shelter_registrations": "registration_id",
    "emergency_reports": "report_id",
    "resource_requests": "request_id",
}
REFS = {
    "request_id": "resource_requests",
    "location_id": "locations",
    "reported_by": "users",
    "user_id": "users",
    "resource_id": "resources",
    "disaster_id": "disasters",
    "shelter_id": "shelters",
    "allocated_by": "users",
    "assigned_by": "users",
    "volunteer_id": "volunteers",
}
CHILDREN = {
    "locations": [
        ("disasters", "location_id"),
        ("shelters", "location_id"),
        ("emergency_reports", "location_id"),
    ],
    "users": [
        ("disasters", "reported_by"),
        ("volunteers", "user_id"),
        ("emergency_reports", "reported_by"),
        ("emergency_reports", "reviewed_by"),
        ("shelter_registrations", "user_id"),
        ("resource_allocations", "allocated_by"),
        ("volunteer_assignments", "assigned_by"),
    ],
    "disasters": [
        ("resource_requests", "disaster_id"),
        ("resource_allocations", "disaster_id"),
        ("volunteer_assignments", "disaster_id"),
        ("emergency_reports", "disaster_id"),
    ],
    "shelters": [
        ("resource_allocations", "shelter_id"),
        ("volunteer_assignments", "shelter_id"),
        ("shelter_registrations", "shelter_id"),
    ],
    "resources": [("resource_requests", "resource_id"), ("resource_allocations", "resource_id")],
    "volunteers": [("volunteer_assignments", "volunteer_id")],
}


def record(db, table, id, lock=False):
    r = (
        db.execute(
            text(f"SELECT * FROM {table} WHERE {IDS[table]}=:id" + (" FOR UPDATE" if lock else "")),
            {"id": id},
        )
        .mappings()
        .first()
    )
    if not r:
        raise HTTPException(404, table.replace("_", " ").capitalize() + " record not found")
    return dict(r)


def references(db, data):
    for field, table in REFS.items():
        if data.get(field) is not None:
            record(db, table, data[field])


def insert(db, table, data):
    fields = ",".join(data)
    values = ",".join(":" + f for f in data)
    return db.execute(text(f"INSERT INTO {table}({fields}) VALUES({values})"), data).lastrowid


def update(db, table, id, data):
    if data:
        db.execute(
            text(
                f"UPDATE {table} SET "
                + ",".join(f"{f}=:{f}" for f in data)
                + f" WHERE {IDS[table]}=:record_id"
            ),
            {**data, "record_id": id},
        )


def remove(db, table, id):
    db.execute(text(f"DELETE FROM {table} WHERE {IDS[table]}=:id"), {"id": id})


def block_dependencies(db, table, id):
    for child, fk in CHILDREN.get(table, []):
        if db.execute(text(f"SELECT 1 FROM {child} WHERE {fk}=:id LIMIT 1"), {"id": id}).first():
            raise HTTPException(
                409, f"Record has related {child.replace('_', ' ')}. Remove or reassign them first."
            )


def simple_save(db, table, body, id=None):
    old = record(db, table, id, True) if id else None
    data = body.model_dump(exclude_unset=(table == "disasters" and id is not None))
    if not data:
        raise HTTPException(400, "No fields supplied")
    if table == "disasters" and old:
        merged = {k: old.get(k) for k in DisasterCreate.model_fields}
        merged.update(data)
        try:
            DisasterCreate.model_validate(merged)
        except ValidationError:
            raise HTTPException(422, "Invalid disaster fields or time range")
    references(db, data)
    if table == "locations":
        import hashlib

        fields = ["state", "district", "city", "address"]
        normalized = {f: data[f].strip().lower() for f in fields}
        existing = (
            db.execute(
                text(
                    "SELECT location_id FROM locations WHERE "
                    + " AND ".join(f"LOWER(TRIM({f}))=:{f}" for f in fields)
                    + " AND location_id!=:id LIMIT 1"
                ),
                {**normalized, "id": id or 0},
            )
            .mappings()
            .first()
        )
        if existing and existing["location_id"] != id:
            if id:
                raise HTTPException(409, "This saved location already exists")
            return {
                "message": "Existing saved location selected; coordinates retained",
                "location_id": existing["location_id"],
            }
        data["location_key"] = hashlib.sha256(
            "\x1f".join(normalized[f] for f in fields).encode()
        ).hexdigest()
    if table == "volunteers":
        if old:
            active = db.execute(
                text(
                    "SELECT COUNT(*) FROM volunteer_assignments WHERE volunteer_id=:id AND status IN ('ASSIGNED','ACTIVE')"
                ),
                {"id": id},
            ).scalar_one()
            if active and data["availability_status"] != "ASSIGNED":
                raise HTTPException(409, "Volunteer still has active assignments")
        if data["availability_status"] == "ASSIGNED" and (not old or not active):
            raise HTTPException(422, "Create an active assignment to mark a volunteer assigned")
    if table == "resources" and old:
        if data["unit"] != old["unit"]:
            raise HTTPException(
                409,
                "Resource units cannot be changed; create a separate resource for a different unit",
            )
        used = db.execute(
            text(
                "SELECT COALESCE(SUM(quantity),0) FROM resource_allocations WHERE resource_id=:id AND status!='CANCELLED'"
            ),
            {"id": id},
        ).scalar_one()
        if data["total_quantity"] - data["available_quantity"] < used:
            raise HTTPException(409, "Inventory must reserve the quantity already allocated")
    if table == "shelters" and old:
        occupied = db.execute(
            text(
                "SELECT COUNT(*) FROM shelter_registrations WHERE shelter_id=:id AND status='ACTIVE'"
            ),
            {"id": id},
        ).scalar_one()
        if data["current_occupancy"] < occupied:
            raise HTTPException(409, "Occupancy cannot be below active registrations")
    if id:
        update(db, table, id, data)
    else:
        id = insert(db, table, data)
    db.commit()
    return {"message": "Record saved successfully", IDS[table]: id}


def simple_delete(db, table, id):
    record(db, table, id, True)
    block_dependencies(db, table, id)
    remove(db, table, id)
    db.commit()
    return {"message": "Record deleted successfully", IDS[table]: id}


def allocation_save(db, body, id=None, approval_key=None):
    table = "resource_allocations"
    old = record(db, table, id, True) if id else None
    data = body.model_dump()
    if old and "request_id" not in body.model_fields_set:
        data["request_id"] = old.get("request_id")
    references(db, data)
    request_ids = sorted(
        {r for r in [data.get("request_id"), old.get("request_id") if old else None] if r}
    )
    requests = {r: record(db, "resource_requests", r, True) for r in request_ids}
    if data.get("request_id"):
        request = requests[data["request_id"]]
        if (
            request["status"] != "OPEN"
            or request["resource_id"] != data["resource_id"]
            or request["disaster_id"] != data["disaster_id"]
        ):
            raise HTTPException(
                409, "Allocation must match an open request and its resource/disaster"
            )
        allocated = db.execute(
            text(
                "SELECT COALESCE(SUM(quantity),0) FROM resource_allocations WHERE request_id=:request AND allocation_id!=:id AND status!='CANCELLED'"
            ),
            {"request": data["request_id"], "id": id or 0},
        ).scalar_one()
        if data["status"] != "CANCELLED" and allocated + data["quantity"] > request["quantity"]:
            raise HTTPException(409, "Allocation exceeds remaining requested quantity")
    if approval_key:
        data["approval_key"] = approval_key
    resource_ids = sorted({data["resource_id"]} | ({old["resource_id"]} if old else set()))
    resources = {rid: record(db, "resources", rid, True) for rid in resource_ids}
    if old and old["status"] != "CANCELLED":
        rid = old["resource_id"]
        restored = resources[rid]["available_quantity"] + old["quantity"]
        if restored > resources[rid]["total_quantity"]:
            raise HTTPException(409, "Inventory is inconsistent; review it before restoring stock")
        resources[rid]["available_quantity"] = restored
    if data["status"] != "CANCELLED":
        resource = resources[data["resource_id"]]
        if data["quantity"] > resource["available_quantity"]:
            raise HTTPException(409, "Insufficient available resource quantity")
        resource["available_quantity"] -= data["quantity"]
    if id:
        update(db, table, id, data)
    else:
        id = insert(db, table, data)
    for rid, r in resources.items():
        with movement_context(db, "ALLOCATION_CHANGE", "Allocation saved: " + data["status"], id):
            update(db, "resources", rid, {"available_quantity": r["available_quantity"]})
    db.commit()
    return {"message": "Allocation saved", "allocation_id": id}


def allocation_delete(db, id):
    old = record(db, "resource_allocations", id, True)
    r = record(db, "resources", old["resource_id"], True)
    if old["status"] != "CANCELLED":
        amount = r["available_quantity"] + old["quantity"]
        if amount > r["total_quantity"]:
            raise HTTPException(409, "Inventory is inconsistent; review stock before deletion")
        with movement_context(db, "RETURN", "Stock returned by allocation deletion", id):
            update(db, "resources", old["resource_id"], {"available_quantity": amount})
    remove(db, "resource_allocations", id)
    db.commit()
    return {"message": "Allocation deleted", "allocation_id": id}


def refresh_volunteer(db, id):
    active = db.execute(
        text(
            "SELECT COUNT(*) FROM volunteer_assignments WHERE volunteer_id=:id AND status IN ('ASSIGNED','ACTIVE')"
        ),
        {"id": id},
    ).scalar_one()
    if active:
        update(db, "volunteers", id, {"availability_status": "ASSIGNED"})
    else:
        db.execute(
            text(
                "UPDATE volunteers SET availability_status='AVAILABLE' WHERE volunteer_id=:id AND availability_status='ASSIGNED'"
            ),
            {"id": id},
        )


def assignment_save(db, body, id=None):
    table = "volunteer_assignments"
    old = record(db, table, id, True) if id else None
    data = body.model_dump()
    references(db, data)
    ids = sorted({data["volunteer_id"]} | ({old["volunteer_id"]} if old else set()))
    volunteers = {v: record(db, "volunteers", v, True) for v in ids}
    if (
        data["status"] in {"ASSIGNED", "ACTIVE"}
        and volunteers[data["volunteer_id"]]["availability_status"] == "UNAVAILABLE"
    ):
        raise HTTPException(409, "Volunteer is unavailable")
    if id:
        update(db, table, id, data)
    else:
        id = insert(db, table, data)
    for v in ids:
        refresh_volunteer(db, v)
    db.commit()
    return {"message": "Assignment saved", "assignment_id": id}


def assignment_delete(db, id):
    old = record(db, "volunteer_assignments", id, True)
    record(db, "volunteers", old["volunteer_id"], True)
    remove(db, "volunteer_assignments", id)
    refresh_volunteer(db, old["volunteer_id"])
    db.commit()
    return {"message": "Assignment deleted", "assignment_id": id}


def refresh_shelter(db, id):
    db.execute(
        text("""
UPDATE shelters
SET status=CASE WHEN status='CLOSED' THEN 'CLOSED' WHEN current_occupancy>=capacity THEN 'FULL' ELSE 'AVAILABLE'
           END
WHERE shelter_id=:id
"""),
        {"id": id},
    )


def registration_save(db, body, id=None):
    table = "shelter_registrations"
    old = record(db, table, id, True) if id else None
    data = body.model_dump()
    references(db, data)
    shelter_ids = sorted({data["shelter_id"]} | ({old["shelter_id"]} if old else set()))
    shelters = {s: record(db, "shelters", s, True) for s in shelter_ids}
    # Lock the person as well, so concurrent checkins to different shelters cannot duplicate.
    record(db, "users", data["user_id"], True)
    if old and old["status"] == "ACTIVE":
        s = shelters[old["shelter_id"]]
        if s["current_occupancy"] < 1:
            raise HTTPException(409, "Shelter occupancy is inconsistent")
        s["current_occupancy"] -= 1
    if data["status"] == "ACTIVE":
        duplicate = db.execute(
            text(
                "SELECT registration_id FROM shelter_registrations WHERE user_id=:user AND status='ACTIVE' AND registration_id!=:id FOR UPDATE"
            ),
            {"user": data["user_id"], "id": id or 0},
        ).first()
        if duplicate:
            raise HTTPException(409, "Person already has an active shelter registration")
        s = shelters[data["shelter_id"]]
        if s["status"] == "CLOSED":
            raise HTTPException(409, "Shelter is closed")
        if s["current_occupancy"] >= s["capacity"]:
            raise HTTPException(409, "Shelter is full")
        s["current_occupancy"] += 1
    data["check_in"] = data["check_in"] or (old["check_in"] if old else datetime.now())
    if data["status"] == "CHECKED_OUT":
        data["check_out"] = data["check_out"] or datetime.now()
    try:
        RegistrationCreate.model_validate(data)
    except ValidationError:
        raise HTTPException(422, "Invalid registration time range")
    if id:
        update(db, table, id, data)
    else:
        id = insert(db, table, data)
    for sid, s in shelters.items():
        update(db, "shelters", sid, {"current_occupancy": s["current_occupancy"]})
        refresh_shelter(db, sid)
    db.commit()
    return {"message": "Registration saved", "registration_id": id}


def registration_delete(db, id):
    old = record(db, "shelter_registrations", id, True)
    s = record(db, "shelters", old["shelter_id"], True)
    if old["status"] == "ACTIVE":
        if s["current_occupancy"] < 1:
            raise HTTPException(409, "Shelter occupancy is inconsistent")
        update(db, "shelters", old["shelter_id"], {"current_occupancy": s["current_occupancy"] - 1})
    remove(db, "shelter_registrations", id)
    refresh_shelter(db, old["shelter_id"])
    db.commit()
    return {"message": "Registration deleted", "registration_id": id}
