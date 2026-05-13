"""Structured exception hierarchy for agenteval.

Every error carries a stable `code` string for CLI scripting and a `details` dict
for structured logging. See DESIGN.md §1.4.
"""

from __future__ import annotations

from typing import Any


class AgentevalError(Exception):
    """Base class. All agenteval errors derive from this."""

    code: str = "agenteval_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details


class SkillBundleError(AgentevalError):
    code = "skill_bundle_error"


class TaskSetError(AgentevalError):
    code = "task_set_error"


class SandboxError(AgentevalError):
    code = "sandbox_error"


class RunnerError(AgentevalError):
    code = "runner_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: int | None = None,
        retryable: bool = False,
        **details: Any,
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            status_code=status_code,
            retryable=retryable,
            **details,
        )


class LeaderboardIneligible(AgentevalError):
    code = "leaderboard_ineligible"


class VerifierMismatch(AgentevalError):
    code = "verifier_mismatch"

    def __init__(
        self,
        message: str,
        *,
        field: str,
        expected: Any,
        actual: Any,
        **details: Any,
    ) -> None:
        super().__init__(
            message, field=field, expected=expected, actual=actual, **details
        )


class GraderError(AgentevalError):
    """Raised when a grader script itself errors (distinct from a task failing)."""

    code = "grader_error"
