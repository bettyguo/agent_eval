"""Pydantic v2 schema for task YAMLs and task-set meta.yaml.

Implements docs/tasks.md §1 verbatim. Strict mode; unknown keys forbidden; the
schema is locked at v1 — additions require a new task-set version, not a key
addition. See docs/tasks.md §4.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskCategory = Literal[
    "tdd-enforcement",
    "code-review",
    "style-adherence",
    "refactor",
    "multi-file",
]

GraderType = Literal["python"]
Panel = Literal["primary", "secondary"]

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
_FORBIDDEN_GRADER_IMPORTS = ("anthropic", "openai", "google.generativeai", "google.genai")


class _Strict(BaseModel):
    """Pydantic base with strict mode + unknown-key rejection (forward-compat via versioning)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Setup(_Strict):
    """Sandbox setup at task start. See docs/tasks.md §1."""

    files: dict[str, str] = Field(default_factory=dict)
    pip_install: list[str] = Field(default_factory=list)


class Grader(_Strict):
    """Deterministic Python grader. LLM-as-judge is disallowed in v1."""

    type: GraderType
    script: str

    @field_validator("script")
    @classmethod
    def _no_llm_imports(cls, v: str) -> str:
        for forbidden in _FORBIDDEN_GRADER_IMPORTS:
            patterns = [
                rf"^\s*import\s+{re.escape(forbidden)}\b",
                rf"^\s*from\s+{re.escape(forbidden)}\b",
            ]
            for pat in patterns:
                if re.search(pat, v, re.MULTILINE):
                    raise ValueError(
                        f"grader scripts may not import {forbidden!r} (no LLM-as-judge in v1)"
                    )
        return v


class TaskMeta(_Strict):
    """A single task YAML, fully parsed. Filename should match `{id}.yaml`."""

    id: str
    category: TaskCategory
    description: str = Field(min_length=1, max_length=200)
    license: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    setup: Setup = Field(default_factory=Setup)
    grader: Grader
    time_budget_s: int = Field(default=300, ge=1, le=300)
    expected_tokens: int = Field(default=5000, ge=1)
    network: bool = False
    panel: Panel | None = None  # if None, inherit from TaskSetMeta.panel

    @field_validator("id")
    @classmethod
    def _id_kebab(cls, v: str) -> str:
        if not _ID_PATTERN.match(v):
            raise ValueError(
                f"task id must be kebab-case matching {_ID_PATTERN.pattern!r}, got {v!r}"
            )
        return v


class TaskSetMeta(_Strict):
    """meta.yaml at the root of a task-set directory."""

    name: str
    version: str
    panel: Panel
    description: str = Field(min_length=1)
    license: str = Field(default="Apache-2.0")
    generator: str = Field(default="hand-curated")
    contamination_notes: str | None = None
