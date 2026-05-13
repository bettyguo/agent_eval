"""End-to-end harness wiring smoke test.

Uses MockRunner so the test doesn't consume API credits and runs in CI.
Exercises the full SkillBundle.empty() -> TaskSet -> Harness path and the
eligibility logic for canonical / non-canonical / temperature-perturbed runs.
"""

from __future__ import annotations

from agenteval.harness import Harness
from agenteval.runners.mock import MockRunner, MockTurn
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task, TaskSet


def _code_review_solver_turns(task: Task) -> list[MockTurn]:
    """A scripted mock that 'solves' code-review-01 by naming the bug class + line."""
    return [
        MockTurn(
            text=(
                "I reviewed buggy.py and found an off-by-one error at buggy.py:12. "
                "The slice `items[-n - 1:]` returns one item too many; it should be `items[-n:]`."
            ),
            tool_calls=None,
            tokens_in=200,
            tokens_out=100,
            stop=True,
        ),
    ]


def _generic_giveup_turns() -> list[MockTurn]:
    """A scripted mock that gives up immediately without producing useful output."""
    return [
        MockTurn(
            text="I am a mock and have not done the task.",
            tool_calls=None,
            tokens_in=50,
            tokens_out=20,
            stop=True,
        ),
    ]


def _scripted(task: Task, history):
    """Dispatch per-task scripts so the demo path exercises both pass and fail outcomes."""
    if task.id == "code-review-01":
        turns = _code_review_solver_turns(task)
    else:
        turns = _generic_giveup_turns()
    idx = len(history)
    if idx >= len(turns):
        return MockTurn(text="", tool_calls=None, stop=True)
    return turns[idx]


def test_demo_path(reference_task_set: TaskSet):
    runner = MockRunner(script=_scripted)
    harness = Harness(
        runner=runner,
        model="mock-model",
        temperature=0.0,
        canonical_seeds=True,
    )
    bundle = SkillBundle.empty()
    result = harness.evaluate(bundle, reference_task_set)

    # 20 tasks × 5 seeds = 100 attempts.
    assert len(result.per_attempt) == 100

    summary = result.summary()
    assert summary["n_attempts"] == 100
    # Only code-review-01 is solved by the mock; the bug-line localization for
    # code-review-02..04 (different keywords) won't match. So 1/20 tasks pass.
    assert abs(summary["pass@1"]["point"] - 0.05) < 1e-6
    assert abs(summary["pass^5"]["point"] - 0.05) < 1e-6

    # Eligibility: temperature 0.0, canonical seeds, primary panel — eligible.
    assert result.leaderboard_eligible is True
    entry = result.to_leaderboard_entry()
    assert entry["task_set"]["name"] == "skill-specific-v1"
    assert entry["runner"]["seeds"] == [1, 2, 3, 4, 5]


def test_exploratory_mode_not_eligible(reference_task_set: TaskSet):
    runner = MockRunner(script=_scripted)
    harness = Harness(
        runner=runner,
        model="mock-model",
        temperature=0.0,
        canonical_seeds=False,
        custom_seeds=[7],
    )
    result = harness.evaluate(SkillBundle.empty(), reference_task_set)
    assert result.leaderboard_eligible is False

    # to_leaderboard_entry must refuse.
    import pytest

    from agenteval.errors import LeaderboardIneligible

    with pytest.raises(LeaderboardIneligible):
        result.to_leaderboard_entry()


def test_non_zero_temperature_not_eligible(reference_task_set: TaskSet):
    runner = MockRunner(script=_scripted)
    harness = Harness(
        runner=runner,
        model="mock-model",
        temperature=0.5,
        canonical_seeds=True,
    )
    result = harness.evaluate(SkillBundle.empty(), reference_task_set)
    assert result.leaderboard_eligible is False
