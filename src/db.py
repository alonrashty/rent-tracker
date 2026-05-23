"""
Database initialisation and connection helper.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "listings.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT UNIQUE NOT NULL,
    platform            TEXT NOT NULL,
    external_id         TEXT,

    title               TEXT,
    address             TEXT,
    postcode            TEXT,
    area                TEXT,
    bedrooms            INTEGER,
    bathrooms           INTEGER,
    property_type       TEXT,
    sqft                INTEGER,
    sqm                 REAL,

    rent_pcm            INTEGER NOT NULL,
    bills_included      BOOLEAN DEFAULT FALSE,
    deposit             INTEGER,

    available_date      DATE,
    min_tenancy_months  INTEGER,

    listed_date         DATE,
    last_seen_date      DATE,
    days_on_market      INTEGER,
    agent_name          TEXT,
    agent_phone         TEXT,

    image_url           TEXT,
    photos_json         TEXT,
    listing_description TEXT,

    lat                 REAL,
    lon                 REAL,
    location_accuracy   TEXT,                        -- 'ACCURATE_POINT' | 'APPROXIMATE_POINT' (Rightmove only)
    neighbourhood       TEXT,                        -- parsed from address (e.g. 'Islington', 'Kings Cross')

    commute_work_mins   INTEGER,
    commute_lse_mins    INTEGER,
    tfl_enriched_at     TIMESTAMP,
    tfl_failed          BOOLEAN DEFAULT FALSE,
    tfl_error           TEXT,

    area_median_pcm     INTEGER,
    price_vs_median_pct REAL,

    status              TEXT DEFAULT 'new',
    notes               TEXT,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_url         ON listings(url);
CREATE INDEX IF NOT EXISTS idx_area        ON listings(area);
CREATE INDEX IF NOT EXISTS idx_area_beds   ON listings(area, bedrooms);
CREATE INDEX IF NOT EXISTS idx_status      ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listed_date ON listings(listed_date);
CREATE INDEX IF NOT EXISTS idx_rent_pcm    ON listings(rent_pcm);
CREATE INDEX IF NOT EXISTS idx_commute     ON listings(commute_work_mins);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
    if "photos_json" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN photos_json TEXT")
    if "lat" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN lat REAL")
        conn.execute("ALTER TABLE listings ADD COLUMN lon REAL")
        conn.execute("ALTER TABLE listings ADD COLUMN location_accuracy TEXT")
    if "neighbourhood" not in cols:
        conn.execute("ALTER TABLE listings ADD COLUMN neighbourhood TEXT")


def init(path: Path = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)
    print(f"DB ready: {path}")
