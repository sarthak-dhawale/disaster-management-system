import { lazy, Suspense, useState } from 'react';
import { request } from './api';
const PointMap = lazy(() => import('./overview').then((m) => ({ default: m.PointMap })));
export function LocationPicker({ onPick }) {
  const [search, setSearch] = useState(''),
    [items, setItems] = useState([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [mapOpen, setMapOpen] = useState(false);
  async function find() {
    setBusy(true);
    setError('');
    try {
      setItems(
        (await request('/api/intelligence/places/search?q=' + encodeURIComponent(search))).items,
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="location-picker span-two">
      <h3>Find an unfamiliar location</h3>
      <p className="muted">
        Place matches help identify coordinates; they do not verify an incident. You can enter an
        address and coordinates manually.
      </p>
      <div className="toolbar">
        <input
          aria-label="Search place name"
          placeholder="Place, street or village in India"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" disabled={busy || search.trim().length < 3} onClick={find}>
          {busy ? 'Searching…' : 'Find place'}
        </button>
        <button type="button" onClick={() => setMapOpen(!mapOpen)}>
          {mapOpen ? 'Close map' : 'Select point on map'}
        </button>
      </div>
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      <div className="place-results">
        {items.map((item, index) => (
          <button
            key={index}
            type="button"
            onClick={() => {
              onPick({ ...item, coordinate_source: 'GEOCODER' });
              setItems([]);
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      {mapOpen && (
        <Suspense fallback={<p>Loading map…</p>}>
          <PointMap onPick={onPick} />
        </Suspense>
      )}
      <small>Place lookup: Photon / OpenStreetMap contributors. Map points are unverified.</small>
    </div>
  );
}
