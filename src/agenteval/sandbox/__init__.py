"""Sandbox layer.

M1 shipped `LocalSubprocessSandbox` (dev-only). M2 adds the hardened
`DockerSandbox` per `docs/sandbox.md`. The factory `default_sandbox_factory()`
selects via the `AGENTEVAL_SANDBOX` env var (default: `docker` when the daemon
is reachable; falls back to `local` with a warning otherwise).
"""

from __future__ import annotations

import os
import sys
from typing import Callable

from agenteval.sandbox.base import Sandbox, SandboxFactory
from agenteval.sandbox.docker import DockerSandbox
from agenteval.sandbox.local import LocalSubprocessSandbox

__all__ = [
    "DockerSandbox",
    "LocalSubprocessSandbox",
    "Sandbox",
    "SandboxFactory",
    "default_sandbox_factory",
]


def default_sandbox_factory() -> SandboxFactory:
    """Choose the sandbox backend based on env + Docker daemon availability."""
    selection = os.environ.get("AGENTEVAL_SANDBOX", "docker").lower()
    if selection == "local":
        return LocalSubprocessSandbox
    if selection != "docker":
        print(
            f"agenteval: unknown AGENTEVAL_SANDBOX={selection!r}; falling back to 'docker'",
            file=sys.stderr,
        )
    if _docker_daemon_reachable():
        return DockerSandbox
    print(
        "agenteval: Docker daemon unreachable; falling back to LocalSubprocessSandbox "
        "(trusted-task dev mode). Set AGENTEVAL_SANDBOX=local to silence this warning.",
        file=sys.stderr,
    )
    return LocalSubprocessSandbox


def _docker_daemon_reachable() -> bool:
    try:
        import docker  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False
