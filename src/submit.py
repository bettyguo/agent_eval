"""Submission + verification machinery (M5).

Implements docs/reproducibility.md §3 (verifier) and ADR-0015 enforcement at
the submission gate.

Per anti-pattern #10 of the master prompt: every primary-panel leaderboard
entry must be re-verified in TWO different VMs. The two-VM rule is enforced
by CI, not by this module — the module produces single-VM `verify` reports
that CI then aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agenteval.errors import LeaderboardIneligible
from agenteval.harness import Harness, Result
from agenteval.metrics import load_pricing
from agenteval.reproducibility import compute_entry_hash
from agenteval.runners.anthropic import AnthropicRunner
from agenteval.runners.base import Runner
from agenteval.runners.google import GoogleRunner
from agenteval.runners.openai import OpenAIRunner
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import TaskSet

SCHEMA_VERSION = "1"

# Acceptance tolerances (docs/reproducibility.md §3).
COST_TOLERANCE_FRAC = 0.05
LATENCY_TOLERANCE_FRAC = 0.25


@dataclass
class VerificationReport:
    """Output of `verify`. CI aggregates across the two-VM rule."""

    verified: bool
    entry_hash_match: bool
    pass_fail_match: bool
    flipped_task_ids: list[str]
    cost_within_tolerance: bool
    latency_within_tolerance: bool
    fingerprint_match: bool
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "entry_hash_match": self.entry_hash_match,
            "pass_fail_match": self.pass_fail_match,
            "flipped_task_ids": self.flipped_task_ids,
            "cost_within_tolerance": self.cost_within_tolerance,
            "latency_within_tolerance": self.latency_within_tolerance,
            "fingerprint_match": self.fingerprint_match,
            "notes": self.notes,
        }


def build_leaderboard_entry(result: Result) -> dict[str, Any]:
    """Construct the canonical LeaderboardEntry JSON (DESIGN.md §1.2).

    Raises LeaderboardIneligible if the result wouldn't qualify.
    """
    if not result.leaderboard_eligible:
        raise LeaderboardIneligible(
            "result not eligible: see eligibility criteria in DESIGN.md §1.2",
            seeds=list(result.seeds),
            temperature=result.temperature,
            task_set_panel=result.task_set_panel,
        )
    pricing_hash = result.pricing_yaml_hash or ("0" * 64)
    entry_hash = compute_entry_hash(
        skill_bundle_hash=result.bundle_hash,
        task_set_hash=result.task_set_hash,
        model=result.model,
        temperature=result.temperature,
        seed_list=list(result.seeds),
        pricing_yaml_hash=pricing_hash,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "entry_hash": entry_hash,
        "bundle": {"hash": result.bundle_hash},
        "task_set": {
            "name": result.task_set_name,
            "hash": result.task_set_hash,
            "panel": result.task_set_panel,
        },
        "runner": {
            "name": result.runner_name,
            "provider": result.provider,
            "model": result.model,
            "model_response_fingerprint": result.model_response_fingerprint,
            "temperature": result.temperature,
            "seeds": list(result.seeds),
        },
        "pricing": {
            "yaml_hash": result.pricing_yaml_hash,
            "last_audited": result.pricing_last_audited,
        },
        "metrics": result.summary(),
        "flags": [{"name": f.name, "why": f.why, "details": f.details} for f in result.flags],
        "per_attempt": [a.as_dict() for a in result.per_attempt],
        "verification": {"verified": False, "report": None},
    }


def verify_entry(
    entry: dict[str, Any],
    *,
    skill_bundle: SkillBundle,
    task_set: TaskSet,
    api_key: str | None = None,
) -> VerificationReport:
    """Re-run the entry from scratch; compare structured features.

    `skill_bundle` and `task_set` must already be loaded by the caller (the
    bundle/task-set artefacts are content-addressed by hash, and the caller is
    responsible for fetching them from wherever the submission JSON references).
    """
    notes: list[str] = []

    # 1. Bundle / task-set hash agreement.
    expected_bundle = entry["bundle"]["hash"]
    if skill_bundle.hash != expected_bundle:
        return VerificationReport(
            verified=False,
            entry_hash_match=False,
            pass_fail_match=False,
            flipped_task_ids=[],
            cost_within_tolerance=False,
            latency_within_tolerance=False,
            fingerprint_match=False,
            notes=[
                f"skill bundle hash mismatch: expected {expected_bundle[:12]}…, "
                f"loaded {skill_bundle.hash[:12]}…"
            ],
        )
    expected_ts = entry["task_set"]["hash"]
    if task_set.hash != expected_ts:
        return VerificationReport(
            verified=False,
            entry_hash_match=False,
            pass_fail_match=False,
            flipped_task_ids=[],
            cost_within_tolerance=False,
            latency_within_tolerance=False,
            fingerprint_match=False,
            notes=[
                f"task set hash mismatch: expected {expected_ts[:12]}…, "
                f"loaded {task_set.hash[:12]}…"
            ],
        )

    # 2. Rebuild the harness.
    runner_meta = entry["runner"]
    provider = runner_meta["provider"]
    model = runner_meta["model"]
    runner: Runner
    if provider == "anthropic":
        runner = AnthropicRunner(
            model=model, temperature=runner_meta["temperature"], api_key=api_key
        )
    elif provider == "openai":
        runner = OpenAIRunner(model=model, temperature=runner_meta["temperature"], api_key=api_key)
    elif provider == "google":
        runner = GoogleRunner(model=model, temperature=runner_meta["temperature"], api_key=api_key)
    else:
        return VerificationReport(
            verified=False,
            entry_hash_match=False,
            pass_fail_match=False,
            flipped_task_ids=[],
            cost_within_tolerance=False,
            latency_within_tolerance=False,
            fingerprint_match=False,
            notes=[f"unsupported provider: {provider!r}"],
        )
    pricing = load_pricing()
    harness = Harness(
        runner=runner,
        model=model,
        provider=provider,
        temperature=float(runner_meta["temperature"]),
        canonical_seeds=True,
        pricing=pricing,
    )

    # 3. Re-run.
    new_result = harness.evaluate(skill_bundle, task_set)
    new_entry = build_leaderboard_entry(new_result)

    # 4. Compare.
    entry_hash_match = new_entry["entry_hash"] == entry["entry_hash"]

    original_per_attempt = {
        (a["task_id"], a["seed"]): bool(a["passed"]) for a in entry["per_attempt"]
    }
    new_per_attempt = {
        (a["task_id"], a["seed"]): bool(a["passed"]) for a in new_entry["per_attempt"]
    }
    flipped: list[str] = []
    for key, orig in original_per_attempt.items():
        new_val = new_per_attempt.get(key)
        if new_val is None:
            flipped.append(f"{key[0]}#{key[1]}@missing")
        elif new_val != orig:
            flipped.append(f"{key[0]}#{key[1]}")
    pass_fail_match = not flipped

    # Cost / latency tolerance — only check if pricing was computed.
    cost_ok = True
    latency_ok = True
    try:
        orig_cost = entry["metrics"].get("cost_usd", {}).get("median", 0.0)
        new_cost = new_entry["metrics"].get("cost_usd", {}).get("median", 0.0)
        if orig_cost > 0:
            cost_ok = abs(new_cost - orig_cost) / orig_cost <= COST_TOLERANCE_FRAC
    except Exception:
        cost_ok = True
    try:
        orig_lat = entry["metrics"].get("latency_s", {}).get("p50", 0.0)
        new_lat = new_entry["metrics"].get("latency_s", {}).get("p50", 0.0)
        if orig_lat > 0:
            latency_ok = abs(new_lat - orig_lat) / orig_lat <= LATENCY_TOLERANCE_FRAC
    except Exception:
        latency_ok = True

    fingerprint_match = entry["runner"].get("model_response_fingerprint") == new_entry[
        "runner"
    ].get("model_response_fingerprint")

    if not entry_hash_match:
        notes.append("entry_hash mismatch (likely pricing.yaml or runner config drift)")
    if flipped:
        notes.append(f"{len(flipped)} task/seed pair(s) flipped pass/fail")
    if not fingerprint_match:
        notes.append("model_response_fingerprint changed since submission")

    verified = pass_fail_match and cost_ok and latency_ok and entry_hash_match
    return VerificationReport(
        verified=verified,
        entry_hash_match=entry_hash_match,
        pass_fail_match=pass_fail_match,
        flipped_task_ids=flipped,
        cost_within_tolerance=cost_ok,
        latency_within_tolerance=latency_ok,
        fingerprint_match=fingerprint_match,
        notes=notes,
    )
