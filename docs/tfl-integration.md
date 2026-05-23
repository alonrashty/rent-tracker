# TfL Integration

## API
TfL Journey Planner API — free, no API key required for basic use.
Docs: https://api.tfl.gov.uk

## Destinations
Both journey times are calculated for every listing.

| Destination | Address | Notes |
|---|---|---|
| Your work | Old Street Station, EC1V 9NR | Alon's workplace |
| Partner's university | LSE, Houghton St, WC2A 2AE | Partner's study location |

## Endpoint
```
GET https://api.tfl.gov.uk/Journey/JourneyResults/{from}/to/{to}
  ?mode=tube,bus,walking,overground,elizabeth-line,dlr
  &time=0900
  &timeIs=Arriving
  &date=20260901
```

- `{from}`: prefer `lat,lon` from Apify coordinates; fall back to postcode if coordinates unavailable
- `{to}`: destination postcode
- Use a fixed weekday morning (2026-09-01, Tuesday) for consistency
- `timeIs=Arriving` at 9am gives realistic commute time

## Response fields to extract
```python
journey["duration"]          # total minutes
journey["legs"][0]["mode"]   # primary mode
```
Take the first (fastest) journey returned.

## Storage
Stored as columns in listings table:
- `commute_work_mins` — journey to Old Street
- `commute_lse_mins` — journey to LSE
- `tfl_failed` — TRUE if postcode is permanently unresolvable
- `tfl_error` — last error message for failed enrichments

## Rate limiting
- No key = 50 requests/minute limit
- With app_id + app_key (free registration): 500/minute
- Registration: https://api-portal.tfl.gov.uk
- At ~200 new listings/day max, 50/min is fine without a key

## Error handling
- If TfL returns no results: set `tfl_failed = TRUE`, store error in `tfl_error`, move on
- Retry once on timeout, then skip and leave `commute_work_mins = NULL` for retry next run
- Permanent failures (`tfl_failed = TRUE`) are never retried
- Do not block ingestion on TfL failure — enrich asynchronously

## Implementation note
Run enrichment after ingestion, not inline.
`enrich.py` queries `WHERE tfl_failed = FALSE AND commute_work_mins IS NULL` and processes in batches.
