"""Grader interface, shared utilities, and execution.

Implements docs/tasks.md §3 (grader interface contract) and §3.5 (shared utility
library). Graders are deterministic Python (ADR-0006: no LLM-as-judge).
"""

from agenteval.grading.runner import run_grader
from agenteval.grading.types import (
    FinalState,
    GraderResult,
    TrajectoryStep,
    TrajectoryTool,
)
from agenteval.grading.utils import (
    ast_function_count,
    ast_normalised_equal,
    assert_unchanged,
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
