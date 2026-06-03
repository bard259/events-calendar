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
CREATE TABLE IF NOT EXISTS event_setups (
    event_uid     TEXT PRIMARY KEY,
    ticker        TEXT,
    score         INTEGER NOT NULL,   -- 0–100 asymmetry score
    label         TEXT,               -- "High-asymmetry setup" | "Notable setup" | "Low"
    short_pct     REAL,               -- short interest as % of float (nullable)
    short_as_of   TEXT,
    activists     TEXT,               -- json list
    analyst_trend TEXT,
    bias          TEXT,
    notes         TEXT,               -- json list
    sources       TEXT,               -- json list
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE TABLE IF NOT EXISTS event_previews (
    event_uid TEXT PRIMARY KEY,
    ticker    TEXT,
    payload   TEXT NOT NULL,   -- json: consensus bar, implied move, lean, bull/bear/watch, sources
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE TABLE IF NOT EXISTS earnings_scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    days_requested  INTEGER DEFAULT 0,
    days_ok         INTEGER DEFAULT 0,
    rows_seen       INTEGER DEFAULT 0,
    events_inserted INTEGER DEFAULT 0,
    errors          TEXT,
    notes           TEXT
);
CREATE TABLE IF NOT EXISTS earnings_scrape_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER,
    event_uid    TEXT,
    ticker       TEXT,
    company      TEXT,
    event_date   TEXT,
    source       TEXT,
    status       TEXT,
    raw_json     TEXT,
    collected_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES earnings_scrape_runs(id),
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE TABLE IF NOT EXISTS decision_agent_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    horizon_days    INTEGER NOT NULL,
    events_reviewed INTEGER DEFAULT 0,
    decisions_made  INTEGER DEFAULT 0,
    report_path     TEXT,
    memory_path     TEXT,
    notes           TEXT
);
CREATE TABLE IF NOT EXISTS investment_decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER,
    run_date        TEXT NOT NULL,
    event_uid       TEXT NOT NULL,
    event_date      TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    company         TEXT,
    action          TEXT NOT NULL,   -- BUY | WATCH | PASS | IGNORE
    confidence      TEXT,
    significance    TEXT,
    score           INTEGER,
    thesis          TEXT,
    risks           TEXT,
    memory_snapshot TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(run_date, event_uid),
    FOREIGN KEY(run_id) REFERENCES decision_agent_runs(id),
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE TABLE IF NOT EXISTS decision_critic_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date         TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    decisions_checked INTEGER DEFAULT 0,
    findings_count   INTEGER DEFAULT 0,
    missed_count     INTEGER DEFAULT 0,
    report_path      TEXT,
    memory_path      TEXT,
    notes            TEXT
);
CREATE TABLE IF NOT EXISTS decision_critic_findings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER,
    event_uid   TEXT,
    ticker      TEXT,
    finding_type TEXT NOT NULL,
    severity    TEXT,
    summary     TEXT,
    lesson      TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES decision_critic_runs(id),
    FOREIGN KEY(event_uid) REFERENCES events(uid)
);
CREATE TABLE IF NOT EXISTS investment_price_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id   INTEGER,
    ticker        TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    price         REAL,
    price_source  TEXT,
    raw_json      TEXT,
    created_at    TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES investment_decisions(id)
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_cat  ON events(category_id);
CREATE INDEX IF NOT EXISTS idx_earnings_scrape_items_run ON earnings_scrape_items(run_id);
CREATE INDEX IF NOT EXISTS idx_earnings_scrape_items_date ON earnings_scrape_items(event_date);
CREATE INDEX IF NOT EXISTS idx_investment_decisions_date ON investment_decisions(run_date);
CREATE INDEX IF NOT EXISTS idx_investment_decisions_event ON investment_decisions(event_uid);
CREATE INDEX IF NOT EXISTS idx_decision_critic_findings_run ON decision_critic_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_investment_price_snapshots_decision ON investment_price_snapshots(decision_id);

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


def save_setups(conn, setups: list[dict]):
    """Upsert pre-event setup rows (one per event_uid)."""
    conn.executemany(
        """INSERT OR REPLACE INTO event_setups
           (event_uid, ticker, score, label, short_pct, short_as_of,
            activists, analyst_trend, bias, notes, sources)
           VALUES (:event_uid, :ticker, :score, :label, :short_pct, :short_as_of,
            :activists, :analyst_trend, :bias, :notes, :sources)""",
        setups,
    )
    conn.commit()


def save_previews(conn, previews: list[dict]):
    """Upsert earnings-preview rows (one per event_uid). Each: {event_uid, ticker, payload}."""
    conn.executemany(
        """INSERT OR REPLACE INTO event_previews (event_uid, ticker, payload)
           VALUES (:event_uid, :ticker, :payload)""",
        previews,
    )
    conn.commit()


