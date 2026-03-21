#!/usr/bin/env python3
"""Snapshot Ben Gurion Airport flight data into local SQLite database.

Fetches current flights from data.gov.il and upserts into ~/.natbag/flights.db.
On first run, imports airlines/airports reference data from the shipped iata.db.
Respects ~/.natbag/config.json for daily_snapshot opt-out and dedup.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

NATBAG_DIR = Path.home() / ".natbag"
DB_PATH = NATBAG_DIR / "flights.db"
CONFIG_PATH = NATBAG_DIR / "config.json"
SCRIPT_DIR = Path(__file__).resolve().parent
IATA_DB_PATH = SCRIPT_DIR.parent / "data" / "iata.db"

API_URL = (
    "https://data.gov.il/api/3/action/datastore_search"
    "?resource_id=e83f763b-b7d7-479e-b172-ae981ddc6de5"
    "&limit=500"
)

FIELDS = [
    "choper", "chfltn", "choperd", "chstol", "chptol", "chaord",
    "chloc1", "chloc1t", "chloc1th", "chlocct", "chloc1ch",
    "chterm", "chcint", "chckzn", "chrmine", "chrminh",
]


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"daily_snapshot": True, "last_snapshot": None}


def save_config(config):
    NATBAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def should_run(config, force=False):
    if force:
        return True
    if not config.get("daily_snapshot", True):
        return False
    last = config.get("last_snapshot")
    if last:
        last_date = datetime.fromisoformat(last).date()
        if last_date == datetime.now(timezone.utc).date():
            return False
    return True


def init_db(conn):
    """Create all tables and indexes."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_key TEXT UNIQUE,
            choper TEXT, chfltn TEXT, choperd TEXT,
            chstol TEXT, chptol TEXT, chaord TEXT,
            chloc1 TEXT, chloc1t TEXT, chloc1th TEXT,
            chlocct TEXT, chloc1ch TEXT,
            chterm INTEGER, chcint TEXT, chckzn TEXT,
            chrmine TEXT, chrminh TEXT,
            snapshot_time TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flights_chstol ON flights(chstol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flights_chaord ON flights(chaord)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_flights_choper ON flights(choper)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS airlines (
            iata_code TEXT PRIMARY KEY,
            name TEXT,
            country TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS airports (
            iata_code TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            country TEXT,
            lat REAL,
            lon REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_airports_city ON airports(city)")
    conn.commit()


def import_iata_data(conn):
    """Import airlines/airports from the shipped iata.db into the user's DB."""
    if not IATA_DB_PATH.exists():
        print(f"  Warning: {IATA_DB_PATH} not found, skipping IATA import", file=sys.stderr)
        return

    airlines_count = conn.execute("SELECT COUNT(*) FROM airlines").fetchone()[0]
    airports_count = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
    if airlines_count > 0 and airports_count > 0:
        return

    print("Importing IATA reference data from shipped database...")
    src = sqlite3.connect(str(IATA_DB_PATH))
    try:
        for row in src.execute("SELECT iata_code, name, country FROM airlines"):
            conn.execute("INSERT OR IGNORE INTO airlines VALUES (?, ?, ?)", row)
        for row in src.execute("SELECT iata_code, name, city, country, lat, lon FROM airports"):
            conn.execute("INSERT OR IGNORE INTO airports VALUES (?, ?, ?, ?, ?, ?)", row)
        conn.commit()
        ac = conn.execute("SELECT COUNT(*) FROM airlines").fetchone()[0]
        ap = conn.execute("SELECT COUNT(*) FROM airports").fetchone()[0]
        print(f"  Imported {ac} airlines, {ap} airports")
    finally:
        src.close()


def fetch_flights():
    with urlopen(API_URL, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("success"):
        raise RuntimeError(f"API returned success=false: {data}")
    return data["result"]["records"]


def upsert_flights(conn, records):
    now = datetime.now(timezone.utc).isoformat()
    new_count = 0
    updated_count = 0

    for rec in records:
        flight_key = f"{rec.get('CHOPER', '')}-{rec.get('CHFLTN', '')}-{rec.get('CHSTOL', '')}"
        values = {f: rec.get(f.upper(), "") for f in FIELDS}
        values["flight_key"] = flight_key

        existing = conn.execute(
            "SELECT chrmine, chptol FROM flights WHERE flight_key = ?",
            (flight_key,)
        ).fetchone()

        if existing is None:
            values["snapshot_time"] = now
            values["updated_at"] = now
            cols = ", ".join(values.keys())
            placeholders = ", ".join(":" + k for k in values.keys())
            conn.execute(f"INSERT INTO flights ({cols}) VALUES ({placeholders})", values)
            new_count += 1
        else:
            old_status, old_ptol = existing
            new_status = values.get("chrmine", "")
            new_ptol = values.get("chptol", "")
            if new_status != old_status or new_ptol != old_ptol:
                conn.execute("""
                    UPDATE flights SET
                        chrmine = :chrmine, chrminh = :chrminh,
                        chptol = :chptol, chcint = :chcint,
                        chckzn = :chckzn, chterm = :chterm,
                        updated_at = :updated_at
                    WHERE flight_key = :flight_key
                """, {
                    "chrmine": new_status,
                    "chrminh": values.get("chrminh", ""),
                    "chptol": new_ptol,
                    "chcint": values.get("chcint", ""),
                    "chckzn": values.get("chckzn", ""),
                    "chterm": values.get("chterm", ""),
                    "updated_at": now,
                    "flight_key": flight_key,
                })
                updated_count += 1

    conn.commit()
    return new_count, updated_count


def main():
    force = "--force" in sys.argv
    config = load_config()

    if not should_run(config, force):
        if not config.get("daily_snapshot", True):
            print("Snapshot disabled in config. Use --force to override.")
        else:
            print("Already ran today. Use --force to run again.")
        return

    NATBAG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        init_db(conn)
        import_iata_data(conn)

        records = fetch_flights()
        new_count, updated_count = upsert_flights(conn, records)
        total = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
        print(f"Snapshot: {new_count} new, {updated_count} updated, {total} total flights in DB")
    except (URLError, RuntimeError) as e:
        print(f"Error fetching flights: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    config["last_snapshot"] = datetime.now(timezone.utc).isoformat()
    save_config(config)


if __name__ == "__main__":
    main()
