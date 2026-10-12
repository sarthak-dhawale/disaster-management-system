import { useEffect, useRef, useState } from 'react';
import { useData, useDebounced } from './hooks';
import { query, invalidate } from './api';
import { Metrics, State, ExportButtons, DataTable, Badge, label } from './ui';
import { enums } from './modules';
import { IncidentDetails } from './management';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
export function PointMap({ onPick }) {
  const element = useRef(),
    selected = useRef(),
    pick = useRef(onPick);
  pick.current = onPick;
  useEffect(() => {
    const map = L.map(element.current, { scrollWheelZoom: false }).setView([23.4, 81], 4);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);
    map.on('click', (e) => {
      if (selected.current) selected.current.remove();
      selected.current = L.circleMarker(e.latlng, { radius: 7, color: '#bf5e28' }).addTo(map);
      pick.current({
        latitude: Number(e.latlng.lat.toFixed(7)),
        longitude: Number(e.latlng.lng.toFixed(7)),
        coordinate_source: 'MAP_POINT',
      });
    });
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(element.current);
    return () => {
      observer.disconnect();
      map.remove();
    };
  }, []);
  return (
    <>
      <p className="muted">
        Click the location to use its coordinates, then provide a descriptive address.
      </p>
      <div ref={element} className="point-map" aria-label="Select location coordinates on map" />
    </>
  );
}
export function IndiaMap({ items, onSelect }) {
  const element = useRef(),
    map = useRef(),
    markers = useRef(),
    select = useRef(onSelect);
  const config = useData('/api/intelligence/map-config');
  select.current = onSelect;
  useEffect(() => {
    const instance = L.map(element.current, {
      scrollWheelZoom: false,
      minZoom: 3,
      maxZoom: 18,
    }).setView([23.4, 81], 4.5);
    map.current = instance;
    markers.current = L.markerClusterGroup({ maxClusterRadius: 45, chunkedLoading: true });
    instance.addLayer(markers.current);
    const controller = new AbortController();
    fetch('/data/india-states.geojson', { signal: controller.signal })
      .then((r) => r.json())
      .then((data) => {
        if (map.current === instance)
          L.geoJSON(data, {
            style: { color: '#71899a', weight: 0.8, fillColor: '#b9cbd6', fillOpacity: 0.2 },
            onEachFeature: (feature, layer) => {
              const name = feature.properties.shapeName || feature.properties.name || 'Region';
              layer.bindTooltip(name);
            },
          }).addTo(instance);
      })
      .catch((e) => {
        if (e.name !== 'AbortError') console.error('Boundary data unavailable', e.message);
      });
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(element.current);
    return () => {
      controller.abort();
      observer.disconnect();
      instance.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    if (!map.current || !config.data) return;
    const tiles = L.tileLayer(config.data.tile_url, {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map.current);
    return () => tiles.remove();
  }, [config.data]);
  useEffect(() => {
    if (!markers.current) return;
    const start = performance.now();
    markers.current.clearLayers();
    for (const item of items) {
      if (!item.plottable) continue;
      const pending = item.kind === 'report';
      const icon = L.divIcon({
        className: 'incident-marker',
        html: `<span class="map-dot ${pending ? 'pending' : 'official'}"></span>`,
        iconSize: [20, 20],
      });
      const marker = L.marker([Number(item.latitude), Number(item.longitude)], { icon });
      const tooltip = document.createElement('span');
      tooltip.textContent = `${item.title} • ${label(item.severity)} • ${label(item.review_status)}`;
      marker.bindTooltip(tooltip).on('click', () => select.current(item));
      markers.current.addLayer(marker);
    }
    performance.measure('dms-map-update', { start, end: performance.now() });
  }, [items]);
  return <div ref={element} className="india-map" aria-label="Interactive India incident map" />;
}
export function Overview({ user }) {
  const admin = ['ADMIN', 'DISASTER_MANAGER'].includes(user.role);
  const [filters, setFilters] = useState({}),
    [search, setSearch] = useState(''),
    [selected, setSelected] = useState(null);
  const q = useDebounced(search),
    params = query({ ...filters, q });
  const incidents = useData(`/api/intelligence/incidents?${params}&limit=500`);
  const dashboard = useData(admin ? '/api/dashboard/' : null);
  const summaries = useData(admin ? '/api/intelligence/overview/summary' : null);
  const items = incidents.data?.items || [];
  const data = dashboard.data;
  const metricItems = data
    ? [
        ['Recorded disasters', data.disasters.total, 'Official records'],
        ['Active incidents', data.disasters.active, 'Status: active'],
        ['Pending review', data.emergency_reports.pending, 'Unverified reports'],
        ['Available shelters', data.shelters.available, 'Available status and spare capacity'],
        ['Volunteers', data.volunteers.total, 'Registered volunteer records'],
        [
          'Resources in stock',
          data.resources.available_types,
          'Distinct inventory types; no mixed-unit sum',
        ],
      ]
    : [];
  function filter(key, value) {
    setFilters((v) => ({ ...v, [key]: value }));
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">SITUATION OVERVIEW</span>
          <h1>{admin ? 'Response operations' : 'Your emergency reports'}</h1>
          <p>
            {admin
              ? 'A shared picture of incidents, capacity and response priorities.'
              : 'Submit suspected emergencies and follow their recorded review status.'}
          </p>
        </div>
        <div className="heading-actions">
          {admin && (
            <ExportButtons path={(format) => `/api/reports/overview/${format}?${params}`} />
          )}
          <a className="button primary" href="#/emergency-reports">
            Report an emergency
          </a>
        </div>
      </div>
      <section className="panel map-panel">
        <div className="panel-heading">
          <div>
            <h2>India incident map</h2>
            <p>Official incidents and reports awaiting verification.</p>
          </div>
          <button onClick={invalidate}>Refresh data</button>
        </div>
        <div className="toolbar map-toolbar">
          <input
            aria-label="Search map incidents"
            placeholder="Search incident or location…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <input
            aria-label="Filter state"
            placeholder="State"
            value={filters.state || ''}
            onChange={(e) => filter('state', e.target.value)}
          />
          {[
            ['disaster_type', enums.disaster_type],
            ['severity', enums.severity],
            [
              'status',
              ['ACTIVE', 'REPORTED', 'CONTAINED', 'RESOLVED', 'PENDING_REVIEW', 'REJECTED'],
            ],
          ].map(([key, values]) => (
            <select
              key={key}
              aria-label={label(key)}
              value={filters[key] || ''}
              onChange={(e) => filter(key, e.target.value)}
            >
              <option value="">All {label(key).toLowerCase()}</option>
              {values.map((v) => (
                <option value={v} key={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          ))}
          <label>
            From
            <input
              type="date"
              value={filters.start || ''}
              onChange={(e) => filter('start', e.target.value)}
            />
          </label>
          <label>
            To
            <input
              type="date"
              value={filters.end || ''}
              onChange={(e) => filter('end', e.target.value)}
            />
          </label>
          <button
            onClick={() => {
              setSearch('');
              setFilters({});
            }}
          >
            Clear
          </button>
        </div>
        <State {...incidents}>
          <IndiaMap items={items} onSelect={setSelected} />
          <div className="map-legend">
            <span>
              <i className="legend-dot official" />
              Official disaster
            </span>
            <span>
              <i className="legend-dot pending" />
              Emergency report
            </span>
            <span>{items.filter((i) => !i.plottable).length} unlocated in loaded records</span>
            <span>
              {items.length} of {incidents.data?.total || 0} matching records loaded
            </span>
          </div>
          {incidents.data?.total > 500 && (
            <p className="notice">
              Map shows the first 500 priority-ranked records. Narrow filters to display the full
              scope; exports include all matching records up to the documented limit.
            </p>
          )}
        </State>
      </section>
      {admin && (
        <State {...dashboard}>
          <Metrics items={metricItems} />
        </State>
      )}
      <div className="overview-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>{admin ? 'Priority incidents' : 'Your recent reports'}</h2>
              <p>Ranked by recorded severity, status and waiting time.</p>
            </div>
            <a href={admin ? '#/disasters' : '#/emergency-reports'}>View records</a>
          </div>
          <State {...incidents} empty={!items.length}>
            <DataTable
              rows={items.slice(0, 8)}
              columns={[
                { key: 'title', label: 'Incident' },
                { key: 'severity', label: 'Severity' },
                { key: 'review_status', label: 'Verification' },
                { key: 'priority_score', label: 'Priority' },
              ]}
              actions={(row) => <button onClick={() => setSelected(row)}>Open</button>}
            />
          </State>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Operational attention</h2>
          </div>
          {admin ? (
            <State {...summaries}>
              {summaries.data && (
                <>
                  <h3>Outstanding demand</h3>
                  {summaries.data.requests.length ? (
                    summaries.data.requests.map((r) => (
                      <div className="attention-row" key={r.request_id}>
                        <span>
                          {r.resource_name}
                          <small>Request #{r.request_id}</small>
                        </span>
                        <strong>
                          {r.outstanding_quantity} {r.unit}
                        </strong>
                      </div>
                    ))
                  ) : (
                    <p className="muted">No outstanding requests recorded.</p>
                  )}
                  <a className="button" href="#/resource-intelligence">
                    Open Resource Intelligence
                  </a>
                  <h3>Shelter warnings</h3>
                  {summaries.data.shelter_warnings.length ? (
                    summaries.data.shelter_warnings.map((r, i) => (
                      <div className="attention-row" key={i}>
                        <span>{r.name}</span>
                        <Badge value={r.status} />
                      </div>
                    ))
                  ) : (
                    <p className="muted">No capacity warnings recorded.</p>
                  )}
                </>
              )}
            </State>
          ) : (
            <p className="muted">
              Reports remain unverified until a disaster manager reviews them. Only your own reports
              are visible here.
            </p>
          )}
        </section>
      </div>
      {selected && (
        <IncidentDetails kind={selected.kind} id={selected.id} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
