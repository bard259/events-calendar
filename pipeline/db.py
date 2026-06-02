"""SQLite persistence layer + storage measurement helpers."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH, CATEGORIES
from models import Event, CollectorReport

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT UNIQUE NOT NULL,
    category_id   INTEGER NOT NULL,
    category      TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    event_date    TEXT NOT NULL,
    event_datetime TEXT,
    entity        TEXT,
    importance    TEXT,
    source        TEXT NOT NULL,
    source_type   TEXT NOT NULL,
    source_url    TEXT,
    pub_date      TEXT,
    pub_source    TEXT,
    raw_json      TEXT,
    collected_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS event_stock_impacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_uid   TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    direction   INTEGER NOT NULL,   -- +1 positive, -1 negative, 0 neutral/watch
    confidence  TEXT NOT NULL,      -- "high" | "medium" | "low"
    reason      TEXT NOT NULL,
    sector      TEXT,
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_cat  ON events(category_id);

CREATE TABLE IF NOT EXISTS collection_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    month          TEXT,
    started_at     TEXT,
    finished_at    TEXT,
    total_events   INTEGER,
    new_events     INTEGER,
    db_bytes_before INTEGER,
    db_bytes_after  INTEGER
);

CREATE TABLE IF NOT EXISTS collector_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER,
    collector       TEXT,
    category_id     INTEGER,
    source_type     TEXT,
    status          TEXT,
    events_collected INTEGER,
    http_requests   INTEGER,
    rate_limited    INTEGER,
    tos_issues      TEXT,
    errors          TEXT,
    notes           TEXT,
    duration_s      REAL,
    FOREIGN KEY(run_id) REFERENCES collection_runs(id)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)
    conn.commit()


def db_size_bytes() -> int:
    return DB_PATH.stat().st_size if DB_PATH.exists() else 0


def upsert_events(conn: sqlite3.Connection, events: list[Event]) -> int:
    """Insert events, ignoring duplicates by uid. Returns count of NEW rows."""
    before = conn.total_changes
    rows = []
    for ev in events:
        r = ev.to_row()
        r["category"] = CATEGORIES.get(ev.category_id, "Unknown")
        rows.append(r)
    conn.executemany(
        """
        INSERT OR IGNORE INTO events
          (uid, category_id, category, title, description, event_date, event_datetime,
           entity, importance, source, source_type, source_url, pub_date, pub_source,
           raw_json, collected_at)
        VALUES
          (:uid, :category_id, :category, :title, :description, :event_date, :event_datetime,
           :entity, :importance, :source, :source_type, :source_url, :pub_date, :pub_source,
           :raw_json, :collected_at)
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def start_run(conn: sqlite3.Connection, month: str, db_bytes_before: int) -> int:
    cur = conn.execute(
        "INSERT INTO collection_runs (month, started_at, db_bytes_before) VALUES (?,?,?)",
        (month, datetime.now(timezone.utc).isoformat(), db_bytes_before),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id, total_events, new_events, db_bytes_after):
    conn.execute(
        """UPDATE collection_runs
           SET finished_at=?, total_events=?, new_events=?, db_bytes_after=?
           WHERE id=?""",
        (datetime.now(timezone.utc).isoformat(), total_events, new_events,
         db_bytes_after, run_id),
    )
    conn.commit()


def save_report(conn, run_id: int, rep: CollectorReport):
    conn.execute(
        """INSERT INTO collector_reports
           (run_id, collector, category_id, source_type, status, events_collected,
            http_requests, rate_limited, tos_issues, errors, notes, duration_s)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, rep.collector, rep.category_id, rep.source_type, rep.status,
         rep.events_collected, rep.http_requests, int(rep.rate_limited),
         json.dumps(rep.tos_issues), json.dumps(rep.errors), json.dumps(rep.notes),
         rep.duration_s),
    )
    conn.commit()


def save_stock_impacts(conn, impacts: list[dict]):
    """Upsert stock impact rows. Each dict: {event_uid, ticker, direction, confidence, reason, sector}."""
    conn.executemany(
        """INSERT OR REPLACE INTO event_stock_impacts
           (event_uid, ticker, direction, confidence, reason, sector)
           VALUES (:event_uid, :ticker, :direction, :confidence, :reason, :sector)""",
        impacts,
    )
    conn.commit()


def storage_breakdown(conn) -> dict:
    """Per-category row counts + on-disk size accounting."""
    counts = {
        row["category_id"]: row["n"]
        for row in conn.execute(
            "SELECT category_id, COUNT(*) n FROM events GROUP BY category_id"
        )
    }
    total = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
    # Logical payload size = sum of stored text lengths (approx bytes of useful data)
    payload = conn.execute(
        """SELECT COALESCE(SUM(
              LENGTH(title)+LENGTH(COALESCE(description,''))+LENGTH(COALESCE(raw_json,''))
              +LENGTH(COALESCE(entity,''))+LENGTH(event_date)+LENGTH(uid)
           ),0) b FROM events"""
    ).fetchone()["b"]
    return {
        "total_events": total,
        "counts_by_category": counts,
        "payload_bytes": payload,
        "file_bytes": db_size_bytes(),
    }
