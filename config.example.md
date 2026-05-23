# Config

Copy this file to `config.md` (git-ignored) and fill in your values.

## API Keys
```
APIFY_API_TOKEN=your_token_here
APIFY_RIGHTMOVE_ACTOR=memo23/rightmove-scraper
APIFY_ZOOPLA_ACTOR=shahidirfan/zoopla-scraper
TFL_APP_ID=optional_see_tfl_docs
TFL_APP_KEY=optional_see_tfl_docs
```

## Email
```
EMAIL_FROM=you@gmail.com
EMAIL_TO=you@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

## Destinations (for TfL)
```
DEST_WORK_POSTCODE=EC1V 9NR        # Old Street Station
DEST_LSE_POSTCODE=WC2A 2AE         # LSE Houghton Street
```

## Search
```
MIN_RENT=1500
MAX_RENT=2500
MIN_BEDS=1
MAX_BEDS=2
AVAILABLE_FROM=2026-08-15
AVAILABLE_TO=2026-10-15
```

## Rightmove search URLs (one per area, furnished long-let to-rent, 1–2 beds, max £2,500)
```
RIGHTMOVE_URL_1=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=STATION%5E245&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_2=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E87500&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_3=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=STATION%5E3431&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_4=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E85332&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_5=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E87528&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_6=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E85259&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_URL_7=https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E85224&minBedrooms=1&maxBedrooms=2&minPrice=1500&maxPrice=2500&propertyTypes=flat&letFurnishType=furnished&letType=longTerm&includeLetAgreed=false&radius=1.0&sortType=6
RIGHTMOVE_AREA_1=Angel
RIGHTMOVE_AREA_2=Clerkenwell
RIGHTMOVE_AREA_3=Farringdon
RIGHTMOVE_AREA_4=Hoxton
RIGHTMOVE_AREA_5=Shoreditch
RIGHTMOVE_AREA_6=Barbican
RIGHTMOVE_AREA_7=Bethnal Green
```

## Zoopla search URLs (one per area)
```
ZOOPLA_URL_1=https://www.zoopla.co.uk/to-rent/flats/angel/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_URL_2=https://www.zoopla.co.uk/to-rent/flats/clerkenwell/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_URL_3=                                                      # Farringdon has no Zoopla slug; covered by Clerkenwell above
ZOOPLA_URL_4=https://www.zoopla.co.uk/to-rent/flats/hoxton/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_URL_5=https://www.zoopla.co.uk/to-rent/flats/ec2a/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_URL_6=https://www.zoopla.co.uk/to-rent/flats/barbican/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_URL_7=https://www.zoopla.co.uk/to-rent/flats/bethnal-green/?beds_min=1&beds_max=2&price_frequency=per_month&price_min=1500&price_max=2500&furnished_state=furnished&radius=1&results_sort=newest_listings
ZOOPLA_AREA_1=Angel
ZOOPLA_AREA_2=Clerkenwell
ZOOPLA_AREA_3=                                                      # blank — no Zoopla coverage for Farringdon
ZOOPLA_AREA_4=Hoxton
ZOOPLA_AREA_5=Shoreditch
ZOOPLA_AREA_6=Barbican
ZOOPLA_AREA_7=Bethnal Green
```
Areas: same order as Rightmove URLs above. Farringdon (URL_3) intentionally blank — no Zoopla slug; covered by Clerkenwell. Shoreditch uses EC2A postcode slug.

## Webapp
```
WEBAPP_PORT=5000
WEBAPP_HOST=127.0.0.1
```
