import test from 'node:test';
import assert from 'node:assert/strict';
import { advanceEvent, playbackDelay } from '../src/replay-controls.js';
import { modules } from '../src/modules.js';
import { navigationFor } from '../src/navigation.js';
test('playback seeking is bounded and speeds are proportional', () => {
  assert.equal(advanceEvent(0, 5, -1), 0);
  assert.equal(advanceEvent(4, 5), 4);
  assert.equal(advanceEvent(0, 5, 3), 3);
  assert.equal(advanceEvent(0, 0), 0);
  assert.equal(playbackDelay(4), playbackDelay(1) / 4);
  assert.equal(playbackDelay(2), playbackDelay(1) / 2);
});
test('actual primary keys lead the three management tables', () => {
  for (const module of ['disasters','shelters','volunteers']) assert.equal(modules[module].columns[0].key, modules[module].id);
});
test('replay is available only to existing response roles', () => {
  for (const role of ['ADMIN','DISASTER_MANAGER']) assert(navigationFor(role).routes.some(([route]) => route === 'disaster-replay'));
  for (const role of ['VOLUNTEER','PUBLIC_USER']) assert(!navigationFor(role).routes.some(([route]) => route === 'disaster-replay'));
});
