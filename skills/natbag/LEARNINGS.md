# Natbag Skill Learnings

Accumulated observations from real usage. Read this on every invocation to avoid repeating past mistakes.

## API Quirks

- data.gov.il responses can take 5-15 seconds. Always use `--max-time 30` with curl.
- The API returns Hebrew error messages (e.g., "לא נמצא" for not found). Parse `success: false` to detect errors, not the message text.

## Data Patterns

- Most domestic/regional flights use airlines IZ (Arkia), 6H (Israir), E2 (Air Haifa).
- Long-haul flights (JFK, LAX, BKK) are typically LY (El Al) only.
- Terminal 3 handles virtually all commercial flights. Terminal 1 is rare.
- Gate assignments appear 2-4 hours before departure. Earlier queries will show null.

## Common User Mistakes

- Users often say "El Al 001" meaning flight LY001. Parse airline name to IATA code.
- Users may type city names in Hebrew — use full-text search `q=` parameter which matches Hebrew fields.
- "My flight" without context — always ask for flight number or destination.

<!-- Add new learnings below this line -->
