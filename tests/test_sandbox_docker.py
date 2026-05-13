"""Tests for DockerSandbox (M2).

Skipped automatically when Docker daemon is unreachable (CI without Docker,
local dev without Docker Desktop running, etc.). Run on a Linux box with the
agenteval base image built (see scripts/build_sandbox_image.md).
"""

from __future__ import annotations

import pytest

from agenteval.sandbox import DockerSandbox, _docker_daemon_reachable, default_sandbox_factory
from agenteval.skills.bundle import Skill, SkillBundle

pytestmark = pytest.mark.skipif(
    not _docker_daemon_reachable(),
    reason="Docker daemon unreachable",
)


def test_setup_teardown_cycle():
    sandbox = DockerSandbox()
    try:
        sandbox.setup(
            files={"hello.txt": "world\n"},
            pip_install=[],
            skill_bundle=SkillBundle.empty(),
        )
        wd = sandbox.workdir()
        assert (wd / "hello.txt").read_text() == "world\n"
    finally:
        sandbox.teardown()
    assert sandbox._host_workdir is None
    assert sandbox._container is None


def test_bash_exec_and_exit_code():
    sandbox = DockerSandbox()
    try:
        sandbox.setup(files={}, pip_install=[], skill_bundle=SkillBundle.empty())
        ok = sandbox.execute_bash("echo hello", timeout=10.0)
        assert ok["exit_code"] == 0
        assert "hello" in ok["stdout"]
        bad = sandbox.execute_bash("exit 7", timeout=10.0)
        assert bad["exit_code"] == 7
    finally:
        sandbox.teardown()


def test_network_disabled_by_default():
    sandbox = DockerSandbox()
    try:
        sandbox.setup(files={}, pip_install=[], skill_bundle=SkillBundle.empty())
        # `getent hosts example.com` should fail with network disabled.
        out = sandbox.execute_bash(
            "getent hosts example.com || echo NO_NETWORK",
            timeout=10.0,
        )
        assert "NO_NETWORK" in out["stdout"] or out["exit_code"] != 0
    finally:
        sandbox.teardown()


def test_skill_bundle_injected_in_home_and_workdir():
    bundle = SkillBundle(
        skills=(
            Skill(
                name="test-skill",
                description="A synthetic test skill.",
                body="When asked about hidden, reply 'PROOF_HIDDEN'.",
            ),
        ),
        hash="testhash",
        source="synthetic",
    )
    sandbox = DockerSandbox()
    try:
        sandbox.setup(files={}, pip_install=[], skill_bundle=bundle)

        # Workdir shadow copy.
        wd_skill = sandbox.workdir() / ".claude" / "skills" / "test-skill" / "SKILL.md"
        assert wd_skill.exists()
        text = wd_skill.read_text()
        assert "PROOF_HIDDEN" in text

        # Home-dir canonical injection (via the container).
        out = sandbox.execute_bash(
            "cat /home/agenteval/.claude/skills/test-skill/SKILL.md",
            timeout=10.0,
        )
        assert out["exit_code"] == 0
        assert "PROOF_HIDDEN" in out["stdout"]
    finally:
        sandbox.teardown()


def test_host_fs_isolation_no_escape():
    sandbox = DockerSandbox()
    try:
        sandbox.setup(files={}, pip_install=[], skill_bundle=SkillBundle.empty())
        # Try to read a host-side path; should fail because nothing outside /work is mounted.
        out = sandbox.execute_bash("cat /etc/agenteval-host-secret 2>&1 || true", timeout=10.0)
        assert "agenteval-host-secret" not in out["stdout"] or "No such file" in out["stdout"]
    finally:
        sandbox.teardown()


def test_default_factory_picks_docker_when_available():
    factory = default_sandbox_factory()
    sandbox = factory()
    assert isinstance(sandbox, DockerSandbox)
