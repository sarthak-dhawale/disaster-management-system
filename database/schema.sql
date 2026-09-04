CREATE DATABASE IF NOT EXISTS disaster_management;

USE disaster_management;

SET FOREIGN_KEY_CHECKS = 0;

DROP TRIGGER IF EXISTS trg_allocation_target_insert;
DROP TRIGGER IF EXISTS trg_allocation_target_update;
DROP TRIGGER IF EXISTS trg_assignment_target_insert;
DROP TRIGGER IF EXISTS trg_assignment_target_update;

DROP TABLE IF EXISTS shelter_registrations;
DROP TABLE IF EXISTS volunteer_assignments;
DROP TABLE IF EXISTS resource_allocations;
DROP TABLE IF EXISTS emergency_reports;
DROP TABLE IF EXISTS volunteers;
DROP TABLE IF EXISTS shelters;
DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS disasters;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;


CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    role ENUM(
        'ADMIN',
        'DISASTER_MANAGER',
        'VOLUNTEER',
        'PUBLIC_USER'
    ) NOT NULL DEFAULT 'PUBLIC_USER',
    status ENUM(
        'ACTIVE',
        'INACTIVE',
        'SUSPENDED'
    ) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE disasters (
    disaster_id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    reported_by INT,
    disaster_type ENUM(
        'FLOOD',
        'EARTHQUAKE',
        'CYCLONE',
        'LANDSLIDE',
        'FIRE',
        'DROUGHT',
        'TSUNAMI',
        'OTHER'
    ) NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    severity ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'CRITICAL'
    ) NOT NULL,
    status ENUM(
        'REPORTED',
        'ACTIVE',
        'CONTAINED',
        'RESOLVED'
    ) NOT NULL DEFAULT 'REPORTED',
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_disaster_location
        FOREIGN KEY (location_id)
        REFERENCES locations(location_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_disaster_reporter
        FOREIGN KEY (reported_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);


CREATE TABLE shelters (
    shelter_id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    capacity INT NOT NULL,
    current_occupancy INT NOT NULL DEFAULT 0,
    contact_phone VARCHAR(15),
    status ENUM(
        'AVAILABLE',
        'FULL',
        'CLOSED'
    ) NOT NULL DEFAULT 'AVAILABLE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_shelter_location
        FOREIGN KEY (location_id)
        REFERENCES locations(location_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_shelter_capacity
        CHECK (capacity > 0),

    CONSTRAINT chk_shelter_occupancy
        CHECK (
            current_occupancy >= 0
            AND current_occupancy <= capacity
        )
);


CREATE TABLE volunteers (
    volunteer_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    skills VARCHAR(255),
    availability_status ENUM(
        'AVAILABLE',
        'ASSIGNED',
        'UNAVAILABLE'
    ) NOT NULL DEFAULT 'AVAILABLE',
    emergency_contact VARCHAR(100),
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_volunteer_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE TABLE resources (
    resource_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_name VARCHAR(100) NOT NULL,
    category ENUM(
        'FOOD',
        'WATER',
        'MEDICINE',
        'CLOTHING',
        'EQUIPMENT',
        'SHELTER_SUPPLIES',
        'OTHER'
    ) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    total_quantity DECIMAL(12, 2) NOT NULL DEFAULT 0,
    available_quantity DECIMAL(12, 2) NOT NULL DEFAULT 0,
    minimum_required DECIMAL(12, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_resource_total
        CHECK (total_quantity >= 0),

    CONSTRAINT chk_resource_available
        CHECK (
            available_quantity >= 0
            AND available_quantity <= total_quantity
        ),

    CONSTRAINT chk_resource_minimum
        CHECK (minimum_required >= 0)
);


CREATE TABLE resource_allocations (
    allocation_id INT AUTO_INCREMENT PRIMARY KEY,
    resource_id INT NOT NULL,
    disaster_id INT,
    shelter_id INT,
    allocated_by INT,
    quantity DECIMAL(12, 2) NOT NULL,
    allocation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM(
        'ALLOCATED',
        'DELIVERED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'ALLOCATED',

    CONSTRAINT fk_allocation_resource
        FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_allocation_disaster
        FOREIGN KEY (disaster_id)
        REFERENCES disasters(disaster_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_allocation_shelter
        FOREIGN KEY (shelter_id)
        REFERENCES shelters(shelter_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_allocation_user
        FOREIGN KEY (allocated_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT chk_allocation_quantity
        CHECK (quantity > 0)
);


CREATE TABLE emergency_reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT,
    location_id INT NOT NULL,
    reported_by INT,
    report_type ENUM(
        'MEDICAL',
        'TRAPPED_PERSON',
        'MISSING_PERSON',
        'INFRASTRUCTURE_DAMAGE',
        'FIRE',
        'FLOODING',
        'OTHER'
    ) NOT NULL,
    description TEXT NOT NULL,
    severity ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'CRITICAL'
    ) NOT NULL,
    status ENUM(
        'PENDING',
        'IN_PROGRESS',
        'RESOLVED',
        'REJECTED'
    ) NOT NULL DEFAULT 'PENDING',
    reported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,

    CONSTRAINT fk_report_disaster
        FOREIGN KEY (disaster_id)
        REFERENCES disasters(disaster_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CONSTRAINT fk_report_location
        FOREIGN KEY (location_id)
        REFERENCES locations(location_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_report_user
        FOREIGN KEY (reported_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);


CREATE TABLE volunteer_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    volunteer_id INT NOT NULL,
    disaster_id INT,
    shelter_id INT,
    assigned_by INT,
    assignment_role VARCHAR(100) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    status ENUM(
        'ASSIGNED',
        'ACTIVE',
        'COMPLETED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'ASSIGNED',

    CONSTRAINT fk_assignment_volunteer
        FOREIGN KEY (volunteer_id)
        REFERENCES volunteers(volunteer_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_assignment_disaster
        FOREIGN KEY (disaster_id)
        REFERENCES disasters(disaster_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_assignment_shelter
        FOREIGN KEY (shelter_id)
        REFERENCES shelters(shelter_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_assignment_user
        FOREIGN KEY (assigned_by)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);


CREATE TABLE shelter_registrations (
    registration_id INT AUTO_INCREMENT PRIMARY KEY,
    shelter_id INT NOT NULL,
    user_id INT NOT NULL,
    check_in DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    check_out DATETIME,
    status ENUM(
        'ACTIVE',
        'CHECKED_OUT'
    ) NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT fk_registration_shelter
        FOREIGN KEY (shelter_id)
        REFERENCES shelters(shelter_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_registration_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


CREATE INDEX idx_disasters_location
    ON disasters(location_id);

CREATE INDEX idx_disasters_status
    ON disasters(status);

CREATE INDEX idx_disasters_severity
    ON disasters(severity);

CREATE INDEX idx_shelters_location
    ON shelters(location_id);

CREATE INDEX idx_resources_category
    ON resources(category);

CREATE INDEX idx_reports_location
    ON emergency_reports(location_id);

CREATE INDEX idx_reports_status
    ON emergency_reports(status);

CREATE INDEX idx_allocations_resource
    ON resource_allocations(resource_id);

CREATE INDEX idx_assignments_volunteer
    ON volunteer_assignments(volunteer_id);

CREATE INDEX idx_registrations_shelter
    ON shelter_registrations(shelter_id);


DELIMITER $$

CREATE TRIGGER trg_allocation_target_insert
BEFORE INSERT ON resource_allocations
FOR EACH ROW
BEGIN
    IF
        (NEW.disaster_id IS NULL AND NEW.shelter_id IS NULL)
        OR
        (NEW.disaster_id IS NOT NULL AND NEW.shelter_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT =
        'Allocation must target either a disaster or a shelter, not both';
    END IF;
END$$


CREATE TRIGGER trg_allocation_target_update
BEFORE UPDATE ON resource_allocations
FOR EACH ROW
BEGIN
    IF
        (NEW.disaster_id IS NULL AND NEW.shelter_id IS NULL)
        OR
        (NEW.disaster_id IS NOT NULL AND NEW.shelter_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT =
        'Allocation must target either a disaster or a shelter, not both';
    END IF;
END$$


CREATE TRIGGER trg_assignment_target_insert
BEFORE INSERT ON volunteer_assignments
FOR EACH ROW
BEGIN
    IF
        (NEW.disaster_id IS NULL AND NEW.shelter_id IS NULL)
        OR
        (NEW.disaster_id IS NOT NULL AND NEW.shelter_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT =
        'Assignment must target either a disaster or a shelter, not both';
    END IF;
END$$


CREATE TRIGGER trg_assignment_target_update
BEFORE UPDATE ON volunteer_assignments
FOR EACH ROW
BEGIN
    IF
        (NEW.disaster_id IS NULL AND NEW.shelter_id IS NULL)
        OR
        (NEW.disaster_id IS NOT NULL AND NEW.shelter_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT =
        'Assignment must target either a disaster or a shelter, not both';
    END IF;
END$$

DELIMITER ;