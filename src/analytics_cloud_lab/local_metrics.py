"""Compute variant summaries from the local CSV files (no Snowflake needed).

Mirrors the logic in sql/04_analysis.sql so you can check your SQL results:
  1. keep the FIRST offer row per (session, experience)  -> QUALIFY ROW_NUMBER() = 1
  2. a session converts if it has an order at/after that first qualification
  3. aggregate per (experience, variant)
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


def variant_summary(data_dir: str | Path = "data") -> dict[str, list[dict]]:
    data = Path(data_dir)
    first: dict[tuple[str, str], dict] = {}
    with open(data / "offers.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["session_id"], row["experience_id"])
            if key not in first or row["first_qualified_ts"] < first[key]["first_qualified_ts"]:
                first[key] = row

    orders: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with open(data / "conversions.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            orders[row["session_id"]].append((row["conversion_ts"], float(row["revenue"])))

    agg: dict[tuple[str, str, str], dict] = {}
    for (session_id, exp_id), offer in first.items():
        after = [rev for ts, rev in orders.get(session_id, []) if ts >= offer["first_qualified_ts"]]
        key = (offer["client_id"], exp_id, offer["variant_id"])
        a = agg.setdefault(key, {"client_id": key[0], "experience_id": exp_id, "variant_id": key[2],
                                 "sessions": 0, "conversions": 0, "total_revenue": 0.0})
        a["sessions"] += 1
        a["conversions"] += 1 if after else 0
        a["total_revenue"] += sum(after)

    by_exp: dict[str, list[dict]] = defaultdict(list)
    for a in sorted(agg.values(), key=lambda r: (r["experience_id"], r["variant_id"])):
        a["total_revenue"] = round(a["total_revenue"], 2)
        by_exp[a["experience_id"]].append(a)
    return dict(by_exp)
