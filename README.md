# agenteval

> The first reproducible benchmark for **Claude Code Skills** and **CLAUDE.md** configurations.
> Do skills actually work? Here's an honest, reproducible answer.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Status: v1 feature-complete](https://img.shields.io/badge/status-v1_feature_complete-green.svg)](STATUS.md)

---

## The 30-second TL;DR

The Claude Code Skills ecosystem ([mattpocock/skills](https://github.com/mattpocock/skills), [obra/superpowers](https://github.com/obra/superpowers), [andrej-karpathy-skills](https://github.com/karpathy/skills), …) is exploding in 2026 — with anecdotal claims like *"95% reliability vs. 60–70%"* and zero credible methodology backing them.

**agenteval** is a Python harness that:

1. Loads a `.claude/skills/` directory (or a single `CLAUDE.md`) into a SkillBundle.
2. Runs it against a fixed task set in a hardened Docker sandbox.
3. Reports pass@1, pass@5, pass^5 (TAU-Bench reliability), cost, latency, tool-call count, timeout-rate, and 8 adversarial flags — all with bootstrapped 95% CIs.
4. **Content-addresses every leaderboard entry** so anyone can re-verify with: skill-bundle SHA, task-set SHA, model, temperature, canonical seed list, and pricing.yaml SHA.

Three providers from day one: Anthropic, OpenAI, Google.

> **Status:** v1 feature-complete (all 6 milestones M1–M6). Polish + launch prep in progress. Target launch ~July 2026.
> See [STATUS.md](STATUS.md) for current state and [DESIGN.md](DESIGN.md) for the locked v1 surface.

---

## Quick start

```bash
pip install -e .

# Dry-run (no API calls):
agenteval dry-run --skills none --tasks skill-specific-v1 --model claude-opus-4-7

# Real run (set ANTHROPIC_API_KEY first):
agenteval eval --skills none --tasks skill-specific-v1 --model claude-opus-4-7 --out result.json
agenteval submit ./result.json                # → result.entry.json (canonical, hash-stamped)
agenteval verify ./result.entry.json --skills none --tasks skill-specific-v1

# Cross-provider:
agenteval eval --runner openai --model gpt-5.2     --skills ./.claude/skills/ --tasks skill-specific-v1 --out result-openai.json
agenteval eval --runner google --model gemini-3-pro --skills ./.claude/skills/ --tasks skill-specific-v1 --out result-google.json

# Exploratory (non-leaderboard, any seed count):
agenteval eval --exploratory --seeds 1 --skills none --tasks skill-specific-v1 --model claude-opus-4-7
```

### Sandbox

By default the harness runs in a Docker container with `--cpus=1 --memory=2g --network=none`, non-root user, no host filesystem mount. Build the base image once:

```bash
docker build -f sandbox/Dockerfile.base -t agenteval-sandbox:base sandbox/
```

Without Docker, the harness falls back to a `LocalSubprocessSandbox` (dev-only) with a stderr warning. Set `AGENTEVAL_SANDBOX=local` to silence it.

---

## What's measured

| Metric | What it is | Why it's there |
|---|---|---|
| `pass@1` | mean per-task success on seed 1 | capability — does the skill help solve the task at all? |
| `pass@5` | Chen-2021 unbiased estimator over 5 canonical seeds | capability with sampling variance accounted for |
| `pass^5` | TAU-Bench reliability — fraction of tasks where **all** 5 seeds pass | reliability — does the skill help **consistently**? |
| `cost_usd` | tokens × `pricing.yaml`, median + p95 | what the skill costs you per task |
| `latency_s` | wall-clock per attempt, p50 + p95 | how long the skill makes the agent take |
| `tool_calls` | normalized tool-invocation count, median | does the skill make the agent chatty/expensive? |
| `timeout_rate` | (task, seed) pairs that hit `time_budget_s` | distinguishes "wrong answer" from "ran out of time" |

All point estimates carry **95% bootstrapped CIs** (10 000 iterations, resampling tasks). The leaderboard does not publish a scalar "agenteval score" — every column is sortable, nothing is ranked.

### Adversarial flags (descriptive badges, never ranked)

- `high-variance` — pass@5 ≥ 2 × pass^5 → gains likely from nondeterminism, not capability
- `talkative` — output-tokens-median ≥ 2 × baseline
- `tool-storm` — tool_calls-median ≥ 2 × baseline
- `pricing-stale` — `pricing.yaml.last_audited` > 30 days old
- `model-drift` — provider response-fingerprint changed between submission and verification
- `borderline-stability` — at least one task pass/failed flipped on re-verification
- `holdout-divergence` — public vs. holdout pass@1 gap > 15 pp (Goodhart detector)
- `passive` — timeout_rate ≥ 2× baseline AND pass^5 ≥ baseline (silently bails on hard tasks)

Each flag has a synthetic pathological-skill test in [`docs/adversarial.md`](docs/adversarial.md).

---

## What is **NOT** measured

- **Code style / aesthetics.** We run linters where graders demand it; we don't grade "is this Pythonic".
- **Long-horizon (>5 min) task quality.** Out of scope; see [METR's HCAST/RE-Bench](https://metr.org/) for that work.
- **Multi-modal.** v1 is code/text only. v2+ may add screenshots, voice, etc.
- **LLM-as-judge scores.** [ADR-0006](DECISIONS.md) — deterministic graders only in v1.
- **Aggregate scalar rank.** Goodhart's Law non-negotiable. The leaderboard is sortable, not ranked.

---

## Methodology in one paragraph

We take the existing agentic-coding benchmark literature (HELM, SWE-bench, TAU-Bench, METR's time-horizon work), steal what's defensible (pass@k unbiased estimator, multi-metric reporting, per-category breakdown, bootstrap CIs), and refuse what's not (LLM-as-judge in v1, scalar rankings). We split the leaderboard into a **primary panel** (skill-specific-v1 + tau-bench-v1, uncontaminated by construction) and a **secondary panel** (swe-bench-lite-v1, marked "informative but contaminated" — see [§4](docs/methodology.md) on the SWE-bench contamination story driven by OpenAI's December 2025 announcement). Reproducibility is content-addressed: every leaderboard entry can be re-verified in a fresh VM with the skill-bundle SHA, task-set SHA, model, temperature, the canonical seed list `[1,2,3,4,5]`, and pricing.yaml SHA. The full treatment is in [`docs/methodology.md`](docs/methodology.md).

---

## How to evaluate **your own** skill bundle

1. **Run it locally.**

   ```bash
   agenteval eval \
     --skills ./.claude/skills/ \
     --tasks skill-specific-v1 \
     --model claude-opus-4-7 \
     --out my-result.json
   ```

2. **Canonicalize.**

   ```bash
   agenteval submit ./my-result.json    # → my-result.entry.json
   ```

3. **Submit.** Open a PR adding `my-result.entry.json` under `frontend/data/submissions/`. CI re-verifies in two cloud VMs (per master prompt anti-pattern #10) and merges if verification agrees.

Full submission protocol: [`frontend/README.md`](frontend/README.md). FAQ: [`docs/faq.md`](docs/faq.md). For methodology questions in particular, read [`docs/methodology.md`](docs/methodology.md) first — most reviewer concerns are already addressed there.

---

## License

Apache 2.0 — see [LICENSE](LICENSE). Skill snapshots used as references retain their upstream licenses.

## Contributing

Issues + PRs welcome. See [`docs/good-first-issues.md`](docs/good-first-issues.md) for starter tickets. CI runs lint + type + tests on every push (`.github/workflows/ci.yml`). Pre-commit hooks recommended: `pre-commit install`.

For non-trivial changes:
1. Open an issue first describing the change.
2. If it touches the leaderboard methodology, draft an ADR in [`DECISIONS.md`](DECISIONS.md) before the PR.
3. Adversarial test cases required for any new metric or grader.

## State & history

- [STATUS.md](STATUS.md) — current phase, next action, session log.
- [DECISIONS.md](DECISIONS.md) — append-only ADR log (16 ADRs as of v1 feature-complete).
- [DESIGN.md](DESIGN.md) — locked v1 surface.
- [docs/methodology.md](docs/methodology.md) — defense-against-reviewers methodology doc.
- [docs/faq.md](docs/faq.md) — pre-drafted answers to common criticisms.
