"""Generate a realistic, deterministic mock of personalization/experiment data.

This is a simplified teaching schema inspired by experience-data products
(sessions, page views, variant assignments, conversions). It is NOT Monetate's
actual data dictionary.

Run:
    python -m analytics_cloud_lab.generate_data --sessions 50000 --out data
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)
TS_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Experience:
    experience_id: str
    client_id: str
    name: str
    uplift: float  # absolute change in conversion probability for 'treatment'


CLIENTS = {"RETAILER_A": 0.030, "RETAILER_B": 0.025}  # client_id -> base conversion rate
EXPERIENCES = [
    Experience("EXP-001", "RETAILER_A", "Free shipping banner", 0.006),
    Experience("EXP-002", "RETAILER_A", "Recommended products carousel", 0.001),
    Experience("EXP-003", "RETAILER_B", "Exit-intent discount", 0.007),
]
DEVICES = (["desktop", "mobile", "tablet"], [0.45, 0.48, 0.07])
BROWSERS = (["chrome", "safari", "edge", "firefox"], [0.6, 0.28, 0.08, 0.04])
COUNTRIES = (["US", "GB", "DE", "PH", "AU"], [0.5, 0.2, 0.1, 0.1, 0.1])
QUALIFY_RATE = 0.7
REQUALIFY_RATE = 0.2  # duplicate assignment rows -> practice QUALIFY


def _catalog(rng: random.Random) -> list[dict]:
    return [{"sku": f"SKU-{1000 + i}", "price": round(rng.uniform(8, 120), 2)} for i in range(50)]


def generate(
    n_sessions: int = 50_000,
    out_dir: str | Path = "data",
    seed: int = 42,
    start: datetime = datetime(2026, 10, 1),
    days: int = 30,
) -> dict[str, int]:
    """Write CSV + JSONL files and return row counts per file."""
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    catalog = _catalog(rng)
    exps_by_client: dict[str, list[Experience]] = {}
    for e in EXPERIENCES:
        exps_by_client.setdefault(e.client_id, []).append(e)

    sessions, page_views, offers, conversions, events = [], [], [], [], []
    order_seq = 0

    for i in range(n_sessions):
        client_id = rng.choices(list(CLIENTS), weights=[0.6, 0.4])[0]
        session_id = f"S{i:07d}"
        visitor_id = f"V{rng.randint(1, max(1, n_sessions // 2)):07d}"
        t0 = start + timedelta(seconds=rng.randint(0, days * 86_400))
        sessions.append({
            "session_id": session_id, "visitor_id": visitor_id, "client_id": client_id,
            "session_start": t0.strftime(TS_FMT),
            "device_type": rng.choices(*DEVICES)[0],
            "browser": rng.choices(*BROWSERS)[0],
            "country": rng.choices(*COUNTRIES)[0],
        })

        # Variant assignment and conversion probability
        assignments: dict[str, str] = {}
        p = CLIENTS[client_id]
        for exp in exps_by_client[client_id]:
            if rng.random() < QUALIFY_RATE:
                variant = rng.choice(["control", "treatment"])
                assignments[exp.experience_id] = variant
                if variant == "treatment":
                    p += exp.uplift
        converted = rng.random() < p

        # Page path
        path = ["home"] + ["category"] * rng.randint(0, 3) + ["product"] * rng.randint(1, 4)
        if converted:
            path += ["cart", "checkout"]
        elif rng.random() < 0.15:
            path += ["cart"]
        t = t0
        page_ts = []
        for page_type in path:
            t += timedelta(seconds=rng.randint(5, 120))
            page_ts.append(t)
            page_views.append({"session_id": session_id, "page_view_ts": t.strftime(TS_FMT), "page_type": page_type})
            props: dict = {"page_type": page_type}
            if page_type == "product":
                props["products"] = [rng.choice(catalog)]
            events.append({"event_type": "page_view", "session_id": session_id, "client_id": client_id,
                           "ts": t.strftime(TS_FMT), "properties": props})

        # Offers: qualify on an early page; sometimes re-qualify later (duplicate row)
        for exp_id, variant in assignments.items():
            idx = rng.randint(0, min(2, len(path) - 1))
            offers.append({"client_id": client_id, "session_id": session_id, "experience_id": exp_id,
                           "variant_id": variant, "first_qualified_ts": page_ts[idx].strftime(TS_FMT)})
            if rng.random() < REQUALIFY_RATE and idx + 1 < len(path):
                later = page_ts[rng.randint(idx + 1, len(path) - 1)]
                offers.append({"client_id": client_id, "session_id": session_id, "experience_id": exp_id,
                               "variant_id": variant, "first_qualified_ts": later.strftime(TS_FMT)})

        if converted:
            order_seq += 1
            items = rng.sample(catalog, rng.randint(1, 4))
            revenue = round(sum(x["price"] for x in items) * rng.uniform(0.9, 1.1), 2)
            ts = (page_ts[-1] + timedelta(seconds=30)).strftime(TS_FMT)
            order_id = f"O{order_seq:07d}"
            conversions.append({"order_id": order_id, "session_id": session_id, "client_id": client_id,
                                "conversion_ts": ts, "revenue": revenue, "items": len(items)})
            events.append({"event_type": "purchase", "session_id": session_id, "client_id": client_id, "ts": ts,
                           "properties": {"order_id": order_id, "revenue": revenue, "products": items}})

    experiences = [{"experience_id": e.experience_id, "client_id": e.client_id, "experience_name": e.name}
                   for e in EXPERIENCES]
    tables = {"sessions": sessions, "page_views": page_views, "offers": offers,
              "conversions": conversions, "experiences": experiences}
    for name, rows in tables.items():
        with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    with open(out / "events.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    counts = {name: len(rows) for name, rows in tables.items()} | {"events": len(events)}
    log.info("Wrote %s to %s", counts, out)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sessions", type=int, default=50_000)
    parser.add_argument("--out", default="data")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    counts = generate(args.sessions, args.out, args.seed)
    for name, n in counts.items():
        print(f"{name:12s} {n:>9,d} rows")


if __name__ == "__main__":
    main()
