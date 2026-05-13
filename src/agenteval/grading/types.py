"""Dataclasses for the grader interface (docs/tasks.md §3.2, §3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TrajectoryTool = Literal[
    "Read", "Write", "Edit", "Bash", "Glob", "Grep", "Other"
]


@dataclass(frozen=True)
class TrajectoryStep:
    """A single normalized step in the agent's trajectory."""

    t: float  # seconds since task start
    tool: TrajectoryTool
    args: dict[str, Any]
    result: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class FinalState:
    """The terminal state passed to the grader (docs/tasks.md §3.3)."""

    assistant_final_message: str
    file_hashes: dict[str, str]
    timed_out: bool
    raw_response_fingerprint: str | None = None


@dataclass(frozen=True)
class GraderResult:
    """What a grader returns. `details` is free-form structured data for the run record."""

    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "details": self.details}
