import React, { useState } from 'react';
import { useData } from './hooks';
import { request } from './api';
import { State, Metrics, DataTable, ExportButtons, label } from './ui';
import { FormField } from './forms';
import { enums } from './modules';
const defaults = {
  name: 'Assam flood preparedness',
  disaster_type: 'FLOOD',
  region: 'Assam',
  district: '',
  population: 2000,
  severity: 'HIGH',
  description: 'Hypothetical planning exercise. Quantities are manager-entered assumptions.',
  accommodation_required: 2000,
  reserve_percent: 20,
  latitude: '',
  longitude: '',
  disaster_id: '',
};
export function Simulator({ notify }) {
  const catalog = useData('/api/simulations/catalog');
  const [scenario, setScenario] = useState(defaults),
    [demands, setDemands] = useState([
      { resource_id: '', quantity: '', region: 'Assam', priority: 3 },
    ]);
  const [result, setResult] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [plan, setPlan] = useState('A'),
    [editing, setEditing] = useState(true);
  function change(key, value) {
    setScenario((v) => ({ ...v, [key]: value }));
  }
  function demandChange(index, key, value) {
    setDemands((rows) => rows.map((r, i) => (i === index ? { ...r, [key]: value } : r)));
  }
  async function run(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const body = {
        ...scenario,
        population: Number(scenario.population),
        accommodation_required: Number(scenario.accommodation_required),
        reserve_percent: Number(scenario.reserve_percent),
        latitude: scenario.latitude === '' ? null : Number(scenario.latitude),
        longitude: scenario.longitude === '' ? null : Number(scenario.longitude),
        disaster_id: scenario.disaster_id === '' ? null : Number(scenario.disaster_id),
        demands: demands.map((d) => ({
          ...d,
          resource_id: Number(d.resource_id),
          priority: Number(d.priority),
          quantity: d.quantity,
        })),
      };
      const next = await request('/api/simulations/run', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (result) {
        try {
          await request(`/api/simulations/${result.simulation_id}`, { method: 'DELETE' });
        } catch (e) {
          if (e.status !== 404)
            setError(
              'New comparison is ready. The previous cached result could not be discarded: ' +
                e.message,
            );
        }
      }
      setResult(next);
      setEditing(false);
      notify('Three hypothetical plans calculated. Live records unchanged.');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function discard() {
    setBusy(true);
    setError('');
    try {
      if (result) await request(`/api/simulations/${result.simulation_id}`, { method: 'DELETE' });
      setResult(null);
      setEditing(true);
      notify('Hypothetical result discarded');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const fields = [
    { key: 'name', label: 'Scenario name', type: 'text', required: true, minLength: 3, max: 150 },
    {
      key: 'disaster_type',
      label: 'Disaster type',
      type: 'select',
      required: true,
      values: enums.disaster_type,
    },
    { key: 'region', label: 'State / region', type: 'text', required: true, max: 100 },
    { key: 'district', label: 'District', type: 'text', max: 100 },
    {
      key: 'population',
      label: 'Estimated affected population',
      type: 'number',
      required: true,
      min: 0,
      maxNumber: 100000000,
    },
    {
      key: 'severity',
      label: 'Hypothetical severity',
      type: 'select',
      required: true,
      values: enums.severity,
    },
    {
      key: 'accommodation_required',
      label: 'People needing shelter',
      type: 'number',
      required: true,
      min: 0,
      maxNumber: Number(scenario.population),
    },
    {
      key: 'reserve_percent',
      label: 'Plan C reserve percentage',
      type: 'number',
      required: true,
      min: 0,
      maxNumber: 100,
    },
    {
      key: 'latitude',
      label: 'Latitude (optional)',
      type: 'number',
      min: -90,
      maxNumber: 90,
      step: 'any',
    },
    {
      key: 'longitude',
      label: 'Longitude (optional)',
      type: 'number',
      min: -180,
      maxNumber: 180,
      step: 'any',
    },
    { key: 'description', label: 'Planning assumptions', type: 'textarea', max: 2000 },
  ];
  const orderedFields = [
    'name',
    'disaster_type',
    'region',
    'district',
    'latitude',
    'longitude',
    'population',
    'severity',
    'accommodation_required',
    'reserve_percent',
    'description',
  ].map((key) => fields.find((f) => f.key === key));
  const chosen = result?.plans.find((p) => p.code === plan);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">HYPOTHETICAL PLANNING</span>
          <h1>Response Simulator</h1>
          <p>
            Compare response options using an explicit snapshot of actual inventory and shelter
            capacity.
          </p>
        </div>
        {result && (
          <ExportButtons
            path={(format) => `/api/simulations/${result.simulation_id}/export/${format}`}
          />
        )}
      </div>
      <div className="notice simulation-notice">
        <strong>HYPOTHETICAL SCENARIO — NOT A LIVE INCIDENT</strong>
        <p>
          Running, editing, comparing and discarding a scenario does not create disasters, reserve
          stock or change shelter occupancy.
        </p>
      </div>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {editing && (
        <State {...catalog}>
          <form onSubmit={run}>
            <section className="panel form-panel">
              <div className="section-heading">
                <span className="step">1</span>
                <div>
                  <h2>Scenario details</h2>
                  <p>The Assam flood example is hypothetical and is never saved as an incident.</p>
                </div>
              </div>
              <div className="form-grid">
                {orderedFields.map((f) => (
                  <React.Fragment key={f.key}>
                    {{
                      region: 'Affected area',
                      population: 'Affected population & urgency',
                      accommodation_required: 'Shelter requirements',
                      reserve_percent: 'Simulation constraints',
                      description: 'Planning assumptions',
                    }[f.key] && (
                      <div className="scenario-section">
                        <h3>
                          {
                            {
                              region: 'Affected area',
                              population: 'Affected population & urgency',
                              accommodation_required: 'Shelter requirements',
                              reserve_percent: 'Simulation constraints',
                              description: 'Planning assumptions',
                            }[f.key]
                          }
                        </h3>
                      </div>
                    )}
                    <FormField
                      key={f.key}
                      field={f}
                      value={scenario[f.key]}
                      onChange={(value) => change(f.key, value)}
                    />
                  </React.Fragment>
                ))}
                <label>
                  <span>Reference an existing official incident (optional)</span>
                  <select
                    value={scenario.disaster_id}
                    onChange={(e) => change('disaster_id', e.target.value)}
                  >
                    <option value="">Independent hypothetical scenario</option>
                    {catalog.data?.disasters.map((d) => (
                      <option value={d.disaster_id} key={d.disaster_id}>
                        {d.title}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>
            <section className="panel form-panel">
              <div className="section-heading">
                <span className="step">2</span>
                <div>
                  <h2>Resource demand assumptions</h2>
                  <p>
                    Choose actual inventory items. Each quantity uses that item’s unit. Rows can
                    represent competing regional demands.
                  </p>
                </div>
              </div>
              {!catalog.data?.resources.length && (
                <p className="notice">
                  No resource inventory is available. Add real inventory in Resources before
                  planning.
                </p>
              )}
              <div className="demand-inputs">
                {demands.map((d, index) => {
                  const resource = catalog.data?.resources.find(
                    (r) => r.resource_id === Number(d.resource_id),
                  );
                  return (
                    <div className="demand-row" key={index}>
                      <label>
                        <span>Resource</span>
                        <select
                          required
                          value={d.resource_id}
                          onChange={(e) => demandChange(index, 'resource_id', e.target.value)}
                        >
                          <option value="">Select inventory resource</option>
                          {catalog.data?.resources.map((r) => (
                            <option key={r.resource_id} value={r.resource_id}>
                              {r.resource_name} / {r.unit}
                            </option>
                          ))}
                        </select>
                        <small>
                          {resource
                            ? `Available ${resource.available_quantity} ${resource.unit}`
                            : 'No invented resource types'}
                        </small>
                      </label>
                      <label>
                        <span>Required {resource?.unit || 'quantity'}</span>
                        <input
                          required
                          type="number"
                          min="0.01"
                          step="0.01"
                          max="9999999999.99"
                          value={d.quantity}
                          onChange={(e) => demandChange(index, 'quantity', e.target.value)}
                        />
                      </label>
                      <label>
                        <span>Demand region</span>
                        <input
                          required
                          maxLength={100}
                          value={d.region}
                          onChange={(e) => demandChange(index, 'region', e.target.value)}
                        />
                      </label>
                      <label>
                        <span>Priority (5 highest)</span>
                        <select
                          value={d.priority}
                          onChange={(e) => demandChange(index, 'priority', e.target.value)}
                        >
                          {[1, 2, 3, 4, 5].map((v) => (
                            <option key={v} value={v}>
                              {v}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        disabled={demands.length === 1}
                        onClick={() => setDemands((rows) => rows.filter((_, i) => i !== index))}
                      >
                        Remove
                      </button>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                disabled={demands.length >= 100}
                onClick={() =>
                  setDemands((rows) => [
                    ...rows,
                    { resource_id: '', quantity: '', region: scenario.region, priority: 3 },
                  ])
                }
              >
                + Add demand
              </button>
            </section>
            <footer className="form-actions">
              <p className="muted">All three plans share one fresh, read-only MySQL snapshot.</p>
              <button className="primary" disabled={busy || !catalog.data?.resources.length}>
                {busy ? 'Calculating…' : 'Run hypothetical simulation'}
              </button>
            </footer>
          </form>
        </State>
      )}
      {result && (
        <>
          <section className="panel simulation-summary">
            <div>
              <h2>{result.scenario.name}</h2>
              <p>
                {label(result.scenario.disaster_type)} · {result.scenario.region} ·{' '}
                {result.scenario.population.toLocaleString()} people ·{' '}
                {label(result.scenario.severity)}
              </p>
              <small>
                Snapshot: {result.snapshot.captured_at} · Results expire after one hour and are lost
                on backend restart.
              </small>
            </div>
            <div className="heading-actions">
              <button disabled={busy} onClick={() => setEditing(true)}>
                Edit & rerun
              </button>
              <button disabled={busy} onClick={discard}>
                Discard result
              </button>
            </div>
          </section>
          <section className="panel comparison-note">
            <h2>Compare feasible coverage</h2>
            <DataTable
              rows={result.plans.map((p) => ({
                plan: 'Plan ' + p.code,
                fully: p.fully_covered_requests,
                partial: p.partially_covered_requests,
                unallocated: p.unallocated_requests,
                shelter_gap: result.shelters.gap,
              }))}
              columns={[
                { key: 'plan', label: 'Strategy' },
                { key: 'fully', label: 'Fully covered' },
                { key: 'partial', label: 'Partially covered' },
                { key: 'unallocated', label: 'Unallocated' },
                { key: 'shelter_gap', label: 'Shelter gap' },
              ]}
            />
            <p className="muted">
              Plan A follows priority when resource distances are unavailable. Plan B serves the
              largest demand within each resource first; this may cover fewer smaller requests. Plan
              C protects {result.scenario.reserve_percent}% of available stock and can leave more
              unmet demand. All plans use the same snapshot; choose the trade-off, not an assumed
              optimal score.
            </p>
          </section>
          <div className="plan-tabs" role="tablist" aria-label="Response plans">
            {result.plans.map((p) => (
              <button
                role="tab"
                aria-selected={p.code === plan}
                className={p.code === plan ? 'selected' : ''}
                key={p.code}
                onClick={() => setPlan(p.code)}
              >
                <strong>Plan {p.code}</strong>
                <span>{p.title}</span>
              </button>
            ))}
          </div>
          <Metrics
            items={[
              [
                'Fully covered requests',
                chosen.fully_covered_requests,
                'Non-zero demand rows covered in full',
              ],
              ['Partially covered', chosen.partially_covered_requests],
              ['Unallocated', chosen.unallocated_requests],
              ['Shelter gap', result.shelters.gap, 'People; all-region capacity upper bound'],
            ]}
          />
          {(chosen.resources.some((r) => Number(r.unmet) > 0) || result.shelters.gap > 0) && (
            <div className="notice" role="status">
              Plan {plan} leaves unmet demand for{' '}
              {chosen.resources.filter((r) => Number(r.unmet) > 0).length} resource types. Shelter
              shortfall: {result.shelters.gap} people. Review the per-unit shortages and protected
              reserves below.
            </div>
          )}
          <section className="panel">
            <div className="panel-heading">
              <h2>Plan {plan}: resource balance</h2>
            </div>
            <DataTable
              rows={chosen.resources.map((r) => ({
                ...r,
                shortage_percent: (100 - Number(r.coverage_percent)).toFixed(2),
              }))}
              columns={[
                { key: 'resource_name', label: 'Resource' },
                { key: 'unit', label: 'Unit' },
                { key: 'required', label: 'Required' },
                { key: 'available', label: 'Snapshot available' },
                { key: 'proposed', label: 'Proposed' },
                { key: 'remaining', label: 'Remaining' },
                { key: 'reserve', label: 'Protected reserve' },
                { key: 'unmet', label: 'Unmet' },
                { key: 'coverage_percent', label: 'Demand covered %' },
                { key: 'shortage_percent', label: 'Unmet %' },
              ]}
            />
            <p className="panel-note">
              Coverage = proposed ÷ required for each resource. Quantities are never summed across
              different units.
            </p>
          </section>
          <section className="panel">
            <div className="panel-heading">
              <h2>Regional demand distribution</h2>
            </div>
            <DataTable
              rows={chosen.rows}
              columns={[
                { key: 'region', label: 'Region' },
                { key: 'resource_name', label: 'Resource' },
                { key: 'unit', label: 'Unit' },
                { key: 'required', label: 'Required' },
                { key: 'proposed', label: 'Proposed' },
                { key: 'unmet', label: 'Unmet' },
                { key: 'coverage_percent', label: 'Covered %' },
              ]}
            />
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Eligible shelters</h2>
                <p>
                  {result.shelters.required} people requested; {result.shelters.eligible_capacity}{' '}
                  available places across all regions.
                </p>
              </div>
            </div>
            <DataTable
              rows={result.shelters.items}
              columns={[
                { key: 'name', label: 'Shelter' },
                { key: 'state', label: 'State' },
                { key: 'available_capacity', label: 'Spare places' },
                { key: 'distance_km', label: 'Straight-line km' },
              ]}
            />
            <p className="panel-note">
              {result.shelters.distance_method}. Missing coordinates show no distance.
            </p>
          </section>
          <section className="panel form-panel">
            <h2>Assumptions & limitations</h2>
            {result.warnings.map((w) => (
              <p key={w} className="muted">
                {w}
              </p>
            ))}
          </section>
        </>
      )}
    </>
  );
}
