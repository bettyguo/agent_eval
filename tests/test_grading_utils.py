"""Tests for the shared grader utility library (docs/tasks.md §3.5)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from agenteval.grading.types import TrajectoryStep
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
)


def step(t: float, tool: str, args: dict, result: dict) -> TrajectoryStep:
    return TrajectoryStep(t=t, tool=tool, args=args, result=result)  # type: ignore[arg-type]


class TestFirstModifyTime:
    def test_returns_earliest_match(self):
        traj = [
            step(0.1, "Read", {"path": "a.py"}, {}),
            step(0.2, "Write", {"path": "a.py", "content": "..."}, {}),
            step(0.3, "Edit", {"path": "a.py", "old_string": "x", "new_string": "y"}, {}),
        ]
        assert first_modify_time(traj, "a.py") == 0.2

    def test_returns_none_when_absent(self):
        traj = [step(0.1, "Read", {"path": "b.py"}, {})]
        assert first_modify_time(traj, "a.py") is None

    def test_normalizes_paths(self):
        traj = [step(0.1, "Write", {"path": "./a.py"}, {})]
        assert first_modify_time(traj, "a.py") == 0.1


class TestRanPytestFailureThenSuccess:
    def test_true_for_fail_then_pass(self):
        traj = [
            step(0.1, "Bash", {"command": "pytest -q"}, {"exit_code": 1}),
            step(0.5, "Bash", {"command": "pytest -q"}, {"exit_code": 0}),
        ]
        assert ran_pytest_failure_then_success(traj)

    def test_false_when_only_passing(self):
        traj = [step(0.1, "Bash", {"command": "pytest -q"}, {"exit_code": 0})]
        assert not ran_pytest_failure_then_success(traj)

    def test_false_when_pass_before_fail(self):
        traj = [
            step(0.1, "Bash", {"command": "pytest -q"}, {"exit_code": 0}),
            step(0.2, "Bash", {"command": "pytest -q"}, {"exit_code": 1}),
        ]
        assert not ran_pytest_failure_then_success(traj)


class TestCountAssertions:
    def test_counts_assert_nodes(self, tmp_path: Path):
        p = tmp_path / "t.py"
        p.write_text(
            "def test():\n    assert 1\n    assert 2\n    if True:\n        assert 3\n",
            encoding="utf-8",
        )
        assert count_assertions(p) == 3

    def test_missing_file_returns_zero(self, tmp_path: Path):
        assert count_assertions(tmp_path / "missing.py") == 0

    def test_syntax_error_returns_zero(self, tmp_path: Path):
        p = tmp_path / "bad.py"
        p.write_text("def (((", encoding="utf-8")
        assert count_assertions(p) == 0


class TestGrepFinalMessage:
    def test_case_insensitive(self):
        assert grep_final_message("This is an OFF-BY-ONE bug", [r"off.?by.?one"])

    def test_no_match(self):
        assert not grep_final_message("nothing here", [r"missing"])


class TestLocalizesToLine:
    def test_matches_file_colon_line(self):
        assert localizes_to_line("see buggy.py:12 for the issue", "buggy.py", 12)

    def test_within_tolerance(self):
        assert localizes_to_line("see buggy.py:14 for the issue", "buggy.py", 12, tolerance=2)

    def test_outside_tolerance(self):
        assert not localizes_to_line("buggy.py:20", "buggy.py", 12, tolerance=2)

    def test_line_keyword_form(self):
        assert localizes_to_line("buggy.py line 12", "buggy.py", 12)


class TestNoSuppressions:
    def test_no_suppressions_in_clean_file(self, tmp_path: Path):
        p = tmp_path / "clean.py"
        p.write_text("x = 1\n", encoding="utf-8")
        assert no_suppressions(p, forbidden=["noqa", "type: ignore"])

    def test_detects_suppression(self, tmp_path: Path):
        p = tmp_path / "dirty.py"
        p.write_text("x = 1  # noqa\n", encoding="utf-8")
        assert not no_suppressions(p, forbidden=["noqa", "type: ignore"])


class TestAstFunctionCount:
    def test_counts_top_level_and_nested(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text(
            "def a():\n    pass\n\ndef b():\n    def c(): pass\n    return c\n",
            encoding="utf-8",
        )
        assert ast_function_count(p) == 3


class TestAstNormalisedEqual:
    def test_equal_after_format_normalization(self, tmp_path: Path):
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("def f(x): return x + 1\n", encoding="utf-8")
        b.write_text(
            'def f(x):\n    """docstring."""\n    return x + 1\n',
            encoding="utf-8",
        )
        # Docstrings are stripped before comparison.
        assert ast_normalised_equal(a, b)

    def test_not_equal_after_semantic_change(self, tmp_path: Path):
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("def f(x): return x + 1\n", encoding="utf-8")
        b.write_text("def f(x): return x + 2\n", encoding="utf-8")
        assert not ast_normalised_equal(a, b)


class TestAssertUnchanged:
    def test_matching_hash(self, tmp_path: Path):
        p = tmp_path / "f.txt"
        p.write_text("hello", encoding="utf-8")
        sha = hashlib.sha256(b"hello").hexdigest()
        assert_unchanged(p, sha)  # no raise

    def test_mismatch_raises(self, tmp_path: Path):
        p = tmp_path / "f.txt"
        p.write_text("hello", encoding="utf-8")
        try:
            assert_unchanged(p, "0" * 64)
        except AssertionError:
            return
        raise AssertionError("expected AssertionError")


class TestGrepRepo:
    def test_finds_pattern(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("import os\nx = legacy_parse()\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("from c import parse\n", encoding="utf-8")
        matches = grep_repo(tmp_path, r"\blegacy_parse\b")
        assert len(matches) == 1
        assert matches[0][0].name == "a.py"
        assert matches[0][1] == 2

    def test_returns_empty_when_no_match(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        assert grep_repo(tmp_path, r"\blegacy_parse\b") == []
