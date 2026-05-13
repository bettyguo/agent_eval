# Methodology

The protocol behind the agenteval benchmark, written for reviewers who want to
challenge it. If a claim here is wrong, please file an issue.

## 1. Motivation

By mid-2026, Claude Code Skills (the `.claude/skills/` directory format that
shipped in late 2025) had become one of the most active categories on GitHub.
Reference repositories like `mattpocock/skills`, `obra/superpowers`, and
`andrej-karpathy-skills` each carry tens of thousands of stars, and the
surrounding discourse circulates quantitative claims ("raises reliability from
60-70% to 95%", "makes Claude 30% faster") with no defined task population,
no control, and no confidence intervals.

agenteval measures whether a `.claude/skills/` directory (or single `CLAUDE.md`
file) changes downstream agent behaviour on a fixed, public task set, across
multiple providers, with full reproducibility.

Three positioning constraints:

1. Narrow scope. This is not a general LLM eval framework. HELM and
   `lm-evaluation-harness` already cover that ground.
2. Comparison over absolute capability. The reported axis is the delta a
   skill bundle introduces against the no-skill baseline, not the model's
   capability. This matters for the contamination discussion in §4.
3. Methodology over headline numbers. The credibility of a benchmark is its
   protocol, not its leaderboard.

## 2. Related work

### 2.1 HELM (Liang et al., 2022)

HELM framed LLM eval as multi-dimensional: not just accuracy but calibration,
robustness, fairness, bias, toxicity, efficiency. ~16 scenarios x 7 metrics
rather than a single headline.

What we borrow: multi-metric reporting. Every leaderboard row carries pass@1,
pass@5, cost, latency, tool-call count, and adversarial flags simultaneously.
The default view is a sortable table; a single rank order is intentionally
absent.

### 2.2 BIG-bench (Srivastava et al., 2022)

204 crowdsourced tasks. Insight: heterogeneity catches things uniform
benchmarks miss. Scar: heterogeneity made it expensive to maintain and made
cross-task aggregation suspect.

What we borrow: distinct task categories with category-level scores. v1 tasks
are author-curated; v2 may add a curated-PR pipeline.

### 2.3 HumanEval / pass@k (Chen et al., 2021)

`arxiv.org/abs/2107.03374` introduced the pass@k metric for code generation,
the probability that at least one of k sampled completions passes the unit
tests. The paper gives the unbiased estimator:

$$
\widehat{\text{pass@}k} \;=\; 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

with `n` total samples, `c` correct samples, `k ≤ n`. This avoids the
high-variance plug-in estimate at non-zero sampling temperature.

We use this estimator verbatim. See [metrics.md](metrics.md). The original
n=200 sampling budget is prohibitive at 2026 frontier prices; we use n in
{5, 10, 25} depending on task cost.

### 2.4 SWE-bench (Jimenez et al., 2024) and the contamination story

SWE-bench evaluates agents on real GitHub issues from 12 Python repos, scored
against the repo's own test suite. SWE-bench-Lite is a 300-task subset chosen
for reproducibility and lower per-task cost; SWE-bench Verified is an
OpenAI-curated 500-task subset that further filters for solubility.

In late 2025, OpenAI publicly announced they would stop reporting SWE-bench
Verified scores: every major frontier model could reproduce verbatim gold
patches under appropriate elicitation, meaning Verified performance was a
confounded mix of capability and memorisation of leaked solutions.

Community response: SWE-bench Pro (tougher tasks, fewer cleanly-leaked
patches) and SWE-bench-Live (continuously updated; monthly new tasks cap the
contamination half-life).

This drives the two-panel architecture in §3.1.

### 2.5 TAU-Bench (Yao et al., 2024)

`arxiv.org/abs/2406.12045`. Simulates multi-turn tool-agent-user interactions
in two domains (retail, airline): an LLM-simulated user with goals, a domain
API with policy documents, evaluation by terminal database state vs.
annotated goal. Introduces the pass^k metric: the fraction of tasks where
the agent succeeds in all k independent trials. pass^k is reliability-oriented
where pass@k is capability-oriented.

We borrow pass^k as an auxiliary reliability metric reported alongside pass@k.
A skill that raises pass@1 by 5 points but lowers pass^5 by 10 points is
introducing volatility, which is the failure mode we want to detect.

We leave behind the LLM-simulated user. v1 adapts the single-shot tool-use
subset of TAU-Bench; multi-turn simulation goes to v2 because (a) it
introduces a second LLM in the loop and (b) it inflates per-task cost.

### 2.6 METR HCAST / RE-Bench (Kwa et al., 2025)

`arxiv.org/abs/2503.14499`. METR's time-horizon framework doesn't score
pass-rate; it fits a logistic regression of P(success | log human completion
time) and reports the 50% time horizon. As of Time-Horizon 1.1 (Jan 2026)
frontier models sit at roughly 50-60 minutes of human-equivalent time.

We don't fit a logistic curve (too few tasks, too much variance for v1), but
we report per-category pass rates with similar intent: a skill that helps on
5-min tasks but not 30-min tasks should look different from one that helps
uniformly.

### 2.7 Recent surveys

Mohammadi et al.'s *Evaluation and Benchmarking of LLM Agents* survey
(`arxiv.org/html/2507.21504v1`) lays out the taxonomy: evaluation objectives
(behaviour, capabilities, reliability, safety) crossed with evaluation
process (interaction mode, dataset, metric computation, environment).
NeurIPS 2025 alone carried 45+ papers in computer-use agents.

We tag each leaderboard entry with (objective, process) axes so future
filters and meta-analyses can slice cleanly.

### 2.8 lm-evaluation-harness (EleutherAI)

The de facto infrastructure for academic LM eval. Strength: breadth of task
adapters, standardised scoring discipline. Limitation for our use case: it
assumes a generation-then-score loop, not a tool-using agent with a
trajectory.

We borrow the discipline of pinned task-set versioning (semver:
`skill-specific-v1`, `swe-bench-lite-v1`, etc.) but don't integrate
upstream; forking would pull us back toward general LM eval.

## 3. Task selection

### 3.1 Two leaderboard panels

After adversarial self-review, v1 ships with two panels. The primary panel
underwrites all headline claims; the secondary panel is informative but
explicitly non-citable.

Primary (uncontaminated):

| Family | Source | Count |
|---|---|---|
| `skill-specific-v1` | hand-curated | 20 |
| `tau-bench-v1` | Yao et al. 2024, subset | 50 |
| Total | | 70 |

Secondary (informative but contaminated):

| Family | Source | Count |
|---|---|---|
| `swe-bench-lite-v1` | Jimenez et al. 2024, subset | 30 |

Rendered in a separate section of the leaderboard with a banner:
*"Contaminated benchmark; delta may be confounded by skill x memorisation
interaction; not citable as a skill-effect claim."*

v1 grand total: 100 tasks. v2 migrates the SWE-bench family from Lite to
Pro + Live.

### 3.2 Why these task families

- Statistical floor. A 100-task set with a no-skill baseline is the minimum
  for detecting a ~5-point skill-induced delta at 95% confidence over 5
  seeds.
- Skill-discriminating core. The 20 hand-curated tasks are explicitly
  designed so that a good skill should outperform no skill or a bad skill.
  Existing benchmarks weren't designed with this discrimination in mind.
- Breadth. SWE-bench-Lite and TAU-Bench cover dev-tooling and customer-
  service tool use respectively.
- Per-task wall-time <=5 min. Rules out long-horizon METR-style tasks. A
  separate long-horizon task family may follow in v2.

### 3.3 What v1 does not measure

- Code style or aesthetics. Linter pass is part of style tasks; "is this
  Pythonic" is not.
- Long-horizon (>5 min) task quality. METR territory.
- Multi-modal (voice, vision, UI navigation).
- Open-ended creative writing.
- Safety / alignment.

## 4. Contamination audit

### 4.1 Empirical situation

SWE-bench is materially contaminated. The strongest evidence is OpenAI's
December 2025 announcement
(`openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/`): under
appropriate elicitation, every major frontier model can reproduce verbatim
gold patches, indicating presence in pretraining or fine-tuning data.
OpenAI ceased reporting Verified scores as a result.

SWE-bench-Lite is a subset of the same source distribution and contaminated
at least as much as Verified, possibly more (Lite was selected for
"well-behaved" properties that may correlate with public visibility).

### 4.2 Mitigation

1. Demote SWE-bench-Lite to a secondary "informative but contaminated"
   panel. Adversarial self-review found two flaws in the original
   "delta is contamination-invariant" claim:
   - Contamination is not skill-invariant. Skills naming files, repos, or
     patterns can disproportionately activate memorised solutions vs. the
     no-skill baseline, so the delta mixes the skill effect with a skill x
     memorisation interaction.
   - Contamination shrinks variance. Memorised solutions reproduce
     deterministically; pass/fail flips are rare. This artificially tightens
     CIs and inflates apparent significance.
2. Primary panel uses skill-specific-v1 + tau-bench-v1 (70 tasks), which are
   either author-curated or post-cutoff for most pretraining.
3. Disclose contamination flags from upstream literature in
   `tasks/swe-bench-lite-v1/CONTAMINATION.md` once that adapter lands;
   researchers consulting the secondary panel can subset.
4. Migrate to SWE-bench Pro + Live in v2.

### 4.3 What we don't do

- Run our own contamination detection. The state of the art (verbatim-patch
  elicitation, distributional fingerprinting) is unsettled; rolling our own
  would need its own methodological defence. We rely on upstream evidence.
- Exclude tasks the model "may have seen". That introduces a selection bias
  that's hard to defend.

### 4.4 TAU-Bench contamination

TAU-Bench is newer (mid-2024) with synthetic policy documents plus a
simulated user, so it's less subject to pre-training inclusion. We adopt it
without the caveat banner, but note that we haven't independently audited
TAU-Bench beyond upstream authors' claims.

## 5. Metrics

Full per-metric spec in [metrics.md](metrics.md).

### 5.1 Primary

- pass@1: single-sample success rate; mean across seeds with bootstrapped
  95% CIs.
- pass@5: Chen 2021 unbiased estimator over n=5 seeds, with per-task CIs.
- pass^5: fraction of tasks where the agent succeeds on all 5 seeds.
  Captures reliability; sensitive to volatility.

### 5.2 Cost and efficiency

- cost ($): token counts x current `pricing.yaml`, per task. Median + p95
  across seeds. Pricing pinned and dated; cost recomputation under a new
  `pricing.yaml` produces a new entry hash.
- latency (s): wall clock per task; p50 + p95.
- tool_calls: invocations per task. A skill that triples this for the same
  pass rate is suspect.
- timeout_rate: fraction of (task, seed) pairs that hit `time_budget_s`
  without producing a final result. Distinguishes capability failure from
  timeout exhaustion.

### 5.3 Adversarial / quality flags

Flags, not rankings. They appear as badges on the leaderboard row.

- `high-variance`: pass@5 >= 2 x pass^5. Skill is buying success through
  nondeterminism rather than reasoning improvement.
- `talkative`: median output tokens >= 2 x baseline.
- `tool-storm`: median tool_calls per task >= 2 x baseline.
- `pricing-stale`: `pricing.yaml.last_audited` is more than 30 days old at
  submission.
- `model-drift`: provider response fingerprint differs between submission
  and re-verification.
- `borderline-stability`: at least one task's pass/fail flipped between
  submission and re-verification.

Each flag has a synthetic-skill test that exercises it.

### 5.4 What's not a primary metric

- LLM-as-judge scores. v1 = deterministic graders only. v2 may add it as an
  experimental, ranking-excluded metric.
- Subjective "style" scores. Linter passes are objective; aesthetic quality
  isn't.
- An aggregate scalar rank. The leaderboard is sortable on any column; no
  "agenteval score" is published. Goodhart non-negotiable.

## 6. Sandbox and threat model

### 6.1 Spec

Every (task, seed) attempt runs in a fresh Docker container:

- Pinned Python base image; SHA recorded in run metadata.
- 1 CPU, 2 GB RAM, 5-minute wall-time by default. Task spec may override
  wall-time up to 10 min for TAU-Bench tasks.
- Network disabled by default. Task spec may opt in.
- No host filesystem mount outside the per-attempt working directory.
- The skill bundle is injected at `~/.claude/skills/` inside the container.

### 6.2 Threat model

Skill authors are assumed not actively malicious. We defend against accidental
side effects (a typo running `rm -rf`, a skill exfiltrating env vars).
Graders are trusted; agent-produced code is not.

The container is a soft boundary. We do not defend against deliberate
sandbox escape (kernel exploits, Docker breakout). A determined adversary
with a skill submission could probably escape; that's a known limit. If
this becomes a problem we'll move to gVisor or Firecracker.

### 6.3 Cross-platform

Docker on macOS goes through a Linux VM with known filesystem-mount and
network performance issues; same with Windows + Docker Desktop. The harness
warns above 20 tasks on these platforms. For full runs, use Linux directly
or the `--remote` SSH option.

## 7. Reproducibility

Full spec in [reproducibility.md](reproducibility.md).

### 7.1 Content addressing

Every leaderboard entry is identified by:

```
entry_hash = sha256(
    skill_bundle_hash || task_set_hash || model || temperature ||
    seed_list || pricing_yaml_hash
)
```

- `skill_bundle_hash`: SHA256 of the normalised tarball of `.claude/skills/`
  (sorted file order, stripped trailing whitespace, no timestamps).
- `task_set_hash`: SHA256 of the task-set tarball, same normalisation.
- `model`: exact API model string.
- `temperature`: float; must be 0.0 for leaderboard entries.
- `seed_list`: list of integers used. For primary-leaderboard entries this
  must be exactly `[1, 2, 3, 4, 5]`. Non-canonical seed lists are rejected
  at the API gate; users wanting capability sweeps use
  `agenteval eval --exploratory`, which produces a non-leaderboard result.
  Rationale: prevents the cherry-pick attack where a submitter runs many
  seeds and selects the favourable five.
- `pricing_yaml_hash`: SHA256 of the `pricing.yaml` used.

Stored alongside but not hashed:

- `model_response_fingerprint`: provider-side fingerprint (e.g.
  OpenAI's `system_fingerprint`). Mismatch across re-verifications triggers
  the `model-drift` flag.
- `sandbox_image_sha`: the Docker base-image digest. Mismatch triggers
  `sandbox-drift`. Excluded from the hash so routine image bumps don't
  mass-invalidate the leaderboard.

### 7.2 Verifier

`agenteval verify ./result.json` performs an independent re-run from scratch
in a clean Docker environment. Compares:

- Structured features (per-task pass/fail per seed, token counts, tool-call
  counts): by equality.
- Cost and latency: within tolerance (cost ±5%, latency ±25%) to
  accommodate provider-side jitter and minor token-counting drift.
- Trajectory text: not compared bit-exactly. LLM determinism at T=0 is
  partial; we document this rather than pretend otherwise.

Submissions that fail verification are listed `verified: false` and hidden
from the default leaderboard view. Re-submission is supported. Every
primary-panel entry is verified in two different cloud zones; agreement is
required.

### 7.3 Partial determinism

At T=0 with the same model and prompt, you can still get slightly different
outputs across (a) provider-side model version updates,
(b) provider-side batch composition affecting numerics, (c) tokenizer or
normalisation version drift. The protocol tolerates this on cost and
latency, refuses it on pass/fail. A pass/fail flip between submission and
verification triggers `borderline-stability`.

## 8. Adversarial analysis

Categories of pathological skill behaviour we expect and test for:

1. pass@k gaming via nondeterminism. A skill that emits highly variable
   output may have high pass@5 but low pass@1. Detected by `high-variance`
   and pass^5 reporting.
2. Cost gaming via excessive context. A skill that pads the system prompt
   with retrieval-like content may improve pass-rate while burning tokens.
   Detected by `talkative` and explicit cost reporting.
3. Tool-storm gaming. Many small tool calls inflate latency and cost.
   Detected by `tool-storm`.
4. Grader gaming. Skills could try to produce outputs that match grader
   regexes without solving the task. Mitigation: graders verify behaviour
   (test pass, linter pass, state diff), not text patterns, wherever
   possible.
5. Skill-bundle contamination. A skill could include the gold answer for a
   known task. Skill bundles are content-addressed; we don't yet audit
   skill content for task-answer leakage. v2 may add a grep-style check.

Each pathology has at least one synthetic-skill test that exercises and
verifies the flag.

## 9. Leaderboard design

### 9.1 Pre-mortem

| Failure | Mitigation |
|---|---|
| Goodhart's Law: skills overfit to the public task set. | Hidden holdout tasks rotated quarterly; per-category reporting; no scalar rank. |
| Submission gaming: author claims a result they can't reproduce. | Verifier re-runs every submission in two clean cloud zones. |
| Seed cherry-picking. | Canonical seed list `[1,2,3,4,5]` required for primary entries; non-canonical lists rejected at the API gate. |
| Ranking instability. | Mandatory canonical 5-seed runs; 95% bootstrapped CIs reported on every metric; sortable, not ranked. |
| Cost gaming: a skill wins by burning $100/task. | Pareto-frontier visualisation; cost reported as a first-class column. |
| Pricing drift. | `pricing.yaml` is part of the entry hash; `pricing-stale` flag on submissions older than 30 days. |
| Contamination drift in SWE-bench. | Demoted to secondary panel; never used for headline claims. v2 migrates to Pro + Live. |
| Model-version drift. | Response fingerprint snapshotting; `model-drift` flag on re-verification mismatch. |
| Timeout-rate masking. | `timeout_rate` is a first-class column, not folded into "fail". |
| Cross-provider asymmetry. | Pinned per-provider `no-skills/<provider>.yaml`; cross-provider comparisons are delta-from-baseline, never absolute. |
| Skill-author opt-out. | We comply transparently; entries are removed on request. |

### 9.2 Holdout rotation

A private holdout task set, ~10 tasks per major category, rotated quarterly.
Submissions are evaluated on both the public set and the current holdout;
a public-vs-holdout gap > 15 points fires `holdout-divergence`. The current
holdout's contents are released after rotation. This is the strongest
anti-Goodhart structural defence.

### 9.3 Visualisation

- Default view: sortable table; all metrics + flags + verification status.
- Pareto plot: pass@1 x cost, with model and task-category filters.
- Per-entry detail: bundle SHA, submission JSON, verification log, date.

No scalar "agenteval score".

## 10. Causal language

We do not say "skill X caused a 12% improvement"; we say "with skill X,
pass@1 was 12 points higher than the no-skill baseline on this task set,
with the model, temperature, and seeds held constant." This isn't pedantic;
it's the difference between a defensible measurement and a marketing claim.

Skill authors quoting our numbers are asked to do the same. Each entry
publishes a `quote-this.md` with the verbatim attribution sentence.

For genuine causal claims ("this skill causes better TDD behaviour because
it makes the agent write tests first"), the harness emits trajectory traces
that can be inspected. We don't pre-compute causal scores. v2 may add an
ablation mode that drops one section of the skill at a time and re-measures.

## 11. Limitations

1. Single-language code skew. v1 tasks are predominantly Python. v2 adds
   JS/TS, Go, Rust families.
2. No long-horizon eval. Per §3.3.
3. Partial LLM determinism. Per §7.3. Documented, not solved.
4. Soft sandbox. Per §6.2.
5. No human-baseline anchoring. We anchor against the no-skill baseline.
6. Three providers in v1. Local-model evaluation (Llama, Qwen, etc.) is v2.
7. No LLM-as-judge. Restricts task design to mechanically gradable tasks.
   Intentional; v2 may add it as an experimental, ranking-excluded metric.
8. Skill snapshots can age. A pinned snapshot may not reflect the live
   upstream skill. We surface the snapshot SHA and date.
9. Cross-provider baselines aren't perfectly symmetric. Cross-provider
   comparisons are always delta-from-baseline, never absolute.
10. SWE-bench-Lite results are secondary-panel only. Not citable as a
    skill-effect claim.

## 12. Future work

v2: SWE-bench Pro + Live migration; multi-language task families; optional
LLM-as-judge (flagged experimental); local-model runners; long-horizon
family.

v3: multi-modal eval (screenshots, voice); real-OS-environment tasks
(macOSWorld, TheAgentCompany).

Always-on: holdout rotation; `pricing.yaml` refresh; contamination audit.

## References

1. Liang et al., *Holistic Evaluation of Language Models (HELM)*, 2022.
   `arxiv.org/abs/2211.09110`.
2. Srivastava et al., *Beyond the Imitation Game (BIG-bench)*, 2022.
   `arxiv.org/abs/2206.04615`.
3. Chen et al., *Evaluating Large Language Models Trained on Code*, 2021.
   `arxiv.org/abs/2107.03374`.
4. Jimenez et al., *SWE-bench*, 2024.
5. OpenAI, *Why we no longer evaluate SWE-bench Verified*, December 2025.
6. SWE-bench Pro (Scale Labs), 2026.
7. SWE-bench-Live, 2026.
8. Yao et al., *τ-bench*, 2024. `arxiv.org/abs/2406.12045`.
9. Kwa et al., *Measuring AI Ability to Complete Long Software Tasks
   (METR HCAST/RE-Bench)*, 2025. `arxiv.org/abs/2503.14499`.
10. Mohammadi et al., *Evaluation and Benchmarking of LLM Agents: A
    Survey*, 2025. `arxiv.org/html/2507.21504v1`.
11. Sohl-Dickstein, *Too much efficiency makes everything worse:
    overfitting and the strong version of Goodhart's law*, 2022.
