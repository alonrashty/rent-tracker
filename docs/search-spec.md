# Search Specification

## Target areas
- Angel (Islington)
- Clerkenwell
- Farringdon
- Hoxton
- Shoreditch
- Barbican
- Bethnal Green
- Dalston
- London Fields

## Filters
| Parameter | Value |
|---|---|
| Property type | Whole flat only (no rooms, no house shares) |
| Bedrooms | 1 or 2 |
| Min rent | £1,500/month |
| Max rent | £2,500/month |
| Furnishing | Furnished only |
| Tenancy length | 12+ months (long let) |
| Availability | August–October 2026 |
| Platforms | Rightmove, Zoopla, OpenRent |
| Excluded | SpareRoom, short lets, serviced apartments |

Availability is not filtered at the URL level (platforms don't reliably support it). Instead, `ingest.py` skips listings where `available_date` is outside August–October 2026. Listings with no `available_date` are included and flagged as unknown.

## Priority signals
These don't filter listings out — they inform ranking in the webapp:
- **2-bed under £2,500**: flag prominently — 2-beds in these areas typically exceed the budget, so any that fit are notable
- **Listed 14+ days**: potential negotiation opportunity
- **Price below area median**: calculated from collected data, updated weekly
- **Available September**: closer to target move date scores higher

## Platforms & search URLs
Apify actors accept Rightmove/Zoopla search URLs directly.
Construct URLs with filters pre-applied (furnished, to-rent, max price, bedrooms).

OpenRent is not on Apify — it is collected via Playwright browser automation as a fallback when Apify returns fewer results than expected.

### Rightmove URL template
```
https://www.rightmove.co.uk/property-to-rent/find.html
  ?locationIdentifier={TYPE}%5E{id}
  &minBedrooms=1
  &maxBedrooms=2
  &minPrice=1500
  &maxPrice=2500
  &propertyTypes=flat
  &letFurnishType=furnished
  &letType=longTerm
  &includeLetAgreed=false
  &radius=1.0
  &sortType=6
```

### Zoopla URL template
```
https://www.zoopla.co.uk/to-rent/flats/{area}/
  ?beds_min=1
  &beds_max=2
  &price_frequency=per_month
  &price_min=1500
  &price_max=2500
  &furnished_state=furnished
  &radius=1
  &results_sort=newest_listings
```

### Location identifiers
| Area | Type | ID | Notes |
|---|---|---|---|
| Angel | STATION | 245 | No London REGION exists |
| Clerkenwell | REGION | 87500 | |
| Farringdon | STATION | 3431 | No London REGION exists |
| Hoxton | REGION | 85332 | |
| Shoreditch | REGION | 87528 | |
| Barbican | REGION | 85259 | |
| Bethnal Green | REGION | 85224 | |
| Dalston | STATION | 15132 | Dalston Junction; no REGION exists |
| London Fields | REGION | 70417 | Prefer REGION over STATION^5801 |

See `config.md` for the actual resolved URLs per area.
