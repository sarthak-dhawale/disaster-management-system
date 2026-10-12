"""Guarded additive V2 DDL. Inspect and back up before invoking setup_db migrate."""

from sqlalchemy import inspect

REQUEST_SQL = """
CREATE TABLE IF NOT EXISTS resource_requests
  (request_id INT AUTO_INCREMENT PRIMARY KEY, disaster_id INT NOT NULL, resource_id INT NOT NULL,
                                                                                        quantity DECIMAL(12,

                                                                                                   2) NOT NULL,
                                                                                                      note VARCHAR(500) NULL,
                                                                                                                        status ENUM('OPEN',

                                                                                                                                 'CANCELLED') NOT NULL DEFAULT 'OPEN',
                                                                                                                                                               created_by INT NULL,
                                                                                                                                                                              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                                                                                                                                                                                                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                                                                                                                                                                                                                                                                      CONSTRAINT chk_request_quantity CHECK(quantity>0),
                                                                                                                                                                                                                                                                                                                      CONSTRAINT fk_request_disaster
   FOREIGN KEY(disaster_id) REFERENCES disasters(disaster_id) ON DELETE RESTRICT, CONSTRAINT fk_request_resource
   FOREIGN KEY(resource_id) REFERENCES resources(resource_id) ON DELETE RESTRICT, CONSTRAINT fk_request_creator
   FOREIGN KEY(created_by) REFERENCES users(user_id) ON DELETE
   SET NULL, INDEX idx_requests_target(disaster_id,
                     resource_id, status)) ENGINE=InnoDB
"""


def add_columns(conn, table, definitions):
    columns = {c["name"] for c in inspect(conn).get_columns(table)}
    for name, definition in definitions.items():
        if name not in columns:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def install_v2(conn):
    add_columns(
        conn,
        "locations",
        {
            "coordinate_source": "VARCHAR(30) NOT NULL DEFAULT 'LEGACY'",
            "location_key": "CHAR(64) NULL",
        },
    )
    indexes = {i["name"] for i in inspect(conn).get_indexes("locations")}
    if "uq_location_key_v2" not in indexes:
        conn.exec_driver_sql("CREATE UNIQUE INDEX uq_location_key_v2 ON locations(location_key)")
    # Existing rows/coordinates remain untouched; old duplicates retain NULL keys.
    add_columns(
        conn,
        "emergency_reports",
        {
            "reported_location_text": "VARCHAR(500) NULL",
            "reported_latitude": "DECIMAL(10,7) NULL",
            "reported_longitude": "DECIMAL(10,7) NULL",
            "coordinate_source": "VARCHAR(30) NOT NULL DEFAULT 'LEGACY'",
        },
    )
    location = next(
        c for c in inspect(conn).get_columns("emergency_reports") if c["name"] == "location_id"
    )
    if not location["nullable"]:
        conn.exec_driver_sql("ALTER TABLE emergency_reports MODIFY COLUMN location_id INT NULL")
    conn.exec_driver_sql(REQUEST_SQL)
    add_columns(
        conn, "resource_allocations", {"request_id": "INT NULL", "approval_key": "VARCHAR(64) NULL"}
    )
    indexes = {i["name"] for i in inspect(conn).get_indexes("resource_allocations")}
    if "uq_allocation_approval_v2" not in indexes:
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_allocation_approval_v2 ON resource_allocations(approval_key)"
        )
    foreign = {f["name"] for f in inspect(conn).get_foreign_keys("resource_allocations")}
    if "fk_allocation_request_v2" not in foreign:
        conn.exec_driver_sql("""
ALTER TABLE resource_allocations ADD CONSTRAINT fk_allocation_request_v2
FOREIGN KEY(request_id) REFERENCES resource_requests(request_id) ON
DELETE RESTRICT
""")
