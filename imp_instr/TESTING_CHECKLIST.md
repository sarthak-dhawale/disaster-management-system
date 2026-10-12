# V3 acceptance checklist

Use actual MySQL on the primary/secondary laptop for these unchecked acceptance steps. Isolated test fixtures are not real-data proof.

- [ ] Start the correct existing MySQL 8.4 instance; health returns 200 connected. Restart API/MySQL and verify records persist.
- [ ] Existing administrator logs in; public account registration hashes password and cannot choose an administrative role; logout invalidates session; expiry redirects safely.
- [ ] Public user cannot call admin CRUD, intelligence, simulator, history or aggregate export endpoints; manager cannot manage Users; one public account cannot read another's report/export.
- [ ] All 17 destinations load, light/dark theme persists, navigation works on desktop/tablet/phone, focus is visible, forms/dialogs remain usable and tables scroll inside their containers.
- [ ] Create/read/edit/delete disasters, shelters, volunteers, resources, locations, users, allocations, assignments and shelter registrations using isolated owner-chosen demo records. Verify FK/duplicate/missing/invalid errors, inventory restoration, shelter capacity and volunteer availability.
- [ ] Pending report: saved verified location or unfamiliar address with optional paired coordinates; reference shown; no official disaster until review. Manager confirms with location/link or rejects with reason. Repeat confirmation returns the existing official record. Check owner status and privacy.
- [ ] Map filters/search/dates/clear agree with actual records; missing coordinates stay visible; confirmed reports do not double-count official incidents; map survives filter updates; internet-provider failure leaves manual location entry usable.
- [ ] Resource Intelligence: competing same-resource requests share stock; cancellation removes reserved coverage and restores stock exactly once; coverage and delivery remain distinct; recommendations never promise the same stock to all requests; approve/retry is idempotent and permission protected. Check matching history and ledger.
- [ ] Overview, Disasters, Reports, Emergency Reports, Shelters, Resources, Resource Intelligence: PDF/CSV exports match documented scopes/filters, dates and permissions. PDFs open, paginate, include readable fonts, real map/legend and footer. Empty/long/Unicode records remain readable. Larger-than-limit scope returns actionable error, not incomplete export.
- [ ] Simulator: hypothetical Assam flood / 2,000 population, select real catalog resources and manager-entered quantities; run all three plans from the same captured timestamp. Stock is never oversubscribed, units never mixed, reserve respected. Validate negative/zero/missing/oversized/invalid IDs/paired coordinates.
- [ ] Compare priorities/regions, shelter availability/missing coordinates, coverage denominators and gaps. All-region shelter capacity is only an upper bound. No resource-distance claim without warehouse coordinates.
- [ ] Edit/rerun captures a new snapshot; original saved result remains unchanged; exported simulation is visibly hypothetical. Discard/expiry/restart removes only memory results. Confirm database table counts, quantities, occupancy, audit and ledger are unchanged by all simulator actions.
- [ ] Disconnect MySQL: health 503; API returns sanitized errors; UI has loading/error/retry states and never fills with fake records. Reconnect and refresh. Try duplicate submission and slow/stale search responses.
- [ ] ZIP excludes private environment files, database backups, credentials, .git, node_modules and Python environments. Transfer to primary preserves existing container/volume/data.

Unit checks from backend after installing requirements-dev: `python -m pytest --assert=plain -q tests`. Frontend: `npm test` and `npm run build` in frontend. For real integration commands and safeguards see TEST_RESULTS.md.
