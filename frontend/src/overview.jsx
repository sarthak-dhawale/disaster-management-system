import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
export { IndiaMap } from './incident-map';
export { Overview } from './overview-v4';
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
