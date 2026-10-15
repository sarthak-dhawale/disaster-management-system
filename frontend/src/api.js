export const API = import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8001';
export const cache = new Map();
export const listeners = new Set();
export function invalidate() {
  cache.clear();
  listeners.forEach((fn) => fn());
}
export async function request(path, options = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) controller.abort();
  const timer = setTimeout(abort, 30000);
  try {
    const response = await fetch(API + path, {
      credentials: 'include',
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.method && !['GET', 'HEAD'].includes(options.method)
          ? { 'X-DMS-Request': '1' }
          : {}),
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && !path.includes('/auth/'))
        window.dispatchEvent(new Event('dms-session-expired'));
      const error = new Error(data.detail || `Request failed (${response.status})`);
      error.fields = data.errors || [];
      error.status = response.status;
      throw error;
    }
    return data;
  } catch (error) {
    if (error.name === 'TypeError')
      throw new Error('Cannot reach the configured API. Check the backend and MySQL connection.');
    throw error;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', abort);
  }
}
export function subscribe(path) {
  let entry = cache.get(path);
  if (!entry || (entry.data && Date.now() - entry.time > 15000)) {
    const controller = new AbortController();
    entry = { refs: 0, controller, time: Date.now() };
    entry.promise = request(path, { signal: controller.signal })
      .then((data) => {
        entry.data = data;
        entry.time = Date.now();
        return data;
      })
      .catch((error) => {
        if (cache.get(path) === entry) cache.delete(path);
        throw error;
      });
    cache.set(path, entry);
  }
  entry.refs++;
  return {
    promise: entry.data ? Promise.resolve(entry.data) : entry.promise,
    release() {
      entry.refs--;
      setTimeout(() => {
        if (entry.refs === 0 && !entry.data) {
          entry.controller.abort();
          if (cache.get(path) === entry) cache.delete(path);
        }
      }, 0);
    },
  };
}
export function query(values = {}) {
  return new URLSearchParams(
    Object.entries(values).filter(([, v]) => v !== '' && v != null),
  ).toString();
}
// Traverse every server page. Never show a truncated map as a complete result.
export async function allIncidents(params, signal) {
  const items = [], seen = new Set();
  let offset = 0;
  while (true) {
    const page = await request(`/api/intelligence/incidents?${params}&stable_order=true&limit=500&offset=${offset}`, { signal });
    for (const item of page.items) {
      const key = `${item.kind}:${item.id}`;
      if (!seen.has(key)) { seen.add(key); items.push(item); }
    }
    offset += page.items.length;
    if (!page.has_more) break;
    if (!page.items.length) throw new Error('Incident pagination did not advance. Refresh the map.');
  }
  items.sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0) || String(b.incident_time || '').localeCompare(String(a.incident_time || '')) || b.id - a.id);
  return { items, total: items.length };
}
export async function download(path) {
  const response = await fetch(API + path, { credentials: 'include' });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Export failed');
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download =
    response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1] ||
    `dms-report-${new Date().toISOString().slice(0, 10)}.${path.includes('pdf') ? 'pdf' : 'csv'}`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
