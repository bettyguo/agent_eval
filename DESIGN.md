# DESIGN

> Phase 1 deliverable. Locks the public API, the task YAML format, the metric specs, the sandbox design, the reproducibility protocol, and the leaderboard wireframes. Sub-documents (`docs/tasks.md`, `docs/metrics.md`, `docs/sandbox.md`, `docs/reproducibility.md`, `docs/leaderboard.md`) expand each section in detail. This document is the integrating contract; if a sub-doc contradicts it, this doc wins until updated.

**Document status:** v0.1 draft, Phase 1. Mirrors `docs/methodology.md` decisions. After user sign-off, code in Phase 2 M1+ implements against these contracts.

---

## 1. Public Python API (Phase 1 §4.1)

### 1.1 Surface

The user-facing API is intentionally small. Three classes, one function.

```python
from agenteval import Harness, SkillBundle, TaskSet, evaluate

# Load a skill bundle from a directory of .claude/skills/<skill>/SKILL.md files.
# Or from a single CLAUDE.md (compatibility loader).
bundle: SkillBundle = SkillBundle.from_dir("./.claude/skills/")
bundle_md: SkillBundle = SkillBundle.from_claude_md("./CLAUDE.md")
bundle_none: SkillBundle = SkillBundle.empty()             # the no-skills baseline

# Load a task set by registry name, or from a path.
task_set: TaskSet = TaskSet.load("skill-specific-v1")
task_set_local: TaskSet = TaskSet.from_dir("./tasks/skill-specific-v1/")

# Build a harness pinned to a provider + model + temperature.
harness = Harness(
    runner="anthropic",          # one of "anthropic", "openai", "google"
    model="claude-opus-4-7",     # exact API model string
    temperature=0.0,             # MUST be 0.0 for leaderboard entries
    canonical_seeds=True,        # default True; uses [1,2,3,4,5] per ADR-0015
)

# Run.
result: Result = harness.evaluate(bundle, task_set)

# Inspect.
result.summary()                 # → printable table of pass@1, pass@5, pass^5, cost, latency, tool_calls, timeout_rate, flags
result.per_task()                # → pandas DataFrame, one row per (task, seed) pair
result.flags()                   # → list of (flag_name, reason) tuples raised against this run

# Persist.
entry: LeaderboardEntry = result.to_leaderboard_entry()    # JSON-serializable; hash-stamped
entry.write("./result.json")

# Convenience for the 90% case: one-line eval that builds Harness + evaluates + writes JSON.
evaluate(skill_dir=".claude/skills/", task_set="skill-specific-v1",
         runner="anthropic", model="claude-opus-4-7", out="./result.json")
```

### 1.2 Class contracts

#### `SkillBundle`

Immutable. Constructor private; build via the three classmethods.

| Method | Source | Notes |
|---|---|---|
| `SkillBundle.from_dir(path)` | A `.claude/skills/` directory tree | Each immediate child must contain a `SKILL.md`. Other files (scripts/, references/, assets/) are included verbatim. |
| `SkillBundle.from_claude_md(path)` | A single `CLAUDE.md` file | Wrapped as a single synthetic skill named `claude-md`. Compatibility for users without per-skill directories. |
| `SkillBundle.empty()` | nothing | The no-skills baseline. Has a stable hash (`sha256("AGENTEVAL_EMPTY_BUNDLE_v1")`). |

Properties:
- `bundle.hash: str` — SHA256 of the normalized tarball (sorted files, stripped trailing whitespace, no timestamps, perms normalized; per `docs/reproducibility.md`).
- `bundle.skills: list[Skill]` — parsed skill records with `name`, `description` (YAML frontmatter required), `body`, `extra_files`.
- `bundle.license_summary: list[tuple[str, str]]` — list of `(skill_name, license_string)` extracted from each `SKILL.md` if a `license:` frontmatter key is present.

#### `TaskSet`

Immutable. Constructor private; build via classmethods.

| Method | Source |
|---|---|
| `TaskSet.load(name)` | Registry lookup. Builtin names: `skill-specific-v1`, `swe-bench-lite-v1`, `tau-bench-v1`. |
| `TaskSet.from_dir(path)` | Any directory of YAML files conforming to the task schema. |

Properties:
- `task_set.hash: str` — SHA256 of the normalized tarball.
- `task_set.name: str` — human-readable.
- `task_set.tasks: list[Task]` — parsed task records, schema-validated by pydantic.
- `task_set.panel: Literal["primary", "secondary"]` — declared in the task set's `meta.yaml`. `skill-specific-v1` and `tau-bench-v1` declare `primary`; `swe-bench-lite-v1` declares `secondary`. Used by the leaderboard rendering; primary-panel-only metrics are computed only for primary task sets.

