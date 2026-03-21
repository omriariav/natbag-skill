# Example: Historical Delay Analysis

**User prompt**: "Are Arkia flights to Athens usually delayed?"

## Output

```
Arkia (IZ) to Athens — Last 30 Days (from local DB)

Total flights: 24
On time:       16 (67%)
Delayed:        6 (25%)
Canceled:       2 (8%)
Avg delay:     18 min (when delayed)

Most delays occur on evening departures (after 20:00).
```

## SQLite Query Used

```sql
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN chrmine IN ('ON TIME', 'EARLY', 'DEPARTED', 'LANDED') THEN 1 ELSE 0 END) as on_time,
  SUM(CASE WHEN chrmine = 'DELAYED' THEN 1 ELSE 0 END) as delayed,
  SUM(CASE WHEN chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled,
  ROUND(AVG(CASE
    WHEN chrmine = 'DELAYED' AND chptol > chstol
    THEN (julianday(chptol) - julianday(chstol)) * 24 * 60
  END), 0) as avg_delay_min
FROM flights
WHERE choper = 'IZ' AND chloc1 = 'ATH' AND chaord = 'D'
  AND chstol >= date('now', '-30 days');
```
