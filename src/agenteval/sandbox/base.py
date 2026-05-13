"""Sandbox abstract base.

The agent's tool calls (Bash, Read, Write, Edit, Glob, Grep) are dispatched to
a `Sandbox` instance. M1 = `LocalSubprocessSandbox` (no isolation, dev only).
M2 = `DockerSandbox` (hardened per `docs/sandbox.md`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from agenteval.skills.bundle import SkillBundle


class Sandbox(ABC):
    """One sandbox per (task, seed) attempt. Discarded after teardown."""

    @abstractmethod
    def setup(
        self,
        *,
        files: dict[str, str],
        pip_install: list[str],
        skill_bundle: SkillBundle,
    ) -> None: ...

    @abstractmethod
    def workdir(self) -> Path: ...

    @abstractmethod
    def execute_bash(self, command: str, *, timeout: float) -> dict[str, Any]: ...

    @abstractmethod
    def read_file(self, path: str) -> str: ...

    @abstractmethod
    def write_file(self, path: str, content: str) -> dict[str, Any]: ...

    @abstractmethod
    def edit_file(self, path: str, old_string: str, new_string: str) -> dict[str, Any]: ...

    @abstractmethod
    def glob(self, pattern: str) -> list[str]: ...

    @abstractmethod
    def grep(self, pattern: str, path: str | None = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    def file_hashes(self) -> dict[str, str]: ...

    @abstractmethod
    def teardown(self) -> None: ...

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(self, *args: Any) -> None:
        self.teardown()


class SandboxFactory(Protocol):
    """A zero-arg callable that creates a fresh sandbox. Lets Harness inject test doubles."""

    def __call__(self) -> Sandbox: ...
