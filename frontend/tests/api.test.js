import test from 'node:test';
import assert from 'node:assert/strict';
import { subscribe, cache, query, request } from '../src/api.js';
globalThis.window = new EventTarget();
test('independent subscribers share one request and receive the same result', async () => {
  cache.clear();
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return new Response(JSON.stringify({ total: 7 }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  const a = subscribe('/fixture-shared'),
    b = subscribe('/fixture-shared');
  assert.deepEqual(await a.promise, { total: 7 });
  assert.deepEqual(await b.promise, { total: 7 });
  assert.equal(calls, 1);
  a.release();
  b.release();
  const c = subscribe('/fixture-shared');
  assert.deepEqual(await c.promise, { total: 7 });
  assert.equal(calls, 1);
  c.release();
});
test('unmounted last subscriber aborts its pending request', async () => {
  cache.clear();
  let aborted = false;
  globalThis.fetch = (_url, options) =>
    new Promise((resolve, reject) =>
      options.signal.addEventListener('abort', () => {
        aborted = true;
        reject(new DOMException('Aborted', 'AbortError'));
      }),
    );
  const subscription = subscribe('/fixture-abort');
  const failure = subscription.promise.catch((e) => e);
  subscription.release();
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(aborted, true);
  assert.equal((await failure).name, 'AbortError');
});
test('server validation errors retain field locations and no fake fallback records', async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: 'Invalid quantity',
        errors: [{ loc: ['body', 'quantity'], msg: 'Must be positive' }],
      }),
      { status: 422 },
    );
  await assert.rejects(
    request('/fixture-error', { method: 'POST', body: '{}' }),
    (e) => e.message === 'Invalid quantity' && e.fields[0].loc[1] === 'quantity',
  );
});
test('filter query preserves zero and safely encodes user text', () => {
  const parsed = new URLSearchParams(
    query({ q: 'A & B', offset: 0, state: '', resource_id: null }),
  );
  assert.equal(parsed.get('q'), 'A & B');
  assert.equal(parsed.get('offset'), '0');
  assert.equal(parsed.has('state'), false);
});
