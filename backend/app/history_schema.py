"""Versioned, additive MySQL history objects; never log account secrets."""

from sqlalchemy import text, inspect

TABLES = {
    "resource_requests": (
        "request_id",
        ["disaster_id", "resource_id", "quantity", "status", "note"],
    ),
    "locations": ("location_id", ["state", "district", "city", "address"]),
    "disasters": ("disaster_id", ["location_id", "disaster_type", "title", "severity", "status"]),
    "shelters": ("shelter_id", ["location_id", "name", "capacity", "current_occupancy", "status"]),
    "users": ("user_id", ["full_name", "role", "status"]),
    "volunteers": ("volunteer_id", ["user_id", "skills", "availability_status"]),
    "resources": (
        "resource_id",
        [
            "resource_name",
            "category",
            "unit",
            "total_quantity",
            "available_quantity",
            "minimum_required",
        ],
    ),
    "resource_allocations": (
        "allocation_id",
        ["resource_id", "disaster_id", "shelter_id", "quantity", "status"],
    ),
    "volunteer_assignments": (
        "assignment_id",
        ["volunteer_id", "disaster_id", "shelter_id", "assignment_role", "status"],
    ),
    "shelter_registrations": (
        "registration_id",
        ["shelter_id", "user_id", "status", "check_in", "check_out"],
    ),
    "emergency_reports": (
        "report_id",
        [
            "location_id",
            "disaster_id",
            "severity",
            "status",
            "review_status",
            "review_reason",
            "reviewed_by",
            "reviewed_at",
        ],
    ),
}


# V4 extends future audit snapshots only. Existing history remains untouched.
REPLAY_FIELDS = {
    "disasters": ["description", "start_time", "end_time", "created_at"],
    "locations": ["latitude", "longitude", "coordinate_source"],
    "emergency_reports": ["disaster_type", "report_type", "description", "reported_at", "occurred_at", "resolved_at", "reported_location_text", "reported_latitude", "reported_longitude"],
    "resource_requests": ["created_at", "updated_at"],
    "resource_allocations": ["request_id", "allocation_date"],
    "volunteer_assignments": ["start_time", "end_time"],
}
for _table, _fields in REPLAY_FIELDS.items():
    TABLES[_table][1].extend(f for f in _fields if f not in TABLES[_table][1])

AUDIT_SQL = """
CREATE TABLE IF NOT EXISTS audit_history (audit_id BIGINT AUTO_INCREMENT PRIMARY KEY, entity VARCHAR(40) NOT NULL,
                                                                                                         record_id INT NOT NULL,
                                                                                                                       action ENUM('INSERT',

                                                                                                                                'UPDATE',
                                                                                                                                'DELETE') NOT NULL,
                                                                                                                                          actor_id INT NULL,
                                                                                                                                                       actor_name VARCHAR(100) NULL,
                                                                                                                                                                               before_data JSON NULL,
                                                                                                                                                                                                after_data JSON NULL,
                                                                                                                                                                                                                created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                                                                                                                                                                                                                                                         INDEX idx_audit_entity_record(entity,

                                                                                                                                                                                                                                                                 record_id,
                                                                                                                                                                                                                                                                 audit_id),
                                                                                                                                                                                                                                                               INDEX idx_audit_created(created_at,

                                                                                                                                                                                                                                                                       audit_id)) ENGINE=InnoDB
"""
LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS resource_movements (movement_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                                                                 resource_id INT NOT NULL,
                                                                                                 resource_name VARCHAR(100) NOT NULL,
                                                                                                                            unit VARCHAR(30) NOT NULL,
                                                                                                                                             movement_kind VARCHAR(30) NOT NULL,
                                                                                                                                                                       total_delta DECIMAL(12,

                                                                                                                                                                                     2) NOT NULL,
                                                                                                                                                                                        available_delta DECIMAL(12,

                                                                                                                                                                                                          2) NOT NULL,
                                                                                                                                                                                                             total_after DECIMAL(12,

                                                                                                                                                                                                                           2) NOT NULL,
                                                                                                                                                                                                                              available_after DECIMAL(12,

                                                                                                                                                                                                                                                2) NOT NULL,
                                                                                                                                                                                                                                                   allocation_id INT NULL,
                                                                                                                                                                                                                                                                     actor_id INT NULL,
                                                                                                                                                                                                                                                                                  actor_name VARCHAR(100) NULL,
                                                                                                                                                                                                                                                                                                          note VARCHAR(500) NULL,
                                                                                                                                                                                                                                                                                                                            created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                                                                                                                                                                                                                                                                                                                                                                     INDEX idx_movements_resource(resource_id,

                                                                                                                                                                                                                                                                                                                                                                             movement_id),
                                                                                                                                                                                                                                                                                                                                                                           INDEX idx_movements_created(created_at,

                                                                                                                                                                                                                                                                                                                                                                                   movement_id)) ENGINE=InnoDB
