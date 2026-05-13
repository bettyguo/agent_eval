"""SSH-based remote runner.

Used by the two-VM verifier (verifier-B runs on a remote VPS) and by users
on hosts where Docker is slow (macOS / Windows Docker Desktop).

Limitations in v1:
- Only built-in task-set names are supported on the remote (local task-set
  directories would need a separate tarball path).
- Skill bundles can be a local directory (tarballed + scp'd) or the literal
  string "none".
- No streaming output: result.json is scp'd back after completion.

API keys are forwarded via `ssh SendEnv`; the remote `sshd_config` needs
`AcceptEnv ANTHROPIC_API_KEY OPENAI_API_KEY GOOGLE_API_KEY`. The remote
temp workdir is removed after the run (best-effort).
"""

from __future__ import annotations

import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from agenteval.errors import AgentevalError

API_KEY_ENV_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")

# Permissible host strings: user@host or just host. Reject anything with shell
# metacharacters before it can be interpolated into commands.
_SAFE_HOST_RE = re.compile(r"^(?:[A-Za-z0-9_.\-]+@)?[A-Za-z0-9_.\-]+$")


def run_remote(
    *,
    remote_host: str,
    skill_bundle_path: str,
    task_set: str,
    model: str,
    runner: str = "anthropic",
    temperature: float = 0.0,
    exploratory: bool = False,
    seeds: int | None = None,
    out_path: Path,
) -> int:
    """Execute `agenteval eval ...` on `remote_host`. Return the remote exit code.

    The harness must be installed on the remote and the agenteval-sandbox:base
    image must be built there.
    """
    _validate_host(remote_host)
    if not _ssh_available():
        raise AgentevalError(
            "`ssh` / `scp` not on PATH; install OpenSSH client to use --remote",
            remote=remote_host,
        )

    # 1. Resolve the skill bundle: literal "none" → pass through; else tarball.
    job_id = secrets.token_hex(6)
    remote_workdir = f"/tmp/agenteval-job-{job_id}"
    bundle_tar: Path | None = None
    remote_bundle_arg: str
    if skill_bundle_path == "none":
        remote_bundle_arg = "none"
    else:
        local_bundle = Path(skill_bundle_path).resolve()
        if not local_bundle.exists():
            raise AgentevalError(
                f"--skills path does not exist: {local_bundle}",
                path=str(local_bundle),
            )
        bundle_tar = Path(tempfile.mkstemp(suffix="-bundle.tar.gz")[1])
        _tar_directory(local_bundle, bundle_tar)
        remote_bundle_arg = f"{remote_workdir}/skills/"

    try:
        # 2. Create remote workdir + push bundle.
        _ssh(remote_host, f"mkdir -p {shlex.quote(remote_workdir + '/skills')}")
        if bundle_tar is not None:
            _scp(bundle_tar, f"{remote_host}:{remote_workdir}/bundle.tar.gz")
            _ssh(
                remote_host,
                f"tar -xzf {shlex.quote(remote_workdir + '/bundle.tar.gz')} "
                f"-C {shlex.quote(remote_workdir + '/skills')} && "
                f"rm {shlex.quote(remote_workdir + '/bundle.tar.gz')}",
            )

        # 3. Compose the remote eval invocation.
        cmd_parts = [
            "agenteval",
            "eval",
            "--skills",
            remote_bundle_arg,
            "--tasks",
            task_set,
            "--runner",
            runner,
            "--model",
            model,
            "--temperature",
            str(temperature),
            "--out",
            f"{remote_workdir}/result.json",
        ]
        if exploratory:
            cmd_parts.append("--exploratory")
        if seeds is not None:
            cmd_parts += ["--seeds", str(seeds)]
        remote_cmd = " ".join(shlex.quote(p) for p in cmd_parts)

        # 4. Run remotely, forwarding API keys via SendEnv.
        rc = _ssh(
            remote_host,
            remote_cmd,
            send_env=[v for v in API_KEY_ENV_VARS if v in os.environ],
            stream=True,
        )

        # 5. Pull the result back regardless of exit code (useful for partial-run debug).
        try:
            _scp(f"{remote_host}:{remote_workdir}/result.json", out_path)
        except subprocess.CalledProcessError:
            print(
                "[remote] result.json not produced — see remote logs above",
                file=sys.stderr,
            )

        return rc
    finally:
        # Best-effort cleanup. Don't fail the local invocation on cleanup errors.
        try:
            _ssh(remote_host, f"rm -rf {shlex.quote(remote_workdir)}")
        except Exception:
            pass
        if bundle_tar is not None and bundle_tar.exists():
            try:
                bundle_tar.unlink()
            except OSError:
                pass


# ---------- internal helpers ----------


def _validate_host(host: str) -> None:
    if not _SAFE_HOST_RE.match(host):
        raise AgentevalError(
            f"--remote host must match {_SAFE_HOST_RE.pattern!r}; got {host!r}",
            remote=host,
        )


def _ssh_available() -> bool:
    return shutil.which("ssh") is not None and shutil.which("scp") is not None


def _tar_directory(src: Path, dst_tar: Path) -> None:
    with tarfile.open(dst_tar, "w:gz") as tar:
        tar.add(src, arcname=".")


def _ssh(
    host: str,
    command: str,
    *,
    send_env: list[str] | None = None,
    stream: bool = False,
) -> int:
    cmd = ["ssh"]
    for ev in send_env or []:
        cmd += ["-o", f"SendEnv={ev}"]
    cmd += ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", host, command]
    if stream:
        proc = subprocess.Popen(cmd)
        return proc.wait()
    subprocess.run(cmd, check=True)
    return 0


def _scp(src: str | Path, dst: str | Path) -> None:
    cmd = [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        str(src),
        str(dst),
    ]
    subprocess.run(cmd, check=True)
