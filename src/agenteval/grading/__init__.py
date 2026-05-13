"""Grader interface, shared utilities, and execution.

Graders are deterministic Python (no LLM-as-judge in v1). See
`docs/tasks.md` for the interface contract.
"""

from agenteval.grading.runner import run_grader
from agenteval.grading.types import (
    FinalState,
    GraderResult,
    TrajectoryStep,
    TrajectoryTool,
)
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

__all__ = [
    "FinalState",
    "GraderResult",
    "TrajectoryStep",
    "TrajectoryTool",
    "ast_function_count",
    "ast_normalised_equal",
    "assert_unchanged",
    "count_assertions",
    "first_modify_time",
    "grep_final_message",
    "grep_repo",
    "localizes_to_line",
    "no_suppressions",
    "ran_pytest_failure_then_success",
    "run_command",
    "run_grader",
]
