USE disaster_management;

SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM shelter_registrations;
DELETE FROM volunteer_assignments;
DELETE FROM resource_allocations;
DELETE FROM emergency_reports;
DELETE FROM volunteers;
DELETE FROM shelters;
DELETE FROM resources;
DELETE FROM disasters;
DELETE FROM locations;
DELETE FROM users;

SET FOREIGN_KEY_CHECKS = 1;


-- =====================================================
-- USERS
-- =====================================================

INSERT INTO users
(full_name, email, password_hash, phone, role, status)
VALUES
('Arjun Mehta', 'arjun.admin@dms.com', 'hashed_password_1', '9876543210', 'ADMIN', 'ACTIVE'),
('Priya Sharma', 'priya.manager@dms.com', 'hashed_password_2', '9876543211', 'DISASTER_MANAGER', 'ACTIVE'),
('Rahul Patil', 'rahul.volunteer@dms.com', 'hashed_password_3', '9876543212', 'VOLUNTEER', 'ACTIVE'),
('Sneha Kulkarni', 'sneha.volunteer@dms.com', 'hashed_password_4', '9876543213', 'VOLUNTEER', 'ACTIVE'),
('Amit Joshi', 'amit.volunteer@dms.com', 'hashed_password_5', '9876543214', 'VOLUNTEER', 'ACTIVE'),
('Neha Deshmukh', 'neha.user@dms.com', 'hashed_password_6', '9876543215', 'PUBLIC_USER', 'ACTIVE'),
('Rohan Shah', 'rohan.user@dms.com', 'hashed_password_7', '9876543216', 'PUBLIC_USER', 'ACTIVE'),
('Kavya Nair', 'kavya.user@dms.com', 'hashed_password_8', '9876543217', 'PUBLIC_USER', 'ACTIVE'),
('Vikram Singh', 'vikram.manager@dms.com', 'hashed_password_9', '9876543218', 'DISASTER_MANAGER', 'ACTIVE'),
('Ananya Rao', 'ananya.user@dms.com', 'hashed_password_10', '9876543219', 'PUBLIC_USER', 'ACTIVE');


-- =====================================================
-- LOCATIONS
-- =====================================================

INSERT INTO locations
(state, district, city, address, latitude, longitude)
VALUES
('Maharashtra', 'Pune', 'Pune', 'Kharadi Main Road', 18.5514, 73.9360),
('Maharashtra', 'Kolhapur', 'Kolhapur', 'Shivaji Chowk', 16.7050, 74.2433),
('Kerala', 'Ernakulam', 'Kochi', 'Marine Drive', 9.9816, 76.2999),
('Odisha', 'Puri', 'Puri', 'Grand Road', 19.8135, 85.8312),
('Gujarat', 'Ahmedabad', 'Ahmedabad', 'Sabarmati Area', 23.0225, 72.5714),
('Assam', 'Kamrup Metropolitan', 'Guwahati', 'Beltola Road', 26.1445, 91.7362),
('Tamil Nadu', 'Chennai', 'Chennai', 'Adyar Main Road', 13.0067, 80.2206),
('Uttarakhand', 'Dehradun', 'Dehradun', 'Rajpur Road', 30.3165, 78.0322),
('West Bengal', 'South 24 Parganas', 'Kolkata', 'Diamond Harbour Road', 22.4980, 88.2980),
('Karnataka', 'Bengaluru Urban', 'Bengaluru', 'Whitefield Main Road', 12.9698, 77.7500);


-- =====================================================
-- DISASTERS
-- =====================================================

INSERT INTO disasters
(location_id, reported_by, disaster_type, title, description, severity, status, start_time, end_time)
VALUES
(1, 2, 'FLOOD', 'Pune Urban Flooding', 'Heavy rainfall caused flooding in low-lying areas of Pune.', 'HIGH', 'ACTIVE', '2026-09-01 08:30:00', NULL),

(2, 2, 'FLOOD', 'Kolhapur River Flood', 'Rising river levels have affected residential areas near the river.', 'CRITICAL', 'ACTIVE', '2026-08-30 06:00:00', NULL),

(3, 9, 'CYCLONE', 'Kochi Coastal Storm', 'Strong winds and heavy rainfall affected coastal regions.', 'HIGH', 'CONTAINED', '2026-08-25 14:00:00', '2026-08-28 18:00:00'),

