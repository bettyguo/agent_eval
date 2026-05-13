# Sandbox

Methodology context in [methodology.md](methodology.md) §6.

## 1. Container spec

Every (task, seed) attempt runs in a fresh Docker container, never reused.

| Constraint | Value |
|---|---|
| Base image | `python:3.11-bookworm-slim`, SHA pinned in `sandbox/image.lock` |
| CPU | 1 core (`--cpus=1.0`) |
| Memory | 2 GB (`--memory=2g`) |
| Wall-time | task's `time_budget_s` (<=300 in v1) |
| Network | disabled (`--network=none`); task `network: true` opt-in |
| Host FS | nothing mounted outside `/work` |
| User | non-root (`agenteval`, UID 1000) |
| Skills | injected at `/home/agenteval/.claude/skills/` |
| Writable | `/work`, `/tmp` (both discarded on teardown) |

## 2. Lifecycle

1. Pull/verify the base image at the pinned SHA. Raise `SandboxError` if
   unavailable.
2. Materialise `setup.files` into `/work`; run pinned `pip_install`; inject
   the skill bundle at `/home/agenteval/.claude/skills/`.
3. Drive the agent loop. Tool calls run as subprocesses inside the
   container via the runner's tool-dispatch layer.
4. Capture trajectory + final state.
5. Grader runs in a separate sandbox with `/work` mounted read-only;
   30-second wall-time; no network.
6. Teardown: both containers destroyed; `/work` discarded.

## 3. Threat model

Assumed: skill authors are not actively malicious; the defence is against
accidental side effects (a typo running `rm -rf`, a skill trying to make
HTTP calls). Graders are trusted code, reviewed in PR. Agent-produced code
is untrusted; the sandbox is a soft boundary.

Not defended against:

- Deliberate sandbox escape (kernel exploit, Docker breakout).
- Adversarial graders.
- Denial-of-service via host-shared resource starvation. Run on dedicated
  infra.

## 4. Cross-platform

| Platform | Status | Notes |
|---|---|---|
| Linux x86_64 | Supported; CI uses this. | |
| Linux arm64 | Supported; the pinned image must have an arm64 variant. | |
| macOS (Docker Desktop) | Caveat: slower filesystem. Warning above 20 tasks. | |
| Windows (WSL2 + Docker Desktop) | Same caveats as macOS. | |
| Remote runner | `agenteval eval --remote <ssh-host>` ships bundle + task set over SSH. | |

## 5. Image SHA pinning

`sandbox/image.lock` records the base-image SHA. Bumps go via:

1. New SHA selected (typically a base-image security update).
2. Re-run existing leaderboard entries on the new image to detect
   behavioural drift.
3. If drift exceeds tolerance, don't promote; investigate.
4. Otherwise commit the new SHA. Re-verified entries that ran under the
   previous SHA fire `sandbox-drift` until they're re-verified against the
   new one.

Use `scripts/pin_image_sha.sh` to resolve the current tag to a digest and
write it into the lock file.

## 6. Implementation

- `src/agenteval/sandbox/docker.py` for container lifecycle.
- `src/agenteval/sandbox/local.py` for the no-isolation dev fallback.
- Tests in `tests/test_sandbox_docker.py` (skipped when the Docker daemon
  is unreachable).
