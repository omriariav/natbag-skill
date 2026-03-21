# natbag

Claude Code plugin for Ben Gurion Airport (TLV) flight data.

## What it does

- **Live flights** — Departures, arrivals, status, gates from [data.gov.il](https://data.gov.il/he/datasets/airport_authority/flydata)
- **Destination weather** — Current conditions via [Open-Meteo](https://open-meteo.com/) (free, no API key)
- **Historical analysis** — On-time performance, delay stats, cancellation rates from local SQLite DB
- **IATA reference** — 999 airlines + 9,240 airports shipped with the plugin (no download needed)
- **Bilingual** — Hebrew and English

## Install

```
/install-plugin omriariav/natbag-skill
```

No setup required. On first use, the plugin automatically:
1. Copies shipped `data/db.db` (airlines + airports) to `~/.natbag/flights.db`
2. Fetches live flight data from Ben Gurion Airport
3. Starts accumulating historical data for delay analysis

## Usage

The skill triggers automatically when you ask about TLV flights. You can also invoke it directly:

```
/natbag departures
/natbag arrivals
/natbag LY001
/natbag delayed
```

### Example prompts

- "Show me departures from Ben Gurion"
- "Is flight LY001 on time?"
- "When is the next flight to Amsterdam?"
- "Any cancelled flights?"
- "Weather in London for my flight"
- "Are El Al flights to JFK usually delayed?"
- "מה הטיסות היום מנתב״ג?"

## How it works

```
Install → ships data/db.db (999 airlines, 6,072 airports)
                ↓
First use → copies IATA data into ~/.natbag/flights.db + fetches live flights
                ↓
Every use → PreToolUse hook runs snapshot.py (once daily, self-guards)
                ↓
Query → scripts return clean JSON → Claude formats for user
```

- `snapshot.py` — fetches live flights, upserts into SQLite, imports IATA data on first run
- `query_flights.py` — queries live API with filters (airline, destination, status)
- `query_history.py` — queries local DB for historical stats, airport/airline lookups

## Configuration

Settings are stored in `~/.natbag/config.json` (created automatically on first use):

```json
{
  "daily_snapshot": true,
  "last_snapshot": "2026-03-21T10:00:00+00:00"
}
```

**Disable daily snapshots:**

Tell Claude: "disable natbag daily snapshots"

Or manually:
```bash
python3 -c "import json; f=open('$HOME/.natbag/config.json','r+'); d=json.load(f); d['daily_snapshot']=False; f.seek(0); json.dump(d,f,indent=2); f.truncate()"
```

## Data sources

| Data | Source | Freshness |
|------|--------|-----------|
| Flight data | [Israel Open Data Portal](https://data.gov.il/) | Live (rolling ~3 day window) |
| Weather | [Open-Meteo](https://open-meteo.com/) | Live (geocoding by city name) |
| Airlines | [Wikipedia](https://en.wikipedia.org/wiki/List_of_airline_codes) | Shipped (March 2026), 999 airlines |
| Airports | [ip2location](https://github.com/ip2location/ip2location-iata-icao-real) + [OpenFlights](https://github.com/jpatokal/openflights) | Shipped (Dec 2025 + 2017 fallback), 9,240 airports |

## License

Flight data: [data.gov.il terms](https://data.gov.il/terms).

Airport data is a modified merge of [ip2location IATA/ICAO](https://github.com/ip2location/ip2location-iata-icao-real) ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) and [OpenFlights](https://github.com/jpatokal/openflights) ([ODbL-1.0](https://opendatacommons.org/licenses/odbl/1.0/)). Airline data scraped from [Wikipedia](https://en.wikipedia.org/wiki/List_of_airline_codes) ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)).
