import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { useData } from './hooks';
import { label } from './ui';

export const mapKey = (item) => `${item.kind}:${item.id}`;
export function IndiaMap({ items = [], onSelect, selected, fitSignal = 0 }) {
  const element = useRef(),
    map = useRef(),
    clusters = useRef(),
    indexed = useRef(new Map());
  const callback = useRef(onSelect),
    [ready, setReady] = useState(false);
  callback.current = onSelect;
  const config = useData('/api/intelligence/map-config');
  useEffect(() => {
    const instance = L.map(element.current, {
      scrollWheelZoom: false,
      minZoom: 2,
      maxZoom: 18,
    }).setView([23.4, 81], 4.5);
    map.current = instance;
    clusters.current = L.markerClusterGroup({ maxClusterRadius: 45, chunkedLoading: true });
    instance.addLayer(clusters.current);
    const controller = new AbortController();
    fetch('/data/india-states.geojson', { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error('Boundary data unavailable');
        return r.json();
      })
      .then((data) => {
        if (map.current === instance)
          L.geoJSON(data, {
            style: { color: '#71899a', weight: 0.8, fillColor: '#b9cbd6', fillOpacity: 0.16 },
            onEachFeature: (f, layer) =>
              layer.bindTooltip(f.properties.shapeName || f.properties.name || 'Region'),
          }).addTo(instance);
      })
      .catch((e) => {
        if (e.name !== 'AbortError') console.error(e.message);
      });
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(element.current);
    setReady(true);
    return () => {
      controller.abort();
      observer.disconnect();
      instance.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    if (!ready || !config.data || !map.current) return;
    const tiles = L.tileLayer(config.data.tile_url, {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map.current);
    return () => tiles.remove();
  }, [ready, config.data]);
  useEffect(() => {
    if (!ready || !clusters.current) return;
    clusters.current.clearLayers();
    indexed.current.clear();
    const markers = [];
    for (const item of items) {
      if (
        !item.plottable ||
        !Number.isFinite(Number(item.latitude)) ||
        !Number.isFinite(Number(item.longitude)) ||
        Math.abs(Number(item.latitude)) > 90 ||
        Math.abs(Number(item.longitude)) > 180
      )
        continue;
      const chosen = selected && mapKey(item) === mapKey(selected);
      const style =
        item.kind === 'report' ? 'pending' : item.kind === 'disaster' ? 'official' : item.kind;
      const icon = L.divIcon({
        className: 'incident-marker',
        html: `<span class="map-dot ${style} ${item.severity === 'CRITICAL' ? 'critical-marker' : ''} ${chosen ? 'selected-marker' : ''}"></span>`,
        iconSize: [24, 24],
      });
      const marker = L.marker([Number(item.latitude), Number(item.longitude)], {
        icon,
        title: `${item.title} #${item.id}`,
        keyboard: true,
      });
      const popup = document.createElement('div');
      for (const value of [
        `${label(item.kind)} #${item.id} · ${item.title}`,
        `${item.city || 'Location'}${item.state ? ', ' + item.state : ''}`,
        [
          item.disaster_type && label(item.disaster_type),
          item.severity && label(item.severity),
          label(item.response_status),
        ]
          .filter(Boolean)
          .join(' · '),
        item.kind === 'shelter' && `${item.current_occupancy} / ${item.capacity} occupied`,
        item.kind === 'resource' && `${item.quantity} ${item.unit} · allocation destination`,
        item.event_title && `Selected event: ${item.event_title}`,
        item.event_record && `Associated record: ${item.event_record}`,
        item.context,
      ].filter(Boolean)) {
        const p = document.createElement('p');
        p.textContent = value;
        popup.append(p);
      }
      marker.bindPopup(popup).on('click', () => callback.current?.(item));
      indexed.current.set(mapKey(item), marker);
      markers.push(marker);
    }
    clusters.current.addLayers(markers);
  }, [ready, items, selected]);
  useEffect(() => {
    if (!ready || !selected?.plottable) return;
    const marker = indexed.current.get(mapKey(selected));
    if (marker) clusters.current.zoomToShowLayer(marker, () => marker.openPopup());
  }, [ready, selected, items]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const bounds = clusters.current.getBounds();
    if (bounds.isValid()) map.current.fitBounds(bounds, { padding: [35, 35], maxZoom: 11 });
    else map.current.setView([23.4, 81], 4.5);
  }, [ready, fitSignal]);
  return <div ref={element} className="india-map" aria-label="Interactive India incident map" />;
}
