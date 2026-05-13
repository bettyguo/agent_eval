"""Execute a task's grader script and return its GraderResult.

Implements the grader interface contract from docs/tasks.md §3. The grader
script is executed in a restricted namespace; it must define a `grade(workdir,
trajectory, final_state)` function. Hard 30-second wall-time per docs/tasks.md
§3.4.
"""

from __future__ import annotations

import signal
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from agenteval.errors import GraderError
from agenteval.grading.types import FinalState, GraderResult, TrajectoryStep
from agenteval.grading.utils import (
    assert_unchanged,
    ast_function_count,
    ast_normalised_equal,
    count_assertions,
    first_modify_time,
    grep_final_message,
    grep_repo,
    localizes_to_line,
    no_suppressions,
    ran_pytest_failure_then_success,
    run_command,
)
from agenteval.tasks.registry import Task

GRADER_TIMEOUT_S = 30


def run_grader(
    task: Task,
    workdir: Path,
    trajectory: Sequence[TrajectoryStep],
    final_state: FinalState,
) -> GraderResult:
    """Run the task's grader script and return its result."""
    script = task.meta.grader.script
    namespace: dict[str, Any] = _build_grader_namespace()

    try:
        compiled = compile(script, f"<grader:{task.id}>", "exec")
    except SyntaxError as exc:
        raise GraderError(
            f"grader for task {task.id!r} has syntax error: {exc}",
            task_id=task.id,
        ) from exc

    try:
        exec(compiled, namespace)
    except Exception as exc:
        raise GraderError(
            f"grader for task {task.id!r} failed at import-time: {exc}",
            task_id=task.id,
            traceback=traceback.format_exc(),
        ) from exc

    grade_fn = namespace.get("grade")
    if not callable(grade_fn):
        raise GraderError(
            f"grader for task {task.id!r} did not define a callable `grade(...)`",
            task_id=task.id,
        )

    with _Timeout(GRADER_TIMEOUT_S, task.id):
        try:
            raw = grade_fn(workdir, list(trajectory), final_state)
        except Exception as exc:
            raise GraderError(
                f"grader for task {task.id!r} raised: {exc}",
                task_id=task.id,
                traceback=traceback.format_exc(),
            ) from exc

    return _coerce(raw, task.id)


def _build_grader_namespace() -> dict[str, Any]:
    """Build the restricted namespace graders run in.

    They get the shared utility library (docs/tasks.md §3.5) and the dataclasses
    they need. They do NOT get `os`, `subprocess`, etc. directly — those are
    funnelled through `run_command` for auditability.
    """
    return {
        # types
        "GraderResult": GraderResult,
        "FinalState": FinalState,
        "TrajectoryStep": TrajectoryStep,
        # utilities (docs/tasks.md §3.5)
        "ast_function_count": ast_function_count,
        "ast_normalised_equal": ast_normalised_equal,
        "assert_unchanged": assert_unchanged,
        "count_assertions": count_assertions,
        "first_modify_time": first_modify_time,
        "grep_final_message": grep_final_message,
        "grep_repo": grep_repo,
        "localizes_to_line": localizes_to_line,
        "no_suppressions": no_suppressions,
        "ran_pytest_failure_then_success": ran_pytest_failure_then_success,
        "run_command": run_command,
    }


def _coerce(raw: Any, task_id: str) -> GraderResult:
    """Accept either GraderResult or a dict-with-passed."""
    if isinstance(raw, GraderResult):
        return raw
    if isinstance(raw, dict) and "passed" in raw:
        return GraderResult(passed=bool(raw["passed"]), details=raw.get("details", {}))
    raise GraderError(
        f"grader for task {task_id!r} returned a {type(raw).__name__}, "
        f"expected GraderResult or {{'passed': bool, 'details': dict}}",
        task_id=task_id,
    )


class _Timeout:
    """Cross-platform-ish timeout. Uses SIGALRM on POSIX; no-op on Windows.

    On Windows, the harness's outer sandbox wall-time enforcement remains the
    primary boundary; the grader's own 30-s budget is a courtesy ceiling. A
    real subprocess sandbox in M2 enforces it strictly.
    """

    def __init__(self, seconds: int, task_id: str) -> None:
        self.seconds = seconds
        self.task_id = task_id
        self._prev_handler: Any = None
        self._enabled = sys.platform != "win32" and hasattr(signal, "SIGALRM")

    def __enter__(self) -> _Timeout:
        if not self._enabled:
            return self
        self._prev_handler = signal.signal(signal.SIGALRM, self._on_timeout)  # type: ignore[attr-defined]  # SIGALRM is POSIX-only; this branch is platform-gated
        signal.alarm(self.seconds)  # type: ignore[attr-defined]
        return self

    def __exit__(self, *args: Any) -> None:
        if not self._enabled:
            return
        signal.alarm(0)  # type: ignore[attr-defined]
        if self._prev_handler is not None:
            signal.signal(signal.SIGALRM, self._prev_handler)  # type: ignore[attr-defined]

    def _on_timeout(self, *_: Any) -> None:
        raise GraderError(
            f"grader for task {self.task_id!r} exceeded {self.seconds}s wall-time",
            task_id=self.task_id,
        )
