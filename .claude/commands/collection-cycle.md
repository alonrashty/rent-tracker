# Skill: Run Collection Cycle

Invoke this skill to run a full data collection cycle.
Reference: `@config.md` for credentials and URLs before starting.

---

## Steps

### 1. Collect
Run `src/collect.py`:
- Call Apify actor for each Rightmove URL in config
- Call Apify actor for each Zoopla URL in config
- If Apify fails for any platform, fall back to OpenRent via browser
- Save raw JSON responses to `data/raw/YYYY-MM-DD/`

### 2. Ingest
Run `src/ingest.py`:
- Parse raw JSON from today's collection
- For each listing: skip if URL already in DB
- Insert new listings with status = 'new'
- Recompute `days_on_market` for all existing listings
- Recompute area median prices (weekly, on Mondays only)
- Print summary: N new, N skipped (duplicate), N total in DB

### 3. Enrich
Run `src/enrich.py`:
- Query all listings WHERE commute_work_mins IS NULL
- Call TfL API for each: to Old Street and to LSE
- Update rows with commute times
- Print summary: N enriched, N failed (log failures)

### 4. Digest (if run is daily scheduled, not manual)
Run `src/digest.py`:
- Query listings WHERE created_at >= now - 24h
- Format HTML email with listing cards
- Send to EMAIL_TO from config
- Print: email sent / skipped (0 new listings)

### 5. Push DB to GitHub (always)
Commit and push the updated database so the live webapp on Railway reflects the latest listings:
```powershell
git add data/listings.db
git commit -m "update listings $(Get-Date -Format 'yyyy-MM-dd')"
git push
```
Railway auto-redeploys on push (~60s). This step runs whether or not new listings were found.

---

## Success criteria
- DB updated, no duplicate URLs inserted
- All new listings have TfL commute times (or NULL with logged reason)
- Email sent if new listings found
- Run summary printed to stdout

## Do not
- Modify config.md
- Contact any landlords or agents
- Delete listings from DB
- Run digest on manual/test invocations unless explicitly asked

## After each step
Update docs immediately — don't batch at the end:
- `docs/build-plan.md` — check the completed item
- `docs/discoveries.md` — log anything non-obvious (API quirks, unexpected behaviour, decisions made)
