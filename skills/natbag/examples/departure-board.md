# Example: Departure Board

**User prompt**: "Show me departures from TLV"

## Output

```
Ben Gurion Departures — March 20, 2026

Time    Flight    Airline              To               Gate       Status
14:45   E2 239    Air Haifa            Larnaca (LCA)    G1-G2      DEPARTED
15:30   IZ 1161   Arkia Israeli        Larnaca (LCA)    G8-G10     DEPARTED
16:00   IZ 1165   Arkia Israeli        Larnaca (LCA)    G11-G13    DEPARTED
16:00   6H 751    Israir Airlines      Prague (PRG)     G15-G18    DEPARTED
16:45   IZ 1211   Arkia Israeli        Athens (ATH)      —         CANCELED
17:20   IZ 2211   Arkia Israeli        Athens (ATH)     G8-G10     DEPARTED
17:45   E2 241    Air Haifa            Larnaca (LCA)    G3-G4      DEPARTED
18:00   IZ 1335   Arkia Israeli        Rome (FCO)       G11-G13    DEPARTED
21:25   IZ 1217   Arkia Israeli        Athens (ATH)      —         DELAYED → 23:45
```

## API Call Used

```bash
curl -s 'https://data.gov.il/api/3/action/datastore_search?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5&limit=200&filters=%7B%22CHAORD%22%3A%22D%22%7D&sort=CHSTOL%20asc'
```