(4, 9, 'CYCLONE', 'Puri Cyclonic Storm', 'Cyclonic winds damaged infrastructure in coastal villages.', 'CRITICAL', 'ACTIVE', '2026-09-02 03:00:00', NULL),

(5, 2, 'EARTHQUAKE', 'Ahmedabad Earthquake', 'Moderate earthquake caused structural damage in several buildings.', 'HIGH', 'CONTAINED', '2026-08-20 11:15:00', '2026-08-22 09:00:00'),

(6, 9, 'FLOOD', 'Guwahati Flash Flood', 'Flash flooding disrupted transportation and residential areas.', 'HIGH', 'ACTIVE', '2026-09-01 05:30:00', NULL),

(7, 2, 'CYCLONE', 'Chennai Coastal Storm', 'Heavy rainfall and strong winds affected coastal neighbourhoods.', 'MEDIUM', 'RESOLVED', '2026-08-10 10:00:00', '2026-08-12 16:00:00'),

(8, 9, 'LANDSLIDE', 'Dehradun Landslide', 'Heavy rainfall triggered landslides on a hill road.', 'HIGH', 'ACTIVE', '2026-09-03 07:00:00', NULL);


-- =====================================================
-- SHELTERS
-- =====================================================

INSERT INTO shelters
(location_id, name, capacity, current_occupancy, contact_phone, status)
VALUES
(1, 'Pune Relief Centre', 500, 325, '9123456701', 'AVAILABLE'),
(2, 'Kolhapur Emergency Shelter', 800, 760, '9123456702', 'AVAILABLE'),
(3, 'Kochi Coastal Relief Camp', 600, 280, '9123456703', 'AVAILABLE'),
(4, 'Puri Cyclone Shelter', 1000, 950, '9123456704', 'AVAILABLE'),
(5, 'Ahmedabad Community Shelter', 400, 120, '9123456705', 'AVAILABLE'),
(6, 'Guwahati Flood Relief Centre', 700, 690, '9123456706', 'AVAILABLE'),
(7, 'Chennai Relief Camp', 450, 0, '9123456707', 'AVAILABLE'),
(8, 'Dehradun Hill Relief Centre', 300, 210, '9123456708', 'AVAILABLE');


-- =====================================================
-- VOLUNTEERS
-- =====================================================

INSERT INTO volunteers
(user_id, skills, availability_status, emergency_contact)
VALUES
(3, 'First Aid, Rescue Operations', 'ASSIGNED', '9000000001'),
(4, 'Medical Assistance, First Aid', 'AVAILABLE', '9000000002'),
(5, 'Food Distribution, Logistics', 'ASSIGNED', '9000000003');


-- =====================================================
-- RESOURCES
-- =====================================================

INSERT INTO resources
(resource_name, category, unit, total_quantity, available_quantity, minimum_required)
VALUES
('Drinking Water', 'WATER', 'litres', 50000, 32500, 10000),
('Rice', 'FOOD', 'kg', 15000, 9200, 3000),
('First Aid Kits', 'MEDICINE', 'kits', 1000, 620, 200),
('Blankets', 'CLOTHING', 'pieces', 5000, 3100, 1000),
('Emergency Tents', 'SHELTER_SUPPLIES', 'pieces', 800, 450, 150),
('Portable Generators', 'EQUIPMENT', 'units', 100, 65, 20),
('Ready-to-Eat Meals', 'FOOD', 'packs', 20000, 12500, 4000),
('Medical Oxygen Cylinders', 'MEDICINE', 'cylinders', 300, 180, 50);


-- =====================================================
-- RESOURCE ALLOCATIONS
-- =====================================================

INSERT INTO resource_allocations
(resource_id, disaster_id, shelter_id, allocated_by, quantity, status)
VALUES
(1, 1, NULL, 2, 5000, 'DELIVERED'),
(2, 1, NULL, 2, 2000, 'DELIVERED'),
(3, 2, NULL, 2, 150, 'ALLOCATED'),
(4, NULL, 2, 2, 500, 'DELIVERED'),
(5, 4, NULL, 9, 100, 'ALLOCATED'),
(6, 6, NULL, 9, 20, 'DELIVERED'),
(7, NULL, 4, 9, 3000, 'ALLOCATED'),
(8, 8, NULL, 9, 30, 'ALLOCATED');


