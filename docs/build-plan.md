# Build Plan

Build in this order. Each step should work end-to-end before starting the next.

## Phase 1 — Data pipeline
- [x] Set up project structure and install dependencies
- [x] `collect.py`: call Apify actor for Rightmove, one area, print raw JSON
- [x] `collect.py`: expand to all areas and both platforms (Rightmove + Zoopla)
- [x] `ingest.py`: create SQLite DB, parse Apify JSON, insert rows, dedup by URL
- [x] `ingest.py`: update `last_seen_date` and `days_on_market` for duplicate URLs on every run
- [ ] `collect.py`: add OpenRent via Playwright browser automation as fallback
- [x] `enrich.py`: TfL API call for one listing, store commute times
- [x] `enrich.py`: batch enrich all listings missing commute times; set `tfl_failed` on permanent errors
- [ ] `ingest.py`: compute area median prices and price_vs_median_pct (Mondays only)
- [ ] End-to-end test: full collection cycle, verify DB populated correctly

## Phase 2 — Webapp
- [x] `serve.py`: basic Flask app, query all listings, render as HTML table
- [x] Webapp: add filters (area, bedrooms, max rent, status, availability)
- [x] Webapp: add sorting (rent, commute time, days on market, listed date)
- [x] Webapp: show listing cards with key fields + TfL commute times
- [x] Webapp: status update buttons (interested / dismissed / viewed) + editable notes field
- [x] Webapp: highlight 2-bed under £2,500 and listings 14+ days old
- [x] Webapp: split-screen layout — sidebar (22%), feed (42%), interactive Leaflet map (36%)
- [x] Webapp: Leaflet + CartoDB Dark Matter map with price-label markers (229/230 listings geocoded)
- [x] Webapp: card → map hover sync; map marker click scrolls to card
- [x] Webapp: simplified sidebar (5 filters: rent, work commute, LSE commute, status, platform)
- [x] Webapp: muted desaturated commute badge palette (ct-good/ct-ok/ct-bad) relative to filter limits

## Phase 3 — Automation
- [ ] `digest.py`: query listings added in last 24h, format HTML email
- [ ] `digest.py`: send via Gmail (SMTP or MCP); accept `--scheduled` flag to enable digest
- [ ] Cron job: schedule daily 8am run in Europe/London timezone (collect → ingest → enrich → digest --scheduled)
- [ ] Test full automated cycle

## Phase 4 — Polish
- [x] `config.example.md`: document all required config fields
- [ ] Error handling: Apify failures, TfL timeouts, empty results
- [ ] Logging: per-run summary (N new listings, N enriched, N emailed)
- [ ] README: setup instructions

## Current status
Phase 1 steps 1–7 complete. 93 listings in DB; 91 enriched with commute times, 2 permanently failed (1 no postcode, 1 timeout). Ready for area median prices (step 8) or webapp (Phase 2).
