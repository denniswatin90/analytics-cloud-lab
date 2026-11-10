import csv
import json

from analytics_cloud_lab.generate_data import generate
from analytics_cloud_lab.local_metrics import variant_summary


def _read(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_generate_is_deterministic(tmp_path):
    a = generate(500, tmp_path / "a", seed=7)
    b = generate(500, tmp_path / "b", seed=7)
    assert a == b
    assert (tmp_path / "a" / "offers.csv").read_text() == (tmp_path / "b" / "offers.csv").read_text()


def test_referential_integrity(tmp_path):
    generate(2000, tmp_path, seed=1)
    session_ids = {r["session_id"] for r in _read(tmp_path / "sessions.csv")}
    assert len(session_ids) == 2000
    for table in ("page_views", "offers", "conversions"):
        assert {r["session_id"] for r in _read(tmp_path / f"{table}.csv")} <= session_ids
    exps = {r["experience_id"]: r["client_id"] for r in _read(tmp_path / "experiences.csv")}
    for offer in _read(tmp_path / "offers.csv"):
        assert exps[offer["experience_id"]] == offer["client_id"]


def test_offers_contain_duplicates_for_qualify_practice(tmp_path):
    generate(2000, tmp_path, seed=3)
    keys = [(r["session_id"], r["experience_id"]) for r in _read(tmp_path / "offers.csv")]
    assert len(keys) > len(set(keys))


def test_events_jsonl_is_valid(tmp_path):
    counts = generate(300, tmp_path, seed=2)
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == counts["events"]
    purchases = [json.loads(x) for x in lines if '"purchase"' in x]
    assert len(purchases) == counts["conversions"]
    assert all(p["properties"]["products"] for p in purchases)


def test_variant_summary_counts_match_first_offers(tmp_path):
    generate(3000, tmp_path, seed=5)
    summary = variant_summary(tmp_path)
    unique_pairs = {(r["session_id"], r["experience_id"]) for r in _read(tmp_path / "offers.csv")}
    assert sum(r["sessions"] for rows in summary.values() for r in rows) == len(unique_pairs)
    for rows in summary.values():
        assert {r["variant_id"] for r in rows} == {"control", "treatment"}
        assert all(r["conversions"] <= r["sessions"] for r in rows)
