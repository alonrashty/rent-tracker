# Database Schema

## File
`data/listings.db` — SQLite, single file, git-ignored.

## Table: listings

```sql
CREATE TABLE listings (
    -- Identity
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT UNIQUE NOT NULL,        -- dedup key
    platform            TEXT NOT NULL,               -- 'rightmove' | 'zoopla' | 'openrent'
    external_id         TEXT,                        -- platform's own listing ID

    -- Property
    title               TEXT,
    address             TEXT,
    postcode            TEXT,
    area                TEXT,                        -- normalised area name from search-spec
    bedrooms            INTEGER,
    bathrooms           INTEGER,
    property_type       TEXT,                        -- 'flat' | 'apartment' | etc
    sqft                INTEGER,                     -- nullable, often missing (Rightmove only)
    sqm                 REAL,                        -- sqft × 0.0929, nullable

    -- Pricing
    rent_pcm            INTEGER NOT NULL,            -- £/month
    bills_included      BOOLEAN DEFAULT FALSE,
    deposit             INTEGER,                     -- nullable

    -- Availability
    available_date      DATE,                        -- nullable if not specified
    min_tenancy_months  INTEGER,                     -- nullable

    -- Listing metadata
    listed_date         DATE,                        -- when first listed on platform
    last_seen_date      DATE,                        -- updated every ingest run, even for duplicates
    days_on_market      INTEGER,                     -- updated every ingest run: today - listed_date
    agent_name          TEXT,
    agent_phone         TEXT,

    -- Media
    image_url           TEXT,                        -- first photo URL
    listing_description TEXT,

    -- Location
    lat                 REAL,                        -- nullable; present for all Rightmove listings
    lon                 REAL,
    location_accuracy   TEXT,                        -- 'ACCURATE_POINT' | 'APPROXIMATE_POINT' (Rightmove only)

    -- Enrichment: TfL
    commute_work_mins   INTEGER,                     -- to Old Street, nullable
    commute_lse_mins    INTEGER,                     -- to LSE, nullable
    tfl_enriched_at     TIMESTAMP,
    tfl_failed          BOOLEAN DEFAULT FALSE,       -- true if postcode unresolvable
    tfl_error           TEXT,                        -- last TfL error message, nullable

    -- Enrichment: price benchmark
    area_median_pcm     INTEGER,                     -- median rent for same bedrooms in area
    price_vs_median_pct REAL,                        -- (rent_pcm / area_median_pcm - 1) * 100

    -- User review
    status              TEXT DEFAULT 'new',          -- 'new' | 'interested' | 'dismissed' | 'viewed'
    notes               TEXT,                        -- free text, user editable

    -- Timestamps
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Indexes
```sql
CREATE INDEX idx_url ON listings(url);
CREATE INDEX idx_area ON listings(area);
CREATE INDEX idx_area_beds ON listings(area, bedrooms);   -- for median price grouping
CREATE INDEX idx_status ON listings(status);
CREATE INDEX idx_listed_date ON listings(listed_date);
CREATE INDEX idx_rent_pcm ON listings(rent_pcm);
CREATE INDEX idx_commute ON listings(commute_work_mins);
```

## Notes
- `url` is the dedup key — never insert if URL already exists
- `status` and `notes` are the only fields the webapp can write
- `last_seen_date` is updated on every ingest run, including for duplicate URLs — use it to detect listings that have gone off market
- `days_on_market` is updated on every ingest run (not a static value)
- `area_median_pcm` is recomputed weekly (Mondays) from all collected listings grouped by `(area, bedrooms)`
- `tfl_failed = TRUE` means enrichment was attempted and permanently failed — skip in future runs
- Listings are never deleted — set `status = 'dismissed'` instead
