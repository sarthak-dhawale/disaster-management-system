-- READ ONLY. Run after the explicit migration and optional seed, not a reset script.
SELECT 'disasters' AS entity,COUNT(*) AS demo_rows FROM disasters WHERE title LIKE '[DEMO V4]%'
UNION ALL SELECT 'shelters',COUNT(*) FROM shelters WHERE name LIKE '[DEMO V4]%'
UNION ALL SELECT 'resources',COUNT(*) FROM resources WHERE resource_name LIKE '[DEMO V4]%'
UNION ALL SELECT 'users',COUNT(*) FROM users WHERE email LIKE 'demo.v4.%@dms.example.com';

-- Each query below should return zero rows.
SELECT resource_id FROM resources WHERE available_quantity<0 OR available_quantity>total_quantity;
SELECT r.resource_id FROM resources r JOIN (
  SELECT resource_id,SUM(quantity) AS committed FROM resource_allocations WHERE status!='CANCELLED' GROUP BY resource_id
) a ON a.resource_id=r.resource_id WHERE a.committed>r.total_quantity-r.available_quantity;
SELECT shelter_id FROM shelters WHERE current_occupancy<0 OR current_occupancy>capacity;
SELECT s.shelter_id FROM shelters s JOIN (
  SELECT shelter_id,COUNT(*) AS registered FROM shelter_registrations WHERE status='ACTIVE' GROUP BY shelter_id
) a ON a.shelter_id=s.shelter_id WHERE a.registered>s.current_occupancy;
SELECT user_id FROM shelter_registrations WHERE status='ACTIVE' GROUP BY user_id HAVING COUNT(*)>1;
SELECT a.allocation_id FROM resource_allocations a WHERE (a.disaster_id IS NULL)=(a.shelter_id IS NULL);
SELECT a.assignment_id FROM volunteer_assignments a WHERE (a.disaster_id IS NULL)=(a.shelter_id IS NULL);
SELECT rr.request_id FROM resource_requests rr JOIN (
  SELECT request_id,SUM(quantity) AS allocated FROM resource_allocations WHERE status!='CANCELLED' GROUP BY request_id
) a ON a.request_id=rr.request_id WHERE a.allocated>rr.quantity;
SELECT a.allocation_id FROM resource_allocations a JOIN resource_requests rr ON rr.request_id=a.request_id
WHERE a.resource_id!=rr.resource_id OR a.disaster_id IS NULL OR a.disaster_id!=rr.disaster_id;
SELECT v.volunteer_id FROM volunteers v LEFT JOIN users u ON u.user_id=v.user_id WHERE u.user_id IS NULL;

-- All twelve demo disasters should be eligible for the unfiltered map.
SELECT d.disaster_id,d.title,d.status,l.state,l.latitude,l.longitude FROM disasters d
JOIN locations l ON l.location_id=d.location_id WHERE d.title LIKE '[DEMO V4]%' ORDER BY d.disaster_id;
SELECT COUNT(*) AS explicitly_demo_audit_events FROM audit_history
WHERE JSON_EXTRACT(after_data,'$.demonstration')=true;
