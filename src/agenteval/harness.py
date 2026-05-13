"""Harness: glue between SkillBundle, TaskSet, Runner, Sandbox.

Iterates over (task × seed), produces a Result.

M1 ships canonical-seeds + single-seed exploratory modes; cost computation and
the full metric/flag battery are M3 deliverables. M1's Result is intentionally
slim: per-task pass/fail, latency, tool_calls, tokens. pass@1 is computed
inline as a sanity check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agenteval.errors import GraderError, LeaderboardIneligible
from agenteval.grading import run_grader
from agenteval.grading.types import GraderResult
from agenteval.metrics import (
    Flag,
    MetricSummary,
    PricingTable,
    compute_flags,
    compute_summary,
)
from agenteval.runners.base import Runner, RunOutcome
from agenteval.sandbox import default_sandbox_factory
from agenteval.sandbox.base import SandboxFactory
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task, TaskSet

CANONICAL_SEEDS = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class PerAttempt:
    """One (task, seed) attempt record."""

    task_id: str
    category: str
    seed: int
    passed: bool
    grader_details: dict[str, Any]
    tokens_in: int
    tokens_out: int
    tool_calls: int
    latency_s: float
    timed_out: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "seed": self.seed,
            "passed": self.passed,
            "grader_details": self.grader_details,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tool_calls": self.tool_calls,
            "latency_s": self.latency_s,
            "timed_out": self.timed_out,
        }


@dataclass(frozen=True)
class Result:
    """Aggregate output of Harness.evaluate (DESIGN.md §1.2)."""

    bundle_hash: str
    task_set_hash: str
    task_set_name: str
    task_set_panel: str
    model: str
    provider: str
    temperature: float
    seeds: tuple[int, ...]
    runner_name: str
    model_response_fingerprint: str | None
    per_attempt: tuple[PerAttempt, ...]
    leaderboard_eligible: bool
    metric_summary: MetricSummary | None = None
    flags: tuple[Flag, ...] = ()
    pricing_yaml_hash: str | None = None
    pricing_last_audited: str | None = None
    aux: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        """Rich M3 summary backed by `compute_summary`."""
        if self.metric_summary is None:
            # Fallback if cost/metrics weren't computed (e.g., mock tests).
            n = len(self.per_attempt)
            passes = sum(1 for a in self.per_attempt if a.passed)
            timeouts = sum(1 for a in self.per_attempt if a.timed_out)
            return {
                "n_attempts": n,
                "n_passed": passes,
                "raw_pass_rate": (passes / n) if n else 0.0,
                "timeout_rate": (timeouts / n) if n else 0.0,
                "leaderboard_eligible": self.leaderboard_eligible,
            }
        out = self.metric_summary.to_dict()
        out["leaderboard_eligible"] = self.leaderboard_eligible
        out["flags"] = [{"name": f.name, "why": f.why} for f in self.flags]
        return out

    def to_leaderboard_entry(self) -> dict[str, Any]:
        """Canonical JSON shape (DESIGN.md §1.2). Full hash-stamping in M5."""
        if not self.leaderboard_eligible:
            raise LeaderboardIneligible(
                "result is not eligible for the primary leaderboard: "
                "see DESIGN.md §1.2 eligibility criteria",
                seeds=list(self.seeds),
                temperature=self.temperature,
                task_set_panel=self.task_set_panel,
            )
        return {
            "schema_version": "0.draft",
            "bundle_hash": self.bundle_hash,
            "task_set": {
                "name": self.task_set_name,
                "hash": self.task_set_hash,
                "panel": self.task_set_panel,
            },
            "runner": {
                "name": self.runner_name,
                "provider": self.provider,
                "model": self.model,
                "model_response_fingerprint": self.model_response_fingerprint,
                "temperature": self.temperature,
                "seeds": list(self.seeds),
            },
            "pricing": {
                "yaml_hash": self.pricing_yaml_hash,
                "last_audited": self.pricing_last_audited,
            },
            "metrics": self.summary(),
            "flags": [{"name": f.name, "why": f.why, "details": f.details} for f in self.flags],
            "per_attempt": [a.as_dict() for a in self.per_attempt],
        }


class Harness:
    """Wires a runner + sandbox + task set + skill bundle. Returns a Result.

    See DESIGN.md §1.2 for the public contract. M1 sequencing is single-process
    over (task × seed); parallelism (§1.5) is an M3 feature.
    """

    def __init__(
        self,
        *,
        runner: Runner,
        model: str | None = None,
        provider: str | None = None,
        temperature: float = 0.0,
        canonical_seeds: bool = True,
        custom_seeds: list[int] | None = None,
        sandbox_factory: SandboxFactory | None = None,
        pricing: PricingTable | None = None,
        bootstrap_iterations: int = 1000,
    ) -> None:
        if not canonical_seeds and not custom_seeds:
            raise ValueError("custom_seeds required when canonical_seeds=False")
        if canonical_seeds and custom_seeds:
            raise ValueError("custom_seeds incompatible with canonical_seeds=True")

        self.runner = runner
        self.model = model or getattr(runner, "model", "unknown-model")
        self.provider = provider or runner.name
        self.temperature = temperature
        self.seeds: tuple[int, ...] = (
            CANONICAL_SEEDS if canonical_seeds else tuple(custom_seeds or ())
        )
        self.sandbox_factory: SandboxFactory = sandbox_factory or default_sandbox_factory()
        self.canonical_seeds = canonical_seeds
        self.pricing = pricing
        self.bootstrap_iterations = bootstrap_iterations

    def evaluate(self, bundle: SkillBundle, task_set: TaskSet) -> Result:
        per_attempt: list[PerAttempt] = []
        fingerprint: str | None = None

        for task in task_set.tasks:
            for seed in self.seeds:
                attempt = self._run_one(task, bundle, seed)
                per_attempt.append(attempt)
                if fingerprint is None:
                    fingerprint = getattr(attempt, "_fingerprint", None)

        eligible = self._eligibility(task_set, per_attempt)

        # M3: compute the full metric summary + applicable flags.
        summary: MetricSummary | None = None
        flags: tuple[Flag, ...] = ()
        pricing_yaml_hash: str | None = None
        pricing_last_audited: str | None = None
        if per_attempt:
            summary = compute_summary(
                per_attempt,
                n_seeds=len(self.seeds),
                provider=self.provider,
                model=self.model,
                pricing=self.pricing,
                bootstrap_iterations=self.bootstrap_iterations,
            )
            if self.pricing is not None:
                pricing_yaml_hash = self.pricing.yaml_hash
                pricing_last_audited = self.pricing.last_audited.isoformat()
                flag_list = compute_flags(
                    pass_at_5=summary.pass_at_5,
                    pass_caret_5=summary.pass_caret_5,
                    tokens_out_median=summary.tokens_out_median,
                    tool_calls_median=summary.tool_calls_median,
                    timeout_rate=summary.timeout_rate,
                    pricing_last_audited=self.pricing.last_audited,
                )
                flags = tuple(flag_list)

        return Result(
            bundle_hash=bundle.hash,
            task_set_hash=task_set.hash,
            task_set_name=task_set.name,
            task_set_panel=task_set.panel,
            model=self.model,
            provider=self.provider,
            temperature=self.temperature,
            seeds=self.seeds,
            runner_name=self.runner.name,
            model_response_fingerprint=fingerprint,
            per_attempt=tuple(per_attempt),
            leaderboard_eligible=eligible,
            metric_summary=summary,
            flags=flags,
            pricing_yaml_hash=pricing_yaml_hash,
            pricing_last_audited=pricing_last_audited,
        )

    def _run_one(self, task: Task, bundle: SkillBundle, seed: int) -> PerAttempt:
        sandbox = self.sandbox_factory()
        sandbox.setup(
            files=dict(task.meta.setup.files),
            pip_install=list(task.meta.setup.pip_install),
            skill_bundle=bundle,
        )
        grader_error: GraderError | None = None
        grader_result: GraderResult | None = None
        try:
            outcome: RunOutcome = self.runner.run(
                bundle=bundle, task=task, sandbox=sandbox, seed=seed
            )
            try:
                grader_result = run_grader(
                    task=task,
                    workdir=sandbox.workdir(),
                    trajectory=outcome.trajectory,
                    final_state=outcome.final_state,
                )
            except GraderError as exc:
                # Per docs/tasks.md §3.4: grader errors are distinct from task
                # failures but still recorded; surface them in `grader_details`
                # so the operator can debug missing tools / broken graders.
                grader_error = exc
        finally:
            sandbox.teardown()

        if grader_error is not None:
            return PerAttempt(
                task_id=task.id,
                category=task.category,
                seed=seed,
                passed=False,
                grader_details={
                    "grader_error": grader_error.message,
                    "grader_error_code": grader_error.code,
                    **{k: v for k, v in grader_error.details.items() if k != "traceback"},
                },
                tokens_in=outcome.tokens_in,
                tokens_out=outcome.tokens_out,
                tool_calls=outcome.tool_calls,
                latency_s=outcome.latency_s,
                timed_out=outcome.final_state.timed_out,
            )

        assert grader_result is not None
        return PerAttempt(
            task_id=task.id,
            category=task.category,
            seed=seed,
            passed=grader_result.passed,
            grader_details=dict(grader_result.details),
            tokens_in=outcome.tokens_in,
            tokens_out=outcome.tokens_out,
            tool_calls=outcome.tool_calls,
            latency_s=outcome.latency_s,
            timed_out=outcome.final_state.timed_out,
        )

    def _eligibility(self, task_set: TaskSet, attempts: list[PerAttempt]) -> bool:
        """ADR-0015 + DESIGN.md §1.2 eligibility criteria, minus M3-only checks."""
        if self.temperature != 0.0:
            return False
        if not self.canonical_seeds or self.seeds != CANONICAL_SEEDS:
            return False
        if task_set.panel != "primary":
            return False
        return True
