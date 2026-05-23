"""
TfL Journey Planner enrichment.
Queries unenriched listings from the DB, calls TfL for both commute destinations,
and writes commute_work_mins / commute_lse_mins back to the DB.

Postcode resolution: full postcodes and bare outward codes are both resolved to
lat,lon via postcodes.io before being passed to TfL, which handles ambiguous
outward codes (e.g. Zoopla returns "N1" rather than "N1 0RA").
"""

import sys
import time
import urllib.parse
from datetime import datetime, timezone

import requests

import config
import db

TFL_BASE          = "https://api.tfl.gov.uk/Journey/JourneyResults"
POSTCODES_BASE    = "https://api.postcodes.io"
NOMINATIM_SEARCH  = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
TFL_DATE       = "20260901"  # fixed Tuesday for consistency
TFL_TIME       = "0900"

DEST_WORK = "EC1V 9NR"
DEST_LSE  = "WC2A 2AE"

SLEEP_BETWEEN = 1.5   # seconds between TfL requests
TIMEOUT_SECS  = 20


def _tfl_params(cfg: dict) -> dict:
    params = {
        "mode": "tube,bus,walking,overground,elizabeth-line,dlr",
        "time": TFL_TIME,
        "timeIs": "Arriving",
        "date": TFL_DATE,
    }
    app_id  = cfg.get("TFL_APP_ID", "").strip()
    app_key = cfg.get("TFL_APP_KEY", "").strip()
    if app_id and not app_id.startswith("optional"):
        params["app_id"] = app_id
    if app_key and not app_key.startswith("optional"):
        params["app_key"] = app_key
    return params


def _resolve_latlon(postcode: str) -> str | None:
    """
    Resolve a full postcode or bare outward code to "lat,lon" via postcodes.io.
    Returns None if resolution fails.
    """
    pc = postcode.strip().upper()

    # Try full postcode first
    try:
        r = requests.get(
            f"{POSTCODES_BASE}/postcodes/{urllib.parse.quote(pc)}",
            timeout=10,
        )
        if r.status_code == 200:
            result = r.json().get("result") or {}
            lat, lon = result.get("latitude"), result.get("longitude")
            if lat and lon:
                return f"{lat},{lon}"
    except requests.RequestException:
        pass

    # Fall back to outward code (first word)
    outcode = pc.split()[0]
    try:
        r = requests.get(
            f"{POSTCODES_BASE}/outcodes/{urllib.parse.quote(outcode)}",
            timeout=10,
        )
        if r.status_code == 200:
            result = r.json().get("result") or {}
            lat, lon = result.get("latitude"), result.get("longitude")
            if lat and lon:
                return f"{lat},{lon}"
    except requests.RequestException:
        pass

    return None


def _resolve_latlon_from_address(address: str) -> str | None:
    """Geocode a street address via Nominatim. Returns 'lat,lon' or None."""
    if not address or not address.strip():
        return None
    try:
        r = requests.get(
            NOMINATIM_SEARCH,
            params={"q": address + ", London, UK", "format": "json", "limit": 1},
            headers={"User-Agent": "rent-tracker/1.0 (alon.rashty@gmail.com)"},
            timeout=10,
        )
        if r.status_code == 200:
            results = r.json()
            if results:
                return f'{results[0]["lat"]},{results[0]["lon"]}'
    except requests.RequestException:
        pass
    return None


def _reverse_geocode_neighbourhood(lat: float, lon: float) -> str | None:
    """Reverse geocode lat/lon via Nominatim. Returns suburb/neighbourhood name or None."""
    try:
        r = requests.get(
            NOMINATIM_REVERSE,
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 14},
            headers={"User-Agent": "rent-tracker/1.0 (alon.rashty@gmail.com)"},
            timeout=10,
        )
        if r.status_code == 200:
            addr = r.json().get("address", {})
            return addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district")
    except requests.RequestException:
        pass
    return None


def _journey_minutes(from_loc: str, destination: str, params: dict) -> int:
    """Return duration in minutes for fastest journey. Raises on failure."""
    frm = urllib.parse.quote(from_loc, safe="")
    to  = urllib.parse.quote(destination, safe="")
    url = f"{TFL_BASE}/{frm}/to/{to}"

    for attempt in (1, 2):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT_SECS)
            r.raise_for_status()
            data = r.json()
            journeys = data.get("journeys", [])
            if not journeys:
                raise ValueError(f"TfL returned no journeys ({from_loc} → {destination})")
            return journeys[0]["duration"]
        except requests.Timeout:
            if attempt == 1:
                print("    [enrich] timeout, retrying…", file=sys.stderr)
                time.sleep(3)
                continue
            raise
    raise RuntimeError("unreachable")


