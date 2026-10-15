import { useEffect, useMemo, useRef, useState } from 'react';
import { useAllIncidents, useData, useDebounced } from './hooks';
import { download } from './api';
import { State, Badge, label, formatValue } from './ui';
import { IndiaMap } from './incident-map';
import { advanceEvent, playbackDelay } from './replay-controls';

export function ReplayStudio() {
  const catalog = useAllIncidents('include_resolved=true');
  const [search, setSearch] = useState(''), [id, setId] = useState(() => new URLSearchParams(location.hash.split('?')[1] || '').get('id') || '');
  const [index, setIndex] = useState(0), [playing, setPlaying] = useState(false), [speed, setSpeed] = useState(1), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const q = useDebounced(search).toLowerCase(), activeRef = useRef();
  const state = useData(id ? `/api/replay/disasters/${id}` : null);
  const all = catalog.data?.items.filter((r) => r.kind === 'disaster') || [];
  const choices = all.filter((r) => [r.id, r.title, r.disaster_type, r.city, r.state, r.response_status].join(' ').toLowerCase().includes(q));
  const events = state.data?.items || [], current = events[index];
  useEffect(() => { setIndex(0); setPlaying(false); setError(''); }, [id, state.data]);
  useEffect(() => {
    if (!playing || !events.length) return;
    if (index >= events.length - 1) { setPlaying(false); return; }
    const timer = setTimeout(() => setIndex((v) => advanceEvent(v, events.length)), playbackDelay(speed));
    return () => clearTimeout(timer);
  }, [playing, index, events.length, speed]);
  useEffect(() => { if (playing) activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [index, playing]);
  const marker = useMemo(() => {
    if (!state.data) return null;
    const d = state.data.disaster, l = current?.location || d;
    return { kind: 'disaster', id: d.disaster_id, title: d.title, disaster_type: d.disaster_type, severity: d.severity,
      response_status: d.status, event_title: current?.title, event_record: current ? `${current.entity} #${current.record_id}` : null,
      ...l, plottable: l.latitude != null && l.longitude != null && l.plottable !== false && Math.abs(Number(l.latitude)) <= 90 && Math.abs(Number(l.longitude)) <= 180 };
  }, [state.data, current]);
  const mapItems = useMemo(() => marker ? [marker] : [], [marker]);
  function seek(next) { setPlaying(false); setIndex(advanceEvent(next, events.length, 0)); }
  async function exportPdf() { setBusy(true); setError(''); try { await download(`/api/replay/disasters/${id}/pdf`); } catch (e) { setError(e.message); } finally { setBusy(false); } }
  return <>
    <div className="page-heading"><div><span className="eyebrow">RECORDED RESPONSE HISTORY</span><h1>Disaster Replay Studio</h1><p>Follow the recorded decisions behind any official disaster.</p></div>{state.data && <button disabled={busy} className="primary" onClick={exportPdf}>{busy ? 'Preparing…' : 'Export timeline PDF'}</button>}</div>
    <section className="panel replay-selector"><label><span>Find a disaster</span><input placeholder="Search ID, type, location or status…" value={search} onChange={(e) => setSearch(e.target.value)} /></label><State {...catalog}><label><span>Select official disaster ({choices.length})</span><select aria-label="Select disaster for replay" value={id} onChange={(e) => setId(e.target.value)}><option value="">Choose a disaster</option>{id && !choices.some((d) => String(d.id) === String(id)) && <option value={id}>Selected disaster #{id}</option>}{choices.map((d) => <option value={d.id} key={d.id}>#{d.id} · {d.title} · {d.city || d.state || 'Location unavailable'} · {label(d.response_status)}</option>)}</select></label></State></section>
    {error && <p className="notice error" role="alert">{error}</p>}
    {!id ? <section className="empty"><h2>Select a disaster to begin</h2><p>Every official record is available, including records with partial history.</p></section> : <State {...state}>{state.data && <>
      <div className="notice"><strong>{state.data.demonstration ? 'DEMONSTRATION RECORD · ' : ''}{events.length} recorded events · {state.data.audit_event_count} audit entries · partial coverage</strong><p>{state.data.history_note}</p></div>
      <section className="panel replay-workspace"><div className="panel-heading"><div><h2>#{state.data.disaster.disaster_id} · {state.data.disaster.title}</h2><p>Map: current stored location context. Status labels follow recorded events where available.</p></div><Badge value={state.data.disaster.status} /></div>
        <IndiaMap items={mapItems} selected={marker} fitSignal={id} onSelect={() => {}} />
        {!marker?.plottable && <p className="panel-note">Location unavailable for this event.</p>}
        <div className="replay-controls"><button disabled={!events.length || index === 0} onClick={() => seek(0)}>Beginning</button><button disabled={!events.length || index === 0} onClick={() => seek(index - 1)}>Previous</button><button className="primary" disabled={events.length < 2} onClick={() => { if (!playing && index === events.length - 1) setIndex(0); setPlaying(!playing); }}>{playing ? 'Pause' : 'Play'}</button><button disabled={!events.length || index === events.length - 1} onClick={() => seek(index + 1)}>Next</button><button disabled={!events.length || index === events.length - 1} onClick={() => seek(events.length - 1)}>Latest</button><label>Playback speed<select aria-label="Playback speed" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>{[1, 2, 4].map((s) => <option value={s} key={s}>{s}×</option>)}</select></label></div>
        <div className="replay-scrubber"><label htmlFor="replay-position">Event {events.length ? index + 1 : 0} of {events.length} · {current ? formatValue('created_at', current.timestamp) : 'No recorded events'}</label><input id="replay-position" aria-label="Timeline position" type="range" min="0" max={Math.max(0, events.length - 1)} value={index} disabled={!events.length} onChange={(e) => seek(Number(e.target.value))} /></div>
      </section>
      <div className="timeline-legend">{['INFORMATION', 'WARNING', 'CRITICAL', 'ACTION_TAKEN'].map((c) => <span key={c}><i className={`event-dot ${c.toLowerCase()}`} />{label(c)}</span>)}</div>
      {!events.length ? <section className="empty"><h2>No usable event timestamps</h2><p>This disaster remains selectable. No history has been fabricated.</p></section> : <ol className="replay-timeline">{events.map((event, i) => <li key={event.event_id} className={`${i === index ? 'current' : ''} ${event.category.toLowerCase()}`} ref={i === index ? activeRef : undefined} aria-current={i === index ? 'step' : undefined}><span className="timeline-node" /><article><button className="event-select" onClick={() => seek(i)}><small>{formatValue('created_at', event.timestamp)}</small><strong>{event.title}</strong></button><div className="event-meta"><span className="badge">{label(event.category)}</span>{event.status && <Badge value={event.status} />}</div><p>{event.description}</p><small>{event.actor_name || (event.actor_id ? `User #${event.actor_id}` : 'Actor not recorded')} · {label(event.entity)} #{event.record_id}</small><details><summary>Inspect recorded details</summary><p>{event.source}</p><pre>{JSON.stringify(event.metadata, null, 2)}</pre></details></article></li>)}</ol>}
    </>}</State>}
  </>;
}