#### `Harness`

Immutable after construction. Holds runner + model config; takes a bundle + task set + returns a `Result`.

```python
Harness(
    runner: Literal["anthropic", "openai", "google"],
    model: str,                                # exact API model string
    temperature: float = 0.0,                  # default 0.0; non-zero allowed for --exploratory
    canonical_seeds: bool = True,              # default True; if True, seeds = [1,2,3,4,5]
    custom_seeds: list[int] | None = None,     # only allowed when canonical_seeds=False
    timeout_per_task_s: int | None = None,     # default = task's `time_budget_s`; can be lowered
    sandbox_image_sha: str | None = None,      # default = current pinned image
    pricing_yaml_path: str = "<package-default>",  # path to pricing.yaml
    api_key_env: str | None = None,            # override the default env var for the runner
    parallelism: int = 4,                      # max concurrent tasks; provider rate-limits override
)
```

Methods:
- `harness.evaluate(bundle: SkillBundle, task_set: TaskSet) -> Result` — runs every task × seed in the sandbox, with progress reporting via `rich`.
- `harness.dry_run(bundle, task_set) -> DryRunPlan` — prints what would be run, total estimated cost (from `expected_tokens` × pricing.yaml), without making API calls.
- `harness.verify(entry: LeaderboardEntry) -> VerificationReport` — re-runs the entry from scratch in a fresh sandbox; compares structured features per §7.

If the harness is constructed with `temperature ≠ 0.0` or `canonical_seeds=False` and `harness.evaluate(...)` is called, the resulting `Result` is tagged `leaderboard: false` and `to_leaderboard_entry()` refuses with an explanatory exception. This is the API gate referenced in ADR-0015.

#### `Result`

Immutable. The output of `evaluate`.

