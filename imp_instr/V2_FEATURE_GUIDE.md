> Historical record: original frontend paths below describe earlier versions. The current React application is in frontend/; use RUN_PROJECT_WINDOWS.md for current commands. Legacy UI files were removed at the user’s request on 12 October 2026.

# V2 features, data sources and limitations

## Design, theme and navigation

Light background #F4F4F4, surfaces #FFFFFF, text #202020 and orange #F28C28; dark surfaces #141414/#202020, readable light text and orange accents. Dark/light selection is the only preference saved in localStorage, persists across navigation, and initially respects OS preference. Focus and reduced-motion styles remain. All management pages use the shared layout, forms and dialogs. Ledger/audit/analytics pages still exist behind contextual links; no standalone sidebar items were removed from the backend.

## India map and picker

Leaflet 1.9.4 and markercluster 1.5.3 are bundled locally with licenses. Tiles use [OpenStreetMap's standard service](https://operations.osmfoundation.org/policies/tiles/): visible attribution, normal browser caching, no offline download/bulk prefetch or fake live feed. Internet is required for tiles; local boundaries and the incident list remain available on tile failure. MAP_TILE_URL can be replaced with an operator-approved compatible provider; update attribution if that provider requires something different.

The local 36-feature ADM1 boundary dataset is from [geoBoundaries gbOpen India](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/), source DataMeet / Election Commission, boundary ID IND-ADM1-1811400, metadata year 2011, build December 2023, license **CC BY 2.5 India**. Original metadata is retained. It includes Ladakh and the merged Dadra and Nagar Haveli and Daman and Diu feature. This is a cartographic source with its own historical metadata, not a guarantee of current legal boundary precision. Simplified polygons are for display/filtering, not emergency navigation or surveyed coordinates.

Managers see official disasters and unverified/rejected reports; confirmed reports do not duplicate their linked official disaster. Public users see only their own reports; confirmed citizen reports have a V symbol, not an official A marker. Critical active official records use C squares, other official records A circles, pending P dashed squares, resolved R, rejected X (opt-in), and unknown legacy review U. Unlocated/invalid/out-of-India-extent points remain in the list. The extent check is a broad bounding box, not point-in-country legal validation.

Filters cover text/type/severity/status/dates/state; marker and list refresh together with request cancellation and stale-result guards. Data is manually refreshed, not continuously monitored. Matching records are loaded in API pages; very large result sets should be narrowed by filters. State boundary clicks use provider names; existing location spellings may differ and are not silently rewritten.

Saved locations can be searched with debouncing. Place lookup is a manual Search action through [Photon's demo service](https://github.com/komoot/photon#demo-server), suitable only for modest reasonable use, without an SLA. Server requests share a per-process 1.1-second minimum interval and 24-hour bounded memory cache; 429/timeouts preserve form input. It is not an autocomplete request per keystroke. Multiple workers multiply that budget: use a self-hosted/approved provider for larger deployments. Photon receives search text; the UI asks users not to include personal details. Attribution is shown. GEOCODING_ENABLED=false disables lookup while saved locations/text/map points still work.

Coordinates record source USER_ENTERED, GEOCODER, MAP_POINT or LEGACY. A geocoder match verifies neither an incident nor an address entered by a person; managers must check it. Public unfamiliar-location submission does not insert Locations. Confirmation requires a manager-selected official location. Text-only records are valid; paired coordinate validation prevents half a point. Saved-location matching normalizes text and unique keys protect concurrent new duplicates without merging old rows.

## Priority

Deterministic severity weights: CRITICAL 100, HIGH 75, MEDIUM 50, LOW 25, unknown 0. Response adds ACTIVE 20, pending review 15, CONTAINED/IN_PROGRESS 10, otherwise 0. Whole elapsed hours from stored start/submission add min(15, max(0, hours)); missing time adds 0. Resolved/rejected records score 0. Database/business timezone is DB_TIME_ZONE (default +05:30). Severity/status filters and Priority sorting retain human review. This is triage, never prediction or automatic confirmation.

## Resource requests and shelters

A request selects an existing disaster/resource and positive quantity in that resource's unit. Outstanding = requested minus noncancelled linked allocations. Delivered is tracked separately; fulfillment denotes reserved/allocated coverage, not completed delivery. Recommendation = min(outstanding, available), shortage = max(0, outstanding - available). Independent recommendations compete for the same stock and are not added up as guaranteed availability. Existing available stock already excludes reservations; units are never combined. Create/edit a demand does not modify stock. Manager approves/adjusts explicitly; approval uses the existing allocation transaction/row locks, checks remaining demand and stock, and stores an idempotency key. Allocation edits/cancellation/deletion reuse the original restoration/ledger rules.

Nearest eligible shelters use Haversine with earth radius 6371.0088 km and real coordinate pairs. Exclude CLOSED/FULL or capacity <= occupancy, and missing/invalid points. Distances are straight-line, not road/travel distances; live capacity can change. Recommendations never register a person or alter occupancy. Existing registration locks/check-in/out rules remain.

## Timeline, CSV and print/PDF

Timeline combines actual submission/creation/review/resolution timestamps and authorized audit rows, including related allocations/assignments/requests. Missing past actors/status changes are explicitly marked unavailable. Public timelines omit administrative snapshots and actors. Stored review timestamps and an audit change can describe the same recorded action from different sources; no pre-audit history is invented.

CSV endpoints `/api/exports/{module}.csv` cover disasters, emergency-reports, resources and resource-allocations. They reuse list filters and owner scope, stream all matching rows using explicit field allowlists, ignore pagination, emit UTF-8 BOM/ISO dates, escape quotes/newlines and neutralize spreadsheet formulas. Password/session/reporter-account secrets are excluded. A database disconnect during a streaming transfer may interrupt the file; retry rather than trusting a truncated export.

Incident/filtered-summary print views fetch authorized backend records, escape descriptions, include identity/location/status/timeline/resources/assignments/nearest shelters where permitted, repeat table headers and use dedicated A4 print styles. Choose browser **Print / Save as PDF**; no server PDF download is claimed. Browser print margin boxes provide page numbers where supported (recent Chromium); verify your browser's pagination/header settings and Unicode fonts. Huge summaries are more suitable for streaming CSV. Physical/multipage PDF rendering still needs owner verification.

## Preserved DBMS/security

Authentication, roles, CSRF request convention, sessions, inventory/capacity locks, reporting views and history/ledger remain. New endpoints enforce server permissions. No SQLite fallback, cloud service, automatic migration or fake records. Default geocoding/tile access is optional external internet traffic. Requirements remain bounded and Python 3.10-compatible at syntax/dependency-resolution level; actual runtime here is Python 3.12.
