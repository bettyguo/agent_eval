"""Hardened Docker sandbox (M2).

Implements `docs/sandbox.md` §1 modulo the SHA-pinning (M5 hardening). Each
(task, seed) attempt gets a fresh container with the constraints:

- Pinned image tag (`agenteval-sandbox:base`, built from sandbox/Dockerfile.base).
- 1 CPU, 2 GB RAM, 5-min wall-time default.
- Network disabled by default; task spec may opt in via `network: true`.
- No host filesystem mount outside the per-attempt working directory.
- Skill bundle injected at `~/.claude/skills/` (and shadow-copied to
  `workdir/.claude/skills/` so the agent's relative-path tools also find it).

Tool dispatch:
- File operations (`read_file`, `write_file`, `edit_file`, `glob`, `grep`) work
  on the host-side workdir bind-mount; this is the fastest correct option.
- `execute_bash` is `docker exec` into the running container.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from agenteval.errors import SandboxError
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle

DEFAULT_IMAGE_TAG = "agenteval-sandbox:base"
DEFAULT_MEMORY = "2g"
DEFAULT_CPUS = 1.0
DEFAULT_TIME_BUDGET_S = 300


class DockerSandbox(Sandbox):
    """One Docker container per (task, seed) attempt. Auto-discarded on teardown."""

    def __init__(
        self,
        *,
        image: str = DEFAULT_IMAGE_TAG,
        memory: str = DEFAULT_MEMORY,
        cpus: float = DEFAULT_CPUS,
        network: bool = False,
        user: str = "agenteval",
    ) -> None:
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.network_enabled = network
        self.user = user
        self._host_workdir: Path | None = None
        self._container: Any = None
        self._client: Any = None
        self._setup_done = False
        self._pip_installed: list[str] = []

    # ---------- Sandbox API ----------

    def setup(
        self,
        *,
        files: dict[str, str],
        pip_install: list[str],
        skill_bundle: SkillBundle,
    ) -> None:
        if self._setup_done:
            raise SandboxError("sandbox already set up")
        self._ensure_client()
        self._host_workdir = Path(tempfile.mkdtemp(prefix="agenteval-docker-"))

        try:
            # 1. Materialise task setup.files on the host (bind-mounted into the container).
            for relpath, content in files.items():
                self._write_host_file(relpath, content)

            # 2. Shadow-copy the skill bundle to workdir/.claude/skills/ so the
            #    agent's relative-path tools also find it (M2 belt-and-braces).
            self._materialize_skill_bundle_in_workdir(skill_bundle)

            # 3. Launch the container with mounts + resource limits.
            self._container = self._client.containers.run(
                image=self.image,
                command="sleep infinity",
                detach=True,
                auto_remove=False,
                network_mode="none" if not self.network_enabled else "bridge",
                mem_limit=self.memory,
                nano_cpus=int(self.cpus * 1_000_000_000),
                user=self.user,
                working_dir="/work",
                volumes={
                    str(self._host_workdir): {"bind": "/work", "mode": "rw"},
                },
                tty=False,
                stdin_open=False,
                read_only=False,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
            )

            # 4. Inject skills at the canonical ~/.claude/skills/ location inside
            #    the container (separate from the workdir shadow copy). This is
            #    written via `docker cp`-style stream so it lives outside the
            #    mounted workdir and isn't overwritten by agent writes.
            self._inject_skills_in_home(skill_bundle)

            # 5. Run per-task pip_install.
            if pip_install:
                self._run_pip_install(pip_install)
        except Exception:
            self.teardown()
            raise

        self._setup_done = True

    def workdir(self) -> Path:
        if self._host_workdir is None:
            raise SandboxError("sandbox not set up")
        return self._host_workdir

    def execute_bash(self, command: str, *, timeout: float) -> dict[str, Any]:
        if self._container is None:
            raise SandboxError("sandbox not set up")
        start = time.monotonic()
        try:
            exec_id = self._client.api.exec_create(
                self._container.id,
                cmd=["bash", "-c", command],
                user=self.user,
                workdir="/work",
                stdout=True,
                stderr=True,
                tty=False,
            )
        except Exception as exc:
            raise SandboxError(f"docker exec_create failed: {exc}") from exc

        try:
            output = self._client.api.exec_start(exec_id, stream=False, demux=True)
        except Exception as exc:
            raise SandboxError(f"docker exec_start failed: {exc}") from exc

        # demux=True returns (stdout_bytes, stderr_bytes); when not demuxed it's bytes.
        stdout_bytes, stderr_bytes = output if isinstance(output, tuple) else (output, b"")
        stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
        stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

        info = self._client.api.exec_inspect(exec_id["Id"])
        exit_code = info.get("ExitCode")
        elapsed = time.monotonic() - start
        timed_out = elapsed > timeout

        return {
            "exit_code": int(exit_code) if exit_code is not None else 1,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
            "duration_s": elapsed,
        }

    def read_file(self, path: str) -> str:
        abs_path = self._resolve_inside_workdir(path)
        if not abs_path.exists():
            raise SandboxError(f"file not found in sandbox: {path}", path=path)
        return abs_path.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        abs_path = self._resolve_inside_workdir(path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8"))}

    def edit_file(self, path: str, old_string: str, new_string: str) -> dict[str, Any]:
        abs_path = self._resolve_inside_workdir(path)
        if not abs_path.exists():
            raise SandboxError(f"cannot edit missing file: {path}", path=path)
        text = abs_path.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return {"path": path, "replaced": 0, "error": "old_string not found"}
        if count > 1:
            return {"path": path, "replaced": 0, "error": "old_string not unique"}
        new_text = text.replace(old_string, new_string)
        abs_path.write_text(new_text, encoding="utf-8")
        return {
            "path": path,
            "replaced": 1,
            "bytes_written": len(new_text.encode("utf-8")),
        }

    def glob(self, pattern: str) -> list[str]:
        root = self.workdir()
        if "**" in pattern:
            matches = list(root.rglob(pattern.replace("**/", "")))
        else:
            matches = list(root.glob(pattern))
        return [str(p.relative_to(root)).replace("\\", "/") for p in matches if p.is_file()]

    def grep(self, pattern: str, path: str | None = None) -> list[dict[str, Any]]:
        root = self.workdir()
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise SandboxError(f"invalid regex {pattern!r}: {exc}") from exc

        target: list[Path] = []
        if path is None:
            target.extend(p for p in root.rglob("*") if p.is_file())
        else:
            base = self._resolve_inside_workdir(path)
            if base.is_file():
                target.append(base)
            elif base.is_dir():
                target.extend(p for p in base.rglob("*") if p.is_file())

        results: list[dict[str, Any]] = []
        for f in target:
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    results.append(
                        {
                            "path": str(f.relative_to(root)).replace("\\", "/"),
                            "line": i,
                            "match": line,
                        }
                    )
        return results

    def file_hashes(self) -> dict[str, str]:
        root = self.workdir()
        out: dict[str, str] = {}
        for f in sorted(root.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(root)).replace("\\", "/")
                out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return out

    def teardown(self) -> None:
        if self._container is not None:
            try:
                self._container.stop(timeout=2)
            except Exception:
                pass
            try:
                self._container.remove(force=True)
            except Exception:
                pass
            self._container = None
        if self._host_workdir and self._host_workdir.exists():
            shutil.rmtree(self._host_workdir, ignore_errors=True)
        self._host_workdir = None
        self._setup_done = False

    # ---------- internal ----------

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import docker
        except ImportError as exc:
            raise SandboxError("`docker` package not installed; run `pip install docker`") from exc
        try:
            self._client = docker.from_env()
            # Ping the daemon — fail fast.
            self._client.ping()
        except Exception as exc:
            raise SandboxError(
                f"Docker daemon unreachable. Is Docker Desktop running? Underlying error: {exc}"
            ) from exc

    def _resolve_inside_workdir(self, path: str) -> Path:
        root = self.workdir()
        if os.path.isabs(path):
            raise SandboxError(f"absolute paths not allowed in sandbox: {path}", path=path)
        candidate = (root / path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise SandboxError(f"path escapes sandbox workdir: {path}", path=path) from exc
        return candidate

    def _write_host_file(self, relpath: str, content: str) -> None:
        if self._host_workdir is None:
            raise SandboxError("sandbox not set up")
        abs_path = self._host_workdir / relpath
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")

    def _materialize_skill_bundle_in_workdir(self, bundle: SkillBundle) -> None:
        if not bundle.skills or self._host_workdir is None:
            return
        skills_root = self._host_workdir / ".claude" / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        for skill in bundle.skills:
            skill_dir = skills_root / skill.name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(_render_skill_md(skill), encoding="utf-8")

    def _inject_skills_in_home(self, bundle: SkillBundle) -> None:
        if not bundle.skills or self._container is None:
            return
        # Use docker exec to write the SKILL.md files into the container's home
        # dir. Keep it simple: base64-encode then decode on the inside.
        import base64

        for skill in bundle.skills:
            content = _render_skill_md(skill)
            b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            command = (
                f"mkdir -p /home/{self.user}/.claude/skills/{shlex_safe(skill.name)} && "
                f"printf '%s' '{b64}' | base64 -d > "
                f"/home/{self.user}/.claude/skills/{shlex_safe(skill.name)}/SKILL.md"
            )
            self.execute_bash(command, timeout=15.0)

    def _run_pip_install(self, packages: list[str]) -> None:
        if not packages or self._container is None:
            return
        # Sanity-check; reject anything that looks like a shell-injection.
        for pkg in packages:
            if not _safe_pip_token(pkg):
                raise SandboxError(
                    f"unsafe pip_install token rejected: {pkg!r}",
                    package=pkg,
                )
        cmd = "pip install --user " + " ".join(packages)
        result = self.execute_bash(cmd, timeout=180.0)
        if result["exit_code"] != 0:
            raise SandboxError(
                f"pip_install failed: {result['stderr'][-500:]}",
                packages=packages,
            )
        self._pip_installed = list(packages)


def _render_skill_md(skill: Any) -> str:
    """Render a Skill as a frontmatter+body SKILL.md."""
    name = skill.name
    description = skill.description
    license_line = f"license: {skill.license}\n" if getattr(skill, "license", None) else ""
    return f"---\nname: {name}\ndescription: {description}\n{license_line}---\n{skill.body}"


def shlex_safe(value: str) -> str:
    """Tightly restrict skill names used in shell paths."""
    if not re.match(r"^[a-zA-Z0-9._-]+$", value):
        raise SandboxError(
            f"skill name has unsafe characters for shell paths: {value!r}",
            name=value,
        )
    return value


def _safe_pip_token(value: str) -> bool:
    """Allow standard pip package specifiers; reject shell metacharacters."""
    return bool(
        re.match(r"^[A-Za-z0-9_\-]+(\[[A-Za-z0-9_\-,]+\])?([=<>!~]=?[A-Za-z0-9_.\-]+)?$", value)
    )