-- =====================================================
-- EMERGENCY REPORTS
-- =====================================================

INSERT INTO emergency_reports
(disaster_id, location_id, reported_by, report_type, description, severity, status)
VALUES
(1, 1, 6, 'FLOODING', 'Water level has increased near residential buildings.', 'HIGH', 'IN_PROGRESS'),

(1, 1, 7, 'TRAPPED_PERSON', 'Two residents are trapped inside a flooded house.', 'CRITICAL', 'IN_PROGRESS'),

(2, 2, 8, 'INFRASTRUCTURE_DAMAGE', 'Road bridge has suffered severe structural damage.', 'HIGH', 'PENDING'),

(4, 4, 10, 'MEDICAL', 'Several injured people require immediate medical assistance.', 'CRITICAL', 'IN_PROGRESS'),

(6, 6, 6, 'MISSING_PERSON', 'A resident has been missing since the flooding began.', 'HIGH', 'PENDING'),

(8, 8, 7, 'INFRASTRUCTURE_DAMAGE', 'Major landslide has blocked the main road.', 'HIGH', 'IN_PROGRESS'),

(3, 3, 8, 'FLOODING', 'Coastal area experienced severe waterlogging.', 'MEDIUM', 'RESOLVED'),

(5, 5, 10, 'INFRASTRUCTURE_DAMAGE', 'Several buildings developed structural cracks.', 'HIGH', 'RESOLVED');


-- =====================================================
-- VOLUNTEER ASSIGNMENTS
-- =====================================================

INSERT INTO volunteer_assignments
(volunteer_id, disaster_id, shelter_id, assigned_by, assignment_role, start_time, end_time, status)
VALUES
(1, 1, NULL, 2, 'Rescue Team Member', '2026-09-01 10:00:00', NULL, 'ACTIVE'),

(2, 2, NULL, 2, 'Medical Support', '2026-09-01 08:00:00', NULL, 'ACTIVE'),

(3, NULL, 4, 9, 'Food Distribution Coordinator', '2026-09-02 09:00:00', NULL, 'ACTIVE'),

(1, 6, NULL, 9, 'Flood Rescue Volunteer', '2026-09-01 12:00:00', NULL, 'ASSIGNED'),

(2, 8, NULL, 9, 'First Aid Volunteer', '2026-09-03 10:00:00', NULL, 'ACTIVE');


-- =====================================================
-- SHELTER REGISTRATIONS
-- =====================================================

INSERT INTO shelter_registrations
(shelter_id, user_id, check_in, check_out, status)
VALUES
(1, 6, '2026-09-01 11:00:00', NULL, 'ACTIVE'),
(1, 7, '2026-09-01 12:30:00', NULL, 'ACTIVE'),
(2, 8, '2026-08-30 10:00:00', NULL, 'ACTIVE'),
(2, 10, '2026-08-30 11:30:00', NULL, 'ACTIVE'),
(4, 6, '2026-09-02 06:00:00', NULL, 'ACTIVE'),
(4, 7, '2026-09-02 07:30:00', NULL, 'ACTIVE'),
(5, 8, '2026-08-20 15:00:00', '2026-08-22 10:00:00', 'CHECKED_OUT'),
(3, 10, '2026-08-25 18:00:00', '2026-08-28 17:00:00', 'CHECKED_OUT');


-- =====================================================
-- VERIFY DATA
-- =====================================================

SELECT 'users' AS table_name, COUNT(*) AS record_count
FROM users

UNION ALL

SELECT 'locations', COUNT(*)
FROM locations

UNION ALL

SELECT 'disasters', COUNT(*)
FROM disasters

UNION ALL

SELECT 'shelters', COUNT(*)
FROM shelters

UNION ALL

SELECT 'volunteers', COUNT(*)
FROM volunteers

UNION ALL

SELECT 'resources', COUNT(*)
FROM resources

UNION ALL

SELECT 'resource_allocations', COUNT(*)
FROM resource_allocations

UNION ALL

SELECT 'emergency_reports', COUNT(*)
FROM emergency_reports

UNION ALL

SELECT 'volunteer_assignments', COUNT(*)
FROM volunteer_assignments

UNION ALL

SELECT 'shelter_registrations', COUNT(*)
FROM shelter_registrations;