def enrich_all(cfg: dict) -> None:
    params = _tfl_params(cfg)
    conn = db.connect()

    rows = conn.execute("""
        SELECT id, postcode, address, area, lat, lon
        FROM listings
        WHERE tfl_failed = FALSE
          AND commute_work_mins IS NULL
        ORDER BY id
    """).fetchall()

    total = len(rows)
    if total == 0:
        print("[enrich] nothing to enrich", file=sys.stderr)
        conn.close()
        return

    print(f"[enrich] enriching {total} listings", file=sys.stderr)

    ok = failed = 0
    for i, row in enumerate(rows, 1):
        listing_id = row["id"]
        postcode   = (row["postcode"] or "").strip()
        address    = (row["address"] or "").strip()
        label      = f'{row["area"]} — {postcode or address or "(unknown)"}'

        # Resolve location: stored lat/lon → postcode → postcodes.io → Nominatim
        from_loc = None
        resolved = None
        if row["lat"] and row["lon"]:
            from_loc = f'{row["lat"]},{row["lon"]}'
            resolved = "exact"
        elif postcode:
            from_loc = _resolve_latlon(postcode)
            resolved = "coord"
        if not from_loc and address:
            time.sleep(1.0)  # Nominatim: 1 req/sec
            from_loc = _resolve_latlon_from_address(address)
            resolved = "nominatim"
        if not from_loc:
            _mark_failed(conn, listing_id, "could not resolve location")
            failed += 1
            print(f"  [{i}/{total}] SKIP {label} — no location", file=sys.stderr)
            continue

        print(f"  [{i}/{total}] {label} ({resolved})", file=sys.stderr, end="  ")

        try:
            work_mins = _journey_minutes(from_loc, DEST_WORK, params)
            time.sleep(SLEEP_BETWEEN)
            lse_mins  = _journey_minutes(from_loc, DEST_LSE, params)
            time.sleep(SLEEP_BETWEEN)

            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute("""
                    UPDATE listings
                    SET commute_work_mins = ?,
                        commute_lse_mins  = ?,
                        tfl_enriched_at   = ?,
                        updated_at        = ?
                    WHERE id = ?
                """, (work_mins, lse_mins, now, now, listing_id))

            ok += 1
            print(f"work {work_mins}m  LSE {lse_mins}m", file=sys.stderr)

        except Exception as exc:
            msg = str(exc)[:200]
            _mark_failed(conn, listing_id, msg)
            failed += 1
            print(f"FAILED — {msg}", file=sys.stderr)

    conn.close()
    print(f"[enrich] done — {ok} enriched, {failed} failed", file=sys.stderr)


def enrich_neighbourhoods() -> None:
    """Fill neighbourhood for listings where address parsing returned NULL.

    Resolution chain:
      - Rightmove (lat/lon stored): Nominatim reverse geocode directly
      - Zoopla (postcode only): postcodes.io → lat/lon → Nominatim reverse
      - Neither resolves: leave NULL (area search bucket is the fallback in the app)
    """
    conn = db.connect()
    rows = conn.execute("""
        SELECT id, lat, lon, postcode, address, area
        FROM listings
        WHERE neighbourhood IS NULL
        ORDER BY id
    """).fetchall()

    total = len(rows)
    if total == 0:
        print("[enrich] neighbourhoods: nothing to fill", file=sys.stderr)
        conn.close()
        return

    print(f"[enrich] filling neighbourhood for {total} listing(s)", file=sys.stderr)
    ok = skipped = 0

    for row in rows:
        lat, lon = row["lat"], row["lon"]

        # Resolve coordinates if not already stored (Zoopla path)
        if not (lat and lon):
            postcode = (row["postcode"] or "").strip()
            latlon = _resolve_latlon(postcode) if postcode else None
            if latlon:
                lat_s, lon_s = latlon.split(",")
                lat, lon = float(lat_s), float(lon_s)

        if not (lat and lon):
            skipped += 1
            continue

        time.sleep(1.0)  # Nominatim: 1 req/sec
        name = _reverse_geocode_neighbourhood(lat, lon)
        if name:
            with conn:
                conn.execute(
                    "UPDATE listings SET neighbourhood = ?, updated_at = ? WHERE id = ?",
                    (name, datetime.now(timezone.utc).isoformat(), row["id"]),
                )
            ok += 1
        else:
            skipped += 1

    conn.close()
    print(f"[enrich] neighbourhoods: {ok} filled, {skipped} unresolvable", file=sys.stderr)


def _mark_failed(conn, listing_id: int, msg: str) -> None:
    with conn:
        conn.execute("""
            UPDATE listings
            SET tfl_failed = TRUE,
                tfl_error  = ?,
                updated_at = ?
            WHERE id = ?
        """, (msg, datetime.now(timezone.utc).isoformat(), listing_id))


if __name__ == "__main__":
    cfg = config.load()
    enrich_all(cfg)
    enrich_neighbourhoods()
