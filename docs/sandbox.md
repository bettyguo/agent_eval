# Sandbox design

> Phase 1 §4.4 deliverable. Methodology context in [`methodology.md`](methodology.md) §6.

## 1. Container spec

Every (task, seed) pair runs in a fresh Docker container, never reused.

| Constraint | Value | Override |
|---|---|---|
| Base image | `python:3.11-slim` pinned by SHA in run metadata | image SHA bump = new entry hash |
| CPU | 1 core (`--cpus=1.0`) | not overridable per-task |
| Memory | 2 GB (`--memory=2g`) | not overridable per-task |
| Wall-time | task's `time_budget_s` (≤300 in v1) | task spec controls |
| Network | disabled (`--network=none`) | task `network: true` opt-in |
| Host FS | none mounted outside `/work` | not overridable |
| Skill bundle | injected read-only at `/root/.claude/skills/` | not overridable |
| User | non-root (`agenteval` user, UID 1000) | not overridable |
| Writable dirs | `/work` (task working dir), `/tmp` (cleared on exit) | not overridable |

## 2. Lifecycle

1. **Pull/verify base image** at the pinned SHA. If unavailable, raise `SandboxError`.
2. **Compose the container layer**: copy task's `setup.files` into `/work`; run pinned `pip_install`; mount skill bundle read-only at `/root/.claude/skills/`.
3. **Start agent execution.** The harness sends API requests on the host; the agent's tool calls run as subprocesses inside the container via the runner's tool-handling layer.
4. **Capture trajectory + final state.** Trajectory is written to `/work/.trajectory.jsonl` and copied out.
5. **Grader runs** in a *separate* container (the "grader sandbox") with `/work` mounted read-only. Grader has 30 s wall-time, no network.
6. **Teardown.** Both containers destroyed. `/work` discarded.

## 3. Threat model

We assume:
- Skill authors are **not actively malicious**. We defend against accidental side effects (a skill that types `rm -rf` on a typo, a skill that tries to make HTTP calls).
- Graders are **trusted code** maintained by the project and reviewed in PR.
- Agent-produced code is **untrusted**. It runs in the sandbox; the sandbox is a soft boundary.

We do **not** defend against:
- Deliberate sandbox escape (Docker breakout, kernel exploit).
- Adversarial graders (graders are code we review and own).
- Denial-of-service via resource starvation if the host is shared. Run on dedicated infra.

This positioning is documented in [`methodology.md`](methodology.md) §6.2.

## 4. Cross-platform notes

| Platform | Status | Notes |
|---|---|---|
| Linux (x86_64) | Supported, recommended | Used by CI verifier. |
| Linux (arm64) | Supported | Pinned image must have an arm64 variant; verifier currently uses x86_64. |
| macOS (Docker Desktop) | Supported with caveats | Slower filesystem; harness warns at >20 tasks; remote-runner suggested. |
| Windows (WSL2 + Docker Desktop) | Supported with caveats | Same caveats as macOS. |
| Remote runner | Supported | `agenteval eval --remote <ssh-host>` ships the bundle + task set over SSH; results streamed back. |

## 5. Pinned image SHA management

A `sandbox/image.lock` file in the repo records the pinned base-image SHA. Updates happen via:

1. New image SHA selected (typically a security update of `python:3.11-slim`).
2. Re-run all existing leaderboard entries on the new image to verify no behavioural drift.
3. If drift > tolerance, do NOT promote the new image; investigate.
4. If no drift, update `sandbox/image.lock` and bump the build-tooling version.

## 6. Implementation references

- Code: `src/agenteval/sandbox/docker.py` (container lifecycle), `src/agenteval/sandbox/timeout.py` (wall-time enforcement).
- Phase 2 M2 implements this; tests live in `tests/test_sandbox.py` and include OOM-injection, time-out-injection, and network-leak detection.
