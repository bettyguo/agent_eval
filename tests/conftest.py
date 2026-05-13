"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenteval.tasks.registry import TaskSet


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def reference_task_set(repo_root: Path) -> TaskSet:
    return TaskSet.from_dir(repo_root / "tasks" / "skill-specific-v1")
