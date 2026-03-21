#!/usr/bin/env python3
"""Query historical flight data from the local SQLite database.

Provides on-time performance, delay stats, and cancellation rates
by airline, route, or time period.

Usage:
    query_history.py --ontime                    # All airlines, last 30 days
    query_history.py --ontime --airline LY        # El Al on-time performance
    query_history.py --delays --route JFK         # Delay stats for JFK route
    query_history.py --cancellations              # Cancellation rates by route
    query_history.py --coverage                   # Show data coverage
    query_history.py --airports London            # Find airports for a city
    query_history.py --airline-lookup "El Al"     # Find airline IATA code
    query_history.py --json                       # JSON output
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".natbag" / "flights.db"


def get_conn():
    if not DB_PATH.exists():
        print("No historical database found. Run snapshot.py first.", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def parse_args(argv):
    args = {"command": None, "airline": None, "route": None, "days": 30,
            "direction": None, "json": False, "query": None}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--ontime", "--delays", "--cancellations", "--coverage"):
            args["command"] = a[2:]
        elif a == "--airports" and i + 1 < len(argv):
            i += 1
            args["command"] = "airports"
            args["query"] = argv[i]
        elif a == "--airline-lookup" and i + 1 < len(argv):
            i += 1
            args["command"] = "airline_lookup"
            args["query"] = argv[i]
        elif a == "--airline" and i + 1 < len(argv):
            i += 1
            args["airline"] = argv[i].upper()
        elif a == "--route" and i + 1 < len(argv):
            i += 1
            args["route"] = argv[i].upper()
        elif a == "--days" and i + 1 < len(argv):
            i += 1
            args["days"] = int(argv[i])
        elif a == "--departures":
            args["direction"] = "D"
        elif a == "--arrivals":
            args["direction"] = "A"
        elif a == "--json":
            args["json"] = True
        i += 1
    return args


def cmd_coverage(conn, args):
    row = conn.execute("""
        SELECT MIN(chstol), MAX(chstol), COUNT(*),
               COUNT(DISTINCT date(chstol)),
               COUNT(DISTINCT choper),
               COUNT(DISTINCT chloc1)
        FROM flights
    """).fetchone()
    result = {
        "earliest": row[0], "latest": row[1], "total_flights": row[2],
        "days_covered": row[3], "airlines": row[4], "destinations": row[5]
    }
    if args["json"]:
        print(json.dumps(result, indent=2))
    else:
        print(f"Historical Data Coverage")
        print(f"  Period:       {row[0][:10]} to {row[1][:10]}")
        print(f"  Days covered: {row[3]}")
        print(f"  Total flights: {row[2]}")
        print(f"  Airlines:     {row[4]}")
        print(f"  Destinations: {row[5]}")


def cmd_ontime(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')"]
    params = []
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    if args["direction"]:
        where.append("f.chaord = ?")
        params.append(args["direction"])
    where_sql = " AND ".join(where)

    rows = conn.execute(f"""
        SELECT f.choper, COALESCE(a.name, f.choperd) as airline_name,
            COUNT(*) as total,
            SUM(CASE WHEN f.chrmine IN ('ON TIME','EARLY','DEPARTED','LANDED','FINAL') THEN 1 ELSE 0 END) as on_time,
            SUM(CASE WHEN f.chrmine = 'DELAYED' THEN 1 ELSE 0 END) as delayed,
            SUM(CASE WHEN f.chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled
        FROM flights f
        LEFT JOIN airlines a ON f.choper = a.iata_code
        WHERE {where_sql}
        GROUP BY f.choper
        ORDER BY total DESC
    """, params).fetchall()

    if args["json"]:
        print(json.dumps([{"code": r[0], "airline": r[1], "total": r[2],
                           "on_time": r[3], "delayed": r[4], "canceled": r[5],
                           "on_time_pct": round(100 * r[3] / r[2], 1) if r[2] else 0}
                          for r in rows], indent=2))
    else:
        print(f"On-Time Performance — Last {args['days']} Days\n")
        print(f"{'Code':<5} {'Airline':<25} {'Total':>5} {'On Time':>8} {'Delayed':>8} {'Canceled':>9}")
        print("-" * 65)
        for r in rows:
            pct = f"{100*r[3]/r[2]:.0f}%" if r[2] else "—"
            print(f"{r[0]:<5} {(r[1] or '')[:25]:<25} {r[2]:>5} {r[3]:>5} ({pct:>3}) {r[4]:>7} {r[5]:>8}")


def cmd_delays(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')"]
    params = []
    if args["route"]:
        where.append("f.chloc1 = ?")
        params.append(args["route"])
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    where_sql = " AND ".join(where)

    rows = conn.execute(f"""
        SELECT f.chloc1, f.chloc1t,
            COUNT(*) as total,
            SUM(CASE WHEN f.chrmine = 'DELAYED' THEN 1 ELSE 0 END) as delayed,
            ROUND(AVG(CASE
                WHEN f.chptol > f.chstol
                THEN (julianday(f.chptol) - julianday(f.chstol)) * 24 * 60
            END), 0) as avg_delay_min
        FROM flights f
        WHERE {where_sql}
        GROUP BY f.chloc1
        HAVING delayed > 0
        ORDER BY avg_delay_min DESC
    """, params).fetchall()

    if args["json"]:
        print(json.dumps([{"code": r[0], "city": r[1], "total": r[2],
                           "delayed": r[3], "avg_delay_min": r[4]}
                          for r in rows], indent=2))
    else:
        print(f"Delay Analysis — Last {args['days']} Days\n")
        print(f"{'Route':<6} {'City':<16} {'Total':>5} {'Delayed':>8} {'Avg Delay':>10}")
        print("-" * 50)
        for r in rows:
            avg = f"{int(r[4])}m" if r[4] else "—"
            print(f"{r[0]:<6} {(r[1] or '')[:16]:<16} {r[2]:>5} {r[3]:>8} {avg:>10}")


def cmd_cancellations(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')"]
    params = []
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    where_sql = " AND ".join(where)

    rows = conn.execute(f"""
        SELECT f.chloc1, f.chloc1t,
            COUNT(*) as total,
            SUM(CASE WHEN f.chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled,
            ROUND(100.0 * SUM(CASE WHEN f.chrmine = 'CANCELED' THEN 1 ELSE 0 END) / COUNT(*), 1) as cancel_pct
        FROM flights f
        WHERE {where_sql}
        GROUP BY f.chloc1
        HAVING total >= 2
        ORDER BY cancel_pct DESC
    """, params).fetchall()

    if args["json"]:
        print(json.dumps([{"code": r[0], "city": r[1], "total": r[2],
                           "canceled": r[3], "cancel_pct": r[4]}
                          for r in rows], indent=2))
    else:
        print(f"Cancellation Rates — Last {args['days']} Days\n")
        print(f"{'Route':<6} {'City':<16} {'Total':>5} {'Canceled':>9} {'Rate':>6}")
        print("-" * 45)
        for r in rows:
            print(f"{r[0]:<6} {(r[1] or '')[:16]:<16} {r[2]:>5} {r[3]:>9} {r[4]:>5}%")


def cmd_airports(conn, args):
    rows = conn.execute(
        "SELECT iata_code, name, city, country, lat, lon FROM airports WHERE UPPER(city) LIKE ?",
        (f"%{args['query'].upper()}%",)
    ).fetchall()

    if args["json"]:
        print(json.dumps([{"code": r[0], "name": r[1], "city": r[2],
                           "country": r[3], "lat": r[4], "lon": r[5]}
                          for r in rows], indent=2))
    else:
        if not rows:
            print(f"No airports found for '{args['query']}'")
            return
        print(f"Airports matching '{args['query']}':\n")
        for r in rows:
            print(f"  {r[0]}  {r[1][:50]:<50}  {r[2]}, {r[3]}")


def cmd_airline_lookup(conn, args):
    rows = conn.execute(
        "SELECT iata_code, name, country FROM airlines WHERE UPPER(name) LIKE ?",
        (f"%{args['query'].upper()}%",)
    ).fetchall()

    if args["json"]:
        print(json.dumps([{"code": r[0], "name": r[1], "country": r[2]}
                          for r in rows], indent=2))
    else:
        if not rows:
            print(f"No airlines found for '{args['query']}'")
            return
        print(f"Airlines matching '{args['query']}':\n")
        for r in rows:
            print(f"  {r[0]}  {r[1]:<40}  {r[2]}")


def main():
    if len(sys.argv) < 2:
        print("Usage: query_history.py [--ontime|--delays|--cancellations|--coverage]")
        print("       [--airports CITY] [--airline-lookup NAME]")
        print("       [--airline CODE] [--route CODE] [--days N] [--json]")
        sys.exit(0)

    args = parse_args(sys.argv)
    if not args["command"]:
        print("Specify a command: --ontime, --delays, --cancellations, --coverage, --airports, --airline-lookup")
        sys.exit(1)

    conn = get_conn()
    try:
        {"coverage": cmd_coverage, "ontime": cmd_ontime, "delays": cmd_delays,
         "cancellations": cmd_cancellations, "airports": cmd_airports,
         "airline_lookup": cmd_airline_lookup}[args["command"]](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
