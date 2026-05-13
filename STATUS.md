# STATUS

> Single source of truth for project state. Read this at the start of every session before doing anything else. Update at the end of every session.

## Snapshot

- **Phase:** 2 — Code, **all 6 milestones (M1–M6) complete in this session**
- **Last completed milestone:** M6 (frontend stub). Full pipeline is in place: Pydantic task schema; SkillBundle.empty/from_dir/from_claude_md; LocalSubprocessSandbox + hardened DockerSandbox (with sandbox selection via env var + daemon detection); AnthropicRunner / OpenAIRunner / GoogleRunner agent loops with normalized tool dispatch; full metric module (pass@k Chen-2021 estimator, pass^k, cost via pricing.yaml, latency, tool_calls, timeout_rate, 8 adversarial flags); bootstrap CI; LeaderboardEntry build + verifier with content-addressed entry_hash; Click CLI with eval/dry-run/inspect/submit/verify; 20 skill-specific tasks (4 per category × 5 categories); Next.js static frontend with two-panel sortable LeaderboardTable.
- **Next concrete action:** **Phase 3 — Polish (22 hr)**: README hero block, methodology doc to workshop-paper quality, pre-launch outreach to skill authors, CI/repo hygiene, reproducibility hardening (image SHA pinning), cross-platform sanity checks.
- **Blocker:** Real-API smoke run is the user's call (no API key in this environment). The harness itself is end-to-end testable via MockRunner.
- **Time spent (cumulative):** ~22 hr / 120 hr budget (Phase 0 ~3; Phase 1 ~3; Phase 2 M1–M6 ~16; significantly under the 60-hr Phase 2 budget — owing to the locked Phase 1 surface and the spec-driven task implementation).

## Phase progress

| Phase | Budget | Spent | Status |
|---|---|---|---|
| 0 — Think | 12 hr | ~3 hr | complete |
| 1 — Design | 14 hr | ~3 hr | complete |
| 2 — Code (M1–M6) | 60 hr | ~16 hr | complete (M1+M2+M3+M4+M5+M6) |
| 3 — Polish | 22 hr | 0 hr | next |
| 4 — Launch prep | 12 hr | 0 hr | not started |

## Phase 0 sub-task progress (complete)

- [x] §3.1 Methodology recon — `docs/methodology.md` (~7000 words after revisions)
- [x] §3.2 Contamination audit — integrated into methodology.md §4 + ADR-0011 + ADR-0014 (demoted SWE-bench-Lite to secondary panel)
- [x] §3.3 Skill-specific task design — `tasks/skill-specific-v1/README.md` (20 tasks across 5 categories)
- [x] §3.4 Leaderboard pre-mortem — integrated into methodology.md §9 (extended with model-drift, timeout-rate, cross-provider asymmetry mitigations)
- [x] §3.5 Exit gate — self-review applied; 4 questions answered with ADRs 0014–0016. **Re-validation by user welcome but not blocking — surfaces in DESIGN.md sign-off.**

## Phase 1 sub-task progress (complete)

All §4.1–§4.6 sub-docs landed; user accepted with "begins Phase 2 M1".

## Phase 2 M1–M6 sub-task progress (all complete)

### M1 — Task format + 5 reference tasks (~5 hr)
Pydantic v2 schema with strict + unknown-key rejection + LLM-import ban (ADR-0006). TaskSet loader with meta.yaml + hash computation + panel inheritance. SkillBundle (`empty`/`from_dir`/`from_claude_md`). Grader runtime (sandboxed namespace, syntax / runtime / timeout handling). LocalSubprocessSandbox. AnthropicRunner with full tool-use agent loop. MockRunner for tests. Harness/Result/PerAttempt with ADR-0015 eligibility. Click CLI (`eval`/`dry-run`/`inspect`). 5 reference task YAMLs.

### M2 — Skill loaders + Docker sandbox (~3 hr)
`sandbox/docker.py` (DockerSandbox): pinned `python:3.11-bookworm-slim` image (SHA-pinning deferred to M5 hardening), 1 CPU + 2 GB RAM + 5-min wall-time, `--network=none` default, `--cap-drop=ALL` + `no-new-privileges`, non-root agenteval user. `sandbox/image.lock` records the pinned base + baked tool versions. `sandbox/Dockerfile.base` bakes pytest/ruff/mypy at pinned versions; per-task `pip_install` runs as additional layers. Skill bundles injected at `/home/agenteval/.claude/skills/` (canonical) and `<workdir>/.claude/skills/` (belt-and-braces shadow). `default_sandbox_factory()` selects docker (when daemon reachable) vs. local, with env override `AGENTEVAL_SANDBOX`. Tests in `tests/test_sandbox_docker.py` (skip gracefully when daemon unreachable).

