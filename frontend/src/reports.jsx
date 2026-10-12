import { modules } from './modules';
import { useState } from 'react';
import { useData, useDebounced } from './hooks';
import { query } from './api';
import { State, DataTable, Pagination, ExportButtons, label } from './ui';
export function Reports() {
  const [section, setSection] = useState('disasters'),
    [offset, setOffset] = useState(0),
    [search, setSearch] = useState('');
  const q = useDebounced(search);
  const state = useData(`/api/reports/analysis/${section}?${query({ q, limit: 25, offset })}`);
  const rows = state.data?.items || [];
  const columns = rows.length
    ? Object.keys(rows[0]).map((key) => ({ key, label: label(key) }))
    : [];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">RECORDED ANALYSIS</span>
          <h1>Detailed reports</h1>
          <p>
            Database views and unit-aware allocation summaries. These reports use actual stored
            records.
          </p>
        </div>
        <ExportButtons path={(f) => `/api/reports/analysis/${section}/${f}?${query({ q })}`} />
      </div>
      <section className="panel accountability-links">
        <div>
          <h2>Accountability records</h2>
          <p>Review recorded changes and stock movements with authorized access.</p>
        </div>
        <div className="heading-actions">
          <a className="button" href="#/audit-history">
            Review audit history
          </a>
          <a className="button" href="#/resource-movements">
            Review stock movements
          </a>
        </div>
      </section>
      <div className="segmented-tabs" role="tablist">
        {[
          ['disasters', 'Disaster response'],
          ['shelters', 'Shelter occupancy'],
          ['monthly-reports', 'Monthly emergency reports'],
          ['resource-allocations', 'Allocation coverage'],
        ].map(([key, title]) => (
          <button
            role="tab"
            aria-selected={section === key}
            className={section === key ? 'selected' : ''}
            key={key}
            onClick={() => {
              setSection(key);
              setOffset(0);
            }}
          >
            {title}
          </button>
        ))}
      </div>
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Filter analysis"
            placeholder="Filter by name, region or month…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
          <button
            onClick={() => {
              setSearch('');
              setOffset(0);
            }}
          >
            Clear filter
          </button>
        </div>
        <div className="panel-heading">
          <h2>{label(section)}</h2>
        </div>
        <State {...state} empty={!rows.length}>
          <DataTable rows={rows} columns={columns} />
        </State>
        <Pagination total={state.data?.total || 0} offset={offset} setOffset={setOffset} />
      </section>
    </>
  );
}
export function History({ module }) {
  const [filters, setFilters] = useState({}),
    [offset, setOffset] = useState(0);
  const state = useData(`/api/${module}/?${query({ ...filters, offset, limit: 25 })}`);
  const rows = state.data?.items || [];
  const fields =
    module === 'audit-history'
      ? ['created_at', 'entity', 'record_id', 'action', 'actor_name', 'before_data', 'after_data']
      : [
          'created_at',
          'resource_id',
          'movement_kind',
          'available_delta',
          'available_after',
          'actor_name',
          'note',
        ];
  return (
    <>
      <div className="page-heading">
        <div>
          <a href="#/reports">Detailed reports / Accountability</a>
          <span className="eyebrow">ACCOUNTABILITY</span>
          <h1>{label(module.replaceAll('-', ' '))}</h1>
          <p>
            Read-only recorded events. Historical events before auditing began may be unavailable.
          </p>
        </div>
      </div>
      <section className="panel">
        <div className="toolbar">
          {['start', 'end'].map((key) => (
            <label key={key}>
              {label(key)}
              <input
                type="date"
                value={filters[key] || ''}
                onChange={(e) => {
                  setFilters({ ...filters, [key]: e.target.value });
                  setOffset(0);
                }}
              />
            </label>
          ))}
          {module === 'audit-history' ? (
            <select
              aria-label="Entity"
              value={filters.entity || ''}
              onChange={(e) => {
                setFilters({ ...filters, entity: e.target.value });
                setOffset(0);
              }}
            >
              <option value="">All modules</option>
              {[
                'disasters',
                'emergency_reports',
                'resources',
                'resource_requests',
                'resource_allocations',
                'shelters',
                'users',
                'volunteers',
                'locations',
                'volunteer_assignments',
                'shelter_registrations',
              ].map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label="Resource ID"
              type="number"
              min="1"
              placeholder="Resource ID"
              value={filters.resource_id || ''}
              onChange={(e) => {
                setFilters({ ...filters, resource_id: e.target.value });
                setOffset(0);
              }}
            />
          )}
          <button
            onClick={() => {
              setFilters({});
              setOffset(0);
            }}
          >
            Clear
          </button>
        </div>
        <State {...state} empty={!rows.length}>
          <DataTable rows={rows} columns={fields.map((key) => ({ key, label: label(key) }))} />
        </State>
        <Pagination total={state.data?.total || 0} offset={offset} setOffset={setOffset} />
      </section>
    </>
  );
}
export function Search({ user }) {
  const [value, setValue] = useState(''),
    [module, setModule] = useState('disasters'),
    [offset, setOffset] = useState(0);
  const q = useDebounced(value);
  const state = useData(q ? `/api/search/${module}?${query({ q, limit: 25, offset })}` : null);
  const rows = state.data?.[module.replaceAll('-', '_')] || [];
  const choices = [
    'disasters',
    'emergency-reports',
    'shelters',
    'resources',
    'locations',
    'volunteers',
    'resource-allocations',
    'volunteer-assignments',
    'shelter-registrations',
    ...(user.role === 'ADMIN' ? ['users'] : []),
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">DATABASE SEARCH</span>
          <h1>Search records</h1>
          <p>Search the selected module using actual database records.</p>
        </div>
      </div>
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Global search"
            placeholder="Search recorded names, locations or descriptions…"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setOffset(0);
            }}
          />
          <select
            aria-label="Search module"
            value={module}
            onChange={(e) => {
              setModule(e.target.value);
              setOffset(0);
            }}
          >
            {choices.map((v) => (
              <option key={v} value={v}>
                {label(v.replaceAll('-', ' '))}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              setValue('');
              setOffset(0);
            }}
          >
            Clear
          </button>
        </div>
        {q ? (
          <State {...state} empty={!rows.length}>
            <DataTable
              rows={rows}
              columns={modules[module].columns}
              actions={() => (
                <a className="button" href={`#/${module}`}>
                  Open module
                </a>
              )}
            />
          </State>
        ) : (
          <p className="panel-note">Enter a search term to load matching records.</p>
        )}
        <Pagination total={state.data?.total || 0} offset={offset} setOffset={setOffset} />
      </section>
    </>
  );
}
