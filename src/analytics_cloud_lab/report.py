"""Daily experiment report.

Online (reads ANALYTICS.VARIANT_SUMMARY in Snowflake):
    python -m analytics_cloud_lab.report --all --out reports
Offline (computes from local CSVs, no Snowflake account needed):
    python -m analytics_cloud_lab.report --all --offline --data-dir data
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

from .experiment import ExperimentReport

log = logging.getLogger(__name__)

SUMMARY_SQL = """
SELECT experience_id, variant_id, sessions, conversions, total_revenue
FROM MAC_LAB.ANALYTICS.VARIANT_SUMMARY
ORDER BY experience_id, variant_id
"""


def fetch_rows_online() -> dict[str, list[dict]]:
    from .config import SnowflakeSettings
    from .snowflake_client import SnowflakeClient

    by_exp: dict[str, list[dict]] = {}
    with SnowflakeClient(SnowflakeSettings.from_env()) as sf:
        for row in sf.query(SUMMARY_SQL):
            by_exp.setdefault(row["EXPERIENCE_ID"], []).append(row)
    return by_exp


def build_report(by_exp: dict[str, list[dict]], experiences: list[str] | None = None) -> str:
    wanted = experiences or sorted(by_exp)
    parts = [f"# Experiment report — {date.today().isoformat()}", ""]
    for exp_id in wanted:
        if exp_id not in by_exp:
            log.warning("No data for %s", exp_id)
            continue
        parts.append(ExperimentReport.from_rows(exp_id, by_exp[exp_id]).to_markdown())
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Experiment lift report")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--experience", action="append", help="Experience id, e.g. EXP-001 (repeatable)")
    target.add_argument("--all", action="store_true", help="Report on every experience")
    parser.add_argument("--offline", action="store_true", help="Use local CSVs instead of Snowflake")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out", type=Path, help="Folder to write the markdown report into")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.offline:
        from .local_metrics import variant_summary

        by_exp = variant_summary(args.data_dir)
    else:
        by_exp = fetch_rows_online()

    text = build_report(by_exp, None if args.all else args.experience)
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / f"experiment_report_{date.today().isoformat()}.md"
        path.write_text(text, encoding="utf-8")
        log.info("Wrote %s", path)


if __name__ == "__main__":
    main()
