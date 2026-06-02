"""Central configuration for the June-2026 events pipeline."""
from __future__ import annotations

import os
from pathlib import Path

# --- Collection window -------------------------------------------------------
TARGET_MONTH = os.environ.get("EVENTS_MONTH", "2026-06")  # YYYY-MM (single-month runs)
MONTH_START = f"{TARGET_MONTH}-01"
MONTH_END = f"{TARGET_MONTH}-30"  # June has 30 days

# Full multi-month range the calendar now spans (used by daily_update.py).
RANGE_START = os.environ.get("EVENTS_RANGE_START", "2026-06-01")
RANGE_END = os.environ.get("EVENTS_RANGE_END", "2026-12-31")

# --- Paths -------------------------------------------------------------------
PIPELINE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PIPELINE_DIR.parent
DB_PATH = PIPELINE_DIR / "events.db"
APP_DATA_PATH = ROOT_DIR / "app" / "assets" / "events.json"

# --- HTTP politeness ---------------------------------------------------------
# Many APIs (notably SEC EDGAR) require a descriptive User-Agent with contact info
# as part of their Terms of Service / fair-access policy.
CONTACT_EMAIL = os.environ.get("EVENTS_CONTACT", "events-pipeline@example.com")
USER_AGENT = f"EventsPipeline/1.0 ({CONTACT_EMAIL})"
HTTP_TIMEOUT = 15  # seconds
DEFAULT_RATE_DELAY = 0.5  # seconds between requests to the same host (politeness)

# --- Category registry (stable IDs) -----------------------------------------
CATEGORIES = {
    1: "Macro & Economic Data",
    2: "Central Bank & Policy",
    3: "Corporate Financial Events",
    4: "Corporate Strategic Catalysts",
    5: "Operational Milestones",
    6: "Regulatory, Legal & Approval Events",
    7: "Industry & Supply-Demand Events",
    8: "Geopolitical & Security Events",
    9: "AI & Compute Ecosystem",
}

# Rough expected event counts per category for the storage *estimate*.
# These are planning numbers, not collection results.
EXPECTED_COUNTS = {
    1: 30,   # economic releases over the month
    2: 12,   # policy meetings / minutes / refunding
    3: 120,  # earnings + dividends + buybacks
    4: 25,   # product launches / M&A / investor days
    5: 40,   # launches + factory/delivery milestones
    6: 35,   # PDUFA + rulings + approvals
    7: 30,   # OPEC + conferences + pricing
    8: 25,   # elections + summits + tariff deadlines
    9: 20,   # AI chip/model launches + data-center build-outs + supply deals
}
