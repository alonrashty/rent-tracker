"""
ingest.py — parse Apify JSON (stdin), filter, dedup by URL, insert into SQLite.

Usage:
    python src/collect.py | python src/ingest.py --area Angel
    python src/ingest.py --area Angel < listings.json
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

import db
from config import load

_cfg = load()
_AVAILABLE_FROM = date.fromisoformat(_cfg["AVAILABLE_FROM"])  # 2026-08-15
_AVAILABLE_TO   = date.fromisoformat(_cfg["AVAILABLE_TO"])    # 2026-10-15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENERIC_PLACE  = re.compile(r'^(london|uk)$', re.IGNORECASE)
_POSTCODE_START = re.compile(r'^[A-Z]{1,2}\d', re.IGNORECASE)
_LONDON_PC      = re.compile(r'^london\s+[A-Z]{1,2}\d', re.IGNORECASE)
_TRAILING_PC    = re.compile(r'\s+[A-Z]{1,2}\d[A-Z\d]*$', re.IGNORECASE)
_STREET_WORD    = re.compile(
    r'\b(street|road|avenue|lane|way|place|square|gardens|garden|court|close|'
    r'drive|grove|terrace|mews|row|walk|yard|gate|hill|rise|crescent|circus|'
    r'broadway|passage|alley|wharf|quay|mansions|house|apartments|building|'
    r'tower|works|studios?|quarter|southside|north|south|east|west)\b',
    re.IGNORECASE,
)


def _extract_neighbourhood(address: str) -> str | None:
    """Return the neighbourhood component from a comma-separated address string.

    Skips generic terms ('London'), postcodes, 'London N1'-style values,
    and components that are street names or building names.
    """
    if not address:
        return None
    parts = [p.strip().strip('\n') for p in address.split(',')]
    for part in parts[1:]:
        if not part:
            continue
        if _GENERIC_PLACE.match(part):
            continue
        if _POSTCODE_START.match(part):
            continue
        if _LONDON_PC.match(part):
            continue
        # Strip trailing postcode (e.g. "Clerkenwell EC1M" → "Clerkenwell")
        part = _TRAILING_PC.sub('', part).strip()
        if not part:
            continue
        if _GENERIC_PLACE.match(part):
            continue
        if _STREET_WORD.search(part):
            continue
        return part
    return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def _parse_date_iso(s: str | None) -> str | None:
    """Parse an ISO-8601 timestamp or date string → 'YYYY-MM-DD', or None."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def _parse_int_from_text(s: str | None) -> int | None:
    """Extract the first integer from a string like '469 sq ft' or '£2,596'."""
    if not s or s.strip().lower() in ("ask agent", ""):
        return None
    digits = re.sub(r"[,£\s]", "", s)
    m = re.search(r"\d+", digits)
    return int(m.group()) if m else None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_rightmove(item: dict, area: str) -> dict | None:
    """
    Map a single memo23/rightmove-scraper item to our DB schema.
    Returns None if the listing should be skipped.
    """
    url = item.get("propertyUrl", "").strip()
    if not url:
        return None

    # --- whole-flat filter ---
    prop_type = item.get("propertyDisplayType", "").lower()
    if "room" in prop_type or "share" in prop_type:
        return None
    description = _strip_html(item.get("fullDescription", "")).lower()
    if "shared" in description:
        return None

    # --- furnishing filter ---
    lets = item.get("lettingsInfo") or {}
    furnish = lets.get("furnishDisplayType", "")
    if furnish == "Unfurnished":
        return None

    # --- rent ---
    basic = item.get("basicInfo") or {}
    price = basic.get("price") or {}
    rent_pcm = price.get("amount")
    if not rent_pcm:
        return None
    if price.get("frequency") == "weekly":
        rent_pcm = round(rent_pcm * 52 / 12)

    # --- available date ---
    available_date = _parse_date_iso(basic.get("letAvailableDate"))

    # --- availability filter ---
    if available_date:
        ad = date.fromisoformat(available_date)
        if not (_AVAILABLE_FROM <= ad <= _AVAILABLE_TO):
            return None
    # listings with no available_date are kept (flagged as unknown)

    # --- listed date + days on market ---
    listing_update = basic.get("listingUpdate") or {}
    listed_date = _parse_date_iso(listing_update.get("listingUpdateDate"))
    days_on_market = (date.today() - date.fromisoformat(listed_date)).days if listed_date else None

    # --- sqft ---
    size = item.get("size") or {}
    sqft = _parse_int_from_text(size.get("primary"))

    # --- deposit ---
    deposit_str = lets.get("deposit", "")
    deposit = _parse_int_from_text(deposit_str) if deposit_str != "Ask agent" else None

    # --- min tenancy months ---
    tenancy_str = lets.get("minTenancyLength", "")
    min_tenancy = _parse_int_from_text(tenancy_str) if tenancy_str != "Ask agent" else None

    # --- coordinates ---
    loc = item.get("location") or {}
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    location_accuracy = loc.get("pinType")

    # --- images ---
    photos = item.get("photos") or []
    photo_urls = [p["url"] for p in photos if p.get("url")]
    image_url = photo_urls[0] if photo_urls else ""

    return {
        "url":                 url,
        "platform":            "rightmove",
        "external_id":         str(item.get("identifier", "")),
        "title":               item.get("propertyPhrase", ""),
        "address":             item.get("address", ""),
        "postcode":            item.get("postcode", ""),
        "area":                area,
        "bedrooms":            item.get("bedrooms"),
        "bathrooms":           item.get("bathrooms"),
        "property_type":       item.get("propertyDisplayType", ""),
        "sqft":                sqft,
        "sqm":                 round(sqft * 0.0929, 1) if sqft else None,
        "rent_pcm":            int(rent_pcm),
        "bills_included":      False,
        "deposit":             deposit,
        "available_date":      available_date,
        "min_tenancy_months":  min_tenancy,
        "listed_date":         listed_date,
        "last_seen_date":      date.today().isoformat(),
        "days_on_market":      days_on_market,
        "agent_name":          (item.get("branch") or {}).get("displayName", ""),
        "agent_phone":         item.get("telephoneNumber", ""),
        "image_url":           image_url,
        "photos_json":         json.dumps(photo_urls) if photo_urls else None,
        "listing_description": _strip_html(item.get("fullDescription", "")),
        "lat":                 lat,
        "lon":                 lon,
        "location_accuracy":   location_accuracy,
        "neighbourhood":       _extract_neighbourhood(item.get("address", "")),
    }


