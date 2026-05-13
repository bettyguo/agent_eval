"""Tests for M3 metrics module."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from agenteval.metrics import (
    bootstrap_proportion_ci,
    compute_cost_per_attempt,
    compute_flags,
    compute_summary,
    load_pricing,
    pass_at_1,
    pass_at_k,
    pass_caret_k,
)


class TestPassAtK:
    def test_n_eq_k_eq_c(self):
        assert pass_at_k(5, 5, 5) == 1.0

    def test_c_zero(self):
        assert pass_at_k(5, 0, 1) == 0.0
        assert pass_at_k(5, 0, 5) == 0.0

    def test_known_value(self):
        # n=2, c=1, k=1 → pass@1 = 1/2 = 0.5
        assert abs(pass_at_k(2, 1, 1) - 0.5) < 1e-9

    def test_k_gt_n_minus_c_means_one(self):
        # If we draw 5 from 5 samples with 1 correct, k=5 must include the 1 correct.
        assert pass_at_k(5, 1, 5) == 1.0

    def test_large_n_no_overflow(self):
        # Just verify it runs and is in [0, 1].
        v = pass_at_k(10_000, 100, 50)
        assert 0.0 <= v <= 1.0

    def test_bad_args(self):
        with pytest.raises(ValueError):
            pass_at_k(5, 0, 0)
        with pytest.raises(ValueError):
            pass_at_k(5, 0, 6)
        with pytest.raises(ValueError):
            pass_at_k(5, -1, 1)


class TestPassAt1AndCaret:
    def test_pass_at_1_simple(self):
        # 2 tasks: one passes 5/5 seeds, one passes 0/5. pass@1 averaged = 0.5.
        assert pass_at_1([5, 0], n_seeds=5) == 0.5

    def test_pass_caret_5(self):
        # 3 tasks: 5/5, 4/5, 5/5 → pass^5 = 2/3.
        assert abs(pass_caret_k([5, 4, 5], k=5) - 2 / 3) < 1e-9


class TestWilsonInterval:
    def test_no_successes(self):
        lo, hi = bootstrap_proportion_ci(0, 100)
        assert lo == 0.0
        assert 0.0 < hi < 0.1

    def test_all_successes(self):
        lo, hi = bootstrap_proportion_ci(100, 100)
        assert hi == 1.0
        assert lo < 1.0

    def test_zero_n(self):
        assert bootstrap_proportion_ci(0, 0) == (0.0, 0.0)


class TestPricingAndCost:
    def test_load_default_pricing(self):
        pricing = load_pricing()
        rates = pricing.lookup("anthropic", "claude-opus-4-7")
        assert rates["input_per_mtok"] > 0
        assert rates["output_per_mtok"] > rates["input_per_mtok"]

    def test_cost_compute(self):
        pricing = load_pricing()
        # 1M tokens in + 1M tokens out at claude-opus pricing = $15 + $75 = $90.
        cost = compute_cost_per_attempt(
            provider="anthropic",
            model="claude-opus-4-7",
            tokens_in=1_000_000,
            tokens_out=1_000_000,
            pricing=pricing,
        )
        assert abs(cost - 90.0) < 1e-6

    def test_pricing_stale_check(self, tmp_path: Path):
        p = tmp_path / "pricing.yaml"
        old_date = (date.today() - timedelta(days=60)).isoformat()
        p.write_text(
            f"last_audited: '{old_date}'\n"
            "providers:\n  test:\n    test-model:\n      input_per_mtok: 1.0\n      output_per_mtok: 1.0\n",
            encoding="utf-8",
        )
        pricing = load_pricing(p)
        assert pricing.is_stale()


class TestFlags:
    def test_high_variance(self):
        flags = compute_flags(
            pass_at_5=0.50,
            pass_caret_5=0.10,
            tokens_out_median=100,
            tool_calls_median=5,
            timeout_rate=0.0,
            pricing_last_audited=date.today(),
        )
        names = [f.name for f in flags]
        assert "high-variance" in names

    def test_no_high_variance_when_consistent(self):
        flags = compute_flags(
            pass_at_5=0.50,
            pass_caret_5=0.40,
            tokens_out_median=100,
            tool_calls_median=5,
            timeout_rate=0.0,
            pricing_last_audited=date.today(),
        )
        names = [f.name for f in flags]
        assert "high-variance" not in names

    def test_pricing_stale_flag(self):
        old = date.today() - timedelta(days=45)
        flags = compute_flags(
            pass_at_5=0.0,
            pass_caret_5=0.0,
            tokens_out_median=0,
            tool_calls_median=0,
            timeout_rate=0.0,
            pricing_last_audited=old,
        )
        names = [f.name for f in flags]
        assert "pricing-stale" in names

    def test_talkative_when_baseline_doubled(self):
        flags = compute_flags(
            pass_at_5=0.0,
            pass_caret_5=0.0,
            tokens_out_median=400,
            tool_calls_median=5,
            timeout_rate=0.0,
            pricing_last_audited=date.today(),
            baseline_tokens_out_median=100,
        )
        names = [f.name for f in flags]
        assert "talkative" in names

    def test_model_drift_flag(self):
        flags = compute_flags(
            pass_at_5=0.0,
            pass_caret_5=0.0,
            tokens_out_median=0,
            tool_calls_median=0,
            timeout_rate=0.0,
            pricing_last_audited=date.today(),
            fingerprint_now="fp_abc",
            fingerprint_at_verify="fp_xyz",
        )
        assert "model-drift" in [f.name for f in flags]

    def test_holdout_divergence(self):
        flags = compute_flags(
            pass_at_5=0.0,
            pass_caret_5=0.0,
            tokens_out_median=0,
            tool_calls_median=0,
            timeout_rate=0.0,
            pricing_last_audited=date.today(),
            public_pass_at_1=0.50,
            holdout_pass_at_1=0.20,
        )
        assert "holdout-divergence" in [f.name for f in flags]

    def test_passive_flag(self):
        flags = compute_flags(
            pass_at_5=0.0,
            pass_caret_5=0.50,
            tokens_out_median=0,
            tool_calls_median=0,
            timeout_rate=0.40,
            pricing_last_audited=date.today(),
            baseline_timeout_rate=0.10,
            baseline_pass_caret_5=0.40,
        )
        assert "passive" in [f.name for f in flags]


class TestComputeSummaryIntegration:
    """Validate `compute_summary` produces a well-formed MetricSummary on per-attempt data."""

    def test_basic_summary(self):
        from agenteval.harness import PerAttempt

        attempts = []
        # 2 tasks × 5 seeds. Task A: all pass. Task B: only seed 1 passes.
        for seed in range(1, 6):
            attempts.append(
                PerAttempt(
                    task_id="task-a",
                    category="cat-a",
                    seed=seed,
                    passed=True,
                    grader_details={},
                    tokens_in=1000,
                    tokens_out=200,
                    tool_calls=3,
                    latency_s=5.0,
                    timed_out=False,
                )
            )
            attempts.append(
                PerAttempt(
                    task_id="task-b",
                    category="cat-b",
                    seed=seed,
                    passed=(seed == 1),
                    grader_details={},
                    tokens_in=1500,
                    tokens_out=400,
                    tool_calls=8,
                    latency_s=10.0,
                    timed_out=False,
                )
            )

        summary = compute_summary(attempts, n_seeds=5, bootstrap_iterations=100)
        assert summary.n_attempts == 10
        assert summary.n_tasks == 2
        # pass@1: task-a contributes 5/5; task-b contributes 1/5; mean = 0.6.
        assert abs(summary.pass_at_1 - 0.6) < 1e-6
        # pass@5: task-a → 1 (all pass), task-b → 1 (≥1 passes), mean = 1.0.
        assert abs(summary.pass_at_5 - 1.0) < 1e-6
        # pass^5: task-a → 1 (all-5), task-b → 0, mean = 0.5.
        assert abs(summary.pass_caret_5 - 0.5) < 1e-6
        # timeouts.
        assert summary.timeout_rate == 0.0
        # Per-category.
        assert abs(summary.per_category_pass_at_1["cat-a"] - 1.0) < 1e-6
        assert abs(summary.per_category_pass_at_1["cat-b"] - 0.2) < 1e-6
