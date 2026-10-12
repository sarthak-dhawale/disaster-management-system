# Performance evidence and limits

12 October 2026. See TEST_RESULTS.md for the full verification record.

Production Vite build: 49 modules, reported build time 1.01 seconds; measured helper wall time 2.122 seconds. Map implementation is a separate lazy chunk. Sizes are build measurements, not network timings.

| Asset                 |  Bytes | gzip bytes |
| --------------------- | -----: | ---------: |
| index-DSA8Up0w.js     | 283703 |      86979 |
| index-jd5HAwbQ.css    |  18144 |       4710 |
| overview-9Hbp8J6b.css |  17253 |       6716 |
| overview-lHtftIgY.js  | 192140 |      54722 |

Four actual Node tests validate one shared in-flight request for two subscribers, abort after last subscriber unmount, retention of field validation errors without invented records, and safe filter serialization. The shared cache lasts 15 seconds, invalidates after mutations/manual refresh, and separates complete query URLs. Search uses a 300 ms debounce and stale-response guards. Management pages load 25 rows, lookups 200, map at most 500 with an explicit scope note. Maps update layers while preserving their map instance; no map reinitialization on theme changes.

Browser fixture navigation, tables, themes and dialogs were usable at observed 2560/1440/480 CSS widths. Realistic large-data rendering, database query timings, React render counts, map-update timing and a measured V2-versus-V3 comparison were not collected. No percentage speed-up or claim that V3 is demonstrably faster with the owner's records is made. Verify those acceptance items on the primary laptop using its actual dataset.

Planning reads inventory/shelters/disasters in one repeatable-read read-only transaction and performs Decimal calculations in memory. Result cache is bounded to 100 scenarios, 32 MiB and one-hour TTL. Exports/analysis refuse scopes above 10,000 rows instead of silently truncating. ReportLab work runs in FastAPI synchronous route worker threads; reports still require memory proportional to bounded selected rows.
