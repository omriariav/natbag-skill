# natbag

Claude Code plugin for Ben Gurion Airport (TLV) flight data.

## What it does

- **Live flights** — Departures, arrivals, status, gates from [data.gov.il](https://data.gov.il/he/datasets/airport_authority/flydata)
- **Destination weather** — Current conditions via [Open-Meteo](https://open-meteo.com/) (free, no API key)
- **Historical analysis** — On-time performance, delay stats, cancellation rates from local SQLite DB
- **IATA reference** — 992 airlines + 6,072 airports for code/name resolution
- **Bilingual** — Hebrew and English

## Install

```
/install-plugin omriariav/natbag-skill
```

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

- A **PreToolUse hook** runs `snapshot.py` once daily to accumulate flight history
- Scripts in `scripts/` provide composable CLIs (`query_flights.py`, `query_history.py`)
- Data stored in `~/.natbag/flights.db` (SQLite)

## Configuration

Settings are stored in `~/.natbag/config.json`:

```json
{
  "daily_snapshot": true,
  "last_snapshot": "2026-03-21T10:00:00+00:00"
}
```

**Disable daily snapshots:**
```bash
python3 -c "import json; f=open('$HOME/.natbag/config.json','r+'); d=json.load(f); d['daily_snapshot']=False; f.seek(0); json.dump(d,f,indent=2); f.truncate()"
```

Or simply tell Claude: "disable natbag daily snapshots"

## Data sources

- Flight data: [Israel Open Data Portal](https://data.gov.il/) (public API, no key required)
- Weather: [Open-Meteo](https://open-meteo.com/) (free, no key required)
- IATA reference: [OpenFlights](https://github.com/jpatokal/openflights) (ODbL-1.0)

## License

Flight data: [data.gov.il terms](https://data.gov.il/terms). IATA reference data: [ODbL-1.0](https://opendatacommons.org/licenses/odbl/1.0/).
