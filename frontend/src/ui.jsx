import { useEffect, useRef, useState } from 'react';
import { download, invalidate } from './api';
export const label = (value) =>
  String(value ?? '—')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
export function Icon({ name = 'grid' }) {
  const paths = {
    sun: 'M12 3v2m0 14v2M3 12h2m14 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2',
    logout: 'M9 4H4v16h5m5-4 4-4-4-4m-7 4h11',
    grid: 'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z',
    alert: 'm12 3 10 18H2zM12 9v5m0 3v1',
    box: 'm3 7 9-4 9 4v10l-9 4-9-4zm0 0 9 4 9-4m-9 4v10',
    people:
      'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m18 0v-2a4 4 0 0 0-3-4M9 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8m8 0a4 4 0 0 1 0 8',
    map: 'm3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3zm6-3v15m6-12v15',
    chart: 'M4 3v18h17M8 16v-5m5 5V7m5 9V4',
    file: 'M6 2h8l4 4v16H6zm8 0v5h4M9 12h6m-6 4h6',
    search: 'M10 3a7 7 0 1 1 0 14 7 7 0 0 1 0-14m5 12 6 6',
    menu: 'M3 6h18M3 12h18M3 18h18',
    close: 'm5 5 14 14M5 19 19 5',
    home: 'm3 10 9-7 9 7v11H3zm6 11v-8h6v8',
  };
  return (
    <svg
      aria-hidden="true"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name] || paths.file} />
      {name === 'sun' && <circle cx="12" cy="12" r="4" />}
    </svg>
  );
}
export function State({ loading, error, empty, children }) {
  if (loading)
    return (
      <div className="loading" role="status">
        <span className="spinner" />
        Loading records…
      </div>
    );
  if (error)
    return (
      <div className="notice error" role="alert">
        <strong>Unable to load records</strong>
        <p>{error.message}</p>
        <button onClick={invalidate}>Retry</button>
      </div>
    );
  if (empty)
    return (
      <div className="empty">
        <Icon name="file" />
        <h3>No matching records</h3>
        <p>Clear filters or add a record to begin.</p>
      </div>
    );
  return children;
}
export function Badge({ value }) {
  return <span className={`badge ${String(value).toLowerCase()}`}>{label(value)}</span>;
}
export function ExportButtons({ path }) {
  const [busy, setBusy] = useState(''),
    [error, setError] = useState('');
  async function save(format) {
    setBusy(format);
    setError('');
    try {
      await download(path(format));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }
  return (
    <div className="export-actions">
      <button disabled={!!busy} onClick={() => save('pdf')}>
        <Icon name="file" />
        {busy === 'pdf' ? 'Preparing…' : 'Export PDF'}
      </button>
      <button disabled={!!busy} onClick={() => save('csv')}>
        {busy === 'csv' ? 'Preparing…' : 'Export CSV'}
      </button>
      {error && (
        <span className="inline-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
export function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    return () => {
      ref.current?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog ref={ref} onCancel={onClose} className={wide ? 'wide' : ''}>
      <header>
        <h2>{title}</h2>
        <button aria-label="Close dialog" onClick={onClose}>
          <Icon name="close" />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function formatValue(key, value) {
  if (value == null) return '—';
  if (/(_at|_time|_date)$/.test(key) || ['check_in', 'check_out', 'created_at'].includes(key)) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime()))
      return date.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
  }
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}
export function DataTable({ rows, columns, actions }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
            {actions && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key}>
                  {[
                    'severity',
                    'status',
                    'review_status',
                    'fulfillment',
                    'availability_status',
                  ].includes(c.key) ? (
                    <Badge value={r[c.key]} />
                  ) : (
                    <span>{formatValue(c.key, r[c.key])}</span>
                  )}
                </td>
              ))}
              {actions && <td className="row-actions">{actions(r)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Pagination({ total, offset, setOffset, size = 25 }) {
  return (
    <footer className="pagination">
      <span>
        {total ? `${offset + 1}–${Math.min(offset + size, total)} of ${total}` : '0 records'}
      </span>
      <div>
        <button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - size))}>
          Previous
        </button>
        <button disabled={offset + size >= total} onClick={() => setOffset(offset + size)}>
          Next
        </button>
      </div>
    </footer>
  );
}
export function Metrics({ items }) {
  return (
    <div className="metrics">
      {items.map(([title, value, note]) => (
        <article key={title}>
          <span>{title}</span>
          <strong>{value ?? '—'}</strong>
          {note && <small>{note}</small>}
        </article>
      ))}
    </div>
  );
}
