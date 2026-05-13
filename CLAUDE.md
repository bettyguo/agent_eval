# CLAUDE.md — Project-specific Claude Code guidance

> Loaded at the start of every Claude Code session in this repo. Authoritative.

## Project identity

This is **agenteval**: the first reproducible benchmark for Claude Code Skills and CLAUDE.md configurations. The full master prompt lives at `c:\opensource\02-agenteval.md` (outside this repo). Treat it as the canonical spec; this file is the day-to-day operating guide.

## Session start protocol — **mandatory, no exceptions**

1. Read [STATUS.md](STATUS.md). It contains: current phase, last completed milestone, next concrete action, blocker, session log.
2. Read [DECISIONS.md](DECISIONS.md). Every architectural/methodological commitment lives there as an ADR. **Never reverse an ADR in place — append a superseding entry.**
3. Print a 3-line summary: current phase, next milestone, blocker. Then either ask `"Proceed with [next action]?"` or, if instructed to keep moving, proceed and report.
4. (When tests exist) Run `pytest tests/test_demo_path.py` — must be green before substantive work.

## Session end protocol

1. Update STATUS.md "Snapshot" block (phase, last completed milestone, next concrete action, blocker, time spent).
2. Append a session log entry under "Session log (most-recent first)" with today's date and a 1–2 line note.
3. If any new architectural commitment was made, append it to DECISIONS.md as a new ADR (next sequential ID).

## Core methodological commitments — keep front of mind

- **Methodological rigor IS the product.** Every measurement decision must be defensible to a NeurIPS reviewer.
- **No LLM-as-judge in v1** (ADR-0006). Deterministic Python graders only.
- **Apache 2.0** (ADR-0002). Skill snapshots retain their upstream licenses.
- **Docker sandbox; network off by default; no host filesystem** (ADR-0005).
- **Content-addressed reproducibility** (ADR-0008). Temperature must be 0.0 for leaderboard entries. Verifier re-runs in a clean VM and compares structured features.
- **Adversarial self-review**: after building a metric, try to break it. Pathological test cases are required for every metric.
- **Don't conflate "skill caused this" with "skill correlated with this"** (anti-pattern #5). Causal language requires ablation.

## Tech stack — pinned

- Python 3.11+ for the harness. (ADR-0003)
- Anthropic SDK + OpenAI SDK + `google-genai` for the three runner backends. (ADR-0004)
- DuckDB for results; static JSON export for leaderboard. (ADR-0007)
- Docker via `docker-py` for sandbox.
- Next.js 14 + Tailwind on Vercel for the frontend.
- pydantic + pyyaml + click + rich for the CLI layer.

## Scope discipline — say no aggressively

- ❌ General LLM eval framework. (We are narrowly about agent skills / CLAUDE.md.)
- ❌ SaaS-gated leaderboard. (Anyone submits; gating = reproducibility.)
- ❌ Net-new benchmark tasks beyond v1 (= adapt SWE-bench-Lite + TAU-Bench + 20 hand-curated).
- ❌ Telemetry. We log nothing.
- ❌ Multi-modal in v1.

## Time budget — 120 hr across 8 weeks

| Phase | Budget |
|---|---|
| 0 — Think | 12 hr |
| 1 — Design | 14 hr |
| 2 — Code (M1–M6) | 60 hr |
| 3 — Polish | 22 hr |
| 4 — Launch prep | 12 hr |

If a session is heading toward over-budget, surface it; do not silently absorb scope creep.

## Anti-patterns — re-read before every milestone

(Verbatim from §9 of the master prompt.)

1. Don't fudge methodology to get a more dramatic result.
2. Don't release without the adversarial section.
3. Don't pick fights with skill authors in public.
4. Don't let LLM-as-judge sneak in.
5. Don't conflate "skill caused this" with "skill correlated with this".
6. Don't include too many tasks. (100-task ceiling in v1.)
7. Don't promise OAuth / hosted submission at launch.
8. Don't forget pricing changes (`pricing.yaml` stays current).
9. Don't release without contamination caveats.
10. Don't accept the first reproducibility result (re-verify in TWO VMs).

## Working style for this project

- Inner loop: **Think → Design → Code → Iterate**, where "iterate" includes adversarial self-review.
- When in doubt between velocity and rigor, choose rigor.
- The user is a PhD-trained reviewer; lead with the methodology, not the numbers.
- For Phase 0 / Phase 1 deliverables, output **defensible documents** before any code.
