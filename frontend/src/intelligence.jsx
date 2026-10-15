import { useState } from 'react';
import { useData, useDebounced } from './hooks';
import { query, request, invalidate } from './api';
import { Metrics, State, DataTable, Pagination, ExportButtons, Modal, label } from './ui';
import { ActionDialog, Relation } from './forms';
export function DemandDetails({ row, onClose }) {
  const allocations = useData(
    `/api/resource-allocations/?${query({ request_id: row.request_id, limit: 200 })}`,
  );
  const history = useData(
    `/api/audit-history/?entity=resource_requests&record_id=${row.request_id}&limit=100`,
  );
  const ledger = useData(`/api/resource-movements/?resource_id=${row.resource_id}&limit=100`);
  return (
    <Modal title={`Request #${row.request_id} / ${row.resource_name}`} wide onClose={onClose}>
      <p>{row.recommendation_reason}</p>
      <div className="detail-grid">{[['Required',row.quantity],['Reserved / delivered',row.allocated_quantity],['Delivered',row.delivered_quantity],['Outstanding',row.outstanding_quantity],['Available stock',row.available_quantity],['Coverage',row.fulfillment],['Request status',row.status]].map(([title,value]) => <div key={title}><small>{title}</small><p>{value}</p></div>)}</div>
      <h3>Linked allocations (first 200)</h3>
      <State {...allocations}>
        <DataTable
          rows={(allocations.data?.resource_allocations || []).filter(
            (a) => a.request_id === row.request_id,
          )}
          columns={[
            { key: 'allocation_id', label: 'Allocation' },
            { key: 'quantity', label: 'Quantity' },
            { key: 'status', label: 'Status' },
          ]}
        />
      </State>
      <h3>Recorded request history (latest 100)</h3>
      <State {...history}>
        <DataTable
          rows={history.data?.items || []}
          columns={[
            { key: 'created_at', label: 'Timestamp' },
            { key: 'action', label: 'Action' },
            { key: 'actor_name', label: 'Manager' },
          ]}
        />
      </State>
      <h3>Resource movement ledger (latest 100)</h3>
      <State {...ledger}>
        <DataTable
          rows={ledger.data?.items || []}
          columns={[
            { key: 'created_at', label: 'Timestamp' },
            { key: 'movement_kind', label: 'Event' },
            { key: 'available_delta', label: 'Change' },
            { key: 'note', label: 'Note' },
          ]}
        />
      </State>
      <p className="muted">
        Earlier events may not have been recorded. Coverage is reserved stock, not proof of
        delivery.
      </p>
    </Modal>
  );
}
export function ResourceIntelligence({ notify }) {
  const [filters, setFilters] = useState({}),
    [search, setSearch] = useState(''),
    [offset, setOffset] = useState(0),
    [action, setAction] = useState(null),
    [details, setDetails] = useState(null);
  const q = useDebounced(search),
    params = query({ ...filters, q });
  const state = useData(`/api/resource-intelligence?${params}&limit=25&offset=${offset}`);
  const data = state.data,
    metrics = data?.metrics;
  const [advanced, setAdvanced] = useState(false);
  const columns = [
    { key: 'request_id', label: 'Request ID' },
    { key: 'disaster_title', label: 'Disaster' },
    { key: 'severity', label: 'Urgency' },
    { key: 'resource_name', label: 'Resource' },
    { key: 'unit', label: 'Unit' },
    { key: 'quantity', label: 'Required' },
    { key: 'available_quantity', label: 'Available' },
    { key: 'outstanding_quantity', label: 'Unmet request' },
    { key: 'recommended_action', label: 'Recommended next step' },
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">LIVE DEMAND & INVENTORY</span>
          <h1>Resource Intelligence</h1>
          <p>Understand competing demand and approve quantities against real available stock.</p>
        </div>
        <div className="heading-actions">
          <ExportButtons
            path={(format) => `/api/reports/resource-intelligence/${format}?${params}`}
          />
          <button
            className="primary"
            onClick={() =>
              setAction({
                title: 'Record resource demand',
                path: '/api/resource-requests/',
                fields: [
                  {
                    key: 'disaster_id',
                    label: 'Official disaster',
                    type: 'relation',
                    module: 'disasters',
                    required: true,
                  },
                  {
                    key: 'resource_id',
                    label: 'Resource',
                    type: 'relation',
                    module: 'resources',
                    required: true,
                  },
                  {
                    key: 'quantity',
                    label: 'Required quantity in selected resource unit',
                    type: 'number',
                    required: true,
                    min: 0.01,
                    step: 0.01,
                  },
                  { key: 'note', label: 'Demand justification', type: 'textarea', max: 500 },
                ],
              })
            }
          >
            + Record demand
          </button>
        </div>
      </div>
      {metrics && (
        <Metrics
          items={[
            ['Outstanding requests', metrics.outstanding_requests],
            ['Urgent unresolved', metrics.high_priority_unresolved],
            ['Resource types short', metrics.shortage_resource_types],
          ]}
        />
      )}
      {data?.resource_totals.length > 0 && <details className="panel resource-balance"><summary>Resource balances and shortage quantities</summary><DataTable rows={data.resource_totals} columns={[{key:'resource_name',label:'Resource'},{key:'unit',label:'Unit'},{key:'outstanding',label:'Open unmet demand'},{key:'available',label:'Available stock'},{key:'shortage',label:'Shortage'}]} /><p className="panel-note">Stock is shared across requests. Recommendations use rules; approval revalidates stock.</p></details>}
      <section className="panel">
        <div className="toolbar">
          <input
            aria-label="Search demands"
            placeholder="Search disaster, resource or region…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
          <select
            aria-label="Coverage status"
            value={filters.status || ''}
            onChange={(e) => {
              setFilters({ ...filters, status: e.target.value });
              setOffset(0);
            }}
          >
            <option value="">All coverage</option>
            {['FULFILLED', 'PARTIAL', 'UNFULFILLED', 'CANCELLED'].map((v) => (
              <option key={v} value={v}>
                {label(v)}
              </option>
            ))}
          </select>
          <select
            aria-label="Severity"
            value={filters.severity || ''}
            onChange={(e) => {
              setFilters({ ...filters, severity: e.target.value });
              setOffset(0);
            }}
          >
            <option value="">All urgency</option>
            {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((v) => (
              <option value={v} key={v}>
                {label(v)}
              </option>
            ))}
          </select>
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
          <button onClick={() => setAdvanced(!advanced)}>
            {advanced ? 'Hide advanced filters' : 'Advanced filters'}
          </button>
        </div>
        {advanced && (
          <div className="form-grid form-panel">          <input
            aria-label="State"
            placeholder="State"
            value={filters.state || ''}
            onChange={(e) => {
              setFilters({ ...filters, state: e.target.value });
              setOffset(0);
            }}
          />
          <select
            aria-label="Priority"
            value={filters.priority || ''}
            onChange={(e) => {
              setFilters({ ...filters, priority: e.target.value });
              setOffset(0);
            }}
          >
            <option value="">All priorities</option>
            <option value="URGENT">High / critical unresolved</option>
            <option value="AWAITING_REVIEW">Awaiting allocation review</option>
          </select>
          <select
            aria-label="Request status"
            value={filters.request_status || ''}
            onChange={(e) => {
              setFilters({ ...filters, request_status: e.target.value });
              setOffset(0);
            }}
          >
            <option value="">All request statuses</option>
            <option value="OPEN">Open</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

            <label>
              <span>Official disaster</span>
              <Relation
                field={{ label: 'disaster', module: 'disasters' }}
                value={filters.disaster_id}
                onChange={(v) => {
                  setFilters({ ...filters, disaster_id: v });
                  setOffset(0);
                }}
              />
            </label>
            <label>
              <span>Resource</span>
              <Relation
                field={{ label: 'resource', module: 'resources' }}
                value={filters.resource_id}
                onChange={(v) => {
                  setFilters({ ...filters, resource_id: v });
                  setOffset(0);
                }}
              />
            </label>
          </div>
        )}
        {data && !data.items.length && (
          <p className="panel-note">
            No demand matches these filters. Clear filters or record a justified demand for an
            official incident. Missing inventory cannot produce an allocation recommendation.
          </p>
        )}
        <State {...state} empty={!data?.items.length}>
          <DataTable
            rows={data?.items || []}
            columns={columns}
            actions={(row) => (
              <>
                <button onClick={() => setDetails(row)}>Details</button>
                {row.status === 'OPEN' && Number(row.outstanding_quantity) > 0 && (
                  <button
                    disabled={Number(row.recommended_quantity) <= 0}
                    onClick={() =>
                      setAction({
                        title: `Approve request #${row.request_id}`,
                        path: `/api/resource-requests/${row.request_id}/approve`,
                        initial: {
                          quantity: row.recommended_quantity,
                          idempotency_key: crypto.randomUUID(),
                        },
                        description: `Recommended ${row.recommended_quantity} ${row.unit}. ${row.recommendation_reason}`,
                        fields: [
                          {
                            key: 'quantity',
                            label: `Quantity (${row.unit})`,
                            type: 'number',
                            required: true,
                            min: 0.01,
                            step: 0.01,
                            maxNumber: Math.min(
                              Number(row.outstanding_quantity),
                              Number(row.available_quantity),
                            ),
                          },
                          {
                            key: 'idempotency_key',
                            label: 'Approval reference',
                            type: 'text',
                            required: true,
                          },
                        ],
                      })
                    }
                  >
                    Approve
                  </button>
                )}
                {row.status === 'OPEN' && (
                  <button
                    onClick={() =>
                      setAction({
                        title: 'Edit demand',
                        path: `/api/resource-requests/${row.request_id}`,
                        method: 'PUT',
                        initial: { quantity: row.quantity, note: row.note },
                        fields: [
                          {
                            key: 'quantity',
                            label: 'Required quantity',
                            type: 'number',
                            required: true,
                            min: Math.max(0.01, Number(row.allocated_quantity)),
                            step: 0.01,
                          },
                          { key: 'note', label: 'Note', type: 'textarea' },
                        ],
                      })
                    }
                  >
                    Edit
                  </button>
                )}
                {row.status === 'OPEN' && Number(row.allocated_quantity) === 0 && (
                  <button
                    onClick={() =>
                      setAction({
                        title: 'Cancel this demand?',
                        path: `/api/resource-requests/${row.request_id}/cancel`,
                        fields: [],
                        description:
                          'The request will remain in history with CANCELLED status. Inventory is unchanged.',
                      })
                    }
                  >
                    Cancel
                  </button>
                )}
              </>
            )}
          />
        </State>
        <Pagination total={data?.total || 0} offset={offset} setOffset={setOffset} />
      </section>
      {data && (
        <section className="panel">
          <div className="panel-heading">
            <h2>Shared stock contention</h2>
          </div>
          <p className="panel-note">{data.scope_note}</p>
          <DataTable
            rows={data.resource_totals}
            columns={[
              { key: 'resource_name', label: 'Resource' },
              { key: 'unit', label: 'Unit' },
              { key: 'outstanding', label: 'Combined outstanding' },
              { key: 'available', label: 'Available stock' },
              { key: 'shortage', label: 'Shortage' },
            ]}
          />
        </section>
      )}
      {action && <ActionDialog {...action} onClose={() => setAction(null)} onSuccess={notify} />}{' '}
      {details && <DemandDetails row={details} onClose={() => setDetails(null)} />}
    </>
  );
}
