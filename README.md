# agenteval

> The first reproducible benchmark for **Claude Code Skills** and **CLAUDE.md** configurations.
> Do skills actually work? This harness produces an honest, reproducible answer.

**Status:** v1 feature-complete (Phase 2 done). Polish + launch prep remaining. Target launch: ~July 2026.

---

## What this is

A Python harness that takes a `.claude/skills/` directory (or single `CLAUDE.md` file), runs it against a standardized task set across Anthropic, OpenAI, and Google models in a sandboxed environment, and reports:

- **pass@1, pass@5** — success rate, properly bootstrapped
- **cost ($)** — per-task, computed from token counts × current pricing
- **latency** — wall + p50/p95
- **tool-call count** — how chatty the agent is
- **Adversarial flags** — variance, talkativeness, suspicious patterns

Results are **content-addressed**: every leaderboard entry can be re-verified from scratch by anyone with the skill bundle hash, the task-set hash, the model name, the temperature, and the seed list.

## Why

The Claude Code Skills ecosystem (mattpocock/skills, obra/superpowers, andrej-karpathy-skills, …) is exploding in mid-2026 with anecdotal claims like *"95% reliability vs. 60–70%"* — and zero credible methodology backing them. `agenteval` exists to give skill authors, framework maintainers, and researchers a defensible measurement.

## What this isn't

- ❌ A general LLM eval framework. (See `lm-evaluation-harness`.)
- ❌ A SaaS-gated leaderboard. Anyone can submit; gating is **reproducibility**, not curation.
- ❌ A new benchmark from scratch. v1 = adapt SWE-bench-Lite + TAU-Bench + 20 hand-curated skill-specific tasks.
- ❌ A platform for LLM-as-judge grading. v1 = deterministic graders only.
- ❌ Multi-modal eval. v1 = code/text tasks only.

## Quick start

```bash
pip install -e .

# Dry-run (no API calls):
agenteval dry-run --skills none --tasks skill-specific-v1 --model claude-opus-4-7

# Real run (set ANTHROPIC_API_KEY first):
agenteval eval --skills none --tasks skill-specific-v1 --model claude-opus-4-7 --out result.json
agenteval submit ./result.json       # → result.entry.json
agenteval verify ./result.entry.json --skills none --tasks skill-specific-v1

# Cross-provider:
agenteval eval --runner openai --model gpt-5.2 --skills none --tasks skill-specific-v1 --out result-openai.json
agenteval eval --runner google --model gemini-3-pro --skills none --tasks skill-specific-v1 --out result-google.json

# Exploratory (non-leaderboard, custom seed count):
agenteval eval --skills none --tasks skill-specific-v1 --model claude-opus-4-7 --exploratory --seeds 1
```

### Sandbox

The harness uses Docker by default when the daemon is reachable. Build the
base image once:

```bash
docker build -f sandbox/Dockerfile.base -t agenteval-sandbox:base sandbox/
```

Without Docker, the harness falls back to a `LocalSubprocessSandbox` (dev-only,
no isolation) with a stderr warning. To silence the warning, set
`AGENTEVAL_SANDBOX=local`.

## Methodology

See [docs/methodology.md](docs/methodology.md) — the defense-against-reviewers doc. Skim before forming an opinion.

## License

Apache 2.0. See [LICENSE](LICENSE).

## Project state

See [STATUS.md](STATUS.md) for current phase and next steps. See [DECISIONS.md](DECISIONS.md) for the architecture decision log.
