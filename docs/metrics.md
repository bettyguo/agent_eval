# Metrics specification

> Phase 1 §4.3 deliverable. Per-metric formulas, units, adversarial breaking strategies, mitigations, and CI/bootstrap protocols. The metric registry is locked here; new metrics require an ADR and a `docs/metrics.md` version bump.

Methodology context in [`methodology.md`](methodology.md) §5; adversarial test plans in [`adversarial.md`](adversarial.md).

---

## 1. Metric registry

### 1.1 Primary capability metrics

#### `pass@1`

**Definition.** Per-task probability that a single sampled completion (at temperature 0, seed = 1) passes the grader. Averaged across tasks gives the run-level `pass@1`.

Per-task: `pass@1_task = 1[seed_1_passed]`.
Run-level: `pass@1_run = (1/T) Σ_{task} pass@1_task`.

**Unit.** Probability ∈ [0, 1].

**95% CI.** Bootstrapped over T tasks (resample tasks with replacement, 10 000 iterations). Seeds are not resampled because for `pass@1` only one seed contributes. Per-task `pass@1` is binary, so the run-level CI captures task-difficulty heterogeneity.

**Adversarial.** A skill that gets exactly 1 task right out of 50 by chance still scores 0.02; that's only a problem if T is small (it is — 70 primary tasks). Mitigation: report `pass@1` only with the CI; never quote the point estimate alone.

**Implementation.** `src/agenteval/metrics/pass_at_k.py::pass_at_1`. Trivial.

---

#### `pass@5`

**Definition.** Probability that at least one of 5 sampled completions passes the grader. Uses the Chen et al. 2021 unbiased estimator.

For a task with `c` successful seeds out of `n = 5`:

$$
\widehat{\text{pass@}k}_{\text{task}} \;=\; 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

Run-level: `pass@5_run = (1/T) Σ_{task} pass@5_task`. We use `k = n = 5` so the estimator simplifies — for a 5-seed run, `pass@5_task = 1[c ≥ 1]`. We keep the general estimator in code for future runs at `n > k`.

**Unit.** Probability ∈ [0, 1].

**95% CI.** Bootstrapped over T tasks (resample tasks with replacement, 10 000 iterations). Seeds NOT resampled, for the same reason as §1.1 — at k=n, the per-task value is fully determined by the seeds we ran.

**Adversarial.** A skill that nondeterministically outputs a random valid implementation has high `pass@5` and low `pass@1`. Mitigation: the `high-variance` flag (§2.1) catches this, as does pairing `pass@5` with `pass^5`.

**Implementation.** `src/agenteval/metrics/pass_at_k.py::pass_at_k`. Edge-case tests required:

| Test | Expected |
|---|---|
| `n=k=c` | `1.0` |
| `c=0` | `0.0` |
| `c=1, n=2, k=1` | `0.5` |
| `c=1, n=5, k=5` | `1.0` |
| `c=0, n=5, k=5` | `0.0` |
| Large `n` (combinatorial overflow guard) | computed in log-space without overflow |

---

#### `pass^5`

**Definition.** TAU-Bench-style reliability metric (Yao et al. 2024). Probability that all 5 seeds pass for a given task.

Per-task: `pass^5_task = 1[c == n]`.
Run-level: `pass^5_run = (1/T) Σ_{task} pass^5_task`.

**Unit.** Probability ∈ [0, 1].

**95% CI.** Bootstrapped over T tasks; same protocol as `pass@5`.

**Adversarial.** Inversely, a skill optimised for `pass^5` might be timid — preferring easy tasks it can nail consistently, refusing harder ones. Mitigation: report `pass^5` alongside `pass@1`, `pass@5`; flag `passive` if `timeout_rate ≥ 2 × baseline timeout_rate` (i.e., the skill is silently bailing).

**Implementation.** `src/agenteval/metrics/pass_caret_at_k.py`. Trivial given per-task pass-counts.

---

### 1.2 Efficiency metrics

#### `cost_usd`

**Definition.** Per (task, seed) cost in US dollars:

```
cost_task_seed = (tokens_in × price_per_million_in + tokens_out × price_per_million_out) / 1_000_000
```

Prices are looked up in `pricing.yaml` keyed by `(provider, model)`. The `pricing.yaml` SHA is part of the entry hash (ADR-0013); a stale `pricing.yaml` (≥30 days) triggers the `pricing-stale` flag.

**Reported aggregates.** Median + 95th percentile across (task × seed) pairs.

**Unit.** USD.

**95% CI.** Bootstrap as above, but resample (task, seed) pairs since the cost distribution is heavy-tailed and we want the CI to reflect that.

**Adversarial.** A skill that pads system-prompt context to win on pass-rate inflates cost. Mitigation: `talkative` flag (§2.2); Pareto plot exposes the trade-off visually.

**Implementation.** `src/agenteval/metrics/cost.py`. Tests: deterministic given fixed pricing.yaml + token counts; mismatched pricing yields a clear error rather than a silent zero.

---

#### `latency_s`

**Definition.** Wall-clock seconds per (task, seed), measured by the harness from "send first API request" to "grader receives final state."

**Reported aggregates.** `latency_s_p50` (median) and `latency_s_p95` (95th percentile).

**Unit.** Seconds.

**95% CI.** Bootstrap over (task, seed) pairs. Reported as a band around p50 and p95.

**Adversarial.** A skill that triggers many small tool calls inflates latency at marginal cost. Mitigation: `tool-storm` flag (§2.3); Pareto plot includes a latency axis.

**Caveat.** Latency is partly provider-side and varies with regional infra, time of day, and provider batching. The verifier tolerates ±25% on `latency_s_p50` (per `docs/reproducibility.md`); strict comparison would produce false drift alarms.