"""
# No cascading foreign keys: history must survive deletion of its source or actor.
VIEWS = {
    "dms_shelter_occupancy": """
SELECT s.shelter_id,s.name,l.city,s.status,s.capacity,s.current_occupancy,
       s.capacity-s.current_occupancy AS remaining_capacity,
       ROUND(100.0*s.current_occupancy/NULLIF(s.capacity,
                                         0), 2) AS occupancy_percent, COALESCE(r.active_registrations,
                                                                        0) AS active_registrations
FROM shelters s
JOIN locations l ON l.location_id=s.location_id
LEFT JOIN
  (SELECT shelter_id,COUNT(*) AS active_registrations
   FROM shelter_registrations
   WHERE status='ACTIVE'
   GROUP BY shelter_id) r ON r.shelter_id=s.shelter_id
""",
    "dms_disaster_allocations": """
SELECT d.disaster_id,d.title,d.status,l.city,
       COALESCE(a.allocation_count, 0) AS allocation_count, COALESCE(a.resource_types,
                                                              0) AS resource_types,
       COALESCE(v.active_volunteers, 0) AS active_volunteers
FROM disasters d
JOIN locations l ON l.location_id=d.location_id
LEFT JOIN
  (SELECT disaster_id,COUNT(*) AS allocation_count,COUNT(DISTINCT resource_id) AS resource_types
   FROM resource_allocations
   WHERE status!='CANCELLED'
   GROUP BY disaster_id) a ON a.disaster_id=d.disaster_id
LEFT JOIN
  (SELECT disaster_id,COUNT(DISTINCT volunteer_id) AS active_volunteers
   FROM volunteer_assignments
   WHERE status IN ('ASSIGNED','ACTIVE')
   GROUP BY disaster_id) v ON v.disaster_id=d.disaster_id
""",
    "dms_monthly_reports": """
SELECT DATE_FORMAT(er.reported_at, '%Y-%m') AS report_month, l.location_id,l.city,l.district,l.state,COUNT(*) AS total_reports,
       SUM(er.review_status='PENDING_REVIEW') AS pending_reports, SUM(er.review_status='CONFIRMED') AS confirmed_reports,
       SUM(er.review_status='REJECTED') AS rejected_reports, SUM(er.review_status='LEGACY') AS legacy_reports
