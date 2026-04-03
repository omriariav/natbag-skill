#!/usr/bin/env python3
"""Query live Ben Gurion Airport flights. Returns clean JSON.

Usage:
    query_flights.py --departures --upcoming --max 3
    query_flights.py --arrivals --upcoming --max 1
    query_flights.py --airline LY --upcoming
    query_flights.py --destination JFK
    query_flights.py --flight LY001
    query_flights.py --status DELAYED
    query_flights.py --search "London"

Flags:
    --departures/--arrivals  Filter by direction
    --airline CODE|NAME      Filter by airline (resolves names via local DB)
    --destination CODE       Filter by airport code
    --flight LY001           Look up specific flight
    --status STATUS          Filter by exact status
    --search TEXT            Full-text search
    --date YYYY-MM-DD        Filter to specific date (client-side). Without this,
                             the API returns a ~3-day rolling window!
    --upcoming               Exclude LANDED/DEPARTED/CANCELED (API-side filter)
                             Ignored if --status is also set (explicit status takes precedence)
    --max N                  Limit output to first N results
"""

import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import URLError

USER_AGENT = "datagov-external-client"

DB_PATH = Path.home() / ".natbag" / "flights.db"

API_BASE = (
    "https://data.gov.il/api/3/action/datastore_search"
    "?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5"
)


def parse_args(argv):
    args = {"filters": {}, "sort": "CHSTOL asc", "limit": 200, "search": None, "upcoming": False, "max_results": None, "date": None}
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
        elif a == "--date" and i + 1 < len(argv):
            i += 1
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", argv[i]):
                print(f"Invalid --date format: {argv[i]} (expected YYYY-MM-DD)", file=sys.stderr)
                sys.exit(1)
            args["date"] = argv[i]
        elif a == "--upcoming":
            args["upcoming"] = True
        elif a == "--max" and i + 1 < len(argv):
            i += 1
            try:
                args["max_results"] = int(argv[i])
            except ValueError:
                print(f"Invalid --max value: {argv[i]}", file=sys.stderr)
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


def _build_base_url(args):
    """Build the API URL without offset/limit (shared by fetch and fetch_all)."""
    url = f"{API_BASE}&sort={quote(args['sort'])}"
    if args["filters"]:
        url += f"&filters={quote(json.dumps(args['filters']))}"
    if args["search"] and args["search"].strip():
        words = args["search"].strip().split()
        sanitized = [re.sub(r"[^a-zA-Z0-9\u0590-\u05FF]", "", w) for w in words]
        sanitized = [w for w in sanitized if w]
        if sanitized:
            term = " & ".join(f"{w}:*" for w in sanitized)
            url += f"&q={quote(term)}&plain=false"
    return url


def _fetch_page(url):
    """Fetch a single API page and return (records, total)."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=30) as resp:
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


def fetch(args):
    url = _build_base_url(args) + f"&limit={args['limit']}"
    return _fetch_page(url)


def fetch_all(args):
    """Fetch all pages from the API. Used when --date requires complete results."""
    page_size = 200
    base_url = _build_base_url(args)
    records, total = _fetch_page(base_url + f"&limit={page_size}&offset=0")
    all_records = list(records)
    while len(all_records) < total:
        offset = len(all_records)
        page, _ = _fetch_page(base_url + f"&limit={page_size}&offset={offset}")
        if not page:
            break
        all_records.extend(page)
    return all_records, total


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
              "[--search TEXT] [--date YYYY-MM-DD] [--upcoming] [--max N]")
        sys.exit(0)

    args = parse_args(sys.argv)

    # --upcoming: use API-side IN filter to exclude past/canceled flights
    if args["upcoming"] and "CHRMINE" not in args["filters"]:
        args["filters"]["CHRMINE"] = ["ON TIME", "DELAYED", "EARLY", "FINAL", "NOT FINAL"]

    # When --date is set, fetch all pages to avoid truncation, then filter client-side
    if args["date"]:
        records, _ = fetch_all(args)
        results = [clean(r) for r in records]
        results = [r for r in results if r["date"] == args["date"]]
    else:
        records, _ = fetch(args)
        results = [clean(r) for r in records]

    if args["max_results"]:
        results = results[:args["max_results"]]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
