"""Standalone: (re)compute pre-event setup signals and re-export the app JSON.

Run after a collection if you only want to refresh the setup layer without re-collecting:

    python3 pipeline/enrich_setups.py

Setups flag VSCO/VSXY-style high-asymmetry catalysts (short interest + activist +
analyst trend + catalyst type → 0–100 asymmetry score). See analysis/setup_signals.py.
"""
from __future__ import annotations

import db
import export_for_app
from analysis import setup_signals, earnings_preview


def main() -> None:
    conn = db.connect()
    n = setup_signals.enrich_and_save(conn)
    print(f"{n} pre-event setup records written.")
    n_prev = earnings_preview.enrich_and_save(conn)
    print(f"{n_prev} earnings-preview annotations written.")

    # Show the strongest setups for quick inspection.
    rows = conn.execute(
        """SELECT s.score, s.label, s.ticker, e.event_date, e.title
           FROM event_setups s JOIN events e ON e.uid = s.event_uid
           ORDER BY s.score DESC, e.event_date LIMIT 20""").fetchall()
    if rows:
        print("\nTop setups:")
        for r in rows:
            print(f"  [{r['score']:3}] {r['label']:20} {r['ticker']:5} "
                  f"{r['event_date']}  {r['title'][:60]}")
    conn.close()
    export_for_app.main()


if __name__ == "__main__":
    main()
