import { useState } from 'react';
import { modules } from './modules';
import { request, invalidate, query } from './api';
import { useData, useDebounced } from './hooks';
import { Badge, State, DataTable, Pagination, Modal, ExportButtons, label } from './ui';
import { RecordForm, ActionDialog } from './forms';
export function IncidentDetails({ kind, id, onClose }) {
  const state = useData(`/api/intelligence/${kind}/${id}/report`);
  return (
    <Modal
      title={`${kind === 'report' ? 'Emergency report' : 'Disaster'} #${id}`}
      onClose={onClose}
      wide
    >
      <State {...state}>
        {state.data && (
          <>
            <div className="detail-grid">
              {Object.entries(state.data.incident).map(([key, value]) => (
                <div key={key}>
                  <small>{label(key)}</small>
                  <p>{String(value ?? '—')}</p>
                </div>
              ))}
            </div>
            <h3>Recorded timeline</h3>
            <p className="muted">{state.data.timeline.history_note}</p>
            <div className="timeline">
              {state.data.timeline.items.map((e, i) => (
                <article key={i}>
                  <strong>{e.action}</strong>
                  <small>
                    {String(e.timestamp)} {e.actor_name || ''}
                  </small>
                  <p>{e.description}</p>
                </article>
              ))}
            </div>
            {!state.data.restricted_response_data && (
              <>
                <h3>Nearby eligible shelters</h3>
                <p>{state.data.shelters.reason || state.data.shelters.distance_method}</p>
                <DataTable
                  rows={state.data.shelters.items}
                  columns={[
                    { key: 'name', label: 'Shelter' },
                    { key: 'available_capacity', label: 'Available places' },
                    { key: 'distance_km', label: 'Distance km' },
                  ]}
                />
                <h3>Resource allocations</h3>
                <DataTable
                  rows={state.data.allocations}
                  columns={[
                    { key: 'resource_name', label: 'Resource' },
                    { key: 'quantity', label: 'Quantity' },
                    { key: 'unit', label: 'Unit' },
                    { key: 'status', label: 'Status' },
                  ]}
                />
              </>
            )}
          </>
        )}
      </State>
    </Modal>
  );
}
export function Management({ module, user, notify }) {
  const config = modules[module],
    admin = ['ADMIN', 'DISASTER_MANAGER'].includes(user.role);
  const [filters, setFilters] = useState({}),
    [search, setSearch] = useState(''),
    [offset, setOffset] = useState(0);
  const q = useDebounced(search),
    [form, setForm] = useState(null),
    [details, setDetails] = useState(null),
    [action, setAction] = useState(null),
    [deleting, setDeleting] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const params = query({ ...filters, q, limit: 25, offset });
  const state = useData(`/api/${module}/?${params}`);
  const rows = state.data?.[config.key || module] || [];
  function filter(key, value) {
    setFilters((v) => ({ ...v, [key]: value }));
    setOffset(0);
  }
  async function remove() {
    setBusy(true);
    setError('');
    try {
      await request(`/api/${module}/${deleting[config.id]}`, { method: 'DELETE' });
      setDeleting(null);
      invalidate();
      notify('Record deleted');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function review(row, decision) {
    setAction({
      title: `${decision === 'CONFIRMED' ? 'Confirm' : 'Reject'} report #${row.report_id}`,
      path: `/api/emergency-reports/${row.report_id}/review`,
      initial: { decision },
      description:
        decision === 'CONFIRMED'
          ? 'Confirm with a verified location or link an existing official disaster. Repeating a confirmed review will not create another disaster.'
          : 'The decision reason is public to the reporter. Keep internal operational notes out of this field.',
      fields: [
        {
          key: 'decision',
          label: 'Decision',
          type: 'select',
          required: true,
          values: ['CONFIRMED', 'REJECTED'],
        },
        ...(decision === 'CONFIRMED'
          ? [
              { key: 'title', label: 'Official incident title', type: 'text' },
              {
                key: 'location_id',
                label: 'Verified location (required for unfamiliar places)',
                type: 'relation',
                module: 'locations',
              },
              {
                key: 'disaster_id',
                label: 'Link existing disaster (optional)',
                type: 'relation',
                module: 'disasters',
              },
            ]
          : []),
        { key: 'reason', label: 'Public decision reason', type: 'textarea', max: 1000 },
      ],
    });
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">RESPONSE OPERATIONS</span>
          <h1>{!admin && module === 'emergency-reports' ? 'My Reports' : config.title}</h1>
          <p>
            {!admin && module === 'emergency-reports'
              ? 'Track your own submissions and report references. Reports require administrator review.'
              : config.description}
          </p>
        </div>
        <div className="heading-actions">
          {[
            'disasters',
            'emergency-reports',
            'shelters',
            'resources',
            'resource-allocations',
          ].includes(module) && (
            <ExportButtons
              path={(format) => `/api/exports/${module}.${format}?${query({ ...filters, q })}`}
            />
          )}
          <button className="primary" onClick={() => setForm({})}>
            +{' '}
            {module === 'emergency-reports'
              ? 'Report an emergency'
              : `Add ${config.singular.toLowerCase()}`}
          </button>
        </div>
      </div>
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Search records"
            placeholder={`Search ${config.title.toLowerCase()}…`}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
          {Object.entries(config.filters).map(([key, values]) => (
            <select
              aria-label={label(key)}
              key={key}
              value={filters[key] || ''}
              onChange={(e) => filter(key, e.target.value)}
            >
              <option value="">All {label(key).toLowerCase()}</option>
              {values.map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          ))}
          <select
            aria-label="Sort records"
            value={filters.sort || 'desc'}
            onChange={(e) => filter('sort', e.target.value)}
          >
            <option value="desc">Newest record first</option>
            <option value="asc">Oldest record first</option>
            {['disasters', 'emergency-reports'].includes(module) && (
              <option value="priority">Highest priority first</option>
            )}
          </select>
          {module === 'resources' && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={!!filters.low_stock}
                onChange={(e) => filter('low_stock', e.target.checked)}
              />
              Low stock only
            </label>
          )}
          {module === 'shelters' && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={!!filters.available_only}
                onChange={(e) => filter('available_only', e.target.checked)}
              />
              Spare capacity only
            </label>
          )}
          <button
            onClick={() => {
              setSearch('');
              setFilters({});
              setOffset(0);
            }}
          >
            Clear
          </button>
          <button onClick={invalidate}>Refresh</button>
        </div>
        <State {...state} empty={!rows.length}>
          <DataTable
            rows={rows}
            columns={config.columns}
            actions={(row) => (
              <>
                <button onClick={() => setDetails(row)}>Details</button>
                {admin && module !== 'emergency-reports' && (
                  <>
                    <button onClick={() => setForm(row)}>Edit</button>
                    <button className="danger-text" onClick={() => setDeleting(row)}>
                      Delete
                    </button>
                  </>
                )}
                {admin &&
                  module === 'emergency-reports' &&
                  row.review_status === 'PENDING_REVIEW' && (
                    <>
                      <button onClick={() => setForm(row)}>Edit</button>
                      <button onClick={() => setDeleting(row)}>Delete</button>
                      <button onClick={() => review(row, 'CONFIRMED')}>Confirm</button>
                      <button onClick={() => review(row, 'REJECTED')}>Reject</button>
                    </>
                  )}
                {admin && module === 'emergency-reports' && row.review_status === 'CONFIRMED' && (
                  <button
                    onClick={() =>
                      setAction({
                        title: 'Update response progress',
                        path: `/api/emergency-reports/${row.report_id}/progress`,
                        fields: [
                          {
                            key: 'status',
                            label: 'Response status',
                            type: 'select',
                            required: true,
                            values: ['IN_PROGRESS', 'RESOLVED'],
                          },
                        ],
                      })
                    }
                  >
                    Progress
                  </button>
                )}
                {module === 'resources' && (
                  <button
                    onClick={() =>
                      setAction({
                        title: 'Record stock movement',
                        path: `/api/resources/${row.resource_id}/stock`,
                        fields: [
                          {
                            key: 'kind',
                            label: 'Movement',
                            type: 'select',
                            values: ['RESTOCK', 'WITHDRAW'],
                            required: true,
                          },
                          {
                            key: 'quantity',
                            label: `Quantity (${row.unit})`,
                            type: 'number',
                            min: 0.01,
                            step: 0.01,
                            required: true,
                          },
                          {
                            key: 'note',
                            label: 'Reason',
                            type: 'textarea',
                            required: true,
                            minLength: 3,
                          },
                        ],
                      })
                    }
                  >
                    Stock
                  </button>
                )}
              </>
            )}
          />
        </State>
        <Pagination total={state.data?.total || 0} offset={offset} setOffset={setOffset} />
      </section>
      {form && (
        <RecordForm
          module={module}
          config={config}
          record={form[config.id] ? form : null}
          onClose={() => setForm(null)}
          onSuccess={notify}
        />
      )}
      {action && <ActionDialog {...action} onClose={() => setAction(null)} onSuccess={notify} />}
      {details &&
        (['disasters', 'emergency-reports'].includes(module) ? (
          <IncidentDetails
            kind={module === 'disasters' ? 'disaster' : 'report'}
            id={details[config.id]}
            onClose={() => setDetails(null)}
          />
        ) : (
          <Modal title={`${config.singular} details`} wide onClose={() => setDetails(null)}>
            <div className="detail-grid">
              {Object.entries(details)
                .filter(([k]) => !['password_hash', 'approval_key'].includes(k))
                .map(([key, value]) => (
                  <div key={key}>
                    <small>{label(key)}</small>
                    <p>{String(value ?? '—')}</p>
                  </div>
                ))}
            </div>
          </Modal>
        ))}
      {deleting && (
        <Modal title="Delete this record?" onClose={() => setDeleting(null)}>
          <p>This permanently removes the selected record. Linked records may prevent deletion.</p>
          {error && <p className="notice error">{error}</p>}
          <footer className="dialog-actions">
            <button onClick={() => setDeleting(null)}>Cancel</button>
            <button className="danger" disabled={busy} onClick={remove}>
              {busy ? 'Deleting…' : 'Delete record'}
            </button>
          </footer>
        </Modal>
      )}
    </>
  );
}
