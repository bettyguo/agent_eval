# Remote runner

> Phase 3 §6.7 deliverable. Methodology context in [`docs/sandbox.md`](sandbox.md) §4 and [`docs/reproducibility.md`](reproducibility.md) §4 (two-VM rule per master prompt anti-pattern #10).

## Why this exists

Two reasons:

1. **Two-VM verifier rule.** Every primary-leaderboard entry is re-verified in two different cloud zones before being marked `verified: true`. The local CI runner is verifier-A; verifier-B runs on a remote VPS.
2. **Performance.** Docker Desktop on macOS / Windows is materially slower than Docker on Linux. A user running the harness on a laptop can offload runs to a cheap Linux VPS (Hetzner CX21 or similar works well).

## Usage

```bash
agenteval eval \
    --skills ./.claude/skills/ \
    --tasks skill-specific-v1 \
    --model claude-opus-4-7 \
    --remote agenteval-runner@my-vps.example.com \
    --out result.json
```

The remote runner:

1. Tarballs the skill bundle and the local task-set directory (if `--tasks` is a path; built-in task-set names are looked up on the remote).
2. SSHes to the host, ensures `agenteval` is installed there (a pinned version matching the local one), and copies the tarballs into a temp directory.
3. Runs `agenteval eval --skills <unpacked-dir> --tasks <unpacked-dir> ...` remotely with the same flags except `--remote` removed.
4. Streams stdout/stderr back over the SSH connection.
5. Copies the result JSON back to the local `--out` path.

API keys: the harness forwards `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `GOOGLE_API_KEY` from the local environment via SSH `SendEnv`. Make sure the remote `sshd_config` allows `AcceptEnv ANTHROPIC_API_KEY OPENAI_API_KEY GOOGLE_API_KEY`.

## Setup on the remote VPS

```bash
# On the VPS, as a non-root user:
sudo apt update && sudo apt install -y docker.io python3.11 python3.11-venv git
sudo usermod -aG docker $USER   # log out + back in for this to take effect

git clone https://github.com/<org>/agenteval.git
cd agenteval
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

docker build -f sandbox/Dockerfile.base -t agenteval-sandbox:base sandbox/
```

The remote pinned-version requirement: in CI, the verifier-B VPS is pre-baked with a known-good `agenteval` commit. For ad-hoc use, the remote checkout should track `main` and rebuild on every connection.

## Two-VM verifier rule (CI)

The CI verifier (`.github/workflows/verify-submission.yml`) runs verifier-A on the GitHub Actions runner. Verifier-B is configured separately via a webhook from the CI to the VPS; the VPS posts its `VerificationReport` back as a PR check. Both must agree on the strict-equality fields before the entry is marked `verified: true`.

If the two verifiers disagree on a particular task's pass/fail, that task is flagged `borderline-stability` and the run is re-attempted once. Persistent disagreement marks the entry `verified: partial` and the divergent tasks are listed in the entry's verification report.

## Security model

- The remote runs as a non-root user; Docker is the inner sandbox.
- API keys are passed via env vars; never written to disk on the remote (the remote process inherits them).
- The remote's temp workdir is wiped after each run (`agenteval cleanup --remote` ensures this).
- For shared remote hosts, use per-job SSH keys and a dedicated `agenteval` user.

## Limitations

- Only `ssh`-reachable hosts are supported. No Kubernetes, no cloud-API-orchestrated runners in v1.
- The local task-set directory and skill bundle must fit in a single tarball (no streaming).
- Connection drops mid-run abort the run; partial results are discarded. (Resumable runs are a v1.1 feature.)
- Windows-host → Linux-remote works but you'll want `ssh-agent` configured to avoid passphrase prompts.