**Implementation.** `src/agenteval/metrics/latency.py`. Tests: synthetic trajectories produce expected percentiles; tolerance enforced on synthetic noisy data.

---

#### `tool_calls`

**Definition.** Count of normalized tool invocations per (task, seed). The normalization is per the trajectory schema in `docs/tasks.md` §3.2 — provider-specific tool names are mapped to a common vocabulary (`Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, ...).

**Reported aggregates.** Median + 95th percentile across (task × seed) pairs.

**Unit.** Count.

**95% CI.** Bootstrap over (task, seed) pairs.

**Adversarial.** As above — `tool-storm` flag is the structural mitigation.

**Implementation.** `src/agenteval/metrics/tool_calls.py`.

---

#### `timeout_rate`

**Definition.** Fraction of (task, seed) pairs that hit `time_budget_s` without producing a final assistant message. Per ADR-0016.

```
timeout_rate = #{(task, seed) : timed_out} / (T × n_seeds)
```

**Unit.** Probability ∈ [0, 1].

**95% CI.** Wilson interval (binomial proportion), since this is a single proportion across all (task, seed) pairs.

**Why first-class.** Without this metric, a skill that exhausts wall-time on every task looks identical on the leaderboard to one that produces wrong-but-quick answers. Surfacing it separately makes the failure mode legible.

**Implementation.** `src/agenteval/metrics/timeout_rate.py`. Trivial; tests on synthetic mixed trajectories.

---

## 2. Adversarial flags (descriptive badges, never ranked)

Flags carry no weight in any sort order. They appear on the leaderboard row as badges. Each is the output of a deterministic check; all are unit-tested with synthetic pathological skills (`tests/test_metrics.py::adversarial`).

### 2.1 `high-variance`

**Trigger.** `pass@5_run ≥ 2 × pass^5_run`.

**Meaning.** The skill is nondeterministically lucky; one of five seeds tends to pass, but rarely all five. This is consistent with a skill that broadens the agent's sampling without sharpening it.

**False positive risk.** A skill genuinely improving a difficult task may legitimately have low `pass^5` despite improved `pass@5`. Mitigation: the flag is informational, not punitive; it appears as a badge, not a rank deduction.

### 2.2 `talkative`

**Trigger.** Median `tokens_out` per task ≥ 2 × the same model's no-skills baseline median `tokens_out` on the same task set.

**Meaning.** The skill is producing significantly more output than the baseline, inflating cost and latency.

### 2.3 `tool-storm`

**Trigger.** Median `tool_calls` per task ≥ 2 × the same model's no-skills baseline median.

**Meaning.** The skill is invoking tools more aggressively than the baseline. May be legitimate (e.g., a `read-thoroughly` skill); the flag makes the trade-off visible.

### 2.4 `pricing-stale`

**Trigger.** `pricing.yaml.last_audited` is more than 30 calendar days before the submission date.

**Meaning.** Cost numbers may not reflect current provider pricing. Re-running with fresh pricing produces a new entry hash (per ADR-0013).

### 2.5 `model-drift`

**Trigger.** The `model_response_fingerprint` recorded at submission time differs from the fingerprint observed during re-verification.

**Meaning.** The provider has updated the underlying model weights without changing the API model string. Per ADR-0016, deltas across drift are not directly comparable; the flag warns readers.

### 2.6 `borderline-stability`

**Trigger.** Any single task's pass/fail flips between submission and re-verification (at least one of the 5 seeds differs).

**Meaning.** This task is on the boundary; outcomes are not stable even at temperature 0. We do not invalidate the entry; we surface the flag so readers can interpret the gap.

### 2.7 `holdout-divergence`

**Trigger.** The public-task-set `pass@1` and the current quarterly-holdout `pass@1` differ by more than 15 percentage points (in either direction).

**Meaning.** The skill behaves differently on tasks the author may have seen vs. tasks they could not have seen. A strong signal of Goodhart's-Law overfitting.

### 2.8 `passive`

**Trigger.** `timeout_rate ≥ 2 × baseline timeout_rate` AND `pass^5_run ≥ baseline pass^5_run`.

**Meaning.** A skill that improves reliability by silently bailing on hard tasks (preferring time-outs over wrong answers). Surfaced so the leaderboard cannot reward this.

---

## 3. Bootstrap CI protocol

For every metric reported with a CI:

1. Identify the unit of resampling — tasks for capability metrics, (task, seed) pairs for efficiency metrics.
2. Sample with replacement to the same N as the original sample.
3. Recompute the metric on the resample.
4. Repeat 10 000 times.
5. CI = the empirical 2.5th and 97.5th percentiles of the bootstrap distribution.

The bootstrap implementation is in `src/agenteval/metrics/bootstrap.py`. Tests:

- Reproduces analytic Wilson interval within Monte-Carlo error on a synthetic Bernoulli sample.
- Heavy-tail-correct on a synthetic log-normal cost distribution.
- Deterministic at a fixed seed.

---

## 4. What we do NOT report as primary

- **LLM-as-judge scores.** Per ADR-0006. Held even after Phase 0 adversarial review.
- **Subjective "style quality".** Linter passes are objective; aesthetic quality is not.
- **Aggregate scalar rank.** Per `methodology.md` §10. Goodhart's-Law non-negotiable.
- **Provider-comparison absolutes.** Cross-provider comparisons are always delta-from-baseline per ADR-0016, never absolute pass-rates.

---

## 5. To-do (Phase 2 M3)

- [ ] Implement pass@k estimator + unit tests.
- [ ] Implement pass^k.
- [ ] Implement cost / latency / tool_calls / timeout_rate.
- [ ] Implement the 8 adversarial flags with synthetic-skill tests.
- [ ] Implement bootstrap CI module.
- [ ] Wire metrics into `Result.summary`.
