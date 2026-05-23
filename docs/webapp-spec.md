# Webapp Specification

## Overview
A personal read-only Flask webapp to browse, filter, and sort collected listings.
Only `status` and `notes` fields are writable from the UI.

## Listing Card
Each listing displays:
- Photo (first image, if available)
- Address + area
- Rent (£/month) — colour coded (see below)
- Bedrooms / bathrooms
- Size in sqm (if available)
- Commute to work (Old Street) — colour coded (see below)
- Commute to LSE — colour coded (see below)
- Days on market (display only, not used in ranking)
- Available date (if known)
- Platform (Rightmove / Zoopla / OpenRent)
- Listed date
- Status badge (new / interested / dismissed / viewed)
- Links: original listing URL + Google Maps link (https://maps.google.com/?q={postcode})
- Notes field (editable inline)
- Status buttons: Interested / Viewed / Dismissed

## Colour Coding

### Rent
- 🟢 Green: under £1,800/month
- 🟡 Yellow-orange: £1,800–£2,200/month
- 🔴 Red: £2,200–£2,500/month

### Commute (per destination, shown separately)
- 🟢 Green: under 20 minutes
- 🟡 Amber: 20–35 minutes
- 🔴 Red: over 35 minutes
- ⚫ Grey: unavailable (tfl_failed)

### Stale listings
Listings with days_on_market >= 14 get a grey background and muted text.
Still fully visible — stale = negotiation opportunity, not a reason to hide.

## Ranking Score
Computed on the fly, used for default sort order.
All components normalised to 0–1 within current result set.

| Component | Weight | Direction |
|---|---|---|
| Rent | 35% | Lower = better |
| Commute to work | 25% | Lower = better |
| Commute to LSE | 25% | Lower = better |
| Area tier | 15% | Preferred = better |

### Area tiers
- **Preferred** (score 1.0): Angel, Clerkenwell, Farringdon, Barbican
- **Secondary** (score 0.5): Hoxton, Shoreditch, Bethnal Green

### Handling missing data
- If commute unavailable (tfl_failed): use area median commute for that area as fallback
- If no area median available: exclude commute component, reweight rent+area to fill

## Filters (sidebar)
- Area (multi-select checkboxes)
- Bedrooms (1 / 2 / both)
- Max rent (slider or input, default £2,500)
- Max commute to work (slider, minutes)
- Max commute to LSE (slider, minutes)
- Status (multi-select: new / interested / viewed / dismissed)
- Available date range (from / to)
- Platform (multi-select)
- Hide stale listings (toggle, default off)

## Sorting options
- Rank score (default)
- Rent (low to high)
- Listed date (newest first)
- Commute to work
- Commute to LSE
- Days on market

## Default view
- Show all statuses except "dismissed"
- Sorted by rank score descending
- All areas selected
- Filters collapsed on mobile, visible on desktop

## Layout
- Single page, no routing needed
- Listing cards in a responsive grid (2 cols desktop, 1 col mobile)
- Filter sidebar on left (desktop) or collapsible top panel (mobile)
- Sticky header with result count and sort selector

## Tech
- Flask (serve.py)
- Plain HTML + CSS + vanilla JS (no framework)
- All data fetched from SQLite on page load
- Status updates via fetch() POST to /api/listing/{id}/status
- Notes updates via fetch() POST to /api/listing/{id}/notes
- No authentication (local use only)
- Dark mode supported via prefers-color-scheme CSS media query
- All colour coding (rent, commute, stale) must be visible and accessible in both light and dark modes
