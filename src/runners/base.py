"""Runner ABC and the RunOutcome it returns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agenteval.grading.types import FinalState, TrajectoryStep
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task


@dataclass(frozen=True)
class RunOutcome:
    trajectory: tuple[TrajectoryStep, ...]
    final_state: FinalState
    tokens_in: int
    tokens_out: int
    latency_s: float
    tool_calls: int
    model_response_fingerprint: str | None = None
    aux: dict[str, object] = field(default_factory=dict)


class Runner(ABC):
    """One run per (task, seed). Stateless across runs by contract."""

    name: str = "abstract"

    @abstractmethod
    def run(
        self,
        *,
        bundle: SkillBundle,
        task: Task,
        sandbox: Sandbox,
        seed: int,
    ) -> RunOutcome: ...
