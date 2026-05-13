"""Metrics module (M3).

Implements `docs/metrics.md`: primary capability metrics (pass@1, pass@5,
pass^5), efficiency metrics (cost_usd, latency_s, tool_calls, timeout_rate),
the 8 adversarial flags, and the bootstrap CI protocol.
"""

from agenteval.metrics.bootstrap import bootstrap_ci, bootstrap_proportion_ci
from agenteval.metrics.cost import (
    PricingTable,
    compute_cost_per_attempt,
    load_pricing,
)
from agenteval.metrics.flags import (
    FLAG_DEFINITIONS,
    Flag,
    compute_flags,
)
from agenteval.metrics.pass_at_k import pass_at_1, pass_at_k, pass_caret_k
from agenteval.metrics.summary import MetricSummary, compute_summary

__all__ = [
    "FLAG_DEFINITIONS",
    "Flag",
    "MetricSummary",
    "PricingTable",
    "bootstrap_ci",
    "bootstrap_proportion_ci",
    "compute_cost_per_attempt",
    "compute_flags",
    "compute_summary",
    "load_pricing",
    "pass_at_1",
    "pass_at_k",
    "pass_caret_k",
]
