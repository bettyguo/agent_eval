# Metrics

Per-metric formulas, units, adversarial breaking strategies, and CI/bootstrap
protocols. Methodology context in [methodology.md](methodology.md) §5.

## 1. Metric registry

### 1.1 Primary capability

#### pass@1

Per-task probability that a single sampled completion (temperature 0, seed
1) passes the grader. Averaged across tasks for the run-level metric.

- per-task: `pass@1_task = 1[seed_1_passed]`
- run-level: `pass@1_run = (1/T) * sum_task pass@1_task`
- unit: probability in [0, 1]
- 95% CI: bootstrap over T tasks (resample with replacement, 10 000 iters).
  Seeds are not resampled because only one seed contributes.

Adversarial concern: a skill that gets one of 50 tasks right by chance still
scores 0.02. Only a problem if T is small (70 primary). Mitigation: never
quote the point estimate without its CI.

Implementation: `src/agenteval/metrics/pass_at_k.py::pass_at_1`.

#### pass@5

Probability that at least one of 5 sampled completions passes the grader,
using the Chen 2021 unbiased estimator:

$$
\widehat{\text{pass@}k}_{\text{task}} \;=\; 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

Run-level: average over tasks. At `k = n = 5` this simplifies to
`1[c >= 1]`; the general form is preserved in code for future runs at
`n > k`.

- unit: probability in [0, 1]
- 95% CI: bootstrap over T tasks; seeds not resampled at k=n

Adversarial: a nondeterministically successful skill has high pass@5 and low
pass@1. Caught by the `high-variance` flag.

Implementation: `src/agenteval/metrics/pass_at_k.py::pass_at_k`. Edge cases
covered by tests:

| Input | Expected |
|---|---|
| `n=k=c` | 1.0 |
| `c=0` | 0.0 |
| `c=1, n=2, k=1` | 0.5 |
| `c=1, n=5, k=5` | 1.0 |
| `c=0, n=5, k=5` | 0.0 |
| Large `n` | computed in log-space without overflow |

#### pass^5

TAU-Bench reliability metric (Yao et al. 2024). Fraction of tasks where all
5 seeds pass.

- per-task: `pass^5_task = 1[c == n]`
- run-level: `(1/T) * sum_task pass^5_task`
- unit: probability in [0, 1]
- 95% CI: bootstrap over T tasks

Adversarial: a skill optimised for pass^5 might be timid, preferring easy
tasks and refusing harder ones. Caught by the `passive` flag
(`timeout_rate >= 2x baseline` AND `pass^5 >= baseline pass^5`).

### 1.2 Efficiency

#### cost_usd

```
cost = (tokens_in * price_in + tokens_out * price_out) / 1_000_000
```

Prices from `pricing.yaml` keyed by `(provider, model)`. The `pricing.yaml`
SHA is part of `entry_hash`; submissions with a stale `pricing.yaml`
(>30 days) get the `pricing-stale` flag.

- reported: median + p95 across (task x seed) pairs
- unit: USD
- 95% CI: bootstrap over (task, seed) pairs (cost distribution is
  heavy-tailed)

Adversarial: a skill that pads context to win on pass-rate inflates cost.
Mitigated by `talkative` and the Pareto plot.

#### latency_s

Wall-clock seconds from first API request to grader's final-state receipt.

- reported: p50 + p95
- unit: seconds
- 95% CI: bootstrap over (task, seed) pairs

Caveat: latency is partly provider-side and varies with region, time of day,
and provider batching. The verifier tolerates +/-25% on `latency_s_p50`.

#### tool_calls

Count of normalised tool invocations per (task, seed). Provider-specific
tool names are mapped to a common vocabulary (`Read`, `Write`, `Edit`,
`Bash`, `Glob`, `Grep`).

- reported: median + p95
- 95% CI: bootstrap over (task, seed) pairs

#### timeout_rate

```
timeout_rate = #{(task, seed) : timed_out} / (T * n_seeds)
```

- unit: probability in [0, 1]
- 95% CI: Wilson interval (binomial proportion)

A skill that exhausts wall-time on every task would otherwise look identical
on the leaderboard to one that produces wrong-but-quick answers. Surfacing
this separately makes the failure mode legible.

## 2. Adversarial flags

Flags are descriptive badges; they carry no weight in sort order. Each is a
deterministic check.

| Flag | Trigger |
|---|---|
| `high-variance` | `pass@5_run >= 2 x pass^5_run` |
| `talkative` | median `tokens_out` per task >= 2x same-model no-skills baseline |
| `tool-storm` | median `tool_calls` per task >= 2x same-model no-skills baseline |
| `pricing-stale` | `pricing.yaml.last_audited` more than 30 days before submission |
| `model-drift` | provider response fingerprint differs between submission and re-verification |
| `borderline-stability` | at least one task's pass/fail flipped between submission and re-verification |
| `holdout-divergence` | `|pass@1_public - pass@1_holdout| > 0.15` |
| `passive` | `timeout_rate >= 2x baseline` AND `pass^5_run >= baseline pass^5_run` |

`high-variance` has a real false-positive risk: a skill genuinely improving
a difficult task may legitimately have low pass^5 despite improved pass@5.
The flag is informational, not punitive.

## 3. Bootstrap CI protocol

For every metric reported with a CI:

1. Identify the resampling unit (tasks for capability metrics; (task, seed)
   pairs for efficiency metrics).
2. Sample with replacement to the same N as the original sample.
3. Recompute the metric on the resample.
4. Repeat 10 000 times.
5. CI = the empirical 2.5th and 97.5th percentiles.

Implementation: `src/agenteval/metrics/bootstrap.py`. Tests cover the
Wilson-interval match for Bernoulli samples, heavy-tail correctness on
log-normal cost distributions, and seed-determinism.

## 4. Excluded from primary metrics

- LLM-as-judge scores (v1 = deterministic graders only).
- Subjective style scores.
- Aggregate scalar rank. The leaderboard is sortable; no overall ranking is
  published.
- Provider-comparison absolutes. Cross-provider comparisons are
  delta-from-baseline, never absolute pass-rates.
