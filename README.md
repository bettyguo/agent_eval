# agent_eval

A reproducible benchmark for Claude Code skill bundles (`.claude/skills/`
directories) and `CLAUDE.md` configurations. Runs a fixed task set against
Anthropic, OpenAI, and Google models in a sandboxed environment and reports
pass@k, cost, latency, and a handful of adversarial flags.

Apache-2.0.

## Install

```bash
pip install -e .
docker build -f sandbox/Dockerfile.base -t agenteval-sandbox:base sandbox/
```

The sandbox is Docker-based by default. Without Docker the harness falls
back to a local-subprocess mode (no isolation, dev only); set
`AGENTEVAL_SANDBOX=local` to silence the fallback warning.

## Use

```bash
# Dry run.
agenteval dry-run --skills none --tasks skill-specific-v1 --model claude-opus-4-7

# Full run (set ANTHROPIC_API_KEY first).
agenteval eval --skills ./.claude/skills/ --tasks skill-specific-v1 \
    --model claude-opus-4-7 --out result.json

# Canonicalise + verify a submission.
agenteval submit ./result.json
agenteval verify ./result.entry.json --skills ./.claude/skills/ --tasks skill-specific-v1
```

Other runners: `--runner openai --model gpt-5.2`,
`--runner google --model gemini-3-pro`. Exploratory mode for non-leaderboard
seed sweeps: `--exploratory --seeds N`.

## What's measured

`pass@1`, `pass@5` (Chen et al. 2021 unbiased estimator), `pass^5`
(TAU-Bench-style reliability), cost, latency, tool-call count, timeout rate.
All point estimates carry bootstrapped 95% CIs. Eight descriptive flags
(`high-variance`, `talkative`, `tool-storm`, `pricing-stale`, `model-drift`,
`borderline-stability`, `holdout-divergence`, `passive`). No scalar rank.

See [docs/methodology.md](docs/methodology.md) for the protocol, including
the two-panel leaderboard split (uncontaminated primary; SWE-bench-Lite as
secondary, marked contaminated).

## What's not measured (yet)

Code style/aesthetics, long-horizon (>5 min) tasks, multi-modal,
LLM-as-judge subjective grades. v2 may revisit some of these.

## Submitting a result

Submission is PR-based. Run `agenteval submit ./result.json`, commit the
resulting `.entry.json` under `frontend/data/submissions/`, open a PR. CI
re-verifies; merge after the verifier agrees.

## Layout

```
src/agenteval/         harness, runners, metrics, sandbox, grading
tasks/skill-specific-v1/   20 hand-curated task YAMLs
sandbox/               Docker base image
frontend/              Next.js leaderboard (static export)
docs/                  methodology, task/metric/sandbox/reproducibility specs
pricing.yaml           per-(provider, model) token prices
```
