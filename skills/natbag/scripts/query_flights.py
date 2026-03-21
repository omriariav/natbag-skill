#!/usr/bin/env python3
"""Query live Ben Gurion Airport flights. Returns clean JSON.

Wraps the data.gov.il API with argument parsing, airline/airport name resolution
via the local IATA database. All output is JSON with readable field names.

Usage:
    query_flights.py --departures
    query_flights.py --arrivals --airline LY
    query_flights.py --destination JFK
    query_flights.py --flight LY001
    query_flights.py --status DELAYED
    query_flights.py --search "London"
"""

import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError

DB_PATH = Path.home() / ".natbag" / "flights.db"

API_BASE = (
    "https://data.gov.il/api/3/action/datastore_search"
    "?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5"
)


def parse_args(argv):
    args = {"filters": {}, "sort": "CHSTOL asc", "limit": 200, "search": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--departures":
            args["filters"]["CHAORD"] = "D"
        elif a == "--arrivals":
            args["filters"]["CHAORD"] = "A"
        elif a == "--airline" and i + 1 < len(argv):
            i += 1
            args["filters"]["CHOPER"] = resolve_airline(argv[i])
        elif a == "--destination" and i + 1 < len(argv):
            i += 1
            args["filters"]["CHLOC1"] = argv[i].upper()
        elif a == "--status" and i + 1 < len(argv):
            i += 1
            args["filters"]["CHRMINE"] = argv[i].upper()
        elif a == "--flight" and i + 1 < len(argv):
            i += 1
            code, num = parse_flight_number(argv[i])
            if code:
                args["filters"]["CHOPER"] = code
            if num:
                args["filters"]["CHFLTN"] = num
        elif a == "--search" and i + 1 < len(argv):
            i += 1
            args["search"] = argv[i]
        elif a == "--limit" and i + 1 < len(argv):
            i += 1
            try:
                args["limit"] = int(argv[i])
            except ValueError:
                print(f"Invalid --limit value: {argv[i]}", file=sys.stderr)
                sys.exit(1)
        i += 1
    return args


def resolve_airline(name_or_code):
    """Resolve airline name to IATA code using local DB."""
    if len(name_or_code) == 2 and name_or_code.isalnum():
        return name_or_code.upper()
    if not DB_PATH.exists():
        return name_or_code.upper()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT iata_code FROM airlines WHERE UPPER(name) LIKE ? LIMIT 1",
            (f"%{name_or_code.upper()}%",)
        ).fetchone()
        conn.close()
        return row[0] if row else name_or_code.upper()
    except sqlite3.Error:
        return name_or_code.upper()


def parse_flight_number(flight):
    """Parse 'LY001', 'LY 001', or just '001' into (code, number)."""
    flight = flight.strip().upper().replace(" ", "")
    for i, c in enumerate(flight):
        if c.isdigit():
            code = flight[:i] if i > 0 else None
            num = flight[i:]
            return code, num
    return flight, None


def fetch(args):
    url = f"{API_BASE}&limit={args['limit']}&sort={quote(args['sort'])}"
    if args["filters"]:
        url += f"&filters={quote(json.dumps(args['filters']))}"
    if args["search"]:
        url += f"&q={quote(args['search'])}"
    try:
        with urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid API response: {e}", file=sys.stderr)
        sys.exit(1)
    if not data.get("success"):
        print(f"API error: {data.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(1)
    return data["result"]["records"], data["result"].get("total", 0)


def clean(record):
    """Rename cryptic API fields to readable names."""
    stol = record.get("CHSTOL") or ""
    return {
        "flight": f"{record.get('CHOPER', '')} {record.get('CHFLTN', '')}".strip(),
        "airline": (record.get("CHOPERD") or "").strip(),
        "date": stol[:10],
        "time": stol[11:16],
        "updated_time": (record.get("CHPTOL") or "")[11:16],
        "direction": "departure" if record.get("CHAORD") == "D" else "arrival",
        "city": record.get("CHLOC1T") or "",
        "city_he": record.get("CHLOC1TH") or "",
        "country": record.get("CHLOCCT") or "",
        "country_he": record.get("CHLOC1CH") or "",
        "airport": record.get("CHLOC1") or "",
        "terminal": record.get("CHTERM"),
        "gate": record.get("CHCINT"),
        "checkin_zone": record.get("CHCKZN"),
        "status": record.get("CHRMINE") or "",
        "status_he": record.get("CHRMINH") or "",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: query_flights.py [--departures|--arrivals] [--airline CODE] "
              "[--destination CODE] [--flight LY001] [--status DELAYED] "
              "[--search TEXT]")
        sys.exit(0)

    args = parse_args(sys.argv)
    records, _ = fetch(args)
    print(json.dumps([clean(r) for r in records], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
