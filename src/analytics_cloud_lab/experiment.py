"""Experiment statistics: conversion rate, lift and a two-proportion z-test."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_proportion_z_test(conv_a: int, n_a: int, conv_b: int, n_b: int) -> tuple[float, float]:
    """Two-sided z-test for p_b - p_a. Returns (z, p_value)."""
    if min(n_a, n_b) == 0:
        raise ValueError("Both groups need at least one session")
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 0.0, 1.0
    z = (conv_b / n_b - conv_a / n_a) / se
    return z, 2 * (1 - normal_cdf(abs(z)))


@dataclass(frozen=True)
class VariantStats:
    variant_id: str
    sessions: int
    conversions: int
    revenue: float = 0.0

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.sessions if self.sessions else 0.0

    @property
    def revenue_per_session(self) -> float:
        return self.revenue / self.sessions if self.sessions else 0.0


@dataclass(frozen=True)
class Comparison:
    variant_id: str
    abs_diff: float
    rel_lift: float
    ci_low: float
    ci_high: float
    z: float
    p_value: float
    significant: bool


class ExperimentReport:
    """Compare every variant of one experience against its control."""

    def __init__(self, experience_id: str, variants: Mapping[str, VariantStats],
                 control_id: str = "control", alpha: float = 0.05):
        if control_id not in variants:
            raise ValueError(f"Control variant '{control_id}' not found in {list(variants)}")
        self.experience_id = experience_id
        self.variants = dict(variants)
        self.control_id = control_id
        self.alpha = alpha

    @classmethod
    def from_rows(cls, experience_id: str, rows: Iterable[Mapping], **kwargs) -> ExperimentReport:
        """Build from query rows with variant_id, sessions, conversions, total_revenue.

        Keys are matched case-insensitively because Snowflake returns UPPER-CASE names.
        """
        variants = {}
        for row in rows:
            r = {k.lower(): v for k, v in row.items()}
            vs = VariantStats(str(r["variant_id"]), int(r["sessions"]), int(r["conversions"]),
                              float(r.get("total_revenue") or 0))
            variants[vs.variant_id] = vs
        return cls(experience_id, variants, **kwargs)

    def compare(self) -> list[Comparison]:
        c = self.variants[self.control_id]
        z_crit = 1.959963984540054  # 95% two-sided
        results = []
        for vid, v in self.variants.items():
            if vid == self.control_id:
                continue
            z, p = two_proportion_z_test(c.conversions, c.sessions, v.conversions, v.sessions)
            diff = v.conversion_rate - c.conversion_rate
            se = math.sqrt(c.conversion_rate * (1 - c.conversion_rate) / c.sessions
                           + v.conversion_rate * (1 - v.conversion_rate) / v.sessions)
            rel = diff / c.conversion_rate if c.conversion_rate else float("nan")
            results.append(Comparison(vid, diff, rel, diff - z_crit * se, diff + z_crit * se, z, p, p < self.alpha))
        return results

    def to_markdown(self) -> str:
        lines = [f"## Experience {self.experience_id}", "",
                 "| Variant | Sessions | Conversions | Conv. rate | Revenue / session |",
                 "| --- | ---: | ---: | ---: | ---: |"]
        for v in self.variants.values():
            lines.append(f"| {v.variant_id} | {v.sessions:,} | {v.conversions:,} | "
                         f"{v.conversion_rate:.2%} | {v.revenue_per_session:.2f} |")
        lines += ["", "| Variant vs control | Abs. diff | Rel. lift | 95% CI (abs.) | p-value | Significant |",
                  "| --- | ---: | ---: | --- | ---: | --- |"]
        for r in self.compare():
            lines.append(f"| {r.variant_id} | {r.abs_diff:+.2%} | {r.rel_lift:+.1%} | "
                         f"[{r.ci_low:+.2%}, {r.ci_high:+.2%}] | {r.p_value:.4f} | "
                         f"{'yes' if r.significant else 'no'} |")
        return "\n".join(lines) + "\n"
