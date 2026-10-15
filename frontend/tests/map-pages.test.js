import test from 'node:test';
import assert from 'node:assert/strict';
import { allIncidents } from '../src/api.js';
globalThis.window = new EventTarget();
test('map follows every API page including records after the first 500', async () => {
  const seen = [];
  globalThis.fetch = async (url) => {
    const params = new URL(url).searchParams;
    assert.equal(params.get('stable_order'), 'true');
    const offset = Number(params.get('offset')); seen.push(offset);
    const count = offset === 1000 ? 7 : 500;
    return new Response(JSON.stringify({ items: Array.from({ length: count }, (_, i) => ({ kind: 'disaster', id: offset + i + 1 })), has_more: offset < 1000 }));
  };
  const result = await allIncidents('include_resolved=true');
  assert.equal(result.items.length, 1007); assert.deepEqual(seen, [0, 500, 1000]);
});
test('broken pagination fails visibly instead of claiming a complete map', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ items: [], has_more: true }));
  await assert.rejects(allIncidents(''), /pagination did not advance/);
});
