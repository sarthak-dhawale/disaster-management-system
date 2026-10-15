export const operations = [
  ['overview', 'Overview', 'grid'],
  ['disasters', 'Disasters', 'alert'],
  ['emergency-reports', 'Emergency reports', 'file'],
  ['shelters', 'Shelters', 'home'],
  ['volunteers', 'Volunteers', 'people'],
  ['resources', 'Resources', 'box'],
  ['reports', 'Detailed reports', 'file'],
  ['resource-allocations', 'Resource allocations', 'box'],
  ['volunteer-assignments', 'Volunteer assignments', 'people'],
  ['shelter-registrations', 'Shelter registrations', 'home'],
  ['locations', 'Locations', 'map'],
  ['users', 'Users', 'people'],
];
export const advanced = [
  ['disaster-replay', 'Disaster Replay Studio', 'file'],
  ['resource-intelligence', 'Resource Intelligence', 'chart'],
  ['response-simulator', 'Response Simulator', 'chart'],
];
const contextual = [
  ['audit-history', 'Audit history', 'file'],
  ['resource-movements', 'Resource movements', 'box'],
  ['search', 'Search', 'search'],
];
export function navigationFor(role) {
  const manager = ['ADMIN', 'DISASTER_MANAGER'].includes(role);
  const main = manager
    ? operations.filter(([key]) => key !== 'users' || role === 'ADMIN')
    : [operations[0], ['emergency-reports', 'My Reports', 'file']];
  return {
    main,
    advanced: manager ? advanced : [],
    routes: manager ? [...main, ...advanced, ...contextual] : main,
  };
}
