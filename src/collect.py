"""
collect.py — fetch rental listings from Apify actors (Rightmove + Zoopla).

Outputs a JSON array of {"area": str, "platform": str, "items": [...]} objects,
one per search URL, to stdout. Pipe into ingest.py.

Usage:
    python src/collect.py                    # all areas, all platforms
    python src/collect.py --platform rm      # Rightmove only
    python src/collect.py --platform zoopla  # Zoopla only
    python src/collect.py --first            # first URL per platform (debug)
"""

import argparse
import json
import sys
import time

import requests

# Windows cp1252 can't encode emoji/Unicode in listing data
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from config import load, get_urls

APIFY_BASE = "https://api.apify.com/v2"
RM_TIMEOUT_SECS   = 300   # Rightmove actor: sync run timeout
ZOOPLA_POLL_SECS  = 15    # Zoopla actor: polling interval
ZOOPLA_MAX_POLLS  = 60    # Zoopla actor: give up after 60 × 15s = 15 min


def _actor_id(slug: str) -> str:
    return slug.replace("/", "~")


def run_actor_sync(token: str, slug: str, input_data: dict) -> list[dict]:
    """Run an actor synchronously (Rightmove). Blocks until done."""
    url = f"{APIFY_BASE}/acts/{_actor_id(slug)}/run-sync-get-dataset-items"
    params = {"token": token, "timeout": RM_TIMEOUT_SECS, "memory": 1024}
    resp = requests.post(url, params=params, json=input_data, timeout=RM_TIMEOUT_SECS + 30)
    resp.raise_for_status()
    return resp.json()


def _poll_run(token: str, run_id: str, dataset_id: str) -> list[dict]:
    """Poll an Apify run until done, then return its dataset items."""
    for _ in range(ZOOPLA_MAX_POLLS):
        time.sleep(ZOOPLA_POLL_SECS)
        status = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}", params={"token": token}
        ).json()["data"]["status"]
        if status == "SUCCEEDED":
            items = requests.get(
                f"{APIFY_BASE}/datasets/{dataset_id}/items",
                params={"token": token, "limit": 500},
            ).json()
            return items if isinstance(items, list) else []
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"run {run_id} ended with status={status}")
    raise RuntimeError(f"run {run_id} still running after {ZOOPLA_MAX_POLLS} polls")


def run_actor_async(token: str, slug: str, input_data: dict, memory: int = 1024, retries: int = 1) -> list[dict]:
    """Start an actor run, poll until done, return dataset items. Retries on TIMED-OUT."""
    for attempt in range(retries + 1):
        start = requests.post(
            f"{APIFY_BASE}/acts/{_actor_id(slug)}/runs",
            params={"token": token, "memory": memory},
            json=input_data, timeout=30,
        )
        start.raise_for_status()
        data = start.json()["data"]
        try:
            return _poll_run(token, data["id"], data["defaultDatasetId"])
        except RuntimeError as e:
            if attempt < retries and "TIMED-OUT" in str(e):
                print(f"[collect]   run timed out, retrying ({attempt+1}/{retries}) …", file=sys.stderr)
                continue
            raise


def collect_rightmove(token: str, slug: str, urls: list[str], areas: list[str]) -> list[dict]:
    results = []
    for url, area in zip(urls, areas):
        print(f"[collect] rightmove / {area} …", file=sys.stderr)
        try:
            items = run_actor_sync(token, slug, {"startUrls": [{"url": url}]})
            print(f"[collect]   {len(items)} item(s)", file=sys.stderr)
            results.append({"area": area, "platform": "rightmove", "items": items})
        except Exception as e:
            print(f"[collect]   ERROR: {e}", file=sys.stderr)
    return results


def collect_zoopla(token: str, slug: str, urls: list[str], areas: list[str]) -> list[dict]:
    """shahidirfan/zoopla-scraper: async, single startUrl, residential proxy."""
    results = []
    for url, area in zip(urls, areas):
        if not url.strip():
            continue
        print(f"[collect] zoopla / {area} …", file=sys.stderr)
        try:
            items = run_actor_async(
                token, slug,
                {"startUrl": url, "results_wanted": 200,
                 "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]}},
            )
            print(f"[collect]   {len(items)} item(s)", file=sys.stderr)
            results.append({"area": area, "platform": "zoopla", "items": items})
        except Exception as e:
            print(f"[collect]   ERROR: {e}", file=sys.stderr)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", action="store_true", help="first URL per platform only (debug)")
    ap.add_argument("--platform", choices=["rm", "zoopla", "all"], default="all")
    args = ap.parse_args()

    cfg = load()
    token = cfg.get("APIFY_API_TOKEN", "").strip()
    if not token:
        sys.exit("ERROR: APIFY_API_TOKEN not set in config.md")

    results = []

    # --- Rightmove ---
    if args.platform in ("rm", "all"):
        rm_slug  = cfg.get("APIFY_RIGHTMOVE_ACTOR", "").strip()
        rm_urls  = get_urls(cfg, "RIGHTMOVE_URL")
        rm_areas = get_urls(cfg, "RIGHTMOVE_AREA")
        if rm_slug and rm_urls:
            if args.first:
                rm_urls, rm_areas = rm_urls[:1], rm_areas[:1]
            results += collect_rightmove(token, rm_slug, rm_urls, rm_areas)

    # --- Zoopla ---
    if args.platform in ("zoopla", "all"):
        zo_slug  = cfg.get("APIFY_ZOOPLA_ACTOR", "").strip()
        zo_urls  = get_urls(cfg, "ZOOPLA_URL")
        zo_areas = get_urls(cfg, "ZOOPLA_AREA")
        if zo_slug and zo_urls:
            if args.first:
                zo_urls, zo_areas = zo_urls[:1], zo_areas[:1]
            results += collect_zoopla(token, zo_slug, zo_urls, zo_areas)

    total = sum(len(r["items"]) for r in results)
    print(f"[collect] total: {total} item(s) across {len(results)} batch(es)", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
