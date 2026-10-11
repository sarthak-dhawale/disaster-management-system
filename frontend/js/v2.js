/* V2 extensions reuse the existing session/API/controller and actual records. */
window.DMSV2 = (() => {
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => DMS.esc(value);
  const human = (value) => DMS.human(value);
  let leafletPromise;
  const groups = {
    resources: [
      ['resources', 'Inventory'],
      ['resource-allocations', 'Allocations'],
    ],
    shelters: [
      ['shelters', 'Shelters'],
      ['shelter-registrations', 'Registrations'],
    ],
    volunteers: [
      ['volunteers', 'Volunteers'],
      ['volunteer-assignments', 'Assignments'],
    ],
    index: [
      ['index', 'Overview'],
      ['analytics', 'Detailed reports'],
    ],
    users: [
      ['users', 'User management'],
      ['audit-history', 'Audit records'],
    ],
  };
  const parents = {
    'resource-allocations': 'resources',
    'resource-movements': 'resources',
    'shelter-registrations': 'shelters',
    'volunteer-assignments': 'volunteers',
    analytics: 'index',
    'audit-history': 'users',
  };
  function relatedNavigation(page) {
    const entries = groups[parents[page] || page];
    if (!DMS.isAdmin() || !entries) return;
    const nav = document.createElement('nav');
    nav.className = 'related-nav';
    nav.setAttribute('aria-label', 'Related workspace');
    nav.innerHTML = entries
      .map(
        ([key, label]) =>
          `<a href="${key}.html" ${key === page ? 'aria-current="page"' : ''}>${esc(label)}</a>`,
      )
      .join('');
    $('#view').before(nav);
  }
  function loadLeaflet() {
    if (leafletPromise) return leafletPromise;
    leafletPromise = (async () => {
      for (const href of ['vendor/leaflet/leaflet.css', 'vendor/markercluster/MarkerCluster.css']) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        document.head.append(link);
      }
      for (const src of [
        'vendor/leaflet/leaflet-src.js',
        'vendor/markercluster/leaflet.markercluster-src.js',
      ]) {
        await new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = src;
          script.onload = resolve;
          script.onerror = () =>
            reject(new Error('Map library unavailable. The incident list remains usable.'));
          document.head.append(script);
        });
      }
      return window.L;
    })();
    leafletPromise.catch(() => {
      leafletPromise = null;
    });
    return leafletPromise;
  }
  async function baseMap(element, notice, picker = false) {
    const L = await loadLeaflet();
    const map = L.map(element, { scrollWheelZoom: !picker }).fitBounds([
      [6.4, 68],
      [37.6, 97.5],
    ]);
    const config = await DMS.api('/api/intelligence/map-config');
    const tiles = L.tileLayer(config.tile_url, {
      maxZoom: 18,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      keepBuffer: 1,
    }).addTo(map);
    tiles.on('tileerror', () => {
      if (notice)
        notice.textContent =
          'Some map tiles are unavailable. Boundaries, stored points and lists remain accessible.';
    });
    try {
      const response = await fetch('data/india-states.geojson');
      if (!response.ok) throw new Error('Boundary file unavailable');
      const boundaries = await response.json();
      const layer = L.geoJSON(boundaries, {
        style: { color: '#b2691b', weight: 1, fillColor: '#f28c28', fillOpacity: 0.025 },
        onEachFeature: (feature, layer) => {
          const label = document.createElement('span');
          label.textContent = feature.properties.shapeName || 'Administrative boundary';
          layer.bindTooltip(label);
        },
      }).addTo(map);
      map.boundaryLayer = layer;
      map.attributionControl.addAttribution(
        '<a href="https://www.geoboundaries.org/">geoBoundaries / DataMeet / ECI</a>',
      );
    } catch (error) {
      if (notice) notice.textContent = error.message + '. Incident records are still available.';
    }
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(element);
    map.on('unload', () => observer.disconnect());
    return map;
  }
  function style(row) {
    if (row.review_status === 'REJECTED') return ['rejected', 'X', 'Rejected report'];
    if (row.review_status === 'PENDING_REVIEW') return ['pending', 'P', 'Pending citizen report'];
    if (row.kind === 'report' && row.review_status === 'CONFIRMED')
      return ['reviewed', 'V', 'Confirmed citizen report'];
    if (row.kind === 'report' && row.review_status === 'LEGACY')
      return ['pending', 'U', 'Legacy report; review status unknown'];
    if (row.response_status === 'RESOLVED') return ['resolved', 'R', 'Resolved official incident'];
    if (row.kind === 'disaster' && row.severity === 'CRITICAL' && row.response_status === 'ACTIVE')
      return ['critical', 'C', 'Active critical official incident'];
    return [
      'active',
      'A',
      row.kind === 'report' ? 'Reviewed citizen report' : 'Official disaster record',
    ];
  }
  function marker(row) {
    const [kind, symbol, label] = style(row);
    return L.marker([Number(row.latitude), Number(row.longitude)], {
      icon: L.divIcon({
        className: 'incident-marker',
        html: `<span class="incident-symbol ${kind}" aria-hidden="true">${symbol}</span>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      }),
      title: `${label}: ${row.title}`,
      alt: `${label}: ${row.title}`,
    });
  }
  function legend() {
    return /* HTML */ `<div class="map-legend" aria-label="Map legend">
      ${[
        ['critical', 'C', 'Active critical'],
        ['active', 'A', 'Official incident'],
        ['pending', 'P', 'Pending review'],
        ['resolved', 'R', 'Resolved'],
        ['rejected', 'X', 'Rejected (opt-in)'],
        ['reviewed', 'V', 'Confirmed citizen report'],
        ['pending', 'U', 'Legacy review unknown'],
      ]
        .map(
          ([c, s, l]) =>
            `<span><span class="incident-symbol ${c}" aria-hidden="true">${s}</span> ${l}</span>`,
        )
        .join('')}
    </div>`;
  }
  async function mapPage() {
    $('#view').innerHTML =
      DMS.heading(
        'India disaster map',
        'Recorded incidents and citizen reports. Refreshes use the database; this is not a live monitoring service.',
        '<button class="btn" id="map-refresh">Refresh</button>',
      ) +
      /* HTML */ ` <form class="toolbar panel" id="map-filters">
          <label>City, locality or incident<input name="q" type="search" maxlength="150" /></label>
          <label
            >Type<select name="disaster_type">
              <option value="">All types</option>
              ${enums.disaster_type
                .map((t) => `<option value="${t}">${human(t)}</option>`)
                .join('')}
            </select></label
          >
          <label
            >Severity<select name="severity">
              <option value="">All severities</option>
              ${enums.severity.map((t) => `<option>${t}</option>`).join('')}
            </select></label
          >
          <label
            >Status<select name="status">
              <option value="">Active / pending</option>
              ${['ACTIVE', 'CONTAINED', 'PENDING_REVIEW', 'IN_PROGRESS', 'RESOLVED', 'REJECTED']
                .map((t) => `<option value="${t}">${human(t)}</option>`)
                .join('')}
            </select></label
          >
          <label>State / territory<input name="state" maxlength="100" /></label
          ><label>From<input type="date" name="start" /></label
          ><label>Through<input type="date" name="end" /></label>
          <label
            ><span>Include resolved</span
            ><input type="checkbox" name="include_resolved" value="true"
          /></label>
          <label
            ><span>Include rejected</span
            ><input type="checkbox" name="include_rejected" value="true"
          /></label>
          <button class="btn primary">Apply</button
          ><button class="btn" type="button" id="map-reset">Reset filters</button>
        </form>
        ${legend()}
        <p class="muted" id="tile-note"></p>
        <div class="map-workspace">
          <div>
            <div
              class="map-canvas"
              id="india-map"
              aria-label="Interactive India incident map"
            ></div>
            <div class="actions" style="margin:12px 0">
              <button class="btn" id="map-india">India extent</button
              ><button class="btn" id="map-clear">Clear selection</button>
            </div>
            <section class="panel" id="map-details">
              <div class="empty">Select a marker or incident to inspect recorded details.</div>
            </section>
          </div>
          <section class="panel map-side">
            <div class="panel-head">
              <h2>Matching incidents</h2>
              <span id="map-count"></span>
            </div>
            <ul class="incident-list" id="map-list"></ul>
            <div class="pagination">
              <span id="map-list-page"></span>
              <div class="actions">
                <button class="btn small" id="map-prev">Previous</button
                ><button class="btn small" id="map-next">Next</button>
              </div>
            </div>
            <div class="panel-head"><h2>Unlocated incidents</h2></div>
            <ul class="incident-list" id="unlocated-list"></ul>
          </section>
        </div>`;
    let map,
      cluster,
      items = [],
      page = 0,
      generation = 0,
      selection = 0,
      abort,
      selectedKey = null;
    const markers = new Map();
    function clear() {
      selection++;
      selectedKey = null;
      $('#map-details').innerHTML =
        '<div class="empty">Select a marker or incident to inspect recorded details.</div>';
      renderList();
    }
    function renderList() {
      const located = items.filter((r) => r.plottable),
        unlocated = items.filter((r) => !r.plottable);
      const render = (rows) =>
        rows
          .map(
            (row) =>
              /* HTML */ `<li class="${selectedKey === row.kind + ':' + row.id ? 'selected' : ''}">
                <button data-kind="${row.kind}" data-id="${row.id}">
                  <strong>${esc(row.title)}</strong
                  ><small
                    >${esc(human(row.severity))} · ${esc(human(row.review_status))} · Priority
                    ${esc(row.priority_score)}</small
                  ><small
                    >${esc([row.city, row.address, row.state].filter(Boolean).join(', '))}</small
                  >${row.plottable ? '' : `<small>${esc(row.coordinate_note)}</small>`}
                </button>
              </li>`,
          )
          .join('');
      $('#map-list').innerHTML = located.length
        ? render(located.slice(page * 50, (page + 1) * 50))
        : '<li>No plottable incidents match these filters.</li>';
      $('#unlocated-list').innerHTML = unlocated.length
        ? render(unlocated)
        : '<li>No unlocated incidents in this result.</li>';
      $('#map-count').textContent = items.length + ' records';
      $('#map-list-page').textContent = `Page ${page + 1} · ${unlocated.length} unlocated`;
      $('#map-prev').disabled = page === 0;
      $('#map-next').disabled = (page + 1) * 50 >= located.length;
    }
    async function select(row) {
      const token = ++selection;
      selectedKey = row.kind + ':' + row.id;
      renderList();
      if (map && row.plottable) {
        const pin = markers.get(selectedKey);
        if (cluster && cluster.zoomToShowLayer) cluster.zoomToShowLayer(pin, () => pin.openPopup());
        else {
          map.setView([Number(row.latitude), Number(row.longitude)], Math.max(map.getZoom(), 9));
          pin?.openPopup();
        }
      }
      $('#map-details').innerHTML = /* HTML */ `<div class="panel-body">
        <h2>${esc(row.title)}</h2>
        <p class="priority-tag">Priority ${esc(row.priority_score)} · ${esc(row.priority_note)}</p>
        <dl class="details">
          ${[
            ['Reference', row.kind + ' #' + row.id],
            ['Type', human(row.disaster_type)],
            ['Severity', human(row.severity)],
            ['Response', human(row.response_status)],
            ['Verification', human(row.review_status)],
            ['Location', [row.city, row.address, row.state].filter(Boolean).join(', ')],
            [
              'Coordinates',
              row.plottable ? row.latitude + ', ' + row.longitude : row.coordinate_note,
            ],
            ['Incident time', row.incident_time],
            ['Last recorded update', row.recorded_at],
            ['Description', row.description],
          ]
            .map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value ?? 'Unavailable')}</dd>`)
            .join('')}
        </dl>
        <p class="muted">
          Severity ${esc(row.priority_factors.severity)} + response
          ${esc(row.priority_factors.response)} + elapsed time
          ${esc(row.priority_factors.elapsed_hours_bonus)}${row.priority_factors.time_known
            ? ''
            : ' (time unavailable)'}
        </p>
        <div class="actions">
          <a
            class="btn"
            href="${row.kind === 'disaster'
              ? 'disasters'
              : 'emergency-reports'}.html?record_id=${row.id}"
            >Open actual record</a
          ><a class="btn" href="print.html?kind=${row.kind}&id=${row.id}">Print / Save as PDF</a>
        </div>
        <div id="map-response" class="detail-extra">Loading response details...</div>
      </div>`;
      try {
        const data = await DMS.api(`/api/intelligence/${row.kind}/${row.id}/report`);
        if (token !== selection) return;
        $('#map-response').innerHTML = timelineHtml(data.timeline) + shelterHtml(data.shelters);
        if (DMS.isAdmin())
          $('#map-response').insertAdjacentHTML(
            'beforeend',
            '<h3>Resource allocations</h3>' +
              DMS.miniTable(
                data.allocations,
                columns(
                  ['resource_name', 'Resource'],
                  ['unit', 'Unit'],
                  ['quantity', 'Quantity'],
                  ['status', 'Status'],
                ),
              ) +
              '<h3>Response assignments</h3>' +
              DMS.miniTable(
                data.assignments,
                columns(
                  ['volunteer_name', 'Volunteer'],
                  ['assignment_role', 'Role'],
                  ['status', 'Status'],
                ),
              ),
          );
      } catch (error) {
        if (token === selection) $('#map-response').textContent = error.message;
      }
    }
    async function load() {
      const token = ++generation;
      abort?.abort();
      abort = new AbortController();
      page = 0;
      clear();
      items = [];
      markers.clear();
      cluster?.clearLayers();
      $('#map-list').innerHTML = '<li>Loading actual database records...</li>';
      $('#unlocated-list').innerHTML = '';
      $('#map-count').textContent = 'Loading...';
      const params = Object.fromEntries(
        [...new FormData($('#map-filters'))].filter(([, value]) => value !== ''),
      );
      if (params.start && params.end && params.start > params.end) {
        DMS.message('From date must not follow Through date.');
        return;
      }
      try {
        let offset = 0,
          all = [];
        while (true) {
          const data = await DMS.api(
            '/api/intelligence/incidents?' + new URLSearchParams({ ...params, limit: 200, offset }),
            { signal: abort.signal },
          );
          if (token !== generation) return;
          all.push(...data.items);
          if (!data.has_more) break;
          offset += data.items.length;
          if (!data.items.length) break;
          $('#map-count').textContent = `${all.length} / ${data.total} loaded`;
        }
        items = all;
        renderList();
        if (map) {
          for (const row of items.filter((r) => r.plottable)) {
            const pin = marker(row);
            pin.bindPopup(
              `<strong>${esc(row.title)}</strong><br>${esc(human(row.review_status))}<br>${esc(human(row.severity))}`,
            );
            pin.on('click', () => select(row));
            markers.set(row.kind + ':' + row.id, pin);
            cluster.addLayer(pin);
          }
        }
        $('#page-error').textContent = '';
      } catch (error) {
        if (error.name === 'AbortError' || token !== generation) return;
        DMS.message(error);
        $('#map-list').innerHTML =
          '<li>Incident data unavailable. Check MySQL and choose Refresh.</li>';
        $('#map-count').textContent = 'Unavailable';
      }
    }
    const choose = (e) => {
      const button = e.target.closest('[data-kind]');
      if (!button) return;
      const row = items.find(
        (r) => r.kind === button.dataset.kind && r.id === Number(button.dataset.id),
      );
      if (row) select(row);
    };
    $('#map-list').addEventListener('click', choose);
    $('#unlocated-list').addEventListener('click', choose);
    $('#map-filters').addEventListener('submit', (e) => {
      e.preventDefault();
      load();
    });
    let timer;
    $('#map-filters [name=q]').addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(load, 400);
    });
    $('#map-reset').addEventListener('click', () => {
      clearTimeout(timer);
      $('#map-filters').reset();
      load();
    });
    $('#map-refresh').addEventListener('click', load);
    $('#map-clear').addEventListener('click', () => {
      map?.closePopup();
      clear();
    });
    $('#map-prev').addEventListener('click', () => {
      page--;
      renderList();
    });
    $('#map-next').addEventListener('click', () => {
      page++;
      renderList();
    });
    $('#map-india').addEventListener('click', () =>
      map?.fitBounds([
        [6.4, 68],
        [37.6, 97.5],
      ]),
    );
    try {
      map = await baseMap($('#india-map'), $('#tile-note'));
      cluster = L.markerClusterGroup({
        chunkedLoading: true,
        iconCreateFunction: (group) =>
          L.divIcon({
            html: `<span class="cluster-count">${group.getChildCount()}</span>`,
            className: 'cluster-marker',
            iconSize: [36, 36],
          }),
      }).addTo(map);
      map.boundaryLayer?.eachLayer((layer) =>
        layer.on('click', () => {
          $('#map-filters [name=state]').value = (layer.feature.properties.shapeName || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '');
          load();
        }),
      );
    } catch (error) {
      $('#tile-note').textContent = error.message;
      $('#india-map').innerHTML =
        '<div class="empty">Map unavailable. Use the incident list.</div>';
    }
    load();
  }
  function timelineHtml(data) {
    return /* HTML */ `<h3>Recorded timeline</h3>
      <p class="muted">${esc(data.history_note)}</p>
      ${data.items.length
        ? /* HTML */ `<ol class="timeline">
            ${data.items
              .map(
                (event) =>
                  /* HTML */ `<li>
                    <time>${esc(event.timestamp)}</time><strong>${esc(human(event.action))}</strong>
                    <p>
                      ${esc(event.description)}${event.actor_name
                        ? ' · ' + esc(event.actor_name)
                        : ' · Actor not recorded'}
                    </p>
                    ${event.after
                      ? /* HTML */ `<p>
                          ${esc(
                            Object.entries(event.after)
                              .map(([k, v]) => human(k) + ': ' + (v ?? 'Unavailable'))
                              .join(' · '),
                          )}
                        </p>`
                      : ''}
                  </li>`,
              )
              .join('')}
          </ol>`
        : '<p class="muted">No historical events recorded.</p>'}`;
  }
  function shelterHtml(data) {
    return /* HTML */ `<h3>Nearest available shelters</h3>
      <p class="muted">${esc(data.distance_method || data.reason || '')}</p>
      ${data.items.length
        ? DMS.miniTable(
            data.items,
            columns(
              ['name', 'Shelter'],
              ['address', 'Address'],
              ['distance_km', 'Distance km'],
              ['available_capacity', 'Available spaces'],
              ['capacity', 'Capacity'],
              ['current_occupancy', 'Occupancy'],
              ['status', 'Status'],
            ),
          )
        : ''}`;
  }
  function bars(title, rows) {
    const max = Math.max(0, ...rows.map((r) => Number(r.count)));
    return /* HTML */ `<section class="panel panel-body">
      <h2>${esc(title)}</h2>
      ${max
        ? /* HTML */ `<div class="bar-chart" aria-label="${esc(title)}">
            ${rows
              .map(
                (row) =>
                  /* HTML */ `<div class="bar-row">
                    <span>${esc(human(row.label))}</span>
                    <div class="bar-track" aria-hidden="true">
                      <div class="bar-fill" style="width:${(Number(row.count) / max) * 100}%"></div>
                    </div>
                    <strong>${esc(row.count)}</strong>
                  </div>`,
              )
              .join('')}
          </div>`
        : '<p class="muted">No recorded data for this summary.</p>'}
    </section>`;
  }
  async function overview() {
    if (!DMS.isAdmin()) return;
    const wrapper = document.createElement('section');
    wrapper.id = 'v2-overview';
    wrapper.innerHTML = /* HTML */ `<div class="dashboard-grid">
        <section class="panel panel-body">
          <div class="panel-head">
            <h2>India incident preview</h2>
            <a class="btn" href="india-map.html">Open full map</a>
          </div>
          <div class="map-canvas map-preview" id="overview-map"></div>
          <p class="muted" id="overview-map-note">Loading map...</p>
        </section>
        <section class="panel panel-body" id="urgent-summary">
          Loading response intelligence...
        </section>
      </div>
      <div id="overview-charts"></div>`;
    $('#dashboard-data').prepend(wrapper);
    try {
      const data = await DMS.api('/api/intelligence/overview/summary');
      if (!document.contains(wrapper)) return;
      $('#overview-charts').innerHTML = /* HTML */ `<div class="chart-grid">
          ${bars('Disasters by type', data.types)}${bars('Recorded severity', data.severity)}${bars(
            'Active incidents by state',
            data.states,
          )}${bars('Monthly incident trend', data.trend.slice().reverse())}
        </div>
        <div class="dashboard-grid">
          <section class="panel">
            <div class="panel-head">
              <h2>Unfulfilled demand</h2>
              <a class="btn small" href="resources.html#requests">Manage requests</a>
            </div>
            <div class="table-wrap">
              ${DMS.miniTable(
                data.requests,
                columns(
                  ['resource_name', 'Resource'],
                  ['unit', 'Unit'],
                  ['outstanding_quantity', 'Outstanding'],
                  ['available_quantity', 'Available'],
                ),
              )}
            </div>
          </section>
          <section class="panel">
            <div class="panel-head"><h2>Shelter capacity warnings</h2></div>
            <div class="table-wrap">
              ${DMS.miniTable(
                data.shelter_warnings,
                columns(
                  ['name', 'Shelter'],
                  ['status', 'Status'],
                  ['capacity', 'Capacity'],
                  ['current_occupancy', 'Occupancy'],
                  ['status', 'Status'],
                ),
              )}
            </div>
          </section>
        </div>`;
      $('#urgent-summary').innerHTML = /* HTML */ `<h2>Supplies requiring attention</h2>
        <p class="muted">
          Shortages compare available stock with each resource's minimum. Units remain separate.
        </p>
        ${DMS.miniTable(
          data.shortages,
          columns(
            ['resource_name', 'Resource'],
            ['unit', 'Unit'],
            ['available_quantity', 'Available'],
            ['shortage', 'Below minimum'],
          ),
        )}
        <h3 style="margin-top:20px">Recent confirmed reports</h3>
        ${DMS.miniTable(
          data.recent_confirmed,
          columns(
            ['report_id', 'Report'],
            ['disaster_id', 'Official incident'],
            ['severity', 'Severity'],
            ['reviewed_at', 'Reviewed'],
          ),
        )}`;
    } catch (error) {
      if (document.contains(wrapper)) $('#urgent-summary').textContent = error.message;
    }
    try {
      const map = await baseMap($('#overview-map'), $('#overview-map-note'));
      const data = await DMS.api('/api/intelligence/incidents?limit=200');
      if (!document.contains(wrapper)) {
        map.remove();
        return;
      }
      for (const row of data.items.filter((r) => r.plottable)) {
        marker(row)
          .bindPopup(
            `<strong>${esc(row.title)}</strong><br>${esc(human(row.review_status))}<br><a href="india-map.html">Open full map</a>`,
          )
          .addTo(map);
      }
      $('#overview-map-note').textContent =
        `Preview: ${data.items.length} of ${data.total} records. Records without coordinates remain in the full map list. Boundaries: geoBoundaries / DataMeet / ECI.`;
    } catch (error) {
      if (document.contains(wrapper)) $('#overview-map-note').textContent = error.message;
    }
  }
  async function downloadCSV(module, filters = {}) {
    const response = await fetch(
      DMS.base + '/api/exports/' + module + '.csv?' + new URLSearchParams(filters),
      { credentials: 'include', headers: { 'X-DMS-Request': '1' } },
    );
    if (!response.ok) {
      let data;
      try {
        data = await response.json();
      } catch {}
      if (response.status === 401) location.replace('login.html');
      throw new Error(data?.detail || 'Export failed');
    }
    const blob = await response.blob(),
      url = URL.createObjectURL(blob),
      link = document.createElement('a');
    link.href = url;
    link.download =
      (response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/) || [])[1] ||
      `dms-${module}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function moduleActions(page) {
    if (['disasters', 'emergency-reports', 'resources', 'resource-allocations'].includes(page)) {
      const actions = $('#view .page-heading .actions');
      const button = document.createElement('button');
      button.className = 'btn';
      button.textContent = 'Export CSV';
      actions.append(button);
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          await downloadCSV(page, DMS.filters);
        } catch (error) {
          DMS.message(error);
        } finally {
          button.disabled = false;
        }
      });
      const print = document.createElement('button');
      print.className = 'btn';
      print.textContent = 'Print summary';
      actions.append(print);
      print.addEventListener('click', () =>
        location.assign('print.html?' + new URLSearchParams({ module: page, ...DMS.filters })),
      );
    }
    const reference = new URLSearchParams(location.search).get('record_id');
    if (reference) {
      const search = $('#search');
      search.value = reference;
      search.dispatchEvent(new Event('input'));
    }
    if (page === 'resources') {
      const holder = document.createElement('section');
      holder.id = 'requests';
      holder.className = 'panel';
      holder.style.marginTop = '24px';
      holder.innerHTML = /* HTML */ `<div class="panel-head">
          <h2>Demand and recommendations</h2>
          <div class="actions">
            <button class="btn" id="requests-refresh">Refresh demand</button
            ><button class="btn primary" id="demand-add">Add demand</button>
          </div>
        </div>
        <div id="demand-error" class="message"></div>
        <div class="table-wrap" id="demand-table"></div>
        <div class="pagination">
          <span id="demand-count"></span>
          <div class="actions">
            <button class="btn small" id="demand-prev">Previous</button
            ><button class="btn small" id="demand-next">Next</button>
          </div>
        </div>`;
      $('#view').append(holder);
      let offset = 0,
        rows = [],
        generation = 0;
      async function load() {
        const token = ++generation;
        $('#demand-table').innerHTML = '<div class="empty">Loading actual requests...</div>';
        $('#demand-prev').disabled = true;
        $('#demand-next').disabled = true;
        $('#demand-error').textContent = '';
        try {
          const data = await DMS.api(`/api/resource-requests/?limit=25&offset=${offset}`);
          if (token !== generation) return;
          rows = data.items;
          $('#demand-table').innerHTML = rows.length
            ? /* HTML */ `<table>
                <thead>
                  <tr>
                    <th>Incident / resource</th>
                    <th>Demand</th>
                    <th>Allocated / delivered</th>
                    <th>Available / shortage</th>
                    <th>Recommendation</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${rows
                    .map(
                      (row) =>
                        /* HTML */ `<tr>
                          <td>
                            ${esc(row.disaster_title)}<br />${esc(row.resource_name)}
                            <small>${esc(row.unit)}</small>
                          </td>
                          <td>${esc(row.quantity)}<br />${esc(human(row.fulfillment))}</td>
                          <td>${esc(row.allocated_quantity)} / ${esc(row.delivered_quantity)}</td>
                          <td>${esc(row.available_quantity)} / ${esc(row.shortage_quantity)}</td>
                          <td>
                            ${esc(row.recommended_quantity)} ${esc(row.unit)}<small
                              style="display:block"
                              >${esc(row.recommendation_reason)}</small
                            >
                          </td>
                          <td>
                            <div class="row-actions">
                              <button
                                class="btn small"
                                data-demand-action="approve"
                                data-id="${row.request_id}"
                                ${Number(row.recommended_quantity) <= 0 ? 'disabled' : ''}
                              >
                                Approve / adjust</button
                              ><button
                                class="btn small"
                                data-demand-action="edit"
                                data-id="${row.request_id}"
                                ${row.status !== 'OPEN' ? 'disabled' : ''}
                              >
                                Edit</button
                              ><button
                                class="btn small"
                                data-demand-action="cancel"
                                data-id="${row.request_id}"
                                ${row.status !== 'OPEN' ? 'disabled' : ''}
                              >
                                Cancel
                              </button>
                            </div>
                          </td>
                        </tr>`,
                    )
                    .join('')}
                </tbody>
              </table>`
            : '<div class="empty">No demand recorded. Add an actual incident/resource request; suggestions will never change stock automatically.</div>';
          $('#demand-count').textContent =
            `${data.total} requests · Page ${Math.floor(offset / 25) + 1}`;
          $('#demand-prev').disabled = offset === 0;
          $('#demand-next').disabled = offset + 25 >= data.total;
        } catch (error) {
          if (token === generation) {
            $('#demand-error').textContent = error.message;
            $('#demand-table').innerHTML =
              '<div class="empty">Requests unavailable. Apply the V2 migration and retry.</div>';
          }
        }
      }
      $('#requests-refresh').addEventListener('click', load);
      $('#demand-add').addEventListener('click', () => demandForm(null, 'create', load));
      $('#demand-prev').addEventListener('click', () => {
        offset -= 25;
        load();
      });
      $('#demand-next').addEventListener('click', () => {
        offset += 25;
        load();
      });
      $('#demand-table').addEventListener('click', (e) => {
        const button = e.target.closest('[data-demand-action]');
        if (!button) return;
        const row = rows.find((r) => r.request_id === Number(button.dataset.id));
        if (row) demandForm(row, button.dataset.demandAction, load);
      });
      load();
    }
  }
  async function demandForm(row, action, refresh) {
    const fields =
      action === 'create'
        ? [
            relation('disaster_id', 'Official disaster', 'disasters'),
            relation('resource_id', 'Resource', 'resources'),
            field('quantity', 'Requested quantity', 'number', true, { min: 0.01, step: '0.01' }),
            field('note', 'Demand note', 'textarea', false, { max: 500 }),
          ]
        : action === 'edit'
          ? [
              field('quantity', 'Requested quantity', 'number', true, { min: 0.01, step: '0.01' }),
              field('note', 'Demand note', 'textarea', false, { max: 500 }),
            ]
          : action === 'approve'
            ? [
                field('quantity', 'Quantity to approve', 'number', true, {
                  min: 0.01,
                  step: '0.01',
                }),
              ]
            : [];
    const values = action === 'approve' ? { quantity: row.recommended_quantity } : row || {};
    const dialog = DMS.openDialog(
      human(action) + ' resource demand',
      /* HTML */ `<div id="form-error" class="message" role="alert"></div>
        <p class="muted">
          ${action === 'approve'
            ? esc(row.recommendation_reason)
            : action === 'cancel'
              ? 'Cancel this demand? Linked allocations must be cancelled first.'
              : 'Record demand for one inventory resource and its existing unit.'}
        </p>
        <form id="demand-form">
          <div class="form-grid">${DMS.formFields(fields, values)}</div>
        </form>`,
      '<button class="btn primary" type="submit" form="demand-form" id="demand-save">' +
        human(action) +
        '</button>',
    );
    const idempotency = crypto.randomUUID();
    let busy = false;
    if (action === 'create') {
      const save = $('#demand-save');
      save.disabled = true;
      try {
        await DMS.populateLookups();
        if (dialog.open) save.disabled = false;
      } catch (error) {
        DMS.message(error, '#form-error');
      }
    }
    $('#demand-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      busy = true;
      const save = $('#demand-save'),
        close = $('#dialog-close');
      save.disabled = true;
      close.disabled = true;
      const stop = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stop);
      try {
        const data = DMS.collect(fields);
        if (action === 'approve') data.idempotency_key = idempotency;
        const path =
          '/api/resource-requests/' +
          (row
            ? row.request_id +
              (action === 'approve' ? '/approve' : action === 'cancel' ? '/cancel' : '')
            : '');
        const result = await DMS.api(path, {
          method: action === 'edit' ? 'PUT' : 'POST',
          body: JSON.stringify(data),
        });
        dialog.close();
        DMS.toast(result.message);
        await refresh();
      } catch (error) {
        DMS.showFieldErrors(error);
      } finally {
        busy = false;
        save.disabled = false;
        close.disabled = false;
        dialog.removeEventListener('cancel', stop);
      }
    });
  }
  async function detailActions(page, row, dialog) {
    const parent = dialog.querySelector('.dialog-body');
    if (!parent) return;
    const holder = document.createElement('section');
    holder.className = 'detail-extra';
    parent.append(holder);
    if (['disasters', 'emergency-reports'].includes(page)) {
      const kind = page === 'disasters' ? 'disaster' : 'report',
        id = row[modules[page].id];
      holder.innerHTML = /* HTML */ `<div class="actions">
          <a class="btn" href="print.html?kind=${kind}&id=${id}">Print / Save as PDF</a
          ><button class="btn" id="detail-csv">Export record CSV</button>${DMS.isAdmin()
            ? `<a class="btn" href="audit-history.html?entity=${page.replaceAll('-', '_')}&record_id=${id}">Inspect audit history</a>`
            : ''}
        </div>
        <div id="detail-history">Loading recorded history...</div>`;
      holder.querySelector('#detail-csv').addEventListener('click', async (e) => {
        e.target.disabled = true;
        try {
          await downloadCSV(page, { record_id: id });
        } catch (error) {
          DMS.toast(error.message);
        } finally {
          e.target.disabled = false;
        }
      });
      try {
        const timeline = await DMS.api(`/api/intelligence/${kind}/${id}/timeline`);
        if (!dialog.open || !document.contains(holder)) return;
        holder.querySelector('#detail-history').innerHTML = timelineHtml(timeline);
        if (DMS.isAdmin()) {
          const shelters = await DMS.api(`/api/intelligence/${kind}/${id}/shelters`);
          if (dialog.open && document.contains(holder))
            holder.insertAdjacentHTML('beforeend', shelterHtml(shelters));
        }
      } catch (error) {
        if (document.contains(holder))
          holder.querySelector('#detail-history').textContent = error.message;
      }
    } else if (page === 'resources') {
      holder.innerHTML = /* HTML */ `<h3>Resource movement history</h3>
        <p class="muted">
          Opening balances start at creation or migration. Earlier movements may be unknown.
        </p>
        <a class="btn" href="resource-movements.html?resource_id=${row.resource_id}"
          >Full resource ledger</a
        >
        <div id="resource-history">Loading movements...</div>`;
      try {
        const result = await DMS.api(
          `/api/resource-movements/?resource_id=${row.resource_id}&limit=25`,
        );
        if (dialog.open && document.contains(holder))
          holder.querySelector('#resource-history').innerHTML = DMS.miniTable(
            result.items,
            columns(
              ['created_at', 'Time'],
              ['movement_kind', 'Movement'],
              ['available_delta', 'Available change'],
              ['available_after', 'Available after'],
              ['note', 'Note'],
            ),
          );
      } catch (error) {
        if (document.contains(holder))
          holder.querySelector('#resource-history').textContent = error.message;
      }
    } else if (DMS.isAdmin()) {
      holder.innerHTML = `<a class="btn" href="audit-history.html?entity=${page.replaceAll('-', '_')}&record_id=${row[modules[page].id]}">Inspect record history</a>`;
    }
  }
  function locationPicker(page, dialog, row) {
    if (!['locations', 'disasters', 'shelters', 'emergency-reports'].includes(page)) return;
    const form = dialog.querySelector('#record-form');
    if (!form) return;
    const publicReport = page === 'emergency-reports';
    const box = document.createElement('section');
    box.className = 'picker-box';
    box.innerHTML = /* HTML */ `<h3>Location selection</h3>
      <p class="muted">
        ${page === 'locations'
          ? 'Save only a location you have checked. A place match does not verify an incident.'
          : publicReport
            ? 'Choose a saved location above, or describe an unfamiliar place below. Reporting does not modify the official directory.'
            : 'Choose a saved location. Add official places through Locations if needed.'}
      </p>
      ${page !== 'locations'
        ? '<label>Find a saved location<input id="saved-location-query" type="search" maxlength="150" placeholder="City or address"></label><div id="saved-location-results" class="picker-results"></div>'
        : ''}
      ${publicReport
        ? /* HTML */ `<label
              >Unfamiliar location description<textarea
                name="reported_location_text"
                maxlength="500"
                placeholder="Locality, nearby landmark and state"
              ></textarea>
            </label>
            <div class="form-grid">
              <label
                >Reported latitude<input
                  type="number"
                  name="reported_latitude"
                  min="-90"
                  max="90"
                  step="0.0000001" /></label
              ><label
                >Reported longitude<input
                  type="number"
                  name="reported_longitude"
                  min="-180"
                  max="180"
                  step="0.0000001"
              /></label>
            </div>`
        : ''}
      ${page === 'locations' || publicReport
        ? /* HTML */ `<label
              >Place lookup<input
                id="place-query"
                type="search"
                maxlength="150"
                placeholder="Public city or locality; exclude personal details"
            /></label>
            <div class="actions">
              <button type="button" class="btn" id="place-search">Search places</button
              ><button type="button" class="btn" id="point-select">Select a map point</button
              ><button type="button" class="btn" id="point-clear">Clear coordinates</button>
            </div>
            <p class="muted" id="place-status">
              Place queries go to Photon / OpenStreetMap. Search is optional; text-only locations
              are supported.
            </p>
            <div id="place-results" class="picker-results"></div>
            <div id="picker-map" class="map-canvas picker-map" hidden></div>`
        : '<a class="btn" href="locations.html" target="_blank" rel="noopener">Manage official locations</a>'}`;
    form.append(box);
    box.dataset.source = row?.coordinate_source || 'USER_ENTERED';
    let generation = 0,
      pointMap,
      pointMarker;
    const setValue = (name, value) => {
      const el = form.querySelector(`[name="${name}"]`);
      if (el) el.value = value ?? '';
    };
    if (publicReport && row) {
      for (const name of ['reported_location_text', 'reported_latitude', 'reported_longitude'])
        setValue(name, row[name]);
    }
    const clearCoordinates = () => {
      if (pointMarker && pointMap) {
        pointMap.removeLayer(pointMarker);
        pointMarker = null;
      }
      setValue(publicReport ? 'reported_latitude' : 'latitude', '');
      setValue(publicReport ? 'reported_longitude' : 'longitude', '');
      box.dataset.source = 'USER_ENTERED';
    };
    if (publicReport) {
      const official = form.querySelector('[name=location_id]');
      official?.addEventListener('change', () => {
        if (official.value) {
          setValue('reported_location_text', '');
          clearCoordinates();
        }
      });
      box.querySelector('[name=reported_location_text]').addEventListener('input', () => {
        if (form.querySelector('[name=reported_location_text]').value) setValue('location_id', '');
      });
    }
    if (page !== 'locations') {
      let timer;
      box.querySelector('#saved-location-query').addEventListener('input', (e) => {
        clearTimeout(timer);
        const query = e.target.value;
        const token = ++generation;
        timer = setTimeout(async () => {
          try {
            const data = await DMS.api(
              '/api/lookups/locations?' + new URLSearchParams({ q: query }),
            );
            if (!dialog.open || token !== generation) return;
            box.querySelector('#saved-location-results').innerHTML = data.items.length
              ? data.items
                  .map(
                    (r) =>
                      `<button type="button" class="btn" data-location="${r.id}">${esc(r.label)}</button>`,
                  )
                  .join('')
              : '<p class="muted">No saved location found.</p>';
          } catch (error) {
            if (token === generation)
              box.querySelector('#saved-location-results').textContent = error.message;
          }
        }, 400);
      });
      box.querySelector('#saved-location-results').addEventListener('click', (e) => {
        const button = e.target.closest('[data-location]');
        if (!button) return;
        const select = form.querySelector('[name=location_id]');
        let option = [...select.options].find((o) => o.value === button.dataset.location);
        if (!option) {
          option = new Option(button.textContent, button.dataset.location);
          select.add(option);
        }
        select.value = button.dataset.location;
        select.dispatchEvent(new Event('change'));
        box.querySelector('#saved-location-results').textContent =
          'Selected: ' + button.textContent;
      });
    }
    if (page !== 'locations' && !publicReport) return;
    for (const name of publicReport
      ? ['reported_latitude', 'reported_longitude']
      : ['latitude', 'longitude'])
      form.querySelector(`[name=${name}]`)?.addEventListener('input', () => {
        box.dataset.source = 'USER_ENTERED';
      });
    function applyPoint(latitude, longitude, source) {
      if (pointMap) {
        if (pointMarker) pointMap.removeLayer(pointMarker);
        pointMarker = L.circleMarker([latitude, longitude], {
          radius: 8,
          color: '#202020',
          fillColor: '#f28c28',
          fillOpacity: 1,
        }).addTo(pointMap);
      }
      setValue(publicReport ? 'reported_latitude' : 'latitude', Number(latitude).toFixed(7));
      setValue(publicReport ? 'reported_longitude' : 'longitude', Number(longitude).toFixed(7));
      if (publicReport) setValue('location_id', '');
      box.dataset.source = source;
      box.querySelector('#place-status').textContent =
        `Selected ${Number(latitude).toFixed(6)}, ${Number(longitude).toFixed(6)} · ${human(source)}. Confirm the address text yourself.`;
    }
    box.querySelector('#point-clear').addEventListener('click', () => {
      clearCoordinates();
      box.querySelector('#place-status').textContent =
        'Coordinates cleared. The location can be saved as text.';
    });
    box.querySelector('#place-search').addEventListener('click', async (e) => {
      const q = box.querySelector('#place-query').value.trim();
      if (q.length < 3) {
        box.querySelector('#place-status').textContent = 'Enter at least three characters.';
        return;
      }
      const token = ++generation,
        button = e.target;
      button.disabled = true;
      try {
        const data = await DMS.api('/api/intelligence/places/search?' + new URLSearchParams({ q }));
        if (!dialog.open || token !== generation) return;
        box.querySelector('#place-results').innerHTML = data.items.length
          ? data.items
              .map(
                (r, i) =>
                  `<button type="button" class="btn" data-place="${i}">${esc(r.label)}</button>`,
              )
              .join('')
          : '<p class="muted">No place match. Use text or select a point.</p>';
        box.querySelector('#place-status').textContent = data.attribution;
        box.querySelectorAll('[data-place]').forEach((b) =>
          b.addEventListener('click', () => {
            const place = data.items[Number(b.dataset.place)];
            applyPoint(place.latitude, place.longitude, 'GEOCODER');
            if (publicReport) setValue('reported_location_text', place.label);
            else {
              setValue('address', place.label.slice(0, 255));
              for (const name of ['city', 'district', 'state'])
                if (place[name]) setValue(name, place[name]);
            }
            box.querySelector('#place-results').textContent =
              'Selected place match: ' + place.label;
          }),
        );
      } catch (error) {
        if (token === generation) box.querySelector('#place-status').textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
    box.querySelector('#point-select').addEventListener('click', async () => {
      const mapEl = box.querySelector('#picker-map');
      mapEl.hidden = false;
      if (pointMap) {
        pointMap.invalidateSize();
        return;
      }
      try {
        pointMap = await baseMap(mapEl, box.querySelector('#place-status'), true);
        pointMap.on('click', (event) => {
          const { lat, lng } = event.latlng;
          if (lat < 6 || lat > 38 || lng < 68 || lng > 98) {
            box.querySelector('#place-status').textContent = 'Select within the India map extent.';
            return;
          }
          applyPoint(lat, lng, 'MAP_POINT');
        });
        dialog.addEventListener(
          'close',
          () => {
            pointMap.remove();
          },
          { once: true },
        );
      } catch (error) {
        box.querySelector('#place-status').textContent = error.message;
      }
    });
  }
  function collectLocation(data, page) {
    const box = $('#dialog .picker-box');
    if (!box) return data;
    if (page === 'locations') data.coordinate_source = box.dataset.source;
    if (page === 'emergency-reports') {
      const text = $('#dialog [name=reported_location_text]').value.trim();
      if (!data.location_id) {
        data.reported_location_text = text || null;
        for (const name of ['reported_latitude', 'reported_longitude'])
          data[name] = $(`#dialog [name=${name}]`).value || null;
        data.coordinate_source = box.dataset.source;
      }
      if (!data.location_id && !text)
        throw new Error('Choose a saved location or describe the unfamiliar location.');
    }
    return data;
  }
  async function printPage() {
    const query = new URLSearchParams(location.search),
      kind = query.get('kind'),
      id = query.get('id'),
      module = query.get('module');
    $('#view').innerHTML =
      DMS.heading(
        'Incident reporting',
        'Print this view and choose Save as PDF in your browser. PDF files are generated by the browser, not downloaded by this page.',
        '<button class="btn primary" id="print-button" disabled>Print / Save as PDF</button>',
      ) + '<div id="print-data" class="report-document">Loading authorized records...</div>';
    $('#print-button').addEventListener('click', () => window.print());
    try {
      if (kind && id) {
        const data = await DMS.api(
          `/api/intelligence/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/report`,
        );
        const row = data.incident;
        $('#print-data').innerHTML = /* HTML */ `<header>
            <div class="eyebrow">Disaster Management System</div>
            <h1>${esc(row.title || 'Emergency report')} #${esc(id)}</h1>
            <p>Generated ${esc(data.generated_at)} · Version ${esc(data.version)}</p>
          </header>
          <h2>Incident details</h2>
          <dl class="details">
            ${Object.entries(row)
              .filter(([k]) => !['reported_by', 'reviewed_by', 'description'].includes(k))
              .map(([k, v]) => `<dt>${esc(human(k))}</dt><dd>${esc(v ?? 'Unavailable')}</dd>`)
              .join('')}
            <dt>Location</dt>
            <dd>
              ${esc(
                [data.location.city, data.location.address, data.location.state]
                  .filter(Boolean)
                  .join(', '),
              )}
            </dd>
            <dt>Coordinates</dt>
            <dd>${esc(data.latitude ?? 'Unavailable')}, ${esc(data.longitude ?? 'Unavailable')}</dd>
          </dl>
          <h2>Description</h2>
          <p>${esc(row.description || 'No description recorded.')}</p>
          <section>${timelineHtml(data.timeline)}</section>
          <h2>Resource allocations</h2>
          ${DMS.miniTable(
            data.allocations,
            columns(
              ['allocation_id', 'Reference'],
              ['resource_name', 'Resource'],
              ['unit', 'Unit'],
              ['quantity', 'Quantity'],
              ['status', 'Status'],
              ['allocation_date', 'Date'],
            ),
          )}
          <h2>Response assignments</h2>
          ${DMS.miniTable(
            data.assignments,
            columns(
              ['volunteer_name', 'Volunteer'],
              ['assignment_role', 'Role'],
              ['status', 'Status'],
              ['start_time', 'Start'],
            ),
          )}
          <section>${shelterHtml(data.shelters)}</section>
          <footer class="report-footer">
            Disaster Management System · ${esc(kind)} #${esc(id)} · Report generated from stored
            records. ${esc(data.timeline.history_note)}
          </footer>`;
      } else if (
        ['disasters', 'emergency-reports', 'resources', 'resource-allocations'].includes(module)
      ) {
        const filters = Object.fromEntries(query);
        delete filters.module;
        delete filters.offset;
        delete filters.limit;
        const records = [];
        let offset = 0;
        while (true) {
          const data = await DMS.api(
            '/api/' + module + '/?' + new URLSearchParams({ ...filters, limit: 200, offset }),
          );
          const rows = data[modules[module].key || module];
          records.push(...rows);
          if (offset + rows.length >= data.total || !rows.length) break;
          offset += rows.length;
          $('#print-data').textContent =
            `Loading matching records: ${records.length} / ${data.total}`;
        }
        const idfield = modules[module].id;
        $('#print-data').innerHTML = /* HTML */ `<header>
            <div class="eyebrow">Disaster Management System</div>
            <h1>${esc(modules[module].title)} summary</h1>
            <p>
              Generated ${esc(new Date().toLocaleString())} · ${records.length} matching records
            </p>
            <p>
              Filters:
              ${esc(
                Object.entries(filters)
                  .map(([k, v]) => human(k) + ': ' + v)
                  .join(', ') || 'All records',
              )}
            </p>
          </header>
          <h2>Matching records</h2>
          ${DMS.miniTable(records, [
            { key: idfield, label: 'Reference' },
            ...modules[module].columns,
          ])}
          <footer class="report-footer">
            Disaster Management System · Actual authorized database records
          </footer>`;
      } else
        throw new Error('Choose an incident report or supported summary from its management page.');
      $('#print-button').disabled = false;
    } catch (error) {
      DMS.message(error);
      $('#print-data').textContent =
        'Report unavailable. Check permissions, the record reference and the database connection.';
    }
  }
  return {
    relatedNavigation,
    mapPage,
    overview,
    moduleActions,
    detailActions,
    locationPicker,
    collectLocation,
    printPage,
  };
})();
