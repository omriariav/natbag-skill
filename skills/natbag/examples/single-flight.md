# Example: Single Flight Lookup

**User prompt**: "Is flight IZ 442 on time?"

## Output

```
Flight IZ 442 — Arkia Israeli Airlines
Route:     Munich (MUC) → Tel Aviv (TLV)
Scheduled: 17:50  |  Updated: 20:05
Terminal:  3      |  Gate: —
Status:    DELAYED (2h 15m)

Munich Weather: 8°C, Partly Cloudy, Wind 12 km/h
```

## API Calls Used

```bash
# Flight lookup
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&filters=%7B%22CHOPER%22%3A%22IZ%22%2C%22CHFLTN%22%3A%22442%22%7D'

# Weather geocoding
curl -s 'https://geocoding-api.open-meteo.com/v1/search?name=Munich&count=1'

# Weather data
curl -s 'https://api.open-meteo.com/v1/forecast?latitude=48.14&longitude=11.58&current_weather=true'
```
