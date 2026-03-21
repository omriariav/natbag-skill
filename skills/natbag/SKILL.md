---
name: natbag
description: >
  This skill should be used when the user asks about "Ben Gurion airport",
  "TLV flights", "flight status", "departures from Tel Aviv", "arrivals at TLV",
  "is my flight on time", "flight to Amsterdam", "airport delays", "cancelled flights",
  "gate info", "terminal 3", "pickup from airport", "weather at destination",
  "flight delay history", "נתב״ג", "טיסות", "לוח טיסות", "מצב טיסה".
  Provides live flight data from Ben Gurion Airport (TLV), destination weather
  via Open-Meteo, and historical delay analysis via local SQLite database.
  Do NOT use for booking flights, non-TLV airports, or general travel planning.
allowed-tools:
  - Bash(curl)
  - Bash(python3)
  - Bash(sqlite3)
  - Read
  - Write
---

# Natbag — Ben Gurion Airport Flights

Live flight data, destination weather, and historical analysis for Ben Gurion Airport (TLV/LLBG). Data from Israel's open data portal (data.gov.il), covering a rolling ~3-day window.

## Data Sources

1. **Live flights**: data.gov.il API — departures, arrivals, status, gates
2. **Weather**: Open-Meteo API — free, no API key — current conditions at destination
3. **Historical**: Local SQLite DB at `~/.natbag/flights.db` — accumulated via daily snapshots

## Before Any Query — Daily Snapshot

On every natbag invocation, first run the snapshot script to accumulate historical data:

```bash
python3 SKILL_DIR/scripts/snapshot.py
```

Replace `SKILL_DIR` with the resolved path to this skill's directory (where this SKILL.md lives).

The script self-guards: it checks `~/.natbag/config.json` and skips if it already ran today or if the user disabled snapshots (`daily_snapshot: false`). This means it effectively runs once per day on first use, with no background process.

If it fails (e.g., network error), proceed with the live query anyway — the snapshot is best-effort.

## Querying Live Flights

Fetch flights via `curl` and parse the JSON response. Always use `limit=200` to get the full dataset.

**Base pattern:**
```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters={"CHAORD":"D"}&sort=CHSTOL%20asc'
```

### Filter Recipes

| Use Case | filters | sort |
|----------|---------|------|
| All departures | `{"CHAORD":"D"}` | `CHSTOL asc` |
| All arrivals | `{"CHAORD":"A"}` | `CHSTOL asc` |
| Specific airline | `{"CHOPER":"LY"}` | `CHSTOL asc` |
| Specific destination | `{"CHLOC1":"AMS"}` | `CHSTOL asc` |
| Departures to city | `{"CHAORD":"D","CHLOC1":"JFK"}` | `CHSTOL asc` |
| Delayed flights | `{"CHRMINE":"DELAYED"}` | `CHSTOL asc` |
| Cancelled flights | `{"CHRMINE":"CANCELED"}` | `CHSTOL asc` |

For flight number lookup, use full-text search: `q=LY001` or filter by both `CHOPER` and `CHFLTN`.

When the user mentions a city name instead of an airport code, use `q=AMSTERDAM` (full-text) since city name fields may not match exactly.

### Key Fields

| Field | Content |
|-------|---------|
| CHOPER + CHFLTN | Airline code + flight number (e.g., LY 001) |
| CHOPERD | Airline full name |
| CHSTOL | Scheduled time |
| CHPTOL | Updated/actual time (compare with CHSTOL to calculate delay) |
| CHAORD | D = departure, A = arrival |
| CHLOC1 / CHLOC1T | Airport code / City name (English) |
| CHLOC1TH / CHLOC1CH | City / Country (Hebrew) |
| CHTERM | Terminal |
| CHCINT | Gate |
| CHCKZN | Check-in zone |
| CHRMINE / CHRMINH | Status (English / Hebrew) |

Full field reference and curl examples: see [references/api.md](references/api.md).
For complete output examples: see [examples/](examples/) (departure board, single flight, historical stats).

## Destination Weather

After showing flight info, offer weather at the destination. Uses Open-Meteo (free, no key).

**Steps:**
1. Geocode the city: `curl -s 'https://geocoding-api.open-meteo.com/v1/search?name={CHLOC1T}&count=1'`
2. Extract `latitude` and `longitude` from `results[0]`
3. Fetch weather: `curl -s 'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true'`
4. Display: temperature, weather description, wind speed

Cache geocoding results in `~/.natbag/geo_cache.json` to avoid repeated lookups — write `{"city": {"lat": x, "lon": y}}` entries.

Weather codes: 0=Clear, 1-3=Partly cloudy, 45/48=Fog, 51-55=Drizzle, 61-65=Rain, 71-75=Snow, 80-82=Showers, 95=Thunderstorm.

## Historical Analysis

Query `~/.natbag/flights.db` with `sqlite3` for delay patterns, on-time performance, and cancellation rates.

