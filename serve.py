"""
Flask webapp for browsing rent-tracker listings.
Run: python serve.py
"""

import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

DB_PATH = Path(__file__).parent / "data" / "listings.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/listings")
def api_listings():
    if not DB_PATH.exists():
        return jsonify([])
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                id, url, platform, title, address, postcode, area,
                bedrooms, bathrooms, sqm,
                rent_pcm, bills_included, deposit,
                available_date, min_tenancy_months,
                listed_date, days_on_market,
                image_url, photos_json,
                commute_work_mins, commute_lse_mins, tfl_failed,
                area_median_pcm, price_vs_median_pct,
                status, notes, created_at,
                lat, lon, neighbourhood
            FROM listings
            ORDER BY id DESC
        """).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.post("/api/listing/<int:listing_id>/status")
def api_set_status(listing_id):
    data = request.get_json(force=True)
    status = data.get("status", "")
    if status not in ("new", "favourite", "dismissed"):
        abort(400, "invalid status")
    if not DB_PATH.exists():
        abort(404)
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE listings SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, listing_id),
        )
        if cur.rowcount == 0:
            abort(404)
        conn.commit()
    return jsonify({"ok": True})


@app.post("/api/listing/<int:listing_id>/notes")
def api_set_notes(listing_id):
    data = request.get_json(force=True)
    notes = data.get("notes", "")
    if not DB_PATH.exists():
        abort(404)
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE listings SET notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (notes, listing_id),
        )
        if cur.rowcount == 0:
            abort(404)
        conn.commit()
    return jsonify({"ok": True})


_BOROUGH_GEOJSON: dict | None = None


@app.get("/api/neighbourhood-borders")
def api_neighbourhood_borders():
    global _BOROUGH_GEOJSON
    if _BOROUGH_GEOJSON is None:
        geojson_path = Path(__file__).parent / "data" / "london_boroughs.geojson"
        if geojson_path.exists():
            import json as _json
            with open(geojson_path, encoding="utf-8") as f:
                _BOROUGH_GEOJSON = _json.load(f)
        else:
            _BOROUGH_GEOJSON = {"type": "FeatureCollection", "features": []}
    return jsonify(_BOROUGH_GEOJSON)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