def _parse_zoopla_date(s: str | None) -> str | None:
    """Parse Zoopla availableFrom strings like '15th August 2026' → 'YYYY-MM-DD', or None."""
    if not s or s.strip().lower() in ("immediately", ""):
        return None
    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s.strip())
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            pass
    return _parse_date_iso(s)


def parse_zoopla(item: dict, area: str) -> dict | None:
    """
    Map a single shahidirfan/zoopla-scraper item to our DB schema.
    Returns None if the listing should be skipped.
    """
    url = (item.get("url") or item.get("detailUrl") or "").strip()
    if not url:
        return None

    # --- whole-flat filter ---
    prop_type = (item.get("propertyType") or "").lower()
    if "room" in prop_type or "share" in prop_type:
        return None
    description = (item.get("summaryDescription") or "").lower()
    if "shared" in description:
        return None

    # priceValue is unreliable (actor bug: sometimes stores weekly amount even for pcm listings).
    # Parse rent from the price string ("£1,700 pcm" or "£400 pw") which is always correct.
    price_str = item.get("price", "")
    price_num = _parse_int_from_text(price_str)
    if not price_num:
        return None
    if "pw" in price_str.lower():
        rent_pcm = round(price_num * 52 / 12)
    else:
        rent_pcm = price_num

    # --- available date ---
    available_date = _parse_zoopla_date(item.get("availableFrom"))

    # --- availability filter ---
    if available_date:
        ad = date.fromisoformat(available_date)
        if not (_AVAILABLE_FROM <= ad <= _AVAILABLE_TO):
            return None

    # --- listed date + days on market ---
    listed_date = _parse_date_iso(item.get("lastPublishedDate") or item.get("scrapedAt"))
    days_on_market = (date.today() - date.fromisoformat(listed_date)).days if listed_date else None

    branch = item.get("branch") or {}

    # --- images ---
    zo_images = item.get("gallery") or item.get("images") or item.get("imageUrls") or []
    if zo_images and isinstance(zo_images, list):
        zo_photo_urls = [img if isinstance(img, str) else (img.get("url") or img.get("src") or "") for img in zo_images]
        zo_photo_urls = [u for u in zo_photo_urls if u]
    else:
        zo_photo_urls = []
    single_img = item.get("image") or item.get("featuredImageUrl", "")
    if not zo_photo_urls and single_img:
        zo_photo_urls = [single_img]

    return {
        "url":                 url,
        "platform":            "zoopla",
        "external_id":         str(item.get("listingId", "")),
        "title":               item.get("title", ""),
        "address":             item.get("address", ""),
        "postcode":            item.get("postalCode", ""),
        "area":                area,
        "bedrooms":            item.get("beds"),
        "bathrooms":           item.get("baths"),
        "property_type":       item.get("propertyType", ""),
        "sqft":                None,
        "sqm":                 None,
        "rent_pcm":            int(rent_pcm),
        "bills_included":      False,
        "deposit":             None,
        "available_date":      available_date,
        "min_tenancy_months":  None,
        "listed_date":         listed_date,
        "last_seen_date":      date.today().isoformat(),
        "days_on_market":      days_on_market,
        "agent_name":          branch.get("name", ""),
        "agent_phone":         branch.get("phone", ""),
        "image_url":           zo_photo_urls[0] if zo_photo_urls else "",
        "photos_json":         json.dumps(zo_photo_urls) if zo_photo_urls else None,
        "listing_description": item.get("summaryDescription", ""),
        "lat":                 None,
        "lon":                 None,
        "location_accuracy":   None,
        "neighbourhood":       _extract_neighbourhood(item.get("address", "")),
    }


