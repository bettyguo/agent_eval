"""Schema validation tests (docs/tasks.md §1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agenteval.tasks.schema import Grader, TaskMeta, TaskSetMeta


def _valid_task_kwargs(**overrides):
    base = {
        "id": "tdd-enforcement-01",
        "category": "tdd-enforcement",
        "description": "A test task.",
        "license": "MIT",
        "prompt": "Do the thing.",
        "grader": {
            "type": "python",
            "script": "def grade(workdir, trajectory, final_state):\n    return {'passed': True, 'details': {}}",
        },
    }
    base.update(overrides)
    return base


class TestTaskMeta:
    def test_minimal_valid(self):
        m = TaskMeta.model_validate(_valid_task_kwargs())
        assert m.id == "tdd-enforcement-01"
        assert m.category == "tdd-enforcement"
        assert m.time_budget_s == 300  # default

    def test_unknown_key_rejected(self):
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(extra_key=1))

    def test_bad_id_pattern(self):
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(id="BadID-01"))
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(id="123-numeric-first"))

    def test_unknown_category(self):
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(category="not-a-category"))

    def test_description_length(self):
        long = "x" * 201
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(description=long))

    def test_time_budget_capped(self):
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(time_budget_s=301))
        with pytest.raises(ValidationError):
            TaskMeta.model_validate(_valid_task_kwargs(time_budget_s=0))


class TestGraderLLMBan:
    """ADR-0006: grader scripts may not import LLM SDKs."""

    @pytest.mark.parametrize(
        "forbidden",
        [
            "import anthropic\n",
            "import openai\n",
            "from anthropic import Anthropic\n",
            "from openai import OpenAI\n",
            "import google.generativeai as genai\n",
            "from google.genai import Client\n",
        ],
    )
    def test_forbidden_imports_rejected(self, forbidden):
        with pytest.raises(ValidationError):
            Grader(
                type="python", script=forbidden + "def grade(*a, **k):\n    return {'passed': True}"
            )

    def test_innocent_imports_ok(self):
        Grader(
            type="python",
            script="import ast\nimport os\ndef grade(*a, **k):\n    return {'passed': True}",
        )


class TestTaskSetMeta:
    def test_minimal_valid(self):
        m = TaskSetMeta.model_validate(
            {
                "name": "skill-specific-v1",
                "version": "1",
                "panel": "primary",
                "description": "A task set.",
            }
        )
        assert m.panel == "primary"
        assert m.license == "Apache-2.0"  # default

    def test_panel_must_be_known(self):
        with pytest.raises(ValidationError):
            TaskSetMeta.model_validate(
                {
                    "name": "x",
                    "version": "1",
                    "panel": "tertiary",
                    "description": "y",
                }
            )
