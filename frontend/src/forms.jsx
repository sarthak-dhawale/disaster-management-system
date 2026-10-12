import { useEffect, useState } from 'react';
import { request, query, invalidate } from './api';
import { useData, useDebounced } from './hooks';
import { Modal, label } from './ui';
import { LocationPicker } from './location-picker';
export function Relation({ field, value, onChange }) {
  const [search, setSearch] = useState(''),
    [offset, setOffset] = useState(0);
  const q = useDebounced(search);
  const state = useData(`/api/lookups/${field.module}?${query({ q, offset })}`);
  return (
    <div className="relation">
      <input
        aria-label={`Search ${field.label}`}
        placeholder="Search available records…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setOffset(0);
        }}
      />
      <select
        required={field.required}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select {field.label.toLowerCase()}</option>
        {value && !state.data?.items.some((i) => String(i.id) === String(value)) && (
          <option value={value}>Current selection #{value}</option>
        )}
        {(state.data?.items || []).map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
      {state.loading && <small>Loading choices…</small>}
      {state.error && <small className="inline-error">{state.error.message}</small>}
      <div className="lookup-pager">
        {offset > 0 && (
          <button type="button" onClick={() => setOffset(offset - 200)}>
            Previous choices
          </button>
        )}
        {state.data?.has_more && (
          <button type="button" onClick={() => setOffset(offset + 200)}>
            More choices
          </button>
        )}
      </div>
    </div>
  );
}
export function FormField({ field, value, onChange, error }) {
  const props = {
    id: field.key,
    required: field.required,
    value: value ?? '',
    onChange: (e) => onChange(e.target.value),
    maxLength: field.max,
    minLength: field.minLength,
    min: field.min,
    max: field.maxNumber,
    step: field.step,
    'aria-invalid': !!error,
  };
  return (
    <label className={field.type === 'textarea' ? 'span-two' : ''}>
      <span>
        {field.label}
        {field.required && <small> *</small>}
      </span>
      {field.type === 'relation' ? (
        <Relation field={field} value={value} onChange={onChange} />
      ) : field.type === 'select' ? (
        <select {...props}>
          <option value="">Select…</option>
          {field.values.map((v) => (
            <option key={v} value={v}>
              {label(v)}
            </option>
          ))}
        </select>
      ) : field.type === 'textarea' ? (
        <textarea {...props} rows={4} />
      ) : (
        <input {...props} type={field.type} />
      )}
      {error && <small className="inline-error">{error}</small>}
    </label>
  );
}
export function RecordForm({ module, config, record, onClose, onSuccess }) {
  const report = module === 'emergency-reports';
  const fields = config.fields.filter(
    (f) => !(record && module === 'disasters' && f.key === 'reported_by'),
  );
  const [values, setValues] = useState(() => ({
    ...record,
    ...Object.fromEntries(
      config.fields.map((f) => [
        f.key,
        f.type === 'datetime-local'
          ? String(record?.[f.key] || '').slice(0, 16)
          : (record?.[f.key] ?? ''),
      ]),
    ),
  }));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [errors, setErrors] = useState({});
  function set(key, value) {
    setValues((v) => ({ ...v, [key]: value }));
  }
  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setErrors({});
    try {
      const body = {};
      for (const field of fields) {
        const value = values[field.key];
        if (field.key === 'password' && record && !value) continue;
        body[field.key] =
          value === '' ? null : ['number', 'relation'].includes(field.type) ? Number(value) : value;
      }
      if (module === 'locations')
        body.coordinate_source = values.coordinate_source || 'USER_ENTERED';
      if (report && !body.location_id) {
        body.reported_location_text = values.reported_location_text || null;
        body.reported_latitude =
          values.reported_latitude !== '' && values.reported_latitude != null
            ? Number(values.reported_latitude)
            : null;
        body.reported_longitude =
          values.reported_longitude !== '' && values.reported_longitude != null
            ? Number(values.reported_longitude)
            : null;
        body.coordinate_source = values.coordinate_source || 'USER_ENTERED';
      }
      const result = await request(`/api/${module}/${record ? record[config.id] : ''}`, {
        method: record ? 'PUT' : 'POST',
        body: JSON.stringify(body),
      });
      invalidate();
      onSuccess(
        result.message ||
          `Saved ${config.singular.toLowerCase()}${result.report_id ? ` #${result.report_id}` : ''}`,
      );
      onClose();
    } catch (e) {
      setError(e.message);
      setErrors(Object.fromEntries((e.fields || []).map((f) => [f.loc.at(-1), f.msg])));
    } finally {
      setBusy(false);
    }
  }
  const editFields = fields.map((f) =>
    f.key === 'password' && record
      ? { ...f, required: false, label: 'New password (leave blank to keep)' }
      : f,
  );
  return (
    <Modal
      title={`${record ? 'Edit' : 'New'} ${config.singular.toLowerCase()}`}
      onClose={onClose}
      wide
    >
      <form onSubmit={save}>
        <div className="form-grid">
          {(module === 'locations' || (report && !values.location_id)) && (
            <LocationPicker
              onPick={(item) =>
                setValues((v) => ({
                  ...v,
                  ...(module === 'locations'
                    ? {
                        latitude: item.latitude,
                        longitude: item.longitude,
                        city: item.city || v.city,
                        district: item.district || v.district,
                        state: item.state || v.state,
                        address: item.label || v.address,
                      }
                    : {
                        reported_latitude: item.latitude,
                        reported_longitude: item.longitude,
                        reported_location_text: item.label || v.reported_location_text,
                      }),
                  coordinate_source: item.coordinate_source,
                }))
              }
            />
          )}{' '}
          {editFields.map((f) => (
            <FormField
              key={f.key}
              field={f}
              value={values[f.key]}
              onChange={(value) => set(f.key, value)}
              error={errors[f.key]}
            />
          ))}
          {report && (
            <>
              <p className="span-two muted">
                Choose a verified location above, or describe an unfamiliar location below.
                Coordinates are optional and must be supplied together.
              </p>
              <FormField
                field={{
                  key: 'reported_location_text',
                  label: 'Unfamiliar location / address',
                  type: 'textarea',
                  required: !values.location_id,
                  max: 500,
                }}
                value={values.reported_location_text}
                onChange={(v) => set('reported_location_text', v)}
              />
              {['latitude', 'longitude'].map((key) => (
                <FormField
                  key={key}
                  field={{
                    key: 'reported_' + key,
                    label: 'Reported ' + key,
                    type: 'number',
                    step: 'any',
                    min: key === 'latitude' ? -90 : -180,
                    maxNumber: key === 'latitude' ? 90 : 180,
                  }}
                  value={values['reported_' + key]}
                  onChange={(v) => set('reported_' + key, v)}
                />
              ))}
            </>
          )}
        </div>
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        <footer className="dialog-actions">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save record'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
export function ActionDialog({
  title,
  fields,
  initial = {},
  path,
  method = 'POST',
  onClose,
  onSuccess,
  description,
}) {
  const [values, setValues] = useState(initial),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const body = Object.fromEntries(
        fields.map((f) => [
          f.key,
          values[f.key] === '' || values[f.key] == null
            ? null
            : ['number', 'relation'].includes(f.type)
              ? Number(values[f.key])
              : values[f.key],
        ]),
      );
      await request(path, { method, body: JSON.stringify(body) });
      invalidate();
      onSuccess('Action recorded successfully');
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={submit}>
        {description && <p className="muted">{description}</p>}
        <div className="form-grid">
          {fields.map((f) => (
            <FormField
              key={f.key}
              field={f}
              value={values[f.key]}
              onChange={(v) => setValues({ ...values, [f.key]: v })}
            />
          ))}
        </div>
        {error && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}
        <footer className="dialog-actions">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Confirm'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
