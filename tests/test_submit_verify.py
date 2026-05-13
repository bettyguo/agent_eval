"""Tests for the submit/verify machinery (M5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenteval.errors import LeaderboardIneligible
from agenteval.harness import Harness
from agenteval.metrics import load_pricing
from agenteval.runners.mock import MockRunner, MockTurn
from agenteval.skills.bundle import SkillBundle
from agenteval.submit import SCHEMA_VERSION, build_leaderboard_entry
from agenteval.tasks.registry import TaskSet


def _giveup_script(task, history):
    if history:
        return MockTurn(stop=True)
    return MockTurn(text="giving up", stop=True, tokens_in=50, tokens_out=20)


def test_build_entry_eligible(reference_task_set: TaskSet):
    harness = Harness(
        runner=MockRunner(script=_giveup_script),
        model="mock-model",
        provider="anthropic",
        temperature=0.0,
        canonical_seeds=True,
        pricing=load_pricing(),
    )
    result = harness.evaluate(SkillBundle.empty(), reference_task_set)
    assert result.leaderboard_eligible
    entry = build_leaderboard_entry(result)
    assert entry["schema_version"] == SCHEMA_VERSION
    assert len(entry["entry_hash"]) == 64
    assert entry["runner"]["seeds"] == [1, 2, 3, 4, 5]
    assert entry["task_set"]["panel"] == "primary"


def test_build_entry_refuses_ineligible(reference_task_set: TaskSet):
    harness = Harness(
        runner=MockRunner(script=_giveup_script),
        model="mock-model",
        provider="anthropic",
        temperature=0.5,  # non-zero → ineligible
        canonical_seeds=True,
        pricing=load_pricing(),
    )
    result = harness.evaluate(SkillBundle.empty(), reference_task_set)
    assert not result.leaderboard_eligible
    with pytest.raises(LeaderboardIneligible):
        build_leaderboard_entry(result)


def test_entry_hash_stable_across_runs(reference_task_set: TaskSet):
    """Two runs of the deterministic mock should produce the same entry_hash."""
    pricing = load_pricing()
    h1 = Harness(
        runner=MockRunner(script=_giveup_script),
        model="mock-model",
        provider="anthropic",
        temperature=0.0,
        canonical_seeds=True,
        pricing=pricing,
    )
    e1 = build_leaderboard_entry(h1.evaluate(SkillBundle.empty(), reference_task_set))

    h2 = Harness(
        runner=MockRunner(script=_giveup_script),
        model="mock-model",
        provider="anthropic",
        temperature=0.0,
        canonical_seeds=True,
        pricing=pricing,
    )
    e2 = build_leaderboard_entry(h2.evaluate(SkillBundle.empty(), reference_task_set))

    # Bundle, task-set, model, temperature, seeds, pricing all match → same hash.
    assert e1["entry_hash"] == e2["entry_hash"]
