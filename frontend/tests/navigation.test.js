import test from 'node:test';
import assert from 'node:assert/strict';
import { navigationFor } from '../src/navigation.js';
test('management order stays separate from advanced and contextual tools', () => {
  const nav = navigationFor('ADMIN');
  assert.deepEqual(
    nav.advanced.map((r) => r[0]),
    ['resource-intelligence', 'response-simulator'],
  );
  assert.equal(nav.main.at(-1)[0], 'users');
  assert(!nav.main.some((r) => ['audit-history', 'resource-movements', 'search'].includes(r[0])));
  assert(nav.routes.some((r) => r[0] === 'audit-history'));
  assert(nav.routes.some((r) => r[0] === 'resource-movements'));
  assert(nav.routes.some((r) => r[0] === 'search'));
});
test('manager cannot navigate to accounts; public workspace exposes only owned tracking', () => {
  assert(!navigationFor('DISASTER_MANAGER').routes.some((r) => r[0] === 'users'));
  const nav = navigationFor('PUBLIC_USER');
  assert.deepEqual(
    nav.main.map((r) => r[0]),
    ['overview', 'emergency-reports'],
  );
  assert.equal(nav.main[1][1], 'My Reports');
  assert.deepEqual(nav.advanced, []);
  assert.deepEqual(nav.routes, nav.main);
});
