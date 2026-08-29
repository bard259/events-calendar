"""Daily job: refresh earnings data, run decision agent, then run critic agent."""
from __future__ import annotations

import argparse
from datetime import date, timedelta

import db
import export_agent_reports
import export_for_app
from decision_agents import collect_price_snapshots, run_critic_agent, run_decision_agent
from scrape_earnings_previews import run as run_earnings_scrape


def main() -> None:
    ap = argparse.ArgumentParser(description="Run daily earnings decision + critic agents.")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--scrape-days", type=int, default=60)
    ap.add_argument("--decision-horizon-days", type=int, default=7)
    ap.add_argument("--critic-lookback-days", type=int, default=21)
    ap.add_argument("--skip-scrape", action="store_true")
    args = ap.parse_args()

    start = args.date
    end = (date.fromisoformat(args.date) + timedelta(days=args.scrape_days - 1)).isoformat()

    if not args.skip_scrape:
        run_earnings_scrape(start, end)

    decision = run_decision_agent(args.date, args.decision_horizon_days)
    snapshots = collect_price_snapshots(args.date, decision_run_id=decision["run_id"])
    critic = run_critic_agent(args.date, args.critic_lookback_days)

    # Continuously-learning earnings-alpha: refresh predictions, evaluate realized
    # outcomes from the accumulated price snapshots, and self-tune the model.
    from analysis import earnings_alpha
    alpha_conn = db.connect()
    n_alpha = earnings_alpha.enrich_and_save(alpha_conn)
    learn = earnings_alpha.run_learning(alpha_conn)
    alpha_conn.close()

    export_agent_reports.main()
    export_for_app.main()  # refresh app data so look-ahead + pop show on cards
    try:
        import graph_build
        graph_build.build()  # refresh the company-relationship knowledge graph
    except Exception as e:
        print(f"graph_build skipped: {e}")

    print("Daily agents complete.")
    print(f"  Decision report: {decision['report_path']}")
    print(f"  Critic report:   {critic['report_path']}")
    print(f"  Price snapshots: {snapshots['snapshots']}")
    if snapshots["errors"]:
        print("  Snapshot issues:")
        for err in snapshots["errors"]:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