def start_earnings_scrape(conn, source: str, start_date: str, end_date: str,
                          days_requested: int) -> int:
    cur = conn.execute(
        """INSERT INTO earnings_scrape_runs
           (source, start_date, end_date, started_at, days_requested, errors, notes)
           VALUES (?,?,?,?,?,?,?)""",
        (source, start_date, end_date, datetime.now(timezone.utc).isoformat(),
         days_requested, "[]", "[]"),
    )
    conn.commit()
    return cur.lastrowid


def finish_earnings_scrape(conn, run_id: int, *, days_ok: int, rows_seen: int,
                           events_inserted: int, errors: list[str], notes: list[str]):
    conn.execute(
        """UPDATE earnings_scrape_runs
           SET finished_at=?, days_ok=?, rows_seen=?, events_inserted=?, errors=?, notes=?
           WHERE id=?""",
        (datetime.now(timezone.utc).isoformat(), days_ok, rows_seen, events_inserted,
         json.dumps(errors), json.dumps(notes), run_id),
    )
    conn.commit()


def save_earnings_scrape_items(conn, items: list[dict]):
    conn.executemany(
        """INSERT INTO earnings_scrape_items
           (run_id, event_uid, ticker, company, event_date, source, status, raw_json, collected_at)
           VALUES (:run_id, :event_uid, :ticker, :company, :event_date, :source, :status,
                   :raw_json, :collected_at)""",
        items,
    )
    conn.commit()


def start_decision_run(conn, run_date: str, horizon_days: int, memory_path: str) -> int:
    cur = conn.execute(
        """INSERT INTO decision_agent_runs
           (run_date, started_at, horizon_days, memory_path, notes)
           VALUES (?,?,?,?,?)""",
        (run_date, datetime.now(timezone.utc).isoformat(), horizon_days, memory_path, "[]"),
    )
    conn.commit()
    return cur.lastrowid


def finish_decision_run(conn, run_id: int, *, events_reviewed: int, decisions_made: int,
                        report_path: str, notes: list[str]):
    conn.execute(
        """UPDATE decision_agent_runs
           SET finished_at=?, events_reviewed=?, decisions_made=?, report_path=?, notes=?
           WHERE id=?""",
        (datetime.now(timezone.utc).isoformat(), events_reviewed, decisions_made,
         report_path, json.dumps(notes), run_id),
    )
    conn.commit()


def save_investment_decisions(conn, decisions: list[dict]):
    conn.executemany(
        """INSERT OR REPLACE INTO investment_decisions
           (run_id, run_date, event_uid, event_date, ticker, company, action,
            confidence, significance, score, thesis, risks, memory_snapshot, created_at)
           VALUES (:run_id, :run_date, :event_uid, :event_date, :ticker, :company, :action,
            :confidence, :significance, :score, :thesis, :risks, :memory_snapshot, :created_at)""",
        decisions,
    )
    conn.commit()


def start_critic_run(conn, run_date: str, memory_path: str) -> int:
    cur = conn.execute(
        """INSERT INTO decision_critic_runs
           (run_date, started_at, memory_path, notes)
           VALUES (?,?,?,?)""",
        (run_date, datetime.now(timezone.utc).isoformat(), memory_path, "[]"),
    )
    conn.commit()
    return cur.lastrowid


def finish_critic_run(conn, run_id: int, *, decisions_checked: int, findings_count: int,
                      missed_count: int, report_path: str, notes: list[str]):
    conn.execute(
        """UPDATE decision_critic_runs
           SET finished_at=?, decisions_checked=?, findings_count=?, missed_count=?,
               report_path=?, notes=?
           WHERE id=?""",
        (datetime.now(timezone.utc).isoformat(), decisions_checked, findings_count,
         missed_count, report_path, json.dumps(notes), run_id),
    )
    conn.commit()


def save_critic_findings(conn, findings: list[dict]):
    conn.executemany(
        """INSERT INTO decision_critic_findings
           (run_id, event_uid, ticker, finding_type, severity, summary, lesson, created_at)
           VALUES (:run_id, :event_uid, :ticker, :finding_type, :severity, :summary,
                   :lesson, :created_at)""",
        findings,
    )
    conn.commit()


def save_price_snapshots(conn, snapshots: list[dict]):
    conn.executemany(
        """INSERT INTO investment_price_snapshots
           (decision_id, ticker, snapshot_date, price, price_source, raw_json, created_at)
           VALUES (:decision_id, :ticker, :snapshot_date, :price, :price_source,
                   :raw_json, :created_at)""",
        snapshots,
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