# ---------------------------------------------------------------------------
# Insertion
# ---------------------------------------------------------------------------

_INSERT_SQL = """
INSERT INTO listings (
    url, platform, external_id, title, address, postcode, area,
    bedrooms, bathrooms, property_type, sqft, sqm,
    rent_pcm, bills_included, deposit,
    available_date, min_tenancy_months,
    listed_date, last_seen_date, days_on_market,
    agent_name, agent_phone, image_url, photos_json, listing_description,
    lat, lon, location_accuracy, neighbourhood
) VALUES (
    :url, :platform, :external_id, :title, :address, :postcode, :area,
    :bedrooms, :bathrooms, :property_type, :sqft, :sqm,
    :rent_pcm, :bills_included, :deposit,
    :available_date, :min_tenancy_months,
    :listed_date, :last_seen_date, :days_on_market,
    :agent_name, :agent_phone, :image_url, :photos_json, :listing_description,
    :lat, :lon, :location_accuracy, :neighbourhood
)
ON CONFLICT(url) DO UPDATE SET
    last_seen_date    = excluded.last_seen_date,
    days_on_market    = excluded.days_on_market,
    photos_json       = COALESCE(excluded.photos_json, photos_json),
    lat               = COALESCE(excluded.lat, lat),
    lon               = COALESCE(excluded.lon, lon),
    location_accuracy = COALESCE(excluded.location_accuracy, location_accuracy),
    neighbourhood     = COALESCE(excluded.neighbourhood, neighbourhood),
    updated_at        = CURRENT_TIMESTAMP
"""


_PARSERS = {
    "rightmove": parse_rightmove,
    "zoopla":    parse_zoopla,
}


def ingest(items: list[dict], area: str, platform: str = "rightmove") -> tuple[int, int, int, int]:
    """Parse, filter, insert/update. Returns (parsed, inserted, updated, filtered)."""
    parser = _PARSERS.get(platform, parse_rightmove)
    conn = db.connect()

    parsed = filtered = 0
    rows_before = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]

    with conn:
        for item in items:
            row = parser(item, area)
            parsed += 1
            if row is None:
                filtered += 1
                continue
            conn.execute(_INSERT_SQL, row)

    rows_after = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
    conn.close()

    inserted = rows_after - rows_before
    updated = (parsed - filtered) - inserted
    return parsed, inserted, updated, filtered


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Apify JSON into listings DB")
    ap.add_argument("--area", help="Area label — required when input is a flat item list")
    args = ap.parse_args()

    print("[ingest] reading JSON from stdin …", file=sys.stderr)
    data = json.load(sys.stdin)

    # Detect format: wrapped [{"area":..., "platform":..., "items":[...]}, ...] vs flat list
    is_wrapped = isinstance(data, list) and data and isinstance(data[0], dict) and "items" in data[0]
    if is_wrapped:
        batches = data
    else:
        if not args.area:
            sys.exit("ERROR: --area required when input is a flat listing list")
        batches = [{"area": args.area, "platform": "rightmove", "items": data}]

    db.init()
    totals = {"parsed": 0, "inserted": 0, "updated": 0, "filtered": 0}

    for batch in batches:
        area     = batch["area"]
        platform = batch.get("platform", "rightmove")
        items    = batch["items"]
        print(f"[ingest] {platform} / {area}: {len(items)} item(s)", file=sys.stderr)
        parsed, inserted, updated, filtered = ingest(items, area, platform)
        totals["parsed"]   += parsed
        totals["inserted"] += inserted
        totals["updated"]  += updated
        totals["filtered"] += filtered
        print(f"[ingest]   parsed={parsed}  inserted={inserted}  updated={updated}  filtered={filtered}", file=sys.stderr)

    print(
        f"[ingest] TOTAL  parsed={totals['parsed']}  inserted={totals['inserted']}"
        f"  updated={totals['updated']}  filtered={totals['filtered']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
