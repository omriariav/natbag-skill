#!/usr/bin/env python3
"""Query historical flight data from the local SQLite database.

Returns JSON for all commands. Claude handles presentation.

Usage:
    query_history.py --ontime                    # All airlines, last 30 days
    query_history.py --ontime --airline LY        # El Al on-time performance
    query_history.py --delays --route JFK         # Delay stats for JFK route
    query_history.py --cancellations              # Cancellation rates by route
    query_history.py --coverage                   # Show data coverage
    query_history.py --airports London            # Find airports for a city
    query_history.py --airline-lookup "El Al"     # Find airline IATA code
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".natbag" / "flights.db"


def get_conn():
    if not DB_PATH.exists():
        print(json.dumps({"error": "No historical database found. Run snapshot.py first."}))
        sys.exit(1)
    try:
        return sqlite3.connect(str(DB_PATH))
    except sqlite3.Error as e:
        print(json.dumps({"error": f"Database error: {e}"}))
        sys.exit(1)


def parse_args(argv):
    args = {"command": None, "airline": None, "route": None, "days": 30,
            "direction": None, "query": None}
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
            try:
                args["days"] = int(argv[i])
            except ValueError:
                print(json.dumps({"error": f"Invalid --days value: {argv[i]}"}))
                sys.exit(1)
        elif a == "--departures":
            args["direction"] = "D"
        elif a == "--arrivals":
            args["direction"] = "A"
        i += 1
    return args


def _direction_filter(args, where, params):
    if args["direction"]:
        where.append("f.chaord = ?")
        params.append(args["direction"])


def cmd_coverage(conn, args):
    row = conn.execute("""
        SELECT MIN(chstol), MAX(chstol), COUNT(*),
               COUNT(DISTINCT date(chstol)),
               COUNT(DISTINCT choper),
               COUNT(DISTINCT chloc1)
        FROM flights
    """).fetchone()
    if not row[0]:
        print(json.dumps({"error": "No flight data yet. Run snapshot.py first."}))
        return
    print(json.dumps({
        "earliest": row[0], "latest": row[1], "total_flights": row[2],
        "days_covered": row[3], "airlines": row[4], "destinations": row[5]
    }, indent=2))


def cmd_ontime(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')", "chstol <= datetime('now')"]
    params = []
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    _direction_filter(args, where, params)
    where_sql = " AND ".join(where)

    rows = conn.execute(f"""
        SELECT f.choper, COALESCE(a.name, f.choperd) as airline_name,
            COUNT(*) as total,
            SUM(CASE WHEN f.chrmine != 'CANCELED' AND (f.chptol <= f.chstol OR f.chptol IS NULL) THEN 1 ELSE 0 END) as on_time,
            SUM(CASE WHEN f.chrmine != 'CANCELED' AND f.chptol > f.chstol THEN 1 ELSE 0 END) as delayed,
            SUM(CASE WHEN f.chrmine = 'CANCELED' THEN 1 ELSE 0 END) as canceled
        FROM flights f
        LEFT JOIN airlines a ON f.choper = a.iata_code
        WHERE {where_sql}
        GROUP BY f.choper
        ORDER BY total DESC
    """, params).fetchall()

    print(json.dumps([{"code": r[0], "airline": r[1], "total": r[2],
                       "on_time": r[3], "delayed": r[4], "canceled": r[5],
                       "on_time_pct": round(100 * r[3] / r[2], 1) if r[2] else 0}
                      for r in rows], indent=2))


def cmd_delays(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')", "chstol <= datetime('now')"]
    params = []
    if args["route"]:
        where.append("f.chloc1 = ?")
        params.append(args["route"])
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    _direction_filter(args, where, params)
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

    print(json.dumps([{"code": r[0], "city": r[1], "total": r[2],
                       "delayed": r[3], "avg_delay_min": r[4]}
                      for r in rows], indent=2))


def cmd_cancellations(conn, args):
    where = [f"chstol >= date('now', '-{args['days']} days')", "chstol <= datetime('now')"]
    params = []
    if args["airline"]:
        where.append("f.choper = ?")
        params.append(args["airline"])
    _direction_filter(args, where, params)
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

    print(json.dumps([{"code": r[0], "city": r[1], "total": r[2],
                       "canceled": r[3], "cancel_pct": r[4]}
                      for r in rows], indent=2))


def cmd_airports(conn, args):
    rows = conn.execute(
        "SELECT iata_code, name, city, country FROM airports WHERE UPPER(city) LIKE ?",
        (f"%{args['query'].upper()}%",)
    ).fetchall()

    print(json.dumps([{"code": r[0], "name": r[1], "city": r[2], "country": r[3]}
                      for r in rows], indent=2))


def cmd_airline_lookup(conn, args):
    rows = conn.execute(
        "SELECT iata_code, name, country FROM airlines WHERE UPPER(name) LIKE ?",
        (f"%{args['query'].upper()}%",)
    ).fetchall()

    print(json.dumps([{"code": r[0], "name": r[1], "country": r[2]}
                      for r in rows], indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: query_history.py [--ontime|--delays|--cancellations|--coverage]")
        print("       [--airports CITY] [--airline-lookup NAME]")
        print("       [--airline CODE] [--route CODE] [--days N]")
        print("       [--departures|--arrivals]")
        sys.exit(0)

    args = parse_args(sys.argv)
    if not args["command"]:
        print(json.dumps({"error": "Specify a command: --ontime, --delays, --cancellations, --coverage, --airports, --airline-lookup"}))
        sys.exit(1)

    conn = get_conn()
    try:
        {"coverage": cmd_coverage, "ontime": cmd_ontime, "delays": cmd_delays,
         "cancellations": cmd_cancellations, "airports": cmd_airports,
         "airline_lookup": cmd_airline_lookup}[args["command"]](conn, args)
    except sqlite3.Error as e:
        print(json.dumps({"error": f"Database error: {e}"}))
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
