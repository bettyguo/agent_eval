"""Adversarial flags (descriptive badges, not ranked).

8 flags from docs/metrics.md §2 + the spec. Each flag has a deterministic
trigger expressed as a Python predicate over (current run metrics, baseline
run metrics). The flag set is intentionally small and audited; v2 may add to
this list via ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime


@dataclass(frozen=True)
class Flag:
    """A descriptive flag attached to a run."""

    name: str
    why: str
    details: dict[str, float | str] | None = None


# Flag registry: name -> human-readable description (for docs / UI).
FLAG_DEFINITIONS: dict[str, str] = {
    "high-variance": "pass@5 ≥ 2 × pass^5: gains likely driven by nondeterminism.",
    "talkative": "median output tokens ≥ 2 × baseline.",
    "tool-storm": "median tool_calls ≥ 2 × baseline.",
    "pricing-stale": "pricing.yaml last_audited > 30 days ago.",
    "model-drift": "model fingerprint mismatch between submission and re-verification.",
    "borderline-stability": "a task pass/fail flipped between submission and re-verification.",
    "holdout-divergence": "public vs. holdout pass@1 differs by >15 percentage points.",
    "passive": "timeout_rate ≥ 2× baseline AND pass^5 ≥ baseline pass^5 (silently bails on hard tasks).",
}


def compute_flags(
    *,
    pass_at_5: float,
    pass_caret_5: float,
    tokens_out_median: float,
    tool_calls_median: float,
    timeout_rate: float,
    pricing_last_audited: date,
    baseline_tokens_out_median: float | None = None,
    baseline_tool_calls_median: float | None = None,
    baseline_timeout_rate: float | None = None,
    baseline_pass_caret_5: float | None = None,
    holdout_pass_at_1: float | None = None,
    public_pass_at_1: float | None = None,
    fingerprint_now: str | None = None,
    fingerprint_at_verify: str | None = None,
    flipped_task_ids: list[str] | None = None,
) -> list[Flag]:
    """Compute all applicable flags for a run.

    Baseline values must be provided where the flag definition requires a
    reference (talkative, tool-storm, passive). If absent, the flag is skipped.
    """
    flags: list[Flag] = []

    if pass_caret_5 > 0.0 and pass_at_5 >= 2.0 * pass_caret_5:
        flags.append(
            Flag(
                name="high-variance",
                why=f"pass@5={pass_at_5:.3f} >= 2 * pass^5={pass_caret_5:.3f}",
                details={"pass@5": pass_at_5, "pass^5": pass_caret_5},
            )
        )

    if (
        baseline_tokens_out_median is not None
        and baseline_tokens_out_median > 0
        and tokens_out_median >= 2.0 * baseline_tokens_out_median
    ):
        flags.append(
            Flag(
                name="talkative",
                why=(
                    f"median output tokens {tokens_out_median:.0f} "
                    f">= 2 * baseline {baseline_tokens_out_median:.0f}"
                ),
                details={
                    "tokens_out_median": tokens_out_median,
                    "baseline_tokens_out_median": baseline_tokens_out_median,
                },
            )
        )

    if (
        baseline_tool_calls_median is not None
        and baseline_tool_calls_median > 0
        and tool_calls_median >= 2.0 * baseline_tool_calls_median
    ):
        flags.append(
            Flag(
                name="tool-storm",
                why=(
                    f"median tool_calls {tool_calls_median:.1f} "
                    f">= 2 * baseline {baseline_tool_calls_median:.1f}"
                ),
                details={
                    "tool_calls_median": tool_calls_median,
                    "baseline_tool_calls_median": baseline_tool_calls_median,
                },
            )
        )

    now = datetime.now(UTC).date()
    if (now - pricing_last_audited).days > 30:
        flags.append(
            Flag(
                name="pricing-stale",
                why=(
                    f"pricing.yaml last_audited {pricing_last_audited.isoformat()} "
                    f"is {(now - pricing_last_audited).days} days ago (>30)"
                ),
                details={"days_old": (now - pricing_last_audited).days},
            )
        )

    if fingerprint_now and fingerprint_at_verify and fingerprint_now != fingerprint_at_verify:
        flags.append(
            Flag(
                name="model-drift",
                why=(
                    f"fingerprint at submission {fingerprint_now!r} "
                    f"differs from re-verification {fingerprint_at_verify!r}"
                ),
                details={
                    "submission_fingerprint": fingerprint_now,
                    "verify_fingerprint": fingerprint_at_verify,
                },
            )
        )

    if flipped_task_ids:
        flags.append(
            Flag(
                name="borderline-stability",
                why=f"{len(flipped_task_ids)} task(s) flipped pass/fail on re-verification",
                details={"flipped_tasks": ", ".join(flipped_task_ids)},
            )
        )

    if holdout_pass_at_1 is not None and public_pass_at_1 is not None:
        gap = abs(public_pass_at_1 - holdout_pass_at_1)
        if gap > 0.15:
            flags.append(
                Flag(
                    name="holdout-divergence",
                    why=f"|public - holdout| = {gap:.3f} > 0.15",
                    details={
                        "public_pass@1": public_pass_at_1,
                        "holdout_pass@1": holdout_pass_at_1,
                        "gap": gap,
                    },
                )
            )

    if (
        baseline_timeout_rate is not None
        and baseline_pass_caret_5 is not None
        and baseline_timeout_rate > 0
        and timeout_rate >= 2.0 * baseline_timeout_rate
        and pass_caret_5 >= baseline_pass_caret_5
    ):
        flags.append(
            Flag(
                name="passive",
                why=(
                    f"timeout_rate {timeout_rate:.3f} >= 2 * baseline {baseline_timeout_rate:.3f} "
                    f"AND pass^5 {pass_caret_5:.3f} >= baseline {baseline_pass_caret_5:.3f}"
                ),
                details={
                    "timeout_rate": timeout_rate,
                    "baseline_timeout_rate": baseline_timeout_rate,
                    "pass^5": pass_caret_5,
                    "baseline_pass^5": baseline_pass_caret_5,
                },
            )
        )

    return flags