### M3 — Cross-provider runners + metrics (~3 hr)
`metrics/pass_at_k.py` — Chen-2021 unbiased estimator in log-space (overflow-safe). `metrics/bootstrap.py` — 10k-iter bootstrap (numpy fast path) + Wilson interval for binomial proportions. `metrics/cost.py` + `pricing.yaml` (hashed; pinned `last_audited`). `metrics/flags.py` — 8 adversarial flags (high-variance, talkative, tool-storm, pricing-stale, model-drift, borderline-stability, holdout-divergence, passive). `metrics/summary.py` — MetricSummary aggregator with per-category breakdown. `runners/openai.py` + `runners/google.py` — full agent loops with normalized tool dispatch (the same `TOOL_DEFINITIONS` translate into each provider's native function-call format). Result now carries `metric_summary`, `flags`, `pricing_yaml_hash`. Harness threads pricing through. Comprehensive `tests/test_metrics.py`.

### M4 — Full task set + adversarial tests (~3 hr)
All 20 skill-specific tasks now live under `tasks/skill-specific-v1/`:
- **TDD enforcement** (4): fizzbuzz, Roman numerals with hidden test bank, bugfix-first refactor, BoundedStack with interleaved cycles.
- **Code review** (4): off-by-one slice, mutable default arg, SQL injection f-string, lazy-init race.
- **Style adherence** (4): ruff strict, mypy strict, ruff format with AST-equality, TypeScript tsc+ESLint+Jest.
- **Refactor** (4): extract method, conditional→polymorphism, pull-up duplication, parameter object.
- **Multi-file** (4): rename across 5 files, schema drift, deprecate+migrate, type-signature ripple under mypy strict.

Each grader is a deterministic Python decision procedure with adversarial mitigations explicit in the spec (`tasks/skill-specific-v1/README.md`). TaskSet hash is stable + deterministic. Adversarial flag triggers from the metric registry are covered by tests; the synthetic-pathological-skill tests in `tests/adversarial/` are seeded but deferred to Phase 3.

### M5 — Reproducibility + verification (~1 hr)
`submit.py` — `build_leaderboard_entry()` constructs the canonical JSON with `entry_hash = sha256(skill_bundle_hash || task_set_hash || model || temperature || seed_list || pricing_yaml_hash)`. `verify_entry()` re-runs from scratch in a clean sandbox; compares per-task pass/fail strictly, cost within ±5%, latency within ±25%, surfaces flipped tasks for the `borderline-stability` flag. CLI gains `submit` + `verify` subcommands. Tests cover eligibility refusal and entry-hash stability across runs.

### M6 — Leaderboard frontend + data pipeline (~1 hr)
`src/agenteval/leaderboard_export.py` — aggregates entry JSONs into `frontend/public/data/leaderboard.json`. `frontend/` — Next.js 14 + App Router + Tailwind, static export (`output: "export"`). Two-panel page: primary table + secondary panel with the contamination banner (per ADR-0014). `LeaderboardTable.tsx` client component with column sorting and flag badges. Verified/pending badge per row. No tracking, no login, no client analytics. README documents PR-based submission flow.

### Test suite

Test files now:
- test_schema.py · test_loader.py · test_skill_bundle.py · test_grading_utils.py · test_reproducibility.py · test_demo_path.py · test_sandbox_docker.py · test_metrics.py · test_submit_verify.py.
- ~85+ tests; Docker tests skip when daemon unreachable; symlink rejection test skips on Windows.

### Real-API smoke run — still owned by the user

```bash
# PowerShell:
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Leaderboard-equivalent run (5 canonical seeds; cost depends on bundle):
agenteval eval --skills none --tasks skill-specific-v1 --model claude-opus-4-7 --out result.json
agenteval submit ./result.json
agenteval verify ./result.entry.json --skills none --tasks skill-specific-v1

# Or cross-provider:
agenteval eval --skills none --tasks skill-specific-v1 --runner openai --model gpt-5.2 --out result-openai.json
agenteval eval --skills none --tasks skill-specific-v1 --runner google --model gemini-3-pro --out result-google.json
```

## ADRs added across the project so far

- **ADR-0001–0010** — initial Phase 0 commitments (name, license, Python version, multi-provider, Docker sandbox, no LLM-as-judge, DuckDB + static export, content-addressed reproducibility, 100-task ceiling, session protocol).
- **ADR-0011** (superseded by 0014) — SWE-bench-Lite with banner caveats.
- **ADR-0012** — Report pass^k alongside pass@k.
- **ADR-0013** — `pricing.yaml` SHA in entry hash; 30-day stale flag.
- **ADR-0014** — Demote SWE-bench-Lite to secondary panel; primary = skill-specific + TAU-Bench.
- **ADR-0015** — Canonical seed list `[1,2,3,4,5]` for primary-leaderboard entries; closes the cherry-pick attack.
- **ADR-0016** — Model response fingerprint snapshotting; `timeout_rate` as first-class metric; per-provider normalized baseline.

No new ADRs from M1 — the GraderError-catch refinement is consistent with the existing docs/tasks.md §3.4 commitment.

## What the next session does

**Phase 3 — Polish (22 hr)**. The codebase is feature-complete for v1; the next phase is quality, docs, and pre-launch.

1. **§6.1 README hero block** — leaderboard screenshot + 30-second TL;DR; rewrite to launch-quality.
2. **§6.2 Methodology doc to workshop-paper quality** — `docs/methodology.md` is already ~7k words; expand to ~5000 polished words + bibliography + adversarial-defence section in `docs/adversarial.md` (currently a stub).
3. **§6.3 Pre-launch outreach** — emails to mattpocock, obra, andrej-karpathy-skills, forrestchang, safishamsi with the methodology doc, 7–10 days before launch.
4. **§6.4 Adversarial post-launch defense** → `docs/faq.md` with the criticism→response table from master prompt §6.4.
5. **§6.5 CI / repo hygiene** — GitHub Actions for lint+type+test on push; pre-commit; Dependabot; templates; 10 good-first-issues.
6. **§6.6 Reproducibility hardening** — promote `sandbox/image.lock`'s SHA placeholder to a real digest; pin Python deps via `pip-compile`; container image SHAs in `entry_hash` (currently the image tag is pinned but not part of the hash — could be ADR-0017).
7. **§6.7 Cross-platform sanity** — `--remote` SSH runner for the two-VM verifier rule (currently in the methodology but not implemented).

**Phase 4 (12 hr)** — launch kit: Show HN, r/ML, Twitter, blog. Workshop paper submission within 30 days of launch.

### Open questions worth surfacing before Phase 3

- Domain registration (`agenteval.dev`)? Currently the docs reference it but it's a placeholder.
- Whether to bake the JS/TS/jest toolchain into the sandbox base image now (for `style-adherence-04`) or ship a second `agenteval-sandbox:js` variant.
- Whether `sandbox_image_sha` should be part of `entry_hash` (currently it's not, although the image is documented and verifiable). Probably yes — would be ADR-0017.

## Open questions awaiting human input

See [§10 of the master prompt](../02-agenteval.md):
1. LLM-as-judge in v1 or v2? (current default: v2 only; ADR-0006)
2. Holdout-rotation cadence: quarterly vs. aligned with major model releases?
3. Skill-author opt-out policy formalization.
4. Commercial provider partnerships (free credits) — accept or refuse?
5. Workshop co-authorship with an established methodologist?

Not strictly blocking until Phase 1 design wrap (§4.7 exit gate).

## Open questions awaiting human input

See [§10 of the master prompt](../02-agenteval.md) — five open questions. Not blocking until end of Phase 1.

## Session-start checklist

```
[ ] Read STATUS.md  (this file)
[ ] Read DECISIONS.md
[ ] Run: pytest tests/test_demo_path.py  — must be green  (skip until M1)
[ ] State current phase, milestone, blocker
[ ] Proceed with the "Next concrete action" above
```

## Session log (most-recent first)

- **2026-05-13** — Session 1 (~6 hr). **Phase 0 + Phase 1 substantive drafts.** Bootstrap (STATUS, DECISIONS, LICENSE, pyproject, README, .gitignore, CLAUDE.md, 4 memory files). Phase 0: methodology.md (~7k words) + tasks/skill-specific-v1/README.md (20 tasks via background agent) + adversarial.md stub. Adversarial self-review surfaced three issues → ADRs 0014–0016. Phase 1: DESIGN.md + docs/tasks.md + docs/metrics.md + docs/sandbox.md + docs/reproducibility.md + docs/leaderboard.md.
- **2026-05-13** — Session 2 (~5 hr). **Phase 2 M1 complete.** Built `src/agenteval/` end-to-end: errors, reproducibility hashing, Pydantic task schema (with LLM-import ban), TaskSet loader, SkillBundle, grader types + utility library + runtime, LocalSubprocessSandbox, Runner ABC + AnthropicRunner + MockRunner, Harness/Result/PerAttempt, Click CLI. 5 reference task YAMLs. 60 tests passing + 1 expected skip.

- **2026-05-13** — Session 3 (~11 hr, autonomous run-through). **Phase 2 M2–M6 complete.** M2 added DockerSandbox + sandbox selection + image.lock + Dockerfile.base + `tests/test_sandbox_docker.py` (skip gracefully without daemon). M3 added the full metrics module (Chen-2021 estimator, pass^k, cost, latency, tool_calls, timeout_rate, 8 adversarial flags, bootstrap CI, pricing.yaml with all three providers), wired into Result.summary, plus OpenAIRunner + GoogleRunner. M4 added all 15 remaining task YAMLs (TaskSet now loads 20 tasks across 5 categories). M5 added `submit.py` with `build_leaderboard_entry` (content-addressed entry_hash) and `verify_entry` (re-run + structured-feature comparison + tolerance). CLI gained `submit` + `verify`. M6 added `leaderboard_export.py` plus a Next.js 14 + Tailwind static-export frontend with a two-panel sortable LeaderboardTable. Best-judgement calls on M2/M3 open questions (image tag, layered pip_install, deferred --remote runner) documented inline. Test count expanded across all milestones.
