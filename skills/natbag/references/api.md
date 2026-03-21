# Ben Gurion Airport Flight Data API Reference

## Data Source

Israel's open data portal (data.gov.il) provides a CKAN datastore API for Ben Gurion Airport (TLV/LLBG) flight data. The dataset contains a rolling ~3-day window of approximately 200 flights, updated continuously.

## API Endpoint

```
GET https://data.gov.il/api/3/action/datastore_search
```

### Required Parameter

| Param | Value |
|-------|-------|
| `resource_id` | `e83f763b-b7d7-479e-b172-ae981ddc6de5` |

### Optional Parameters

| Param | Type | Description | Example |
|-------|------|-------------|---------|
| `limit` | int | Max records (default 100) | `limit=200` |
| `offset` | int | Pagination offset | `offset=100` |
| `filters` | JSON | Exact match or IN array | `filters={"CHAORD":"D"}` or `{"CHRMINE":["DELAYED","CANCELED"]}` |
| `sort` | string | Sort field + direction | `sort=CHSTOL asc` |
| `q` | string | Full-text search | `q=AMSTERDAM` |
| `q` + `plain=false` | string | Partial/prefix search (supports Hebrew) | `q=לונ:*&plain=false` |
| `fields` | string | Return only specific columns | `fields=CHOPER,CHFLTN,CHRMINE` |

### Required Header

All requests should include: `User-Agent: datagov-external-client`

### Filter Capabilities (tested)

| Filter type | Works | Example |
|-------------|-------|---------|
| Equality | Yes | `{"CHOPER": "LY"}` |
| Array/IN | Yes | `{"CHRMINE": ["DELAYED", "CANCELED"]}` |
| Combined | Yes | `{"CHAORD": "A", "CHRMINE": ["ON TIME", "DELAYED"]}` |
| Greater-than | No | Fails |
| Negation/NOT | No | Fails |
| SQL endpoint | No | 403 blocked |

## Field Reference

| Field | Meaning | Values / Examples |
|-------|---------|-------------------|
| CHOPER | Airline IATA code | LY, IZ, 6H, E2, W6, FR, QS, U2, PC |
| CHFLTN | Flight number | 001, 1511, 996 |
| CHOPERD | Airline full name | EL AL ISRAEL AIRLINES, ARKIA ISRAELI AIRLINES |
| CHSTOL | Scheduled time (ISO 8601) | 2026-03-20T14:10:00 |
| CHPTOL | Updated/actual time | 2026-03-20T15:04:00 |
| CHAORD | Direction | D = departure, A = arrival |
| CHLOC1 | Destination/origin IATA code | AMS, JFK, LHR, CDG, FCO |
| CHLOC1D | City name (raw) | AMSTERDAM |
| CHLOC1T | City (English) | AMSTERDAM |
| CHLOC1TH | City (Hebrew) | אמסטרדם |
| CHLOC1CH | Country (Hebrew) | הולנד |
| CHLOCCT | Country (English) | NETHERLANDS |
| CHTERM | Terminal number | 1, 3 |
| CHCINT | Gate assignment | G11-G13, B2-B4 (null if unassigned) |
| CHCKZN | Check-in zone | G, B (null if N/A) |
| CHRMINE | Status (English) | DEPARTED, LANDED, CANCELED, ON TIME, DELAYED, EARLY, FINAL, NOT FINAL |
| CHRMINH | Status (Hebrew) | המריאה, נחתה, מבוטלת, בזמן, מאחרת, מוקדמת, סופי, לא סופי |

## Known Airline Codes

| Code | Airline | Notes |
|------|---------|-------|
| LY | El Al Israel Airlines | Flag carrier |
| IZ | Arkia Israeli Airlines | Domestic + regional |
| 6H | Israir Airlines | Domestic + short-haul |
| E2 | Air Haifa | Small operator |
| W6 | Wizz Air | European LCC |
| FR | Ryanair | European LCC |
| QS | SmartWings | Czech carrier |
| U2 | easyJet | European LCC |
| PC | Pegasus Airlines | Turkish LCC |
| TK | Turkish Airlines | |
| LH | Lufthansa | |
| AF | Air France | |
| BA | British Airways | |
| AA | American Airlines | |
| UA | United Airlines | |
| DL | Delta Air Lines | |

## curl Query Patterns

All curl examples should include `-H 'User-Agent: datagov-external-client'`.