Properties:
- `result.bundle_hash`, `result.task_set_hash`, `result.model`, `result.temperature`, `result.seeds`, `result.pricing_yaml_hash`, `result.model_response_fingerprint` (may be None for providers that don't expose it).
- `result.entry_hash: str` — the canonical hash. None if `leaderboard: false`.
- `result.per_task: pd.DataFrame` — columns: `task_id`, `category`, `seed`, `passed: bool`, `tokens_in`, `tokens_out`, `tool_calls`, `latency_s`, `timeout: bool`, `trajectory_path: str`.
- `result.summary: dict[str, float]` — pass@1, pass@5, pass^5, cost_usd_median, cost_usd_p95, latency_s_p50, latency_s_p95, tool_calls_median, timeout_rate.
- `result.flags: list[Flag]` — adversarial flags raised against this run.
- `result.leaderboard_eligible: bool` — `True` only if `temperature=0.0`, `seeds=[1,2,3,4,5]`, `task_set.panel == "primary"`, and there is no `borderline-stability` flag from a self-consistency dry-run.

Methods:
- `result.to_leaderboard_entry() -> LeaderboardEntry` — raises `LeaderboardIneligible` if `leaderboard_eligible` is False.
- `result.to_duckdb(path: str)` — append-only write to `results.duckdb`.
- `result.summary_table() -> str` — printable rich table.

#### `LeaderboardEntry`

A JSON-serializable dataclass. Schema is versioned and published in `schemas/leaderboard-entry.v1.json`.

```json
{
  "schema_version": "1",
  "entry_hash": "sha256:...",
  "submitted_at": "2026-05-13T...",
  "bundle": {
    "hash": "sha256:...",
    "skills": [{"name": "...", "description": "...", "license": "..."}],
    "source_url": "https://github.com/.../tree/<sha>"
  },
  "task_set": {"name": "skill-specific-v1", "hash": "sha256:...", "panel": "primary"},
  "runner": {"name": "anthropic", "model": "claude-opus-4-7",
             "model_response_fingerprint": "fp_abc123",
             "temperature": 0.0, "seeds": [1,2,3,4,5]},
  "pricing": {"yaml_hash": "sha256:...", "last_audited": "2026-05-01"},
  "metrics": {"pass@1": {...}, "pass@5": {...}, "pass^5": {...},
              "cost_usd": {...}, "latency_s": {...}, "tool_calls": {...},
              "timeout_rate": {...}},
  "flags": [{"name": "talkative", "details": "..."}],
  "verification": {"verified": false, "report_url": null}
}
```

`flags` are descriptive; never used for ranking. The leaderboard frontend renders them as badges (per `docs/leaderboard.md`).

### 1.3 CLI surface

The CLI is a thin wrapper around the Python API, with one extra command (`leaderboard`) for local viewing.

```bash
# Run an eval.
agenteval eval \
  --skills ./.claude/skills/ \
  --tasks skill-specific-v1 \
  --runner anthropic \
  --model claude-opus-4-7 \
  --out ./result.json

# Exploratory mode (non-leaderboard).
agenteval eval --skills ./.claude/skills/ --tasks skill-specific-v1 \
  --model claude-opus-4-7 --exploratory --seeds 25

# Submit a result for inclusion in the leaderboard data export. Validates schema + leaderboard eligibility.
agenteval submit ./result.json

# Re-verify a submitted entry from scratch. Two-VM rule enforced by CI, not by the local CLI.
agenteval verify ./result.json

# Local leaderboard view (renders the static export).
agenteval leaderboard

# Dry run: print plan + estimated cost, no API calls.
agenteval eval --skills ./.claude/skills/ --tasks skill-specific-v1 \
  --model claude-opus-4-7 --dry-run

# Inspect a single task's trajectory after a run.
agenteval inspect ./result.json --task tdd-enforcement-01 --seed 1
```

Exit codes: 0 success, 1 schema/eligibility error, 2 sandbox failure, 3 API auth failure, 4 verifier mismatch.

### 1.4 Error semantics

- **`SkillBundleError`** — bundle parsing failed (missing SKILL.md, broken frontmatter, symlink).
- **`TaskSetError`** — task YAML parse failure, schema violation, duplicate task IDs.
- **`SandboxError`** — Docker init failed, image SHA unavailable, container OOM.
- **`RunnerError(provider, status_code, reason)`** — provider API error. Includes retry metadata.
- **`LeaderboardIneligible(reason)`** — `to_leaderboard_entry()` called on a non-eligible result.
- **`VerifierMismatch(expected, actual, field)`** — verifier found a strict-equality mismatch.

All errors carry a `details: dict` for structured logging and a `code: str` for stable CLI scripting.

### 1.5 Concurrency

- Tasks within a single `evaluate()` call are executed in parallel up to `Harness.parallelism` (default 4).
- Provider rate-limits are respected via per-runner token-bucket rate-limiters; the harness backs off on `429` with exponential jitter.
- Sandbox containers are spawned in parallel; each task gets its own container. Containers are torn down after their task completes (no reuse — reuse would be a contamination vector).
- The Result aggregator is single-threaded; per-task records flow into a queue.

### 1.6 What this API does NOT support

- Custom graders supplied by the user at evaluation time (graders live in the task set; submitter-supplied graders are a v2 question, dropped from v1 for trust reasons).
- Custom runners. v1 supports the three locked providers; adding a runner is a project-level decision, not a user one.
- Streaming or progressive results to disk between tasks beyond local checkpointing — a `Result` is a single object produced at the end of an `evaluate()` call. Long-running runs can be resumed via the harness checkpoint flag (a v1.1 feature; not in M1).
- LLM-as-judge graders (ADR-0006).

---

## 2. Task YAML format (Phase 1 §4.2)

See [`docs/tasks.md`](docs/tasks.md) for the full spec. Summary:

```yaml
id: tdd-enforcement-01            # kebab-case, unique within task set
category: tdd-enforcement         # one of: tdd-enforcement, code-review, style-adherence, refactor, multi-file
description: "≤200 char one-liner shown on the leaderboard"
license: MIT                      # SPDX identifier
setup:
  files:                          # files materialized in sandbox cwd at t=0
    "fizzbuzz.py": "def fizzbuzz(n): pass\n"
prompt: |                         # the prompt the agent sees
  Implement fizzbuzz using test-driven development.
grader:
  type: python                    # only "python" supported in v1
  script: |
    # Receives: workdir (path), trajectory (list of dict), final_state (FileState)
    # Returns: {"passed": bool, "details": {...}}
    ...
time_budget_s: 300                # ≤300 for v1
expected_tokens: 5000             # for cost-normalization; not a hard cap
network: false                    # default false; opt-in if task requires it
panel: primary                    # primary | secondary; inherited from task-set meta.yaml if omitted
```

The format is **locked**. Any change in v1 produces a new task-set version (e.g., `skill-specific-v2`); no in-place edits.

---

## 3. Metrics (Phase 1 §4.3)

See [`docs/metrics.md`](docs/metrics.md) for the full spec with formulas, adversarial breaking strategies, and CI protocols. The metric registry is locked at:

- **pass@1, pass@5** (Chen et al. 2021 unbiased estimator) — capability.
- **pass^5** (TAU-Bench Yao et al. 2024) — reliability.
- **cost_usd** (median, p95) — efficiency.
- **latency_s** (p50, p95) — efficiency.
- **tool_calls** (median, p95) — efficiency.
- **timeout_rate** — failure-mode disambiguator (ADR-0016).

Flags (descriptive badges, never ranked):
- `high-variance` (pass@5 ≥ 2 × pass^5)
- `talkative` (output tokens ≥ 2 × baseline)
- `tool-storm` (tool_calls ≥ 2 × baseline)
- `pricing-stale` (pricing.yaml older than 30 days)
- `model-drift` (provider fingerprint mismatch on re-verification)
- `borderline-stability` (per-task pass/fail flip between submission and verification)
- `holdout-divergence` (public-vs-holdout gap > 15pp)

CIs are 95% bootstrapped, resampling tasks (not seeds — tasks are the dominant variance source).

---

## 4. Sandbox (Phase 1 §4.4)

See [`docs/sandbox.md`](docs/sandbox.md). Summary:

- Docker container per task. Pinned image SHA in run metadata.
- 1 CPU, 2 GB RAM, 5-min wall-time default.
- Network disabled by default. Per-task `network: true` opt-in.
- No host mount outside the per-task working dir; working dir discarded after the task.
- Skill bundle injected at `~/.claude/skills/` inside the container.
- Per-task fingerprint captured in run metadata.
- Threat model: defend against accidental side effects, not deliberate sandbox escape (`methodology.md` §6.2).
- macOS / Windows users: harness emits a perf warning above 20 tasks; recommends remote runner.

---

## 5. Reproducibility (Phase 1 §4.5)

See [`docs/reproducibility.md`](docs/reproducibility.md). Summary:

```
entry_hash = sha256(
    skill_bundle_hash || task_set_hash || model || temperature ||
    seed_list || pricing_yaml_hash
)
```

- Seed list MUST be `[1, 2, 3, 4, 5]` for primary-panel entries (ADR-0015).
- Model response fingerprint is **stored but not hashed** (ADR-0016) — used for `model-drift` detection.
- Verifier compares per-task pass/fail per seed with strict equality; cost/latency within tolerance; trajectory text not compared.
- Two-VM rule (anti-pattern #10): each leaderboard entry is verified in two different cloud zones; agreement required.

---

## 6. Leaderboard frontend (Phase 1 §4.6)

See [`docs/leaderboard.md`](docs/leaderboard.md). Summary:

- Next.js 14 + Tailwind on Vercel, static export from DuckDB.
- Two clearly-separated panels: **Primary** (skill-specific-v1 + tau-bench-v1) and **Secondary — Informative but contaminated** (swe-bench-lite-v1).
- Sortable table view, no scalar rank published.
- Pareto plot (success × cost).
- Filter by task category, model, runner.
- Per-entry expand: bundle SHA, submission JSON link, verification status, fingerprint, date.
- No tracking. No login. Static + edge.
- "Submit your skill" → markdown instructions page (PR-based submission in v1; hosted API is a v2 question).

---

## 7. Phase 1 exit gate

Sign-off requires:

- [x] `DESIGN.md` (this doc) drafted — API surface locked at v0.1.
- [x] [`docs/tasks.md`](docs/tasks.md) mirrors §2 with the full schema, examples, and grader interface.
- [x] [`docs/metrics.md`](docs/metrics.md) mirrors §3 with per-metric formulas, adversarial breaking strategies, unit-test plan.
- [x] [`docs/sandbox.md`](docs/sandbox.md) mirrors §4 with the threat model and Docker recipe.
- [x] [`docs/reproducibility.md`](docs/reproducibility.md) mirrors §5 with hashing, verifier, normalization, partial-determinism honesty.
- [x] [`docs/leaderboard.md`](docs/leaderboard.md) mirrors §6 with wireframes.
- [x] All sub-docs cross-link consistently.
- [x] No contradictions between this doc and `methodology.md` / `DECISIONS.md`.
- [ ] **User reviews `DESIGN.md` and the sub-docs**; signs off before Phase 2 M1 begins.

Once signed off, Phase 2 M1 (Task format + 5 reference tasks) begins, implementing against the locked surface.
