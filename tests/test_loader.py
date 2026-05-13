"""Tests for the task-set loader (src/agenteval/tasks/registry.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenteval.errors import TaskSetError
from agenteval.tasks.registry import TaskSet


def test_loads_reference_task_set(reference_task_set: TaskSet):
    assert reference_task_set.name == "skill-specific-v1"
    assert reference_task_set.panel == "primary"
    assert len(reference_task_set.tasks) == 20
    # 4 tasks per category × 5 categories.
    expected_categories = {
        "tdd-enforcement",
        "code-review",
        "style-adherence",
        "refactor",
        "multi-file",
    }
    found_categories = {t.category for t in reference_task_set.tasks}
    assert found_categories == expected_categories
    for cat in expected_categories:
        assert sum(1 for t in reference_task_set.tasks if t.category == cat) == 4


def test_hash_is_stable(reference_task_set: TaskSet, repo_root: Path):
    """Loading the same directory twice produces the same hash."""
    second = TaskSet.from_dir(repo_root / "tasks" / "skill-specific-v1")
    assert reference_task_set.hash == second.hash


def test_effective_panel_inherits_from_meta(reference_task_set: TaskSet):
    for t in reference_task_set.tasks:
        assert t.effective_panel == "primary"


def test_missing_meta_yaml_errors(tmp_path: Path):
    (tmp_path / "task.yaml").write_text("id: x\n", encoding="utf-8")
    with pytest.raises(TaskSetError):
        TaskSet.from_dir(tmp_path)


def test_filename_must_match_id(tmp_path: Path):
    (tmp_path / "meta.yaml").write_text(
        "name: x\nversion: '1'\npanel: primary\ndescription: y\n",
        encoding="utf-8",
    )
    (tmp_path / "wrong-name.yaml").write_text(
        "id: actual-id-01\ncategory: code-review\ndescription: x\n"
        "license: MIT\nprompt: 'p'\ngrader:\n  type: python\n  script: |\n"
        "    def grade(*a, **k):\n        return {'passed': True}\n",
        encoding="utf-8",
    )
    with pytest.raises(TaskSetError):
        TaskSet.from_dir(tmp_path)


def test_unknown_task_set_errors():
    with pytest.raises(TaskSetError):
        TaskSet.load("nonexistent-task-set-name")