### All departures, sorted by time
```bash
curl -s -H 'User-Agent: datagov-external-client' 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=\{"CHAORD":"D"\}&sort=CHSTOL%20asc' | python3 -c "import sys,json; [print(f\"{r['CHSTOL'][11:16]}  {r['CHOPER']}{r['CHFLTN']:>5}  {r['CHLOC1T']:15} {r['CHRMINE']}\") for r in json.load(sys.stdin)['result']['records']]"
```

### All arrivals
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=\{"CHAORD":"A"\}&sort=CHSTOL%20asc'
```

### Specific airline (e.g., El Al)
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=\{"CHOPER":"LY"\}&sort=CHSTOL%20asc'
```

### Specific destination (e.g., London)
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=\{"CHLOC1":"LHR"\}'
```

### Delayed flights only
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=\{"CHRMINE":"DELAYED"\}'
```

### Full-text search (e.g., "AMSTERDAM")
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&q=AMSTERDAM'
```

### Combined filters (departures to specific city)
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&filters=\{"CHAORD":"D","CHLOC1":"AMS"\}'
```

## Open-Meteo Weather API (Free, No Key)

### Geocode a city name
```bash
curl -s 'https://geocoding-api.open-meteo.com/v1/search?name=Amsterdam&count=1' | python3 -c "import sys,json; r=json.load(sys.stdin)['results'][0]; print(f\"{r['latitude']},{r['longitude']}\")"
```

### Get current weather by coordinates
```bash
curl -s 'https://api.open-meteo.com/v1/forecast?latitude=52.37&longitude=4.89&current_weather=true'
```

Response includes: `temperature`, `windspeed`, `winddirection`, `weathercode`, `is_day`, `time`.

### Weather codes (WMO)
| Code | Meaning |
|------|---------|
| 0 | Clear sky |
| 1-3 | Partly cloudy |
| 45, 48 | Fog |
| 51-55 | Drizzle |
| 61-65 | Rain |
| 71-75 | Snow |
| 80-82 | Rain showers |
| 95 | Thunderstorm |

## SQLite Historical Query Patterns

Database location: `~/.natbag/flights.db`

### On-time performance by airline
```sql
SELECT choper, choperd,
  COUNT(*) as total,
  SUM(CASE WHEN chrmine IN ('ON TIME', 'EARLY', 'DEPARTED', 'LANDED') THEN 1 ELSE 0 END) as on_time,
  SUM(CASE WHEN chrmine = 'DELAYED' THEN 1 ELSE 0 END) as delayed,
  SUM(CASE WHEN chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled
FROM flights
WHERE chstol >= date('now', '-30 days')
GROUP BY choper
ORDER BY total DESC;
```

### Average delay for a specific route
```sql
SELECT choper, chloc1t,
  COUNT(*) as flights,
  AVG(CASE
    WHEN chptol > chstol
    THEN (julianday(chptol) - julianday(chstol)) * 24 * 60
    ELSE 0
  END) as avg_delay_minutes
FROM flights
WHERE chloc1 = 'JFK' AND chaord = 'D'
  AND chstol >= date('now', '-30 days')
GROUP BY choper;
```

### Cancellation rate by route
```sql
SELECT chloc1, chloc1t,
  COUNT(*) as total,
  SUM(CASE WHEN chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled,
  ROUND(100.0 * SUM(CASE WHEN chrmine = 'CANCELED' THEN 1 ELSE 0 END) / COUNT(*), 1) as cancel_pct
FROM flights
WHERE chstol >= date('now', '-30 days')
GROUP BY chloc1
HAVING total >= 3
ORDER BY cancel_pct DESC;
```

### Historical data coverage
```sql
SELECT
  MIN(chstol) as earliest,
  MAX(chstol) as latest,
  COUNT(*) as total_records,
  COUNT(DISTINCT date(chstol)) as days_covered
FROM flights;
```

## Error Handling

- **API timeout**: data.gov.il can be slow. Use 30s timeout.
- **Empty results**: `total=0` means no matching flights. Check filter spelling — field values are uppercase.
- **Rate limiting**: No documented rate limits, but be conservative. One request per query is usually sufficient (limit=200 covers the full dataset).
- **Field nulls**: `CHCINT` (gate), `CHCKZN` (check-in) are often null for distant future flights or arrivals.
