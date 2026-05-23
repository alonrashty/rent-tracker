# Architecture

## Overview
Three-stage pipeline: collect → enrich → serve.

```
Apify (Rightmove, Zoopla)  ─┐
OpenRent (Claude in Chrome) ─┼→ SQLite DB → Webapp (read-only UI)
                             │            → Daily email digest
                             └→ TfL API enrichment (per new listing)
```

## Stack
- **Runtime**: Python 3.11+
- **Database**: SQLite (single file, `data/listings.db`)
- **Collection**: Apify REST API for Rightmove + Zoopla; Playwright via Claude in Chrome for OpenRent fallback
- **Enrichment**: TfL Journey Planner API (free, no key required)
- **Webapp**: Flask + plain HTML/JS (no framework — keep it simple)
- **Email**: Gmail SMTP or Gmail MCP connector
- **Scheduler**: cron (once daily, 8am)

## Data flow
1. `collect.py` calls Apify actors → raw JSON
2. `ingest.py` parses, deduplicates by URL, inserts new rows to SQLite
3. `enrich.py` runs TfL API on any listing missing journey times
4. `serve.py` runs Flask webapp (read-only, no writes from UI)
5. `digest.py` queries listings added in last 24h → sends email

## Key decisions
- SQLite over JSON: queryable, filterable, zero infrastructure
- Apify over direct scraping: handles anti-bot measures, returns clean JSON
- Flask over heavyweight framework: this is a personal tool, not a product
- No write operations from webapp: UI is for review only, status updates via CLI or direct DB
- Price benchmark built from collected data, no paid API

## Project structure
```
london-flat-hunt/
├── CLAUDE.md
├── config.md              # git-ignored
├── config.example.md
├── data/
│   └── listings.db        # SQLite database
├── src/
│   ├── collect.py         # Apify + OpenRent collection
│   ├── ingest.py          # Parse + dedup + insert
│   ├── enrich.py          # TfL journey times
│   ├── digest.py          # Daily email
│   └── serve.py           # Flask webapp
├── docs/
│   ├── architecture.md    # this file
│   ├── search-spec.md
│   ├── tfl-integration.md
│   ├── schema.md
│   └── build-plan.md
└── tests/
```