FROM emergency_reports er
JOIN locations l ON l.location_id=er.location_id
GROUP BY DATE_FORMAT(er.reported_at, '%Y-%m'),l.location_id,l.city,l.district,l.state
""",
}


def snapshot(alias, fields):
    return "JSON_OBJECT(" + ",".join("'%s',%s.%s" % (f, alias, f) for f in fields) + ")"


def audit_trigger(table, action):
    key, fields = TABLES[table]
    old = snapshot("OLD", fields) if action != "INSERT" else "NULL"
    new = snapshot("NEW", fields) if action != "DELETE" else "NULL"
    alias = "OLD" if action == "DELETE" else "NEW"
    body = ""
    if action == "UPDATE":
        body = f"IF NOT ({old} <=> {new}) THEN "
    body += f"""INSERT INTO audit_history(entity,record_id,action,actor_id,actor_name,before_data,after_data)
    VALUES('{table}',{alias}.{key},'{action}',@dms_actor_id,@dms_actor_name,{old},{new});"""
    if action == "UPDATE":
        body += " END IF;"
    return f"CREATE TRIGGER dms_v12_audit_{table}_{action.lower()} AFTER {action} ON {table} FOR EACH ROW BEGIN {body} END"


def ledger_trigger(action):
    alias = "OLD" if action == "DELETE" else "NEW"
    total = (
        "NEW.total_quantity-OLD.total_quantity"
        if action == "UPDATE"
        else ("-OLD.total_quantity" if action == "DELETE" else "NEW.total_quantity")
    )
    available = (
        "NEW.available_quantity-OLD.available_quantity"
        if action == "UPDATE"
        else ("-OLD.available_quantity" if action == "DELETE" else "NEW.available_quantity")
    )
    after_total = "0" if action == "DELETE" else "NEW.total_quantity"
    after_available = "0" if action == "DELETE" else "NEW.available_quantity"
    kind = (
        "COALESCE(@dms_movement_kind,'INVENTORY_ADJUSTMENT')"
        if action == "UPDATE"
        else ("'REMOVAL'" if action == "DELETE" else "'OPENING'")
    )
    body = f"""INSERT INTO resource_movements(resource_id,resource_name,unit,movement_kind,total_delta,available_delta,total_after,available_after,allocation_id,actor_id,actor_name,note)
    VALUES({alias}.resource_id,{alias}.resource_name,{alias}.unit,{kind},{total},{available},{after_total},{after_available},@dms_allocation_id,@dms_actor_id,@dms_actor_name,@dms_movement_note);"""
    if action == "UPDATE":
        body = f"IF NEW.total_quantity!=OLD.total_quantity OR NEW.available_quantity!=OLD.available_quantity THEN {body} END IF;"
    return f"CREATE TRIGGER dms_v12_ledger_{action.lower()} AFTER {action} ON resources FOR EACH ROW BEGIN {body} END"


def install_history(conn):
    conn.exec_driver_sql(AUDIT_SQL)
    conn.exec_driver_sql(LEDGER_SQL)
    # Migration snapshots current stock only. NOT EXISTS makes reruns retain the original opening.
    conn.exec_driver_sql("""
INSERT INTO resource_movements(resource_id,
              resource_name, unit, movement_kind, total_delta, available_delta, total_after,
              available_after, note)
SELECT r.resource_id,r.resource_name,r.unit,'OPENING',r.total_quantity,r.available_quantity,
       r.total_quantity,r.available_quantity, 'Balance at history migration; earlier movements unknown'
FROM resources r
WHERE NOT EXISTS
    (SELECT 1
     FROM resource_movements m
     WHERE m.resource_id=r.resource_id)
""")
    existing = {
        row[0]
        for row in conn.execute(
            text(
                "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()"
            )
        )
    }
    for table in TABLES:
        for action in ["INSERT", "UPDATE", "DELETE"]:
            name = f"dms_v12_audit_{table}_{action.lower()}"
            if name not in existing:
                conn.exec_driver_sql(audit_trigger(table, action))
    for action in ["INSERT", "UPDATE", "DELETE"]:
        if f"dms_v12_ledger_{action.lower()}" not in existing:
            conn.exec_driver_sql(ledger_trigger(action))
    views = set(inspect(conn).get_view_names())
    for name, sql in VIEWS.items():
        if name not in views:
            conn.exec_driver_sql(f"CREATE VIEW {name} AS {sql}")


def install_v4_history(conn):
    """Refresh owned, outdated triggers during explicit maintenance migration.

    Trigger DDL auto-commits. Stop API writers, back up, rerun on interruption.
    No audit rows, tables, foreign keys or business data are removed.
    """
    existing = {r["TRIGGER_NAME"]:r["ACTION_STATEMENT"] for r in conn.execute(text(
        "SELECT TRIGGER_NAME,ACTION_STATEMENT FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()"
    )).mappings()}
    for table, fields in REPLAY_FIELDS.items():
        for action in ["INSERT","UPDATE","DELETE"]:
            name=f"dms_v12_audit_{table}_{action.lower()}"
            definition=existing.get(name,"")
            if definition and all("'"+field+"'" in definition for field in fields): continue
            if definition: conn.exec_driver_sql("DROP TRIGGER "+name)
            conn.exec_driver_sql(audit_trigger(table,action))
