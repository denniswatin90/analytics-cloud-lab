import math

import pytest

from analytics_cloud_lab.experiment import ExperimentReport, VariantStats, two_proportion_z_test


def test_z_test_known_values():
    # 200/10,000 vs 260/10,000 -> z ≈ 2.83, p ≈ 0.005
    z, p = two_proportion_z_test(200, 10_000, 260, 10_000)
    assert z == pytest.approx(2.83, abs=0.01)
    assert p == pytest.approx(0.0047, abs=0.0005)


def test_z_test_identical_groups():
    z, p = two_proportion_z_test(30, 1000, 30, 1000)
    assert z == 0
    assert p == pytest.approx(1.0)


def test_z_test_rejects_empty_group():
    with pytest.raises(ValueError):
        two_proportion_z_test(0, 0, 1, 10)


def test_variant_stats_rates():
    v = VariantStats("control", sessions=200, conversions=10, revenue=500.0)
    assert v.conversion_rate == 0.05
    assert v.revenue_per_session == 2.5


def test_report_from_uppercase_snowflake_rows():
    rows = [
        {"VARIANT_ID": "control", "SESSIONS": 10_000, "CONVERSIONS": 200, "TOTAL_REVENUE": 11_000},
        {"VARIANT_ID": "treatment", "SESSIONS": 10_000, "CONVERSIONS": 260, "TOTAL_REVENUE": 14_300},
    ]
    report = ExperimentReport.from_rows("EXP-TEST", rows)
    (cmp,) = report.compare()
    assert cmp.variant_id == "treatment"
    assert cmp.abs_diff == pytest.approx(0.006)
    assert cmp.rel_lift == pytest.approx(0.30)
    assert cmp.ci_low > 0 and cmp.significant
    md = report.to_markdown()
    assert "EXP-TEST" in md and "| treatment |" in md


def test_report_requires_control():
    with pytest.raises(ValueError):
        ExperimentReport("X", {"a": VariantStats("a", 10, 1)})


def test_normal_cdf_symmetry():
    from analytics_cloud_lab.experiment import normal_cdf

    assert normal_cdf(0) == 0.5
    assert math.isclose(normal_cdf(1.96) + normal_cdf(-1.96), 1.0)
