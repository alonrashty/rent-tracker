# Discoveries

Running log of non-obvious findings, API quirks, and decisions made during development.
The goal is to save future sessions from re-learning things the hard way.
Entries are grouped by session date. Each entry covers: what was tried, what was found, and what was decided and why.

---

## 2026-05-16 — Session 1: Setup & Rightmove URL Discovery

### Rightmove location identifiers can't be guessed — use the typeahead API

**Tried:** Constructing `locationIdentifier` values by guessing patterns from known URLs (e.g. `REGION%5E93917`).  
**Found:** The IDs are opaque integers with no pattern. Guessed IDs pointed to wrong or nonexistent areas.  
**Decided:** Resolve all location IDs via Rightmove's internal typeahead API:
```
GET https://los.rightmove.co.uk/typeahead?query={query}&limit=10&exclude=STREET
Referer: https://www.rightmove.co.uk/
```
Returns `{"matches": [{"id": "87500", "type": "REGION", "displayName": "Clerkenwell, Central London"}, ...]}`.
locationIdentifier format: `{TYPE}%5E{id}` — e.g. `REGION%5E87500`.
No auth or cookies required; works directly from `requests`. Short queries work best — "Clerkenwell" not "Clerkenwell, London".

---

### Angel and Farringdon have no REGION identifier — use STATION type instead

**Tried:** Querying "Angel" and "Farringdon" for a London REGION match.  
**Found:** "Angel" returns Angel Station (STATION) as the only London result — remaining REGION results are Anglesey and East Anglia. "Farringdon" returns Farringdon Station (STATION) and multiple Hampshire/Devon villages as REGIONs; no London REGION exists.  
**Decided:** Use `STATION%5E245` for Angel and `STATION%5E3431` for Farringdon. Station-based search uses a radius around the station, which is an accurate proxy for these neighbourhoods. Investigated using N1 outcode for Angel but it covers too broad an area (all of Islington).  
**Note:** For the five areas that do have a named REGION (Clerkenwell, Hoxton, Shoreditch, Barbican, Bethnal Green), prefer REGION over STATION — REGION boundaries are tighter and don't overlap with adjacent areas the way a station radius can.

---

### Playwright cannot interact with Rightmove until the OneTrust cookie banner is dismissed

**Tried:** Clicking the search input directly after page load.  
**Found:** The OneTrust consent overlay (`#onetrust-consent-sdk`) intercepts all pointer events, causing `Locator.click` to time out even though the target element is visible. The banner requires two steps: click "Manage Settings", then click "Reject All" (the top-level "Reject All" button is not always present on first load).  
**Decided:** Always call a `dismiss_cookies()` helper immediately after `page.goto()` for any Rightmove page. Selector: try `#onetrust-reject-all-handler` first; fall back to `Manage Settings` → `.ot-pc-refuse-all-handler`. JS removal (`element.remove()`) works as a last resort but may affect subsequent page behaviour.

---

### Zoopla actor: shahidirfan/zoopla-scraper with residential proxies is the only working option

**Tried:** `tri_angle/fast-zoopla-properties-scraper` (most runs, 4.8★) — startUrls returns 0 results immediately; locationQueries times out at 345s. `getdataforme/zoopla-search-location-rent-scraper` — runs 120s and returns 0 items.  
**Found:** Zoopla blocks scrapers without residential proxies. `shahidirfan/zoopla-scraper` works because it defaults to `apifyProxyGroups: ["RESIDENTIAL"]`. Returns 25 items for Angel in ~60–90s.  
**Decided:** Use `shahidirfan/zoopla-scraper` with async polling (not run-sync). Added 1 retry on TIMED-OUT (transient proxy availability). Input: single `startUrl` string (not array), `results_wanted`, `proxyConfiguration`.  
**Note:** Actor intermittently times out (~1 in 3 runs). The retry handles it. If both attempts fail, the area is skipped with an error log.

---

### Zoopla has no slug for Farringdon; Shoreditch uses EC2A postcode

