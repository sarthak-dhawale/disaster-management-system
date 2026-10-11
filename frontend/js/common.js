/* Shared UI and API controller. All displayed records come from the backend. */
const DMS = (() => {
  const extraPages = {
    'audit-history': 'Audit history',
    'resource-movements': 'Resource ledger',
    analytics: 'Analytical reports',
    'india-map': 'India map',
    print: 'Print report',
  };
  const API = `http://${location.hostname || '127.0.0.1'}:8001`;
  const esc = (value) =>
    String(value ?? '').replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c],
    );
  const human = (value) =>
    String(value ?? '')
      .toLowerCase()
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  const $ = (selector) => document.querySelector(selector);
  let user,
    page,
    config,
    offset = 0,
    total = 0,
    records = [],
    sequence = 0,
    controller,
    toastTimer;
  let filters = {},
    sort = 'desc',
    dialogGeneration = 0;
  const theme =
    localStorage.getItem('dms-theme') ||
    (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = theme;

  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(API + path, {
        credentials: 'include',
        ...options,
        headers: { 'Content-Type': 'application/json', 'X-DMS-Request': '1', ...options.headers },
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      if ($('#connection')) $('#connection').textContent = 'Database unavailable';
      throw new Error('Cannot reach the API. Start FastAPI on port 8001 and check the connection.');
    }
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`The server returned an unreadable response (${response.status}).`);
    }
    if (!response.ok) {
      if (response.status === 503 && $('#connection'))
        $('#connection').textContent = 'Database unavailable';
      if (response.status === 401 && page !== 'login') {
        location.replace('login.html');
      }
      const error = new Error(
        typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`,
      );
      error.errors = data.errors;
      error.status = response.status;
      throw error;
    }
    if (path.startsWith('/api/') && !path.startsWith('/api/auth/') && $('#connection'))
      $('#connection').textContent = 'Database connected';
    return data;
  }
  function toast(message) {
    $('#toast').textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      $('#toast').textContent = '';
    }, 6000);
  }
  function message(error, element = '#page-error') {
    const el = $(element);
    if (el) {
      el.textContent = error.message || String(error);
      el.setAttribute('role', 'alert');
    }
  }
  function clearMessage(element = '#page-error') {
    const el = $(element);
    if (el) el.textContent = '';
  }
  function isAdmin() {
    return ['ADMIN', 'DISASTER_MANAGER'].includes(user?.role);
  }
  function permitted(key) {
    return (
      ['emergency-reports', 'india-map', 'print'].includes(key) ||
      (isAdmin() && (key !== 'users' || user.role === 'ADMIN'))
    );
  }
  function badge(value) {
    const warning = [
      'PENDING',
      'PENDING_REVIEW',
      'MEDIUM',
      'HIGH',
      'REPORTED',
      'ASSIGNED',
      'FULL',
      'IN_PROGRESS',
    ];
    const danger = ['CRITICAL', 'REJECTED', 'SUSPENDED', 'CLOSED'];
    const neutral = ['LOW', 'LEGACY', 'INACTIVE', 'UNAVAILABLE', 'CANCELLED'];
    const cls = danger.includes(value)
      ? 'danger'
      : warning.includes(value)
        ? 'warning'
        : neutral.includes(value)
          ? 'neutral'
          : '';
    return `<span class="badge ${cls}">${esc(human(value))}</span>`;
  }
  function format(value, key) {
    if (value === null || value === undefined || value === '')
      return '<span class="muted">—</span>';
    if (['status', 'review_status', 'severity', 'availability_status', 'role'].includes(key))
      return badge(value);
    if (['disaster_type', 'report_type', 'category'].includes(key)) return esc(human(value));
    if (/(?:_at|_time|check_in|check_out|allocation_date|joined_at)$/.test(key)) {
      const date = new Date(String(value).replace(' ', 'T'));
      return esc(
        Number.isNaN(date.getTime())
          ? value
          : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }),
      );
    }
    return esc(value);
  }
  function shell() {
    const activePage =
      {
        'resource-allocations': 'resources',
        'resource-movements': 'resources',
        'shelter-registrations': 'shelters',
        'volunteer-assignments': 'volunteers',
        analytics: 'index',
        'audit-history': 'users',
      }[page] || page;
    const nav = [
      ['index', 'Overview'],
      ['india-map', 'India map'],
      ...(isAdmin() ? [['disasters', 'Disasters']] : []),
      ['emergency-reports', 'Emergency reports'],
      ...(isAdmin()
        ? [
            ['shelters', 'Shelters'],
            ['resources', 'Resources'],
            ['volunteers', 'Volunteers / Teams'],
            ['locations', 'Locations'],
          ]
        : []),
      ['search', 'Search'],
      ...(user.role === 'ADMIN' ? [['users', 'Administration']] : []),
    ];
    $('#app').innerHTML = /* HTML */ `<div class="layout">
        <aside class="sidebar" id="sidebar" aria-label="Main navigation">
          <div class="brand">
            <div class="brand-mark">DM</div>
            <div><strong>DisasterMS</strong><small>Response operations</small></div>
          </div>
          <div>
            <div class="nav-label">WORKSPACE</div>
            <nav>
              ${nav
                .map(
                  ([key, label]) =>
                    `<a href="${key}.html" ${key === activePage ? 'class="active" aria-current="page"' : ''}>${esc(label)}</a>`,
                )
                .join('')}
            </nav>
          </div>
          <div class="sidebar-foot">
            Version 2.0<br /><span id="connection">Checking database connection…</span>
          </div>
        </aside>
        <div class="workspace">
          <header class="topbar">
            <div class="actions">
              <button
                class="btn menu"
                id="menu"
                aria-label="Toggle navigation"
                aria-expanded="false"
              >
                Menu</button
              ><span class="path"
                >Workspace /
                ${esc(
                  page === 'index' ? 'Overview' : config?.title || extraPages[page] || 'Search',
                )}</span
              >
            </div>
            <div class="account">
              <button class="btn small" id="theme" aria-label="Switch color theme"></button
              ><span class="account-name"
                >${esc(user.full_name)}<small>${esc(human(user.role))}</small></span
              ><button class="btn small" id="logout">Sign out</button>
            </div>
          </header>
          <main class="content" id="main" tabindex="-1">
            <div id="page-error" class="message" role="alert"></div>
            <div id="view"></div>
          </main>
        </div>
      </div>
      <dialog id="dialog" aria-labelledby="dialog-title"></dialog>
      <div id="toast" class="toast" role="status" aria-live="polite"></div>`;
    updateThemeLabel();
    $('#theme').addEventListener('click', () => {
      document.documentElement.dataset.theme =
        document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('dms-theme', document.documentElement.dataset.theme);
      updateThemeLabel();
    });
    $('#menu').addEventListener('click', () => {
      const opened = $('#sidebar').classList.toggle('open');
      $('#menu').setAttribute('aria-expanded', String(opened));
    });
    document.addEventListener('click', (e) => {
      if (
        $('#sidebar').classList.contains('open') &&
        !e.target.closest('.sidebar') &&
        !e.target.closest('#menu')
      ) {
        $('#sidebar').classList.remove('open');
        $('#menu').setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        $('#sidebar').classList.remove('open');
        $('#menu').setAttribute('aria-expanded', 'false');
      }
    });
    $('#logout').addEventListener('click', async (e) => {
      e.target.disabled = true;
      try {
        await api('/api/auth/logout', { method: 'POST' });
        location.replace('login.html');
      } catch (error) {
        message(error);
        e.target.disabled = false;
      }
    });
    api('/health')
      .then(() => {
        $('#connection').textContent = 'Database connected';
      })
      .catch(() => {
        $('#connection').textContent = 'Database unavailable';
      });
  }
  function updateThemeLabel() {
    $('#theme').textContent =
      document.documentElement.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode';
  }
  function heading(title, description, buttons = '') {
    return /* HTML */ `<div class="page-heading">
      <div>
        <div class="eyebrow">Response workspace</div>
        <h1>${esc(title)}</h1>
        <p>${esc(description)}</p>
      </div>
      <div class="actions">${buttons}</div>
    </div>`;
  }
  function listView() {
    const exactReference = new URLSearchParams(location.search).get('record_id');
    if (exactReference) filters.record_id = exactReference;
    $('#view').innerHTML =
      heading(
        config.title,
        !isAdmin()
          ? 'Submit a suspected emergency and track your own reports.'
          : config.description,
        /* HTML */ `<button class="btn" id="refresh">Refresh</button
          ><button class="btn primary" id="add">
            ${page === 'emergency-reports'
              ? 'Report an emergency'
              : `Add ${esc(config.singular.toLowerCase())}`}
          </button>`,
      ) +
      /* HTML */ ` <section class="panel" aria-label="${esc(config.title)} records">
          <div class="toolbar">
            <label class="search"
              >Search<input
                id="search"
                type="search"
                placeholder="Search ${esc(config.title.toLowerCase())}"
                maxlength="150"
            /></label>
            ${Object.entries(config.filters)
              .map(
                ([key, values]) =>
                  /* HTML */ `<label
                    >${esc(human(key))}<select data-filter="${key}">
                      <option value="">All ${esc(human(key).toLowerCase())}</option>
                      ${values
                        .map((v) => `<option value="${v}">${esc(human(v))}</option>`)
                        .join('')}
                    </select></label
                  >`,
              )
              .join('')}
            ${page === 'resources'
              ? '<label>Stock<select data-filter="low_stock"><option value="">All stock</option><option value="true">At or below minimum</option></select></label>'
              : ''}
            <label
              >Order<select id="sort">
                <option value="desc">Newest first</option>
                <option value="asc">Oldest first</option>
                ${['disasters', 'emergency-reports'].includes(page)
                  ? '<option value="priority">Highest priority</option>'
                  : ''}
              </select></label
            ><button class="btn" id="clear">Clear</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  ${config.columns.map((c) => `<th scope="col">${esc(c.label)}</th>`).join('')}
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody id="rows"></tbody>
            </table>
          </div>
          <div class="pagination">
            <span id="count">Loading records…</span>
            <div class="actions">
              <button class="btn small" id="previous">Previous</button
              ><button class="btn small" id="next">Next</button>
            </div>
          </div>
        </section>
        <p class="refresh-time" id="updated"></p>`;
    window.DMSV2?.moduleActions(page);
    $('#add').addEventListener('click', () => editForm());
    $('#refresh').addEventListener('click', () => loadList());
    let timer;
    $('#search').addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        filters.q = $('#search').value.trim();
        offset = 0;
        loadList();
      }, 250);
    });
    document.querySelectorAll('[data-filter]').forEach((el) =>
      el.addEventListener('change', () => {
        filters[el.dataset.filter] = el.value;
        offset = 0;
        loadList();
      }),
    );
    $('#sort').addEventListener('change', () => {
      sort = $('#sort').value;
      offset = 0;
      loadList();
    });
    $('#clear').addEventListener('click', () => {
      clearTimeout(timer);
      filters = {};
      offset = 0;
      sort = 'desc';
      $('#sort').value = 'desc';
      $('#search').value = '';
      document.querySelectorAll('[data-filter]').forEach((el) => (el.value = ''));
      loadList();
    });
    $('#previous').addEventListener('click', () => {
      offset = Math.max(0, offset - 25);
      loadList();
    });
    $('#next').addEventListener('click', () => {
      offset += 25;
      loadList();
    });
    $('#rows').addEventListener('click', (e) => {
      const button = e.target.closest('[data-action]');
      if (!button) return;
      const row = records.find((r) => r[config.id] === Number(button.dataset.id));
      if (!row) return;
      if (button.dataset.action === 'view') details(row);
      if (button.dataset.action === 'edit') editForm(row);
      if (button.dataset.action === 'delete') deleteRecord(row);
      if (button.dataset.action === 'review') reviewForm(row);
      if (button.dataset.action === 'progress') progressForm(row);
    });
    loadList();
    if (page === 'emergency-reports')
      setInterval(() => {
        if (!document.hidden && !$('#dialog').open) loadList();
      }, 30000);
  }
  async function loadList() {
    const generation = ++sequence;
    controller?.abort();
    controller = new AbortController();
    clearMessage();
    $('#rows').innerHTML =
      `<tr><td colspan="${config.columns.length + 1}"><div class="empty">Loading ${esc(config.title.toLowerCase())}…</div></td></tr>`;
    $('#previous').disabled = true;
    $('#next').disabled = true;
    $('#count').textContent = 'Loading…';
    const query = new URLSearchParams({
      limit: 25,
      offset,
      sort,
      ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '')),
    });
    try {
      const data = await api(`/api/${page}/?${query}`, { signal: controller.signal });
      if (generation !== sequence) return;
      total = data.total;
      records = data[config.key || page];
      if (offset >= total && offset > 0) {
        offset = Math.max(0, Math.floor((total - 1) / 25) * 25);
        return loadList();
      }
      renderRows();
      $('#count').textContent = total
        ? `${offset + 1}–${offset + records.length} of ${total} records`
        : '0 records';
      $('#previous').disabled = offset === 0;
      $('#next').disabled = offset + 25 >= total;
      $('#updated').textContent =
        `Last refreshed ${new Date().toLocaleTimeString()}${page === 'emergency-reports' ? ' · Refreshes every 30 seconds while this page is visible.' : ''}`;
    } catch (error) {
      if (error.name === 'AbortError' || generation !== sequence) return;
      message(error);
      $('#count').textContent = 'Records unavailable';
      $('#updated').textContent = '';
      $('#rows').innerHTML = /* HTML */ `<tr>
        <td colspan="${config.columns.length + 1}">
          <div class="empty">
            <strong>Records could not be loaded</strong>Check the connection, then choose Refresh.
          </div>
        </td>
      </tr>`;
    }
  }
  function renderRows() {
    $('#rows').innerHTML = records.length
      ? records
          .map(
            (row) =>
              /* HTML */ `<tr>
                ${config.columns
                  .map(
                    (c, index) =>
                      /* HTML */ `<td>
                        ${index === 0
                          ? /* HTML */ `<span class="cell-primary"
                                >${format(
                                  c.key === 'city'
                                    ? row.city || row.reported_location_text
                                    : row[c.key],
                                  c.key,
                                )}</span
                              ><span class="record-id">#${esc(row[config.id])}</span>`
                          : c.key === 'description'
                            ? `<span class="cell-description">${format(c.key === 'city' ? row.city || row.reported_location_text : row[c.key], c.key)}</span>`
                            : format(
                                c.key === 'city'
                                  ? row.city || row.reported_location_text
                                  : row[c.key],
                                c.key,
                              )}
                      </td>`,
                  )
                  .join('')}
                <td>
                  <div class="row-actions">
                    <button class="btn small" data-action="view" data-id="${row[config.id]}">
                      Details
                    </button>
                    ${isAdmin() &&
                    (page !== 'emergency-reports' || row.review_status === 'PENDING_REVIEW')
                      ? /* HTML */ `<button
                            class="btn small"
                            data-action="edit"
                            data-id="${row[config.id]}"
                          >
                            Edit</button
                          ><button
                            class="btn small danger"
                            data-action="delete"
                            data-id="${row[config.id]}"
                          >
                            Delete
                          </button>`
                      : ''}
                    ${isAdmin() &&
                    page === 'emergency-reports' &&
                    row.review_status === 'PENDING_REVIEW'
                      ? `<button class="btn small primary" data-action="review" data-id="${row[config.id]}">Review</button>`
                      : ''}
                    ${isAdmin() &&
                    page === 'emergency-reports' &&
                    ['CONFIRMED', 'LEGACY'].includes(row.review_status) &&
                    row.status !== 'REJECTED'
                      ? `<button class="btn small" data-action="progress" data-id="${row[config.id]}">Response status</button>`
                      : ''}
                  </div>
                </td>
              </tr>`,
          )
          .join('')
      : /* HTML */ `<tr>
          <td colspan="${config.columns.length + 1}">
            <div class="empty">
              <strong>No matching records</strong>${Object.values(filters).some(Boolean)
                ? 'Clear your filters to see more records.'
                : 'Add a record to get started.'}
            </div>
          </td>
        </tr>`;
  }
  function openDialog(title, body, footer = '') {
    const dialog = $('#dialog');
    dialogGeneration++;
    dialog.innerHTML = /* HTML */ `<div class="dialog-head">
        <div><h2 id="dialog-title">${esc(title)}</h2></div>
        <button class="btn small" id="dialog-close" aria-label="Close dialog">Close</button>
      </div>
      <div class="dialog-body">${body}</div>
      ${footer ? `<div class="dialog-foot">${footer}</div>` : ''}`;
    $('#dialog-close').addEventListener('click', () => dialog.close());
    if (!dialog.open) dialog.showModal();
    return dialog;
  }
  function details(row) {
    const labels = Object.fromEntries(
      [...config.fields, ...config.columns].map((f) => [f.key, f.label]),
    );
    openDialog(
      `${config.singular} #${row[config.id]}`,
      /* HTML */ `<dl class="details">
        ${Object.entries(row)
          .filter(([key]) => !['password_hash'].includes(key))
          .map(
            ([key, value]) =>
              `<dt>${esc(labels[key] || human(key))}</dt><dd>${format(value, key)}</dd>`,
          )
          .join('')}
      </dl>`,
    );
    window.DMSV2?.detailActions(page, row, $('#dialog'));
  }
  async function lookup(module) {
    let items = [],
      start = 0;
    while (true) {
      const data = await api(`/api/lookups/${module}?offset=${start}`);
      items.push(...data.items);
      if (!data.has_more) return items;
      start += 200;
    }
  }
  function localNow() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  function formFields(fields, row = {}) {
    return fields
      .map((f) => {
        let value = row[f.key] ?? '';
        if (f.type === 'datetime-local') value = String(value).replace(' ', 'T').slice(0, 16);
        const required = f.required && !(f.key === 'password' && Object.keys(row).length);
        const attrs = `id="field-${f.key}" name="${f.key}" ${required ? 'required' : ''} ${f.max ? `maxlength="${f.max}"` : ''} ${f.minLength ? `minlength="${f.minLength}"` : ''} ${f.min !== undefined ? `min="${f.min}"` : ''} ${f.maxNumber !== undefined ? `max="${f.maxNumber}"` : ''} ${f.step ? `step="${f.step}"` : ''} aria-describedby="error-${f.key}"`;
        const input =
          f.type === 'textarea'
            ? `<textarea ${attrs}>${esc(value)}</textarea>`
            : f.type === 'select'
              ? /* HTML */ `<select ${attrs}>
                  <option value="" ${value === '' ? 'selected' : ''}>
                    Choose ${esc(f.label.toLowerCase())}
                  </option>
                  ${f.values
                    .map(
                      (v) =>
                        `<option value="${v}" ${v === value ? 'selected' : ''}>${esc(human(v))}</option>`,
                    )
                    .join('')}
                </select>`
              : f.type === 'relation'
                ? `<select ${attrs} data-lookup="${f.module}" data-value="${esc(value)}"><option value="">Loading choices…</option></select>`
                : `<input type="${f.type}" ${attrs} value="${f.type === 'password' ? '' : esc(value)}" ${f.type === 'password' ? 'autocomplete="new-password"' : ''}>`;
        return /* HTML */ `<div class="form-field ${f.type === 'textarea' ? 'wide' : ''}">
          <label for="field-${f.key}">${esc(f.label)}${required ? ' *' : ''}</label
          >${input}${f.key === 'password' && Object.keys(row).length
            ? '<small>Leave blank to keep the existing password.</small>'
            : ''}<small id="error-${f.key}" class="field-error"></small>
        </div>`;
      })
      .join('');
  }
  async function populateLookups() {
    const fields = [...document.querySelectorAll('[data-lookup]')];
    const unique = [...new Set(fields.map((el) => el.dataset.lookup))];
    const loaded = await Promise.all(unique.map(async (key) => [key, await lookup(key)]));
    const options = Object.fromEntries(loaded);
    fields.forEach((el) => {
      const value = el.dataset.value;
      el.innerHTML =
        `<option value="">${el.required ? 'Choose a record' : 'None'}</option>` +
        options[el.dataset.lookup]
          .map((item) => `<option value="${item.id}">${esc(item.label)} (#${item.id})</option>`)
          .join('');
      el.value = value;
    });
  }
  function showFieldErrors(error) {
    message(error, '#form-error');
    (error.errors || []).forEach((e) => {
      const key = e.loc?.[1];
      const input = $(`[name="${key}"]`),
        hint = $(`#error-${key}`);
      if (input) input.setAttribute('aria-invalid', 'true');
      if (hint) hint.textContent = e.msg;
    });
  }
  function collect(fields) {
    const payload = {};
    for (const f of fields) {
      const el = $(`[name="${f.key}"]`);
      const value = f.type === 'password' ? el.value : el.value.trim();
      if (f.key === 'password' && !value) continue;
      payload[f.key] =
        value === ''
          ? null
          : ['number', 'relation'].includes(f.type)
            ? f.step && f.step !== '1'
              ? value
              : Number(value)
            : value;
    }
    return payload;
  }
  function clientValidate(data) {
    if (data.capacity !== undefined && data.current_occupancy > data.capacity)
      throw new Error('Occupancy cannot exceed capacity.');
    if (
      data.total_quantity !== undefined &&
      Number(data.available_quantity) > Number(data.total_quantity)
    )
      throw new Error('Available stock cannot exceed total stock.');
    if (data.start_time && data.end_time && data.end_time <= data.start_time)
      throw new Error('End time must be after start time.');
    if (data.check_in && data.check_out && data.check_out <= data.check_in)
      throw new Error('Check-out must be after check-in.');
    if (
      ['resource-allocations', 'volunteer-assignments'].includes(page) &&
      Boolean(data.disaster_id) === Boolean(data.shelter_id)
    )
      throw new Error('Choose exactly one disaster or shelter target.');
  }
  async function editForm(row) {
    let fields = config.fields.filter(
      (f) => !(row && page === 'disasters' && f.key === 'reported_by'),
    );
    if (!row && page === 'volunteers')
      fields = fields.map((f) =>
        f.key === 'availability_status' ? { ...f, values: ['AVAILABLE', 'UNAVAILABLE'] } : f,
      );
    const dialog = openDialog(
      row
        ? `Edit ${config.singular.toLowerCase()} #${row[config.id]}`
        : page === 'emergency-reports'
          ? 'Report a suspected emergency'
          : `Add ${config.singular.toLowerCase()}`,
      /* HTML */ `<div id="form-error" class="message" role="alert"></div>
        ${page === 'emergency-reports'
          ? '<p class="muted" style="margin-bottom:20px">Reports are saved as pending review. An administrator will verify the details before confirming an official incident.</p>'
          : ''}
        <form id="record-form"><div class="form-grid">${formFields(fields, row)}</div></form>`,
      '<button class="btn" id="cancel-form">Cancel</button><button class="btn primary" type="submit" form="record-form" id="save">Save record</button>',
    );
    const version = dialogGeneration;
    $('#cancel-form').addEventListener('click', () => dialog.close());
    if (!row) {
      for (const key of ['start_time', 'check_in']) {
        const el = $(`[name="${key}"]`);
        if (el) el.value = localNow();
      }
      for (const key of [
        'total_quantity',
        'available_quantity',
        'minimum_required',
        'current_occupancy',
      ]) {
        const el = $(`[name="${key}"]`);
        if (el) el.value = '0';
      }
    }
    $('#save').disabled = true;
    window.DMSV2?.locationPicker(page, dialog, row);
    try {
      await populateLookups();
      if (version !== dialogGeneration || !dialog.open) return;
      $('#save').disabled = false;
    } catch (error) {
      if (version !== dialogGeneration || !dialog.open) return;
      message(error, '#form-error');
    }
    let busy = false;
    $('#record-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      const saveButton = $('#save'),
        closeButton = $('#dialog-close'),
        cancelButton = $('#cancel-form');
      clearMessage('#form-error');
      document.querySelectorAll('.field-error').forEach((el) => (el.textContent = ''));
      document
        .querySelectorAll('[aria-invalid]')
        .forEach((el) => el.removeAttribute('aria-invalid'));
      let data;
      try {
        data = collect(fields);
        data = window.DMSV2?.collectLocation(data, page) || data;
        clientValidate(data);
      } catch (error) {
        showFieldErrors(error);
        return;
      }
      busy = true;
      $('#save').disabled = true;
      $('#save').textContent = 'Saving…';
      $('#dialog-close').disabled = true;
      $('#cancel-form').disabled = true;
      const stopCancel = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stopCancel);
      try {
        const result = await api(`/api/${page}/${row ? row[config.id] : ''}`, {
          method: row ? 'PUT' : 'POST',
          body: JSON.stringify(data),
        });
        dialog.close();
        toast(
          page === 'emergency-reports' && !row
            ? `Report #${result.report_id} submitted. Status: Pending review.`
            : result.message,
        );
        await loadList();
      } catch (error) {
        showFieldErrors(error);
      } finally {
        busy = false;
        dialog.removeEventListener('cancel', stopCancel);
        saveButton.disabled = false;
        saveButton.textContent = 'Save record';
        closeButton.disabled = false;
        cancelButton.disabled = false;
      }
    });
  }
  function deleteRecord(row) {
    const dialog = openDialog(
      'Delete this record?',
      /* HTML */ `<div id="form-error" class="message" role="alert"></div>
        <p>
          Delete ${esc(config.singular.toLowerCase())} #${esc(row[config.id])}? Related records may
          prevent deletion. This action cannot be undone.
        </p>`,
      '<button class="btn" id="cancel-delete">Keep record</button><button class="btn danger" id="confirm-delete">Delete record</button>',
    );
    $('#cancel-delete').addEventListener('click', () => dialog.close());
    $('#confirm-delete').addEventListener('click', async (e) => {
      const button = e.target,
        closeButton = $('#dialog-close'),
        cancelButton = $('#cancel-delete');
      button.disabled = true;
      closeButton.disabled = true;
      cancelButton.disabled = true;
      const stopCancel = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stopCancel);
      try {
        await api(`/api/${page}/${row[config.id]}`, { method: 'DELETE' });
        dialog.close();
        toast('Record deleted.');
        await loadList();
      } catch (error) {
        message(error, '#form-error');
      } finally {
        dialog.removeEventListener('cancel', stopCancel);
        button.disabled = false;
        closeButton.disabled = false;
        cancelButton.disabled = false;
      }
    });
  }
  async function reviewForm(row) {
    const fields = [
      relation(
        'location_id',
        'Official saved location (required for unfamiliar reports)',
        'locations',
        false,
      ),
      choice('decision', 'Decision', ['CONFIRMED', 'REJECTED']),
      field('title', 'Official incident title', 'text', false, { max: 150 }),
      relation('disaster_id', 'Link existing disaster (optional)', 'disasters', false),
      field('reason', 'Review note or rejection reason', 'textarea', false, { max: 1000 }),
    ];
    const dialog = openDialog(
      `Review report #${row.report_id}`,
      /* HTML */ `<p class="muted" style="margin-bottom:20px">${esc(row.description)}</p>
        <div id="form-error" class="message" role="alert"></div>
        <form id="review-form">
          <div class="form-grid">
            ${formFields(fields, {
              title: `Emergency report #${row.report_id}`,
              location_id: row.location_id,
            })}
          </div>
          <p class="login-note">
            Confirmation creates one official disaster unless an existing disaster at the same
            location is selected.
          </p>
        </form>`,
      '<button class="btn" id="cancel-review">Cancel</button><button class="btn primary" form="review-form" type="submit" id="review-save">Save decision</button>',
    );
    const version = dialogGeneration;
    $('#cancel-review').addEventListener('click', () => dialog.close());
    $('#review-save').disabled = true;
    try {
      await populateLookups();
      if (version !== dialogGeneration || !dialog.open) return;
      $('#review-save').disabled = false;
    } catch (error) {
      if (version !== dialogGeneration || !dialog.open) return;
      message(error, '#form-error');
    }
    const change = () => {
      const rejected = $('[name="decision"]').value === 'REJECTED';
      $('[name="title"]').disabled = rejected;
      $('[name="disaster_id"]').disabled = rejected;
    };
    $('[name="decision"]').addEventListener('change', change);
    let busy = false;
    $('#review-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      const saveButton = $('#review-save'),
        closeButton = $('#dialog-close'),
        cancelButton = $('#cancel-review');
      busy = true;
      saveButton.disabled = true;
      closeButton.disabled = true;
      cancelButton.disabled = true;
      const stopCancel = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stopCancel);
      let data = collect(fields);
      if (data.decision === 'REJECTED') {
        data.disaster_id = null;
        data.title = null;
        data.location_id = null;
      }
      try {
        const result = await api(`/api/emergency-reports/${row.report_id}/review`, {
          method: 'POST',
          body: JSON.stringify(data),
        });
        dialog.close();
        toast(
          `Report #${row.report_id}: ${human(result.status)}${result.disaster_id ? ` · Disaster #${result.disaster_id}` : ''}`,
        );
        await loadList();
      } catch (error) {
        showFieldErrors(error);
      } finally {
        busy = false;
        dialog.removeEventListener('cancel', stopCancel);
        saveButton.disabled = false;
        closeButton.disabled = false;
        cancelButton.disabled = false;
      }
    });
  }
  function progressForm(row) {
    const fields = [choice('status', 'Response status', ['IN_PROGRESS', 'RESOLVED'])];
    const dialog = openDialog(
      `Response status for report #${row.report_id}`,
      /* HTML */ `<div id="form-error" class="message" role="alert"></div>
        <form id="progress-form">
          <div class="form-grid">${formFields(fields, row)}</div>
          <p class="login-note">
            This tracks response progress. The administrator review and official disaster link
            remain recorded.
          </p>
        </form>`,
      '<button class="btn" id="cancel-progress">Cancel</button><button class="btn primary" type="submit" form="progress-form" id="progress-save">Update status</button>',
    );
    $('#cancel-progress').addEventListener('click', () => dialog.close());
    let busy = false;
    $('#progress-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      busy = true;
      const save = $('#progress-save'),
        close = $('#dialog-close'),
        cancel = $('#cancel-progress');
      save.disabled = true;
      close.disabled = true;
      cancel.disabled = true;
      const stopCancel = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stopCancel);
      try {
        await api(`/api/emergency-reports/${row.report_id}/progress`, {
          method: 'POST',
          body: JSON.stringify(collect(fields)),
        });
        dialog.close();
        toast('Response status updated.');
        await loadList();
      } catch (error) {
        showFieldErrors(error);
      } finally {
        busy = false;
        dialog.removeEventListener('cancel', stopCancel);
        save.disabled = false;
        close.disabled = false;
        cancel.disabled = false;
      }
    });
  }

  const card = (label, value, description, link) =>
    /* HTML */ `<a class="stat" href="${link}.html"
      ><div class="stat-label">${esc(label)}</div>
      <div class="stat-value">${esc(value)}</div>
      <p>${esc(description)}</p></a
    >`;
  async function dashboard() {
    $('#view').innerHTML =
      heading(
        isAdmin() ? 'Operational overview' : 'Your response workspace',
        isAdmin()
          ? 'A clear view of incidents, capacity and the reports needing attention.'
          : 'Report suspected emergencies and follow their review status.',
        '<button class="btn" id="refresh-dashboard">Refresh</button><a class="btn primary" href="emergency-reports.html">Report an emergency</a>',
      ) + '<div id="dashboard-data"><div class="empty">Loading database overview…</div></div>';
    $('#refresh-dashboard').addEventListener('click', dashboard);
    clearMessage();
    try {
      if (!isAdmin()) {
        const data = await api('/api/emergency-reports/?limit=5');
        $('#dashboard-data').innerHTML = /* HTML */ `<div class="callout">
            <div>
              <h2>Help your response team act on verified information.</h2>
              <p>
                Your reports remain pending until an administrator reviews them. Only you and the
                response team can access your reports.
              </p>
            </div>
            <a class="btn primary" href="emergency-reports.html">View your reports</a>
          </div>
          <div class="stats">
            ${card(
              'Your submitted reports',
              data.total,
              'All reports submitted by this account',
              'emergency-reports',
            )}
          </div>
          <section class="panel">
            <div class="panel-head"><h2>Your recent reports</h2></div>
            <div class="table-wrap">
              ${miniTable(data.emergency_reports, modules['emergency-reports'].columns)}
            </div>
          </section>`;
        return;
      }
      const [d, incidents, reports] = await Promise.all([
        api('/api/dashboard/'),
        api('/api/disasters/?limit=5&status=ACTIVE'),
        api('/api/emergency-reports/?limit=5&status=PENDING_REVIEW'),
      ]);
      const percent = d.shelters.total_capacity
        ? Math.round((d.shelters.total_occupancy / d.shelters.total_capacity) * 100)
        : 0;
      $('#dashboard-data').innerHTML = /* HTML */ `<div class="stats">
          ${card(
            'Recorded disasters',
            d.disasters.total,
            'All official disaster records',
            'disasters',
          )}${card('Active disasters', d.disasters.active, 'Status is Active', 'disasters')}${card(
            'Pending review',
            d.emergency_reports.pending,
            'Reports awaiting verification',
            'emergency-reports',
          )}${card(
            'Available shelters',
            d.shelters.available,
            'Open shelters with space',
            'shelters',
          )}${card(
            'Registered volunteers',
            d.volunteers.total,
            `${d.volunteers.available} available for assignment`,
            'volunteers',
          )}${card(
            'Resources in stock',
            d.resources.available_types,
            'Resource types with available stock',
            'resources',
          )}
        </div>
        <div class="dashboard-grid">
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2>Reports needing attention</h2>
                <p>Most recently submitted, pending verification</p>
              </div>
              <a href="emergency-reports.html" class="btn small">Review queue</a>
            </div>
            <div class="table-wrap">
              ${miniTable(
                reports.emergency_reports,
                columns(['report_type', 'Report'], ['city', 'Location'], ['severity', 'Urgency']),
              )}
            </div>
          </section>
          <section class="panel">
            <div class="panel-head">
              <div>
                <h2>Shelter capacity</h2>
                <p>Reported occupancy across all shelters</p>
              </div>
            </div>
            <div class="panel-body">
              <div class="stat-value">
                ${esc(d.shelters.total_occupancy)}
                <span class="muted" style="font-size:18px"
                  >/ ${esc(d.shelters.total_capacity)}</span
                >
              </div>
              <div class="progress">
                <span style="width:${Math.max(0, Math.min(100, percent))}%"></span>
              </div>
              <p class="muted">${percent}% occupied · ${esc(d.shelters.full)} full shelters</p>
            </div>
            <div class="metric-line">
              <span>Low-stock resource types</span
              ><strong>${esc(d.resources.low_stock_count)}</strong>
            </div>
            <div class="metric-line">
              <span>Active shelter registrations</span
              ><strong>${esc(d.shelter_registrations.active)}</strong>
            </div>
          </section>
        </div>
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>Active incidents</h2>
              <p>Five most recent official records with active status</p>
            </div>
            <a href="disasters.html" class="btn small">All incidents</a>
          </div>
          <div class="table-wrap">${miniTable(incidents.disasters, modules.disasters.columns)}</div>
        </section>
        <p class="refresh-time">
          Last refreshed ${esc(new Date().toLocaleTimeString())}. Counts are read from MySQL when
          you refresh.
        </p>`;
      window.DMSV2?.overview();
    } catch (error) {
      message(error);
      $('#dashboard-data').innerHTML =
        '<div class="panel empty"><strong>Overview unavailable</strong>Check MySQL and the API, then choose Refresh.</div>';
    }
  }
  function miniTable(rows, cols) {
    return rows.length
      ? /* HTML */ `<table>
          <thead>
            <tr>
              ${cols.map((c) => `<th>${esc(c.label)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (row) =>
                  `<tr>${cols.map((c) => `<td>${format(c.key === 'city' ? row.city || row.reported_location_text : row[c.key], c.key)}</td>`).join('')}</tr>`,
              )
              .join('')}
          </tbody>
        </table>`
      : '<div class="empty">No records to display.</div>';
  }
  function searchView() {
    const choices = Object.keys(modules).filter(permitted);
    $('#view').innerHTML =
      heading(
        'Search records',
        'Search actual database records. Public accounts can search only their own reports.',
      ) +
      /* HTML */ `<section class="panel">
        <form class="toolbar" id="global-search">
          <label
            >Module<select id="search-module">
              ${choices
                .map((k) => `<option value="${k}">${esc(modules[k].title)}</option>`)
                .join('')}
            </select></label
          ><label class="search"
            >Search<input
              id="global-query"
              maxlength="150"
              type="search"
              placeholder="Name, description, location or record ID" /></label
          ><button class="btn primary">Search</button>
        </form>
        <div id="search-results" class="table-wrap">
          <div class="empty">Choose a module and search for a record.</div>
        </div>
        <div class="pagination">
          <span id="search-count"></span>
          <div class="actions">
            <button class="btn small" id="search-prev" disabled>Previous</button
            ><button class="btn small" id="search-next" disabled>Next</button>
          </div>
        </div>
      </section>`;
    let start = 0,
      searchSequence = 0,
      savedModule = '',
      savedQuery = '';
    async function run() {
      const generation = ++searchSequence;
      clearMessage();
      $('#search-results').innerHTML = '<div class="empty">Searching…</div>';
      $('#search-prev').disabled = true;
      $('#search-next').disabled = true;
      try {
        const result = await api(
          `/api/search/${savedModule}?` +
            new URLSearchParams({ q: savedQuery, limit: 25, offset: start }),
        );
        if (generation !== searchSequence) return;
        const c = modules[savedModule];
        $('#search-results').innerHTML = miniTable(result[c.key || savedModule], c.columns);
        $('#search-count').textContent =
          `${result.total} matching records · Page ${Math.floor(start / 25) + 1}`;
        $('#search-prev').disabled = start === 0;
        $('#search-next').disabled = start + 25 >= result.total;
      } catch (error) {
        if (generation !== searchSequence) return;
        message(error);
        $('#search-results').innerHTML =
          '<div class="empty">Search unavailable. Please retry.</div>';
        $('#search-count').textContent = '';
      }
    }
    $('#global-search').addEventListener('submit', (e) => {
      e.preventDefault();
      start = 0;
      savedModule = $('#search-module').value;
      savedQuery = $('#global-query').value.trim();
      run();
    });
    $('#search-prev').addEventListener('click', () => {
      start = Math.max(0, start - 25);
      run();
    });
    $('#search-next').addEventListener('click', () => {
      start += 25;
      run();
    });
  }
  const reportSections = {
    shelters: {
      title: 'Shelter occupancy',
      description:
        'Reported occupancy and active registrations are shown separately. Remaining capacity includes closed shelters; check status before assigning people.',
      cols: columns(
        ['name', 'Shelter'],
        ['city', 'City'],
        ['status', 'Status'],
        ['capacity', 'Capacity'],
        ['current_occupancy', 'Occupancy'],
        ['remaining_capacity', 'Remaining'],
        ['occupancy_percent', 'Occupied %'],
        ['active_registrations', 'Active registrations'],
      ),
    },
    disasters: {
      title: 'Disaster response',
      description:
        'Non-cancelled allocation counts and distinct resource types. Active volunteers are distinct people with Assigned or Active assignments.',
      cols: columns(
        ['title', 'Incident'],
        ['city', 'City'],
        ['status', 'Status'],
        ['allocation_count', 'Allocations'],
        ['resource_types', 'Resource types'],
        ['active_volunteers', 'Active volunteers'],
      ),
    },
    'monthly-reports': {
      title: 'Reports by month and location',
      description:
        'Grouped by submission month and exact location. Pending, confirmed, rejected and legacy review counts total the submitted reports.',
      cols: columns(
        ['report_month', 'Month'],
        ['city', 'City'],
        ['district', 'District'],
        ['state', 'State'],
        ['location_id', 'Location reference'],
        ['total_reports', 'Total'],
        ['pending_reports', 'Pending'],
        ['confirmed_reports', 'Confirmed'],
        ['rejected_reports', 'Rejected'],
        ['legacy_reports', 'Legacy'],
      ),
    },
    'resource-allocations': {
      title: 'Allocated supplies',
      description:
        'Non-cancelled allocations grouped by target and resource. Quantities in different units are never added together.',
      cols: columns(
        ['target', 'Target'],
        ['disaster_id', 'Disaster reference'],
        ['shelter_id', 'Shelter reference'],
        ['resource_name', 'Resource'],
        ['unit', 'Unit'],
        ['allocation_count', 'Allocations'],
        ['allocated_quantity', 'Quantity'],
      ),
    },
  };
  function historyView() {
    const audit = page === 'audit-history',
      analytics = page === 'analytics';
    const descriptions = {
      'audit-history':
        'Permanent record of selected operational fields changed after the history migration. Account passwords and contact details are excluded. Unattributed changes show an unknown actor.',
      'resource-movements':
        'Stock changes recorded with their resulting balances and units. Opening entries reflect stock at creation or migration; earlier movements are unknown.',
      analytics: 'Database reports for capacity, response activity and incoming emergencies.',
    };
    const entityOptions = Object.entries(modules)
      .map(
        ([key, c]) => `<option value="${esc(key.replaceAll('-', '_'))}">${esc(c.title)}</option>`,
      )
      .join('');
    const kindOptions = [
      'OPENING',
      'RESTOCK',
      'WITHDRAW',
      'ALLOCATION_CHANGE',
      'RETURN',
      'INVENTORY_ADJUSTMENT',
      'REMOVAL',
    ]
      .map((k) => `<option value="${k}">${esc(human(k))}</option>`)
      .join('');
    $('#view').innerHTML =
      heading(
        extraPages[page],
        descriptions[page],
        '<button class="btn" id="history-refresh">Refresh</button>' +
          (page === 'resource-movements'
            ? '<button class="btn primary" id="stock-add">Record stock movement</button>'
            : ''),
      ) +
      /* HTML */ ` <section class="panel">
        <form class="toolbar" id="history-filters">
          ${analytics
            ? /* HTML */ `<label class="search"
                >Report<select name="section">
                  ${Object.entries(reportSections)
                    .map(([key, c]) => `<option value="${key}">${esc(c.title)}</option>`)
                    .join('')}
                </select></label
              >`
            : audit
              ? /* HTML */ `<label
                    >Module<select name="entity">
                      <option value="">All modules</option>
                      ${entityOptions}
                    </select></label
                  ><label
                    >Action<select name="action">
                      <option value="">All actions</option>
                      <option>INSERT</option>
                      <option>UPDATE</option>
                      <option>DELETE</option>
                    </select></label
                  ><label
                    >Record reference<input
                      name="record_id"
                      type="number"
                      min="1"
                      step="1"
                      placeholder="Optional ID"
                  /></label>`
              : /* HTML */ `<label
                    >Resource reference<input
                      name="resource_id"
                      type="number"
                      min="1"
                      step="1"
                      placeholder="Optional ID" /></label
                  ><label
                    >Movement<select name="movement_kind">
                      <option value="">All movements</option>
                      ${kindOptions}
                    </select></label
                  >`}
          ${analytics
            ? ''
            : '<label>From<input name="start" type="date"></label><label>Through<input name="end" type="date"></label>'}
          <button class="btn primary">Apply</button
          ><button class="btn" type="button" id="history-clear">Clear</button>
        </form>
        <div class="panel-body muted" id="report-definition"></div>
        <div class="table-wrap" id="history-table"></div>
        <div class="pagination">
          <span id="history-count"></span>
          <div class="actions">
            <button class="btn small" id="history-prev">Previous</button
            ><button class="btn small" id="history-next">Next</button>
          </div>
        </div>
      </section>`;
    let start = 0,
      generation = 0,
      items = [],
      saved = analytics
        ? { section: 'shelters' }
        : Object.fromEntries(
            [...new URLSearchParams(location.search)].filter(([key]) =>
              (audit ? ['entity', 'record_id'] : ['resource_id']).includes(key),
            ),
          );
    const auditCols = columns(
      ['audit_id', 'Reference'],
      ['created_at', 'Time'],
      ['entity', 'Module'],
      ['record_id', 'Record'],
      ['action', 'Action'],
      ['actor_name', 'Actor'],
    );
    const ledgerCols = columns(
      ['movement_id', 'Reference'],
      ['created_at', 'Time'],
      ['resource_id', 'Resource reference'],
      ['resource_name', 'Resource'],
      ['unit', 'Unit'],
      ['movement_kind', 'Movement'],
      ['total_delta', 'Total change'],
      ['available_delta', 'Available change'],
      ['total_after', 'Total after'],
      ['available_after', 'Available after'],
      ['allocation_id', 'Allocation'],
      ['actor_name', 'Actor'],
      ['note', 'Note'],
    );
    async function load() {
      const token = ++generation;
      clearMessage();
      $('#history-table').innerHTML = '<div class="empty">Loading database records...</div>';
      $('#history-prev').disabled = true;
      $('#history-next').disabled = true;
      $('#history-count').textContent = 'Loading...';
      const section = saved.section || 'shelters';
      const cols = analytics ? reportSections[section].cols : audit ? auditCols : ledgerCols;
      $('#report-definition').textContent = analytics
        ? reportSections[section].description
        : 'History begins when the migration is applied. Unknown actors represent maintenance or direct SQL changes.';
      const params = { ...saved, limit: 25, offset: start };
      delete params.section;
      try {
        const result = await api(
          (analytics ? `/api/analytics/${section}` : `/api/${page}/`) +
            '?' +
            new URLSearchParams(params),
        );
        if (token !== generation) return;
        items = result.items;
        $('#history-table').innerHTML = items.length
          ? /* HTML */ `<table>
              <thead>
                <tr>
                  ${cols.map((c) => `<th scope="col">${esc(c.label)}</th>`).join('')}${audit
                    ? '<th scope="col">Details</th>'
                    : ''}
                </tr>
              </thead>
              <tbody>
                ${items
                  .map(
                    (row, index) =>
                      /* HTML */ `<tr>
                        ${cols
                          .map(
                            (c) =>
                              /* HTML */ `<td>
                                ${c.key === 'actor_name'
                                  ? esc(row.actor_name || 'Unknown')
                                  : format(
                                      c.key === 'city'
                                        ? row.city || row.reported_location_text
                                        : row[c.key],
                                      c.key,
                                    )}
                              </td>`,
                          )
                          .join('')}${audit
                          ? `<td><button class="btn small" data-history-index="${index}">View changes</button></td>`
                          : ''}
                      </tr>`,
                  )
                  .join('')}
              </tbody>
            </table>`
          : '<div class="empty">No records match these filters. History will appear after changes are saved.</div>';
        $('#history-count').textContent =
          `${result.total} records · Page ${Math.floor(start / 25) + 1}`;
        $('#history-prev').disabled = start === 0;
        $('#history-next').disabled = start + 25 >= result.total;
      } catch (error) {
        if (token !== generation) return;
        message(error);
        $('#history-table').innerHTML =
          '<div class="empty">Records unavailable. Check MySQL, apply the additive migration and refresh.</div>';
        $('#history-count').textContent = '';
      }
    }
    $('#history-filters').addEventListener('submit', (e) => {
      e.preventDefault();
      const data = Object.fromEntries(new FormData(e.target));
      if (data.start && data.end && data.start > data.end) {
        message('From date must not follow Through date.');
        return;
      }
      saved = Object.fromEntries(Object.entries(data).filter(([, v]) => v !== ''));
      start = 0;
      load();
    });
    $('#history-clear').addEventListener('click', () => {
      $('#history-filters').reset();
      saved = analytics ? { section: 'shelters' } : {};
      start = 0;
      load();
    });
    $('#history-refresh').addEventListener('click', load);
    $('#history-prev').addEventListener('click', () => {
      start = Math.max(0, start - 25);
      load();
    });
    $('#history-next').addEventListener('click', () => {
      start += 25;
      load();
    });
    $('#history-table').addEventListener('click', (e) => {
      const button = e.target.closest('[data-history-index]');
      if (!button) return;
      const row = items[Number(button.dataset.historyIndex)];
      function snapshot(value) {
        if (typeof value === 'string') {
          try {
            value = JSON.parse(value);
          } catch {
            return esc(value);
          }
        }
        if (!value) return '<p class="muted">No snapshot</p>';
        return /* HTML */ `<dl class="details">
          ${Object.entries(value)
            .map(([key, v]) => `<dt>${esc(human(key))}</dt><dd>${format(v, key)}</dd>`)
            .join('')}
        </dl>`;
      }
      openDialog(
        `Change #${row.audit_id}`,
        /* HTML */ `<p class="muted">
            ${esc(human(row.entity))} #${esc(row.record_id)} · ${esc(row.action)} ·
            ${esc(row.actor_name || 'Unknown actor')}
          </p>
          <h2>Before</h2>
          ${snapshot(row.before_data)}
          <h2>After</h2>
          ${snapshot(row.after_data)}`,
        '',
      );
    });
    if (!analytics && !audit) $('#stock-add').addEventListener('click', () => stockForm(load));
    load();
  }
  async function stockForm(refresh) {
    const fields = [
      relation('resource_id', 'Resource', 'resources'),
      choice('kind', 'Movement', ['RESTOCK', 'WITHDRAW']),
      field('quantity', 'Quantity', 'number', true, { min: 0.01, step: '0.01' }),
      field('note', 'Reason or supply reference', 'textarea', true, { max: 500 }),
    ];
    const dialog = openDialog(
      'Record stock movement',
      /* HTML */ `<p class="muted">
          Restock increases total and available stock. Withdraw removes only available stock. Record
          allocations through Resource Allocations.
        </p>
        <div id="form-error" class="message" role="alert"></div>
        <form id="stock-form"><div class="form-grid">${formFields(fields)}</div></form>`,
      '<button class="btn primary" type="submit" form="stock-form" id="stock-save">Record movement</button>',
    );
    const version = dialogGeneration;
    $('#stock-save').disabled = true;
    try {
      await populateLookups();
      if (version !== dialogGeneration || !dialog.open) return;
      $('#stock-save').disabled = false;
    } catch (error) {
      if (version === dialogGeneration && dialog.open) message(error, '#form-error');
    }
    let busy = false;
    $('#stock-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      const data = collect(fields),
        id = data.resource_id;
      delete data.resource_id;
      const save = $('#stock-save'),
        close = $('#dialog-close');
      busy = true;
      save.disabled = true;
      close.disabled = true;
      const stopCancel = (e) => e.preventDefault();
      dialog.addEventListener('cancel', stopCancel);
      clearMessage('#form-error');
      try {
        const result = await api(`/api/resources/${id}/stock`, {
          method: 'POST',
          body: JSON.stringify(data),
        });
        dialog.close();
        toast(result.message);
        await refresh();
      } catch (error) {
        showFieldErrors(error);
      } finally {
        busy = false;
        save.disabled = false;
        close.disabled = false;
        dialog.removeEventListener('cancel', stopCancel);
      }
    });
  }
  function loginView() {
    let register = false;
    function render() {
      $('#app').innerHTML = /* HTML */ `<main class="login-page" id="main">
        <section class="login-story">
          <div class="brand">
            <div class="brand-mark">DM</div>
            <div><strong>DisasterMS</strong><small>Response operations</small></div>
          </div>
          <div>
            <div class="eyebrow">Prepared. Coordinated. Accountable.</div>
            <h1>Clear information.<br />Coordinated response.</h1>
            <p>
              Report suspected emergencies, review incidents and coordinate the people and supplies
              that support your community.
            </p>
          </div>
          <footer><small>Disaster Management System · Version 2.0</small></footer>
        </section>
        <section class="login-form-wrap">
          <div class="login-card">
            <div class="login-tabs">
              <button id="signin-tab" class="btn ${!register ? 'active' : ''}">Sign in</button
              ><button id="register-tab" class="btn ${register ? 'active' : ''}">
                Create account
              </button>
            </div>
            <h1>${register ? 'Create your account' : 'Welcome back'}</h1>
            <p>
              ${register
                ? 'Public accounts can report emergencies and track their own reports.'
                : 'Sign in to your response workspace.'}
            </p>
            <div id="page-error" class="message" role="alert"></div>
            <form id="login-form">
              ${register
                ? '<label class="form-field">Full name<input name="full_name" required maxlength="100" autocomplete="name"></label>'
                : ''}<label class="form-field"
                >Email<input
                  name="email"
                  type="email"
                  required
                  maxlength="150"
                  autocomplete="username" /></label
              ><label class="form-field"
                >Password<input
                  name="password"
                  type="password"
                  required
                  ${register ? 'minlength="10"' : ''}
                  maxlength="128"
                  autocomplete="${register ? 'new-password' : 'current-password'}" /></label
              >${register
                ? '<label class="form-field">Phone (optional)<input name="phone" type="tel" maxlength="15" autocomplete="tel"></label>'
                : ''}<button class="btn primary" id="login-submit">
                ${register ? 'Create account' : 'Sign in'}
              </button>
            </form>
            <p class="login-note">
              Administrator accounts are provisioned by the project owner. For immediate danger,
              contact your local emergency service; this application records reports for review.
            </p>
            <button class="btn small" id="login-theme">
              ${document.documentElement.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
          </div>
        </section>
      </main>`;
      $('#signin-tab').addEventListener('click', () => {
        register = false;
        render();
      });
      $('#register-tab').addEventListener('click', () => {
        register = true;
        render();
      });
      $('#login-theme').addEventListener('click', () => {
        document.documentElement.dataset.theme =
          document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('dms-theme', document.documentElement.dataset.theme);
        render();
      });
      $('#login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const button = $('#login-submit');
        if (button.disabled) return;
        button.disabled = true;
        clearMessage();
        const data = Object.fromEntries(new FormData(e.target));
        if (register && !data.phone) data.phone = null;
        try {
          const result = await api(`/api/auth/${register ? 'register' : 'login'}`, {
            method: 'POST',
            body: JSON.stringify(data),
          });
          if (register) {
            register = false;
            render();
            $('#page-error').classList.add('success');
            $('#page-error').textContent = result.message;
          } else location.replace('index.html');
        } catch (error) {
          message(error);
        } finally {
          if (document.contains(button)) button.disabled = false;
        }
      });
    }
    render();
  }
  async function start(key) {
    page = key;
    config = modules[page];
    if (page === 'login') {
      loginView();
      return;
    }
    try {
      user = await api('/api/auth/me');
    } catch (error) {
      if (error.status !== 401) {
        $('#app').innerHTML = /* HTML */ `<main class="content" id="main">
          <h1>Workspace unavailable</h1>
          <p class="message">${esc(error.message)}</p>
          <a href="login.html" class="btn">Go to sign in</a
          ><button class="btn" id="retry-start">Retry</button>
        </main>`;
        $('#retry-start').addEventListener('click', () => start(key));
      }
      return;
    }
    if ((config || extraPages[page]) && !permitted(page)) {
      location.replace('index.html');
      return;
    }
    shell();
    window.DMSV2?.relatedNavigation(page);
    if (page === 'index') dashboard();
    else if (page === 'search') searchView();
    else if (page === 'india-map') window.DMSV2.mapPage();
    else if (page === 'print') window.DMSV2.printPage();
    else if (extraPages[page]) historyView();
    else listView();
  }
  return {
    start,
    esc,
    human,
    api,
    openDialog,
    toast,
    message,
    miniTable,
    format,
    heading,
    isAdmin,
    formFields,
    collect,
    populateLookups,
    showFieldErrors,
    get user() {
      return user;
    },
    get page() {
      return page;
    },
    get filters() {
      return { ...filters, sort };
    },
    base: API,
  };
})();
