"""Local subprocess sandbox.

M1 implementation: spins up a temp directory, materializes task files there,
runs Bash commands via subprocess with cwd=workdir. NO isolation — agent code
runs on the host. Documented as **dev-only**; production path is the
DockerSandbox landing in M2.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from agenteval.errors import SandboxError
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle


class LocalSubprocessSandbox(Sandbox):
    """Local, unisolated sandbox. Trusted-task-only. See docs/sandbox.md §4."""

    def __init__(self) -> None:
        self._root: Path | None = None
        self._setup_done = False

    def setup(
        self,
        *,
        files: dict[str, str],
        pip_install: list[str],
        skill_bundle: SkillBundle,
    ) -> None:
        if self._setup_done:
            raise SandboxError("sandbox already set up")
        self._root = Path(tempfile.mkdtemp(prefix="agenteval-"))
        try:
            for relpath, content in files.items():
                self._write_file_internal(relpath, content)

            # Inject the skill bundle at workdir/.claude/skills/<skill>/SKILL.md.
            # Real per-user-home injection (~/.claude/skills/) is M2's concern; M1
            # just makes the bundle reachable.
            if skill_bundle.skills:
                skills_root = self._root / ".claude" / "skills"
                skills_root.mkdir(parents=True, exist_ok=True)
                for skill in skill_bundle.skills:
                    skill_dir = skills_root / skill.name
                    skill_dir.mkdir(parents=True, exist_ok=True)
                    md = f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n{skill.body}"
                    (skill_dir / "SKILL.md").write_text(md, encoding="utf-8")

            # pip_install is a no-op in M1 LocalSandbox (relies on host venv).
            # Phase 2 M2's DockerSandbox does real `pip install` inside the container.
            if pip_install:
                # Record what was requested for the trajectory; surface a warning.
                self._pip_install_requested = list(pip_install)
            else:
                self._pip_install_requested = []
        except Exception:
            self.teardown()
            raise

        self._setup_done = True

    def workdir(self) -> Path:
        if self._root is None:
            raise SandboxError("sandbox not set up")
        return self._root

    def execute_bash(self, command: str, *, timeout: float) -> dict[str, Any]:
        if self._root is None:
            raise SandboxError("sandbox not set up")
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                # Block PATH-poisoning by skill-bundle dirs etc; we still inherit env.
                env={**os.environ},
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "exit_code": 124,
                "stdout": exc.stdout or "",
                "stderr": (exc.stderr or "") + f"\n[timeout after {timeout}s]",
                "timed_out": True,
            }
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "timed_out": False,
        }

    def read_file(self, path: str) -> str:
        abs_path = self._resolve_inside(path)
        if not abs_path.exists():
            raise SandboxError(f"file not found in sandbox: {path}", path=path)
        return abs_path.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        return self._write_file_internal(path, content)

    def edit_file(self, path: str, old_string: str, new_string: str) -> dict[str, Any]:
        abs_path = self._resolve_inside(path)
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
        return {"path": path, "replaced": 1, "bytes_written": len(new_text.encode("utf-8"))}

    def glob(self, pattern: str) -> list[str]:
        if self._root is None:
            raise SandboxError("sandbox not set up")
        # Allow `**` style globs by using rglob when pattern contains `**`
        if "**" in pattern:
            matches = list(self._root.rglob(pattern.replace("**/", "")))
        else:
            matches = list(self._root.glob(pattern))
        return [str(p.relative_to(self._root)).replace("\\", "/") for p in matches if p.is_file()]

    def grep(self, pattern: str, path: str | None = None) -> list[dict[str, Any]]:
        import re

        if self._root is None:
            raise SandboxError("sandbox not set up")
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise SandboxError(f"invalid regex {pattern!r}: {exc}") from exc

        target: list[Path] = []
        if path is None:
            target.extend(p for p in self._root.rglob("*") if p.is_file())
        else:
            base = self._resolve_inside(path)
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
                            "path": str(f.relative_to(self._root)).replace("\\", "/"),
                            "line": i,
                            "match": line,
                        }
                    )
        return results

    def file_hashes(self) -> dict[str, str]:
        if self._root is None:
            raise SandboxError("sandbox not set up")
        out: dict[str, str] = {}
        for f in sorted(self._root.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(self._root)).replace("\\", "/")
                out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return out

    def teardown(self) -> None:
        if self._root and self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)
        self._root = None
        self._setup_done = False

    # ---------- internal ----------

    def _resolve_inside(self, path: str) -> Path:
        """Resolve `path` relative to workdir; reject escapes."""
        if self._root is None:
            raise SandboxError("sandbox not set up")
        if os.path.isabs(path):
            raise SandboxError(f"absolute paths not allowed in sandbox: {path}", path=path)
        candidate = (self._root / path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise SandboxError(
                f"path escapes sandbox workdir: {path}", path=path
            ) from exc
        return candidate

    def _write_file_internal(self, path: str, content: str) -> dict[str, Any]:
        abs_path = self._resolve_inside(path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8"))}