If the database doesn't exist or is empty, inform the user: "Historical data accumulates from install date via daily snapshots. Run `python3 <skill-path>/scripts/snapshot.py --force` to start collecting now."

Check data coverage first:
```sql
SELECT MIN(chstol) as earliest, MAX(chstol) as latest, COUNT(*) as total FROM flights;
```

Common queries — see [references/api.md](references/api.md) for full patterns:
- On-time performance by airline (last 30 days)
- Average delay for a specific route
- Cancellation rate by destination
- Delay calculation: `(julianday(chptol) - julianday(chstol)) * 24 * 60` gives minutes

## Output Formatting

### Departure/Arrival Board

```
Ben Gurion Departures — March 21, 2026

Time    Flight    Airline     To               Gate     Status
14:10   LY 001    El Al       London (LHR)     B2-B4    ON TIME
14:30   IZ 1511   Arkia       Larnaca (LCA)    G11      DELAYED → 15:04
15:00   6H 996    Israir      Amsterdam (AMS)   —       CANCELED
```

- Sort by scheduled time (CHSTOL)
- For DELAYED flights, show updated time from CHPTOL
- Use `—` for null gate/check-in values
- Omit past flights (status DEPARTED/LANDED) unless the user explicitly asks for all

### Single Flight Detail

```
Flight LY 001 — El Al Israel Airlines
Route:     Tel Aviv (TLV) → London Heathrow (LHR)
Scheduled: 14:10  |  Updated: 14:10
Terminal:  3      |  Gate: B2-B4  |  Check-in: B
Status:    ON TIME

London Weather: 12°C, Partly Cloudy, Wind 15 km/h
```

### Historical Stats

```
El Al to JFK — Last 30 Days (from local DB)
Total: 28  |  On time: 19 (68%)  |  Avg delay: 22 min
Cancellations: 1 (3.6%)
```

## Hebrew Support

When the user writes in Hebrew, respond in Hebrew and use Hebrew field values:
- City names: CHLOC1TH instead of CHLOC1T
- Country names: CHLOC1CH instead of CHLOCCT
- Status: CHRMINH instead of CHRMINE
- Board header: `לוח טיסות נתב"ג — יציאות` / `הגעות`

## Smart Behaviors

- **"my flight"**: Ask for flight number or destination to narrow down
- **Pickup planning**: Show arrival time + suggest arriving 30 min after expected landing. If DELAYED, use CHPTOL instead of CHSTOL
- **Delay detection**: When CHPTOL > CHSTOL, calculate and show delay duration in minutes
- **Weather proactively**: When showing a single flight detail, include destination weather automatically
- **First use**: Mention that historical data accumulates over time via daily snapshots. The user can disable this in `~/.natbag/config.json` by setting `daily_snapshot: false`

## Snapshot Management

The `scripts/snapshot.py` script fetches current flights and stores them in SQLite:
- Runs automatically on first skill use each day (see "Before Any Query" above)
- `python3 SKILL_DIR/scripts/snapshot.py --force` to run manually anytime
- Opt-out: set `daily_snapshot: false` in `~/.natbag/config.json`
- Data deduplicates by airline+flight+scheduled time
- Status and gate info are updated on each snapshot

## Gotchas

- **Field names are cryptic**: All fields start with CH (Hebrew abbreviation for "חברה"/company). Always refer to the field reference, never guess. Common mistake: using `STATUS` instead of `CHRMINE`.
- **Rolling window**: API only has ~3 days of data. For older data, rely on local SQLite DB. If no historical DB exists, tell the user data starts accumulating from first use.
- **Uppercase values**: Filter values must be uppercase. `filters={"CHRMINE":"delayed"}` returns 0 results silently — use `"DELAYED"`. Same for airline codes: `"ly"` → no results, `"LY"` → works.
- **API timeout**: data.gov.il can be slow (5-15s). If `curl` hangs, retry once. Error: `curl: (28) Operation timed out` — fix with `curl -s --max-time 30`.
- **Bad resource ID**: Returns `{"success": false, "error": {"__type": "Not Found Error", "message": "לא נמצא: Resource was not found."}}`. Fix: verify the resource_id constant hasn't changed.
- **Malformed filters JSON**: Returns `{"success": false, "error": {"filters": ["Cannot parse JSON"], "__type": "Validation Error"}}`. Fix: ensure filters value is valid JSON with properly escaped quotes in the URL.
- **Empty result confusion**: `"total": 0` with `"success": true` means the filter matched nothing — not an error. Check: is the value uppercase? Is the field name correct? Is the flight within the 3-day window?
- **Gate availability**: `CHCINT` and `CHCKZN` are often null for flights >24h away or for arrivals. Don't treat null gate as an error.
- **"NOT FINAL"**: Many future flights show status "NOT FINAL" — this means the schedule isn't confirmed yet, not that the flight is cancelled. Don't alarm the user.
- **No booking**: This skill provides information only. Cannot book, modify, or cancel flights. If asked, clearly say so.
