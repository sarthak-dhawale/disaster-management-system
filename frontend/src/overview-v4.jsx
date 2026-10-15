import { useEffect, useMemo, useState } from 'react';
import { useData, useDebounced, useAllIncidents } from './hooks';
import { query, invalidate } from './api';
import { State, ExportButtons, DataTable, Pagination, label } from './ui';
import { enums } from './modules';
import { IncidentDetails } from './management';
import { IndiaMap, mapKey } from './incident-map';

export function Overview({ user }) {
  const admin = ['ADMIN', 'DISASTER_MANAGER'].includes(user.role);
  const [filters, setFilters] = useState({}), [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null), [details, setDetails] = useState(null);
  const [offset, setOffset] = useState(0), [fit, setFit] = useState(0);
  const [layers, setLayers] = useState({ disaster: true, report: true, shelter: false, resource: false });
  const q = useDebounced(search), params = query({ ...filters, q, include_resolved: true });
  const incidents = useAllIncidents(params);
  const metrics = useData(admin ? '/api/operations/metrics' : null);
  const extras = useData(admin && (layers.shelter || layers.resource) ? '/api/operations/map-layers' : null);
  const records = useMemo(() => (incidents.data?.items || []).filter((i) => layers[i.kind]), [incidents.data, layers]);
  const mapItems = useMemo(() => [...records, ...(layers.shelter ? extras.data?.shelters || [] : []), ...(layers.resource ? extras.data?.resources || [] : [])], [records, extras.data, layers]);
  useEffect(() => { setOffset(0); setSelected(null); }, [params, layers.disaster, layers.report, layers.shelter, layers.resource]);
  useEffect(() => { if (incidents.data) setFit((v) => v + 1); }, [incidents.data]);
  const metricRows = metrics.data ? [
    ['Active disasters', metrics.data.active, "Status is Active", '#/disasters?status=ACTIVE'],
    ['Critical disasters', metrics.data.critical, 'All critical official records', '#/disasters?severity=CRITICAL'],
    ['Awaiting review', metrics.data.pending, 'Unverified emergency reports', '#/emergency-reports?review_status=PENDING_REVIEW'],
    ['Shelter places', metrics.data.shelter_places, 'Spare places in available shelters', '#/shelters?status=AVAILABLE'],
    ['Resource shortages', metrics.data.shortage_types, 'Resource types below open demand', '#/resource-intelligence'],
  ] : [];
  return <>
    <div className="page-heading"><div><span className="eyebrow">SITUATION OVERVIEW</span><h1>{admin ? 'Response operations' : 'Your emergency reports'}</h1><p>{admin ? 'Incidents, available capacity and response priorities across India.' : 'Submit emergencies and follow your own recorded reports.'}</p></div>
      <div className="heading-actions">{admin && <ExportButtons path={(format) => `/api/reports/overview/${format}?${query({ ...filters, q, record_kind: layers.disaster ? layers.report ? 'all' : 'disaster' : layers.report ? 'report' : 'none' })}`} />}<a className="button primary" href="#/emergency-reports">Report an emergency</a></div></div>
    {admin && <State {...metrics}><div className="metrics overview-metrics">{metricRows.map(([title, value, note, href]) => <a key={title} href={href}><span>{title}</span><strong>{value}</strong><small>{note}</small></a>)}</div><p className="metric-scope">{metrics.data?.scope}</p></State>}
    <section className="panel map-panel"><div className="panel-heading"><div><h2>India disaster map</h2><p>All official statuses are included. Select a record to focus its marker.</p></div><div className="heading-actions"><button onClick={() => setFit((v) => v + 1)}>Fit all results</button><button onClick={invalidate}>Refresh data</button></div></div>
      <div className="toolbar map-toolbar"><input aria-label="Search map incidents" placeholder="Search incident, ID or location…" value={search} onChange={(e) => setSearch(e.target.value)} /><input aria-label="Filter state" placeholder="State (exact name)" value={filters.state || ''} onChange={(e) => setFilters({ ...filters, state: e.target.value })} />
        { [['disaster_type', enums.disaster_type], ['severity', enums.severity], ['status', ['ACTIVE', 'REPORTED', 'CONTAINED', 'RESOLVED', 'PENDING_REVIEW', 'REJECTED']]].map(([key, values]) => <select key={key} aria-label={label(key)} value={filters[key] || ''} onChange={(e) => setFilters({ ...filters, [key]: e.target.value })}><option value="">All {label(key).toLowerCase()}</option>{values.map((v) => <option key={v} value={v}>{label(v)}</option>)}</select>) }
        <button onClick={() => { setFilters({}); setSearch(''); setLayers({ disaster: true, report: true, shelter: false, resource: false }); }}>Clear filters</button></div>
      <fieldset className="map-layer-controls"><legend>Map layers</legend>{[['disaster', 'Disasters'], ['report', admin ? 'Pending reports' : 'My reports'], ...(admin ? [['shelter', 'Shelters'], ['resource', 'Resource allocation destinations']] : [])].map(([key, name]) => <label key={key}><input type="checkbox" checked={layers[key]} onChange={(e) => setLayers({ ...layers, [key]: e.target.checked })} />{name}</label>)}</fieldset>
      <State {...incidents}><IndiaMap items={mapItems} selected={selected} onSelect={setSelected} fitSignal={fit} /><div className="map-legend">{Object.entries(layers).filter(([, visible]) => visible).map(([kind]) => <span key={kind}><i className={`legend-dot ${kind === 'disaster' ? 'official' : kind === 'report' ? 'pending' : kind}`} />{kind === 'resource' ? 'Allocation destination' : label(kind)}</span>)}<span>Outlined marker: critical · ring: selected</span><span>{records.length} incident records · {records.filter((r) => !r.plottable).length} location unavailable</span></div></State>
      {(layers.shelter || layers.resource) && <State loading={extras.loading} error={extras.error}>{layers.resource && <p className="muted">{extras.data?.resource_note}</p>}<p className="muted">Shelter and resource layers are countrywide context; incident filters apply to disaster/report markers and the table.</p></State>}
      {selected && <div className="selected-incident" role="status"><strong>{label(selected.kind)} #{selected.id}: {selected.title}</strong><span>{selected.city || selected.address || 'Location unavailable'} · {label(selected.response_status)}</span>{!selected.plottable && <span>Location unavailable — coordinates were not invented.</span>}{['disaster', 'report'].includes(selected.kind) && <div className="heading-actions"><button onClick={() => setDetails(selected)}>View details</button>{admin && selected.kind === 'disaster' && <a className="button" href={`#/disaster-replay?id=${selected.id}`}>Open replay</a>}</div>}</div>}
    </section>
    <section className="panel"><div className="panel-heading"><div><h2>{admin ? 'Priority incidents' : 'Your reports'}</h2><p>Same incident scope as the map; ordered by severity and recorded status. Missing coordinates remain listed.</p></div><a href={admin ? '#/disasters' : '#/emergency-reports'}>Manage records</a></div><State {...incidents} empty={!records.length}><DataTable rows={records.slice(offset, offset + 15).map((r) => ({ ...r, location: r.plottable ? [r.city, r.state].filter(Boolean).join(', ') || r.address : 'Location unavailable' }))} columns={[{ key: 'id', label: 'ID' }, { key: 'kind', label: 'Record' }, { key: 'title', label: 'Incident' }, { key: 'location', label: 'Location' }, { key: 'severity', label: 'Severity' }, { key: 'response_status', label: 'Status' }]} actions={(row) => <button aria-pressed={selected && mapKey(selected) === mapKey(row)} onClick={() => setSelected(row)}>Locate / select</button>} /><Pagination total={records.length} offset={offset} setOffset={setOffset} size={15} /></State></section>
  </>;
}
