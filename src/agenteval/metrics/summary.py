"""Aggregate per-attempt records into a MetricSummary."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from agenteval.metrics.bootstrap import (
    bootstrap_ci,
    bootstrap_proportion_ci,
)
from agenteval.metrics.cost import (
    PricingTable,
    compute_cost_per_attempt,
)
from agenteval.metrics.pass_at_k import pass_at_1, pass_at_k, pass_caret_k


@dataclass(frozen=True)
class MetricSummary:
    """Aggregate metrics across per-attempt records (docs/metrics.md)."""

    n_attempts: int
    n_tasks: int
    n_seeds: int
    pass_at_1: float
    pass_at_1_ci: tuple[float, float]
    pass_at_5: float
    pass_at_5_ci: tuple[float, float]
    pass_caret_5: float
    pass_caret_5_ci: tuple[float, float]
    cost_usd_median: float
    cost_usd_p95: float
    latency_s_p50: float
    latency_s_p95: float
    tokens_out_median: float
    tool_calls_median: float
    timeout_rate: float
    timeout_rate_ci: tuple[float, float]
    per_category_pass_at_1: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_attempts": self.n_attempts,
            "n_tasks": self.n_tasks,
            "n_seeds": self.n_seeds,
            "pass@1": {"point": self.pass_at_1, "ci95": list(self.pass_at_1_ci)},
            "pass@5": {"point": self.pass_at_5, "ci95": list(self.pass_at_5_ci)},
            "pass^5": {"point": self.pass_caret_5, "ci95": list(self.pass_caret_5_ci)},
            "cost_usd": {"median": self.cost_usd_median, "p95": self.cost_usd_p95},
            "latency_s": {"p50": self.latency_s_p50, "p95": self.latency_s_p95},
            "tokens_out_median": self.tokens_out_median,
            "tool_calls_median": self.tool_calls_median,
            "timeout_rate": {
                "point": self.timeout_rate,
                "ci95": list(self.timeout_rate_ci),
            },
            "per_category_pass@1": self.per_category_pass_at_1,
        }


def compute_summary(
    per_attempt: list[Any],
    *,
    n_seeds: int,
    provider: str | None = None,
    model: str | None = None,
    pricing: PricingTable | None = None,
    bootstrap_iterations: int = 1000,
    bootstrap_seed: int = 42,
) -> MetricSummary:
    """Compute the full MetricSummary from a list of PerAttempt records."""
    if not per_attempt:
        return _empty_summary(n_seeds)

    # Group attempts by task; compute per-task pass-count.
    by_task: dict[str, list[Any]] = defaultdict(list)
    by_category_taskids: dict[str, set[str]] = defaultdict(set)
    for a in per_attempt:
        by_task[a.task_id].append(a)
        by_category_taskids[a.category].add(a.task_id)

    task_ids = sorted(by_task.keys())
    per_task_pass_counts = [
        sum(1 for x in by_task[tid] if x.passed) for tid in task_ids
    ]

    # pass@1 / pass@5 / pass^5 (point + CI).
    p1 = pass_at_1(per_task_pass_counts, n_seeds=n_seeds)
    p5 = sum(pass_at_k(n_seeds, c, n_seeds) for c in per_task_pass_counts) / max(
        1, len(per_task_pass_counts)
    )
    pc5 = pass_caret_k(per_task_pass_counts, k=n_seeds)

    ci_p1 = bootstrap_ci(
        per_task_pass_counts,
        lambda xs: pass_at_1(xs, n_seeds=n_seeds),
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )
    ci_p5 = bootstrap_ci(
        per_task_pass_counts,
        lambda xs: sum(pass_at_k(n_seeds, c, n_seeds) for c in xs) / max(1, len(xs)),
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )
    ci_pc5 = bootstrap_ci(
        per_task_pass_counts,
        lambda xs: pass_caret_k(xs, k=n_seeds),
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )

    # Cost. Gracefully skip if pricing entry is missing for the (provider, model)
    # — useful for mock-runner tests against fabricated models.
    costs: list[float] = []
    if pricing is not None and provider is not None and model is not None:
        try:
            for a in per_attempt:
                costs.append(
                    compute_cost_per_attempt(
                        provider=provider,
                        model=model,
                        tokens_in=a.tokens_in,
                        tokens_out=a.tokens_out,
                        pricing=pricing,
                    )
                )
        except Exception:
            costs = []
    cost_med = statistics.median(costs) if costs else 0.0
    cost_p95 = _p95(costs) if costs else 0.0

    # Latency.
    latencies = [a.latency_s for a in per_attempt]
    latency_p50 = statistics.median(latencies)
    latency_p95 = _p95(latencies)

    # Other efficiency.
    tokens_out = [a.tokens_out for a in per_attempt]
    tool_calls = [a.tool_calls for a in per_attempt]
    tokens_out_med = statistics.median(tokens_out) if tokens_out else 0.0
    tool_calls_med = statistics.median(tool_calls) if tool_calls else 0.0

    # Timeout rate (Wilson CI).
    n_timeouts = sum(1 for a in per_attempt if a.timed_out)
    n_total = len(per_attempt)
    timeout_rate = n_timeouts / n_total
    timeout_ci = bootstrap_proportion_ci(n_timeouts, n_total)

    # Per-category pass@1.
    per_category: dict[str, float] = {}
    for category, tids in by_category_taskids.items():
        per_task_counts_cat = [
            sum(1 for x in by_task[tid] if x.passed) for tid in sorted(tids)
        ]
        per_category[category] = pass_at_1(per_task_counts_cat, n_seeds=n_seeds)

    return MetricSummary(
        n_attempts=n_total,
        n_tasks=len(task_ids),
        n_seeds=n_seeds,
        pass_at_1=p1,
        pass_at_1_ci=ci_p1,
        pass_at_5=p5,
        pass_at_5_ci=ci_p5,
        pass_caret_5=pc5,
        pass_caret_5_ci=ci_pc5,
        cost_usd_median=cost_med,
        cost_usd_p95=cost_p95,
        latency_s_p50=latency_p50,
        latency_s_p95=latency_p95,
        tokens_out_median=tokens_out_med,
        tool_calls_median=tool_calls_med,
        timeout_rate=timeout_rate,
        timeout_rate_ci=timeout_ci,
        per_category_pass_at_1=per_category,
    )


def _empty_summary(n_seeds: int) -> MetricSummary:
    return MetricSummary(
        n_attempts=0,
        n_tasks=0,
        n_seeds=n_seeds,
        pass_at_1=0.0,
        pass_at_1_ci=(0.0, 0.0),
        pass_at_5=0.0,
        pass_at_5_ci=(0.0, 0.0),
        pass_caret_5=0.0,
        pass_caret_5_ci=(0.0, 0.0),
        cost_usd_median=0.0,
        cost_usd_p95=0.0,
        latency_s_p50=0.0,
        latency_s_p95=0.0,
        tokens_out_median=0.0,
        tool_calls_median=0.0,
        timeout_rate=0.0,
        timeout_rate_ci=(0.0, 0.0),
    )


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, int(round(0.95 * (len(s) - 1))))
    return s[idx]