**Found:** `zoopla.co.uk/to-rent/flats/farringdon/` returns 0 results — no residential area with that name on Zoopla. `zoopla.co.uk/to-rent/flats/shoreditch/` also returns 0.  
**Decided:** Farringdon left blank in config (covered by Clerkenwell's search). Shoreditch uses `ec2a` (postcode slug), which returns 3 exact + 22 close matches and captures Shoreditch listings reliably.

---

### Zoopla actor (shahidirfan) returns "close match" listings that bypass URL filters

**Found:** A search URL with `furnished_state=furnished&price_max=2500` returns 7 exact matches and 18 "close matches." The close matches don't honour all filters — some are unfurnished or priced as weekly. 25 total items returned.  
**Decided:** Acceptable for now; these will surface in the webapp for manual review. Could add a stricter filter in ingest if noise becomes a problem.

---

### shahidirfan/zoopla-scraper has a priceValue bug — use price string instead

**Found:** `priceValue` (and `priceUnformatted`) is unreliable: for some listings it stores the weekly amount even when `price` says "£2,492 pcm". Example: `priceValue=575`, `price="£2,492 pcm"` (575 × 52/12 ≈ 2,492).  
**Decided:** Parse rent from the `price` string field, not `priceValue`. Extract integer from the string; multiply by 52/12 if "pw" appears in the string. The `price` field is always accurate.

---

### basicInfo.price.frequency must be checked — some listings return weekly amounts

**Found:** `basicInfo.price.amount` is not always monthly. Some listings (furnished, priced near the weekly boundary) return `frequency: "weekly"` with the weekly figure as `amount`. Example: a £2,249/month flat came through as `amount: 519, frequency: "weekly"` (519 × 52 / 12 ≈ 2,249).  
**Decided:** In `parse_rightmove`, multiply by 52/12 when `frequency == "weekly"`. Use `round()` to avoid fractional pence.

---

### The insert counter inflates "updated" due to within-batch and cross-area URL duplicates

**Found:** Using a pre-INSERT EXISTS check to distinguish inserts from updates fails in two cases: (1) the same URL appearing twice in one area's results is counted as insert then update; (2) a URL already inserted by an earlier area is counted as update for subsequent areas. Both are correct DB behaviour, just mis-labelled.  
**Decided:** Count inserts as `rows_after - rows_before` per batch. "Updated" = rows that passed the filter minus newly inserted rows. This is accurate regardless of duplicates.

---

### memo23/rightmove-scraper returns duplicate URLs within a single run

**Found:** A single actor run for one search URL can return the same `propertyUrl` more than once (same listing on multiple result pages). With `ON CONFLICT DO UPDATE`, the second occurrence triggers an update rather than an insert — harmless, but inflates the "updated" counter.  
**Decided:** No dedup needed at the collect stage. The upsert handles it correctly; duplicates within a run are idempotent. Worth being aware of when reading run stats.

---

### memo23/rightmove-scraper is the correct Apify actor for Rightmove

**Tried:** `dtrungtin/rightmove-scraper` (the slug originally in `config.md`).  
**Found:** Actor returns 404 — it no longer exists on Apify.  
**Decided:** Use `memo23/rightmove-scraper` — 1,730 total runs, updated 2026-05-14, $0.00095/result (cheapest available). Searched via `https://api.apify.com/v2/store?search=rightmove&limit=10`.  
**Input format:** `{"startUrls": [{"url": "..."}]}` — the `{url: ...}` object form, not a plain string array. Plain strings return 400.

---

### config.py must strip inline # comments from values

**Tried:** Storing the actor slug with an inline comment: `APIFY_RIGHTMOVE_ACTOR=dtrungtin/rightmove-scraper    # comment`.  
**Found:** The original `_KV_RE` regex captured everything after `=` including the comment, making the actor slug invalid.  
**Decided:** Added inline comment stripping to `config.load()`: split on first ` #` and discard the rest. Applied to all keys, so comments are safe to use anywhere in config code blocks.

---

---

## 2026-05-16 — Session 2: Zoopla expansion + combined collection

### Windows stdout crashes on emoji in Apify data — must reconfigure to UTF-8

**Tried:** Running `python src/collect.py | python src/ingest.py` on Windows without encoding config.  
**Found:** Zoopla listings include emoji characters (e.g. ✓) in descriptions. Python's default stdout on Windows uses cp1252, which crashes with `UnicodeEncodeError` when writing these to the pipe.  
**Decided:** Add `if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")` at the top of `collect.py` and the equivalent `stdin.reconfigure` at the top of `ingest.py`. The `hasattr` guard keeps it safe on non-Windows platforms.

---

### PowerShell does not support `<` stdin redirect or clean stderr separation in pipes

**Tried:** `python src/collect.py | python src/ingest.py` and `python src/ingest.py < file.json` in PowerShell.  
**Found:** (1) PowerShell does not support `<` for stdin redirection — use `Get-Content file | python` instead. (2) `2>&1 |` merges stderr into stdout, which corrupts the JSON being piped between scripts. The `[ingest] reading…` stderr messages land in the JSON stream and cause a parse error.  
**Decided:** Use a temp file to separate the two streams:
```powershell
python src/collect.py > $tmp 2>collect_stderr.txt
Get-Content $tmp -Encoding UTF8 | python src/ingest.py
```
The `/collection-cycle` slash command handles this correctly. Avoid `2>&1 |` for any script that pipes structured data.

---

### Zoopla `run-sync-get-dataset-items` returns 201 with empty body for long-running actors

**Tried:** Using `run-sync-get-dataset-items` (same endpoint as Rightmove) for the Zoopla actor.  
**Found:** The sync endpoint has a hard server-side timeout. `shahidirfan/zoopla-scraper` takes 60–90s per area — the sync call returns HTTP 201 with an empty body before the run completes. Items are never returned.  
**Decided:** Use async start + poll: POST to `/acts/{slug}/runs` to start, then poll `/actor-runs/{run_id}` every 15s until status is `SUCCEEDED` or terminal. Fetch items from `/datasets/{dataset_id}/items` only after `SUCCEEDED`. Rightmove (`memo23/rightmove-scraper`) completes in <30s so sync is fine for it.

---

---

## 2026-05-16 — Session 3: TfL enrichment

### Zoopla actor only returns outward codes — use postcodes.io centroid for TfL

**Found:** `shahidirfan/zoopla-scraper` stores only the outward code (e.g. `N1`, `E2`, `EC1V`) in `postalCode`. Full postcodes are not available anywhere in the actor output (address field also ends with the outward code). TfL Journey Planner returns 0 journeys for outward codes it can't unambiguously resolve to a point.  
**Decided:** Resolve all postcodes to `lat,lon` via `postcodes.io` before passing to TfL. Full postcodes use `/postcodes/{pc}` (precise); bare outward codes fall back to `/outcodes/{outcode}` (district centroid). Both return `latitude`/`longitude`. Pass `"lat,lon"` as the TfL `{from}` parameter. This is free, no key required, and handles both platforms uniformly. Rightmove listings have full postcodes so they get precise coordinates; Zoopla gets the district centroid, which is accurate enough for commute estimates.

---

### Nominatim geocodes addresses when postcode is missing — use as final fallback before tfl_failed

**Found:** One Zoopla listing had no postcode at all but a valid address ("Squirries Street, London E2"). postcodes.io can't help without a postcode; Nominatim (`nominatim.openstreetmap.org/search`) geocodes free-text addresses and returned accurate lat/lon.  
**Decided:** Resolution chain in `enrich.py`: postcodes.io (full postcode) → postcodes.io outcode centroid → Nominatim address geocode → mark `tfl_failed`. Only the last step is a permanent failure. Nominatim requires a `User-Agent` header and a 1 req/sec rate limit — add a 1s sleep before each Nominatim call.

---

### TfL returns 429 when invalid app_id/app_key are sent — check for placeholder values

**Found:** `config.md` template has `TFL_APP_ID=optional_see_tfl_docs`. When this placeholder is sent as a real credential, TfL returns HTTP 429. Anonymous requests (no params at all) work fine at 50 req/min.  
**Decided:** In `_tfl_params()`, skip any credential value that starts with `"optional"`. Only include `app_id`/`app_key` if they look like real registered values.

---

---

## 2026-05-21 — Session 4: New areas + search parameter updates

### Dalston Junction is STATION-only; London Fields has a REGION

**Tried:** Rightmove typeahead API for "Dalston Junction" and "London Fields".  
**Found:** "Dalston Junction" returns a single match: `STATION^15132`. No REGION exists for Dalston on Rightmove. "London Fields" returns `REGION^70417` ("London Fields, East London") as the first match, plus `STATION^5801` ("London Fields Station") as a second match.  
**Decided:** Use `STATION^15132` for Dalston (only option). Use `REGION^70417` for London Fields — consistent with the existing preference for REGION over STATION where both exist (tighter boundary, less cross-area bleed).

---

---

## 2026-05-22 — Session 5: Dashboard UI refactor

### Zoopla stores outward codes only — postcodes.io /outcodes fallback needed in the frontend too

**Found:** `shahidirfan/zoopla-scraper` stores only outward codes ("N16", "E9") in the `postcode` field, not full postcodes. The `postcodes.io` bulk `/postcodes` endpoint requires full postcodes and returns null for district-only codes. 212 out of 230 listings are Zoopla; without the fallback they would all be unmapped.  
**Decided:** Two-stage geocoding in `boot()`: (1) bulk POST to `/postcodes` for full postcodes (catches Rightmove listings); (2) individual GET to `/outcodes/{outcode}` for remaining listings (catches Zoopla). Result: 229/230 geocoded on first load. Cache stored in `l._lat`/`l._lon` on the listing object in memory.

---

### CartoDB Dark Matter tiles require no API key and match the dark UI aesthetic

**Decided:** Using Leaflet.js + CartoDB Dark Matter (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`) for the embedded map. No Mapbox token required, no rate limits for personal use. Tile layer swaps to `light_all` in light mode via `window.matchMedia('prefers-color-scheme: dark')`.

---

### Zoopla slugs for Dalston and London Fields are unverified

**Decided:** Using `/to-rent/flats/dalston/` and `/to-rent/flats/london-fields/` based on Zoopla's standard slug pattern. Neither has been confirmed to return results. Verify on first collection run — if either returns 0 results, try the E8 postcode slug (`/to-rent/flats/e8/`) as a fallback for both areas (they share the E8 postcode district).

---

### skill.md must live in .claude/commands/ to function as a slash command

**Tried:** Placing the collection cycle instructions in `skill.md` at the project root.  
**Found:** Claude Code only picks up custom slash commands from `.claude/commands/`. A file at the root is just a markdown file — it does nothing automatically.  
**Decided:** Moved to `.claude/commands/collection-cycle.md`. Now invocable as `/collection-cycle`.
