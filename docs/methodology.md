# Methodology

> The defense-against-reviewers document. Every measurement choice in `agenteval` is justified here, with awareness of how a NeurIPS reviewer or a skill author may challenge it. If a claim in this document is wrong, the project's credibility is compromised — please open an issue.

**Document status:** v1.0 (post-Phase-3 polish). Workshop-paper backbone. Pending review by ≥2 IR/ML PhDs before launch (per master prompt §1 quality bar). Adversarial-test plans live in [`adversarial.md`](adversarial.md); reproducibility protocol in [`reproducibility.md`](reproducibility.md); the FAQ at [`faq.md`](faq.md) pre-drafts responses to common criticisms.

## Abstract

The Claude Code Skills ecosystem grew explosively through 2025–2026 — `mattpocock/skills`, `obra/superpowers`, `andrej-karpathy-skills` each carrying tens of thousands of GitHub stars — alongside anecdotal claims about reliability gains that lack defined task populations, control conditions, confidence intervals, or reproducibility metadata. `agenteval` is the first reproducible benchmark for `.claude/skills/` directories and `CLAUDE.md` configurations. It evaluates skill bundles on a fixed 100-task budget across Anthropic, OpenAI, and Google in a hardened Docker sandbox, reports the Chen-2021 unbiased pass@k estimator alongside TAU-Bench-style pass^k reliability, and content-addresses every leaderboard entry so any third party can re-verify the result. We refuse three things in v1 that the broader eval literature is converging on: (1) LLM-as-judge grading, (2) a scalar leaderboard rank, and (3) absolute capability claims on contaminated benchmarks. The first preserves determinism; the second is a structural Goodhart's-Law defense; the third drives our two-panel leaderboard architecture (primary = uncontaminated skill-specific + TAU-Bench; secondary = SWE-bench-Lite, marked "informative but contaminated"). This document is the workshop-paper backbone; the full v1 implementation is open-source at the project repository under Apache-2.0.

---

## 1. Motivation

By May 2026, Claude Code Skills (the `.claude/skills/` directory format introduced in late 2025) have become one of the most active categories on GitHub. Three reference repositories — `mattpocock/skills`, `obra/superpowers`, and `andrej-karpathy-skills` — each carry tens of thousands of stars. Claims circulate in the discourse that skills "raise reliability from 60–70% to 95%" or "make Claude 30% faster", typically without (a) a defined task population, (b) a control condition, (c) confidence intervals, or (d) reproducibility metadata.

`agenteval` exists to close that measurement gap. Concretely, we measure whether a `.claude/skills/` directory (or a single `CLAUDE.md` file) changes downstream agent behavior on a fixed, public task set, across multiple model providers, with full reproducibility guarantees.

We adopt three positioning constraints up front:

1. **Narrow scope.** We are *not* building a general LLM eval framework. `lm-evaluation-harness` and HELM already exist for that. We measure agentic skill bundles, full stop.
2. **Comparison over absolute capability.** Our axis is the *delta* introduced by a skill bundle versus the no-skill baseline, not the absolute capability of the underlying model. This matters for the contamination discussion in §4.
3. **Methodological rigor over headline numbers.** The credibility of a benchmark is its protocol, not its leaderboard. Where rigor and velocity conflict, we choose rigor.

---

## 2. Related work and what we steal from each

### 2.1 HELM (Liang et al., 2022)

HELM (*Holistic Evaluation of Language Models*) framed LLM eval as a multi-dimensional question: not just accuracy, but calibration, robustness, fairness, bias, toxicity, efficiency. It defined ~16 scenarios × 7 metrics rather than chasing a single headline number.

**What we steal:** multi-metric reporting. We refuse to expose a single ranking — every leaderboard row carries pass@1, pass@5, cost, latency, tool-call count, and adversarial flags simultaneously. The default leaderboard view shows a sortable table; a single rank order is intentionally absent (see §10 on leaderboard design).

**What we leave behind:** HELM is hand-curated across many domains. We're narrow. We don't try to span scenarios; we span skill bundles on a fixed task family.

### 2.2 BIG-bench (Srivastava et al., 2022)

BIG-bench (*Beyond the Imitation Game*) crowdsourced 204 tasks. Its main insight: heterogeneity catches things uniform benchmarks miss; its main scar: heterogeneity made it expensive to maintain and made cross-task aggregation suspect.

**What we steal:** distinct task categories with category-level rather than aggregate scores (we report per-category pass rates, plus a weighted aggregate that we explicitly mark "for sorting, not for citation").

**What we leave behind:** crowdsourcing. v1 tasks are author-curated. v2 may add a curated-PR pipeline.

### 2.3 HumanEval / pass@k (Chen et al., 2021)

`arxiv.org/abs/2107.03374` introduced the pass@k metric for code generation, where pass@k is *the probability that at least one of k sampled completions passes the unit tests*. The paper also provides the unbiased estimator we use:

$$
\widehat{\text{pass@}k} \;=\; 1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}
$$

with `n` total samples, `c` correct samples, `k ≤ n`. This avoids the high-variance plug-in estimate when sampling temperature is held above zero.

**What we steal:** the estimator, verbatim. See [`metrics.md`](metrics.md) for our implementation and its unit tests.

**What we leave behind:** the original n=200 sampling budget. At frontier model prices in 2026 that's prohibitive; we use n in {5, 10, 25} depending on task cost and report the corresponding CIs.

### 2.4 SWE-bench (Jimenez et al., 2024), SWE-bench-Lite, SWE-bench Verified, Pro, Live

SWE-bench evaluates agents on real GitHub issues from 12 Python repos, scored against the repo's own test suite. SWE-bench-Lite is a 300-task subset chosen for reproducibility and lower per-task cost. SWE-bench Verified (an OpenAI-curated 500-task subset) further filters for solubility.

**The contamination crisis.** In late 2025, OpenAI publicly announced they would no longer report SWE-bench Verified scores, citing evidence that every major frontier model — GPT-5.2, Claude Opus 4.5, Gemini 3 Flash — could reproduce verbatim gold patches under appropriate elicitation. This means model performance on Verified is a confounded mix of (i) capability and (ii) memorization of leaked solutions.

The community has responded with:
- **SWE-bench Pro:** tougher tasks, fewer cleanly-leaked patches, paid+free tiers.
- **SWE-bench-Live:** continuously updated; monthly new tasks reduce contamination half-life.

**What this means for us.** Our axis is *skill-induced delta*, not absolute capability. Even on a contaminated benchmark, if a no-skill baseline solves X% and the same model with skill `superpowers-v3` solves Y%, the contamination is held constant across both conditions; the delta `Y − X` is interpretable. **But the absolute numbers must NOT be cited as a model-capability ranking** — we make this explicit in every leaderboard row that uses SWE-bench-Lite (banner: *"contaminated — interpret as skill delta only"*).

See [ADR-0011](../DECISIONS.md) for the decision to keep SWE-bench-Lite in v1 with this caveat, and to migrate the SWE-bench task family to Pro and Live by v2.

### 2.5 TAU-Bench (Yao et al., 2024) and τ²-bench (Sierra Research)

`arxiv.org/abs/2406.12045`. TAU-Bench simulates multi-turn tool-agent-user interactions in two domains (retail, airline). The agent talks to (a) an LLM-simulated user with goals and (b) a domain API with policy documents. Evaluation: terminal database state vs. annotated goal state, plus the **pass^k** metric — *the fraction of tasks where the agent succeeds in all k independent trials*. pass^k is reliability-oriented (vs. pass@k which is capability-oriented).

**What we steal:** pass^k as an auxiliary reliability metric, reported alongside pass@k. A skill that *raises* pass@1 by 5 points but *lowers* pass^5 by 10 points is almost certainly introducing volatility (e.g., a nondeterministic prompt path). This is exactly the failure mode we want to detect.

**What we leave behind:** TAU-Bench's LLM-simulated user. We adapt the *single-shot tool-use subset* of TAU-Bench into our v1 task family (see §3), but defer multi-turn simulation to v2 because (a) it introduces an LLM-as-judge-flavored confound (the simulated user's behavior is a second LLM in the loop) and (b) it inflates per-task cost.

### 2.6 METR HCAST + RE-Bench + SWAA

METR's time-horizon framework (Kwa et al., 2025; `arxiv.org/abs/2503.14499`) doesn't score on pass-rate; it fits a logistic regression of `P(success | log(human_completion_time))` and reports the *50% time horizon* — the human-task-length at which the model succeeds half the time. As of Time-Horizon-1.1 (Jan 2026), frontier models sit at roughly 50–60 minutes of human-equivalent time.

**What we steal:** the conceptual framing that "time horizon" is a more useful unit than "fraction of tasks" when tasks vary widely in difficulty. We don't fit a logistic curve in v1 (too few tasks, too much variance), but we report **per-category pass rates** with the same intent: a skill that helps on 5-min tasks but not 30-min tasks should look different from a skill that helps uniformly.

**What we leave behind:** the human-time anchoring. METR has cost millions of dollars and dozens of person-hours per task to anchor human times; we have a contributor team and 120 budgeted project-hours.

### 2.7 NeurIPS 2025 agentic-eval landscape

Mohammadi et al.'s survey *Evaluation and Benchmarking of LLM Agents* (`arxiv.org/html/2507.21504v1`) lays out the taxonomy: evaluation objectives (behavior, capabilities, reliability, safety) × evaluation process (interaction mode, dataset, metric computation, environment). NeurIPS 2025 alone had 45+ papers in computer-use agents (Cua's roundup). Benchmarks like *TheAgentCompany*, *macOSWorld*, *VideoCAD* show the field expanding into multi-modal, real-environment evaluation.

**What we steal:** the taxonomy. Each `agenteval` leaderboard entry is tagged with `(objective, process)` axes in the API and the data export, so future filters and meta-analyses can slice cleanly.

**What we leave behind:** multi-modal, real-OS, full-software-company sims — all v2+. v1 stays narrow to text/code tasks.

### 2.8 lm-evaluation-harness (EleutherAI)

`lm-evaluation-harness` is the *de facto* infrastructure for academic LM eval. Its strength is breadth of task adapters and the discipline of standardized scoring. Its limitation for our use case: it assumes a generation-then-score loop, not a tool-using agent with a trajectory.

**What we steal:** the discipline of pinned task-set versioning and explicit prompt templates. We borrow the convention of versioning task sets with semver (`skill-specific-v1`, `swe-bench-lite-v1`, ...).

**What we leave behind:** integrating with it directly. Our agent trajectories don't fit cleanly into the gen-then-score model, and forking would add a heavyweight upstream that pulls us toward general LM eval — exactly the scope creep we're refusing.

---

## 3. Task selection

### 3.1 Two leaderboard panels in v1

After methodology adversarial self-review (see ADR-0014), v1 ships with **two panels**, not one. The primary panel underwrites all headline claims and rank-sortable comparisons; the secondary panel is informative but explicitly non-citable.

#### Primary panel ("uncontaminated")

| Family | Source | Count | Role |
|---|---|---|---|
| `skill-specific-v1` | hand-curated by `agenteval` team | 20 | core differentiator; tests skill-specific behaviors |
| `tau-bench-v1` | Yao et al. 2024, subset | 50 | tool-use breadth; low contamination concern |
| **Primary total** | | **70** | |

All headline metrics, the Pareto plot, the workshop paper's reported deltas, and the sortable leaderboard use the primary panel only.

#### Secondary panel ("informative but contaminated")

| Family | Source | Count | Role |
|---|---|---|---|
| `swe-bench-lite-v1` | Jimenez et al. 2024, subset | 30 | breadth on realistic dev tasks; contamination caveat |
| **Secondary total** | | **30** | |

Rendered in a separate section of the leaderboard. Banner per entry: *"Contaminated benchmark — delta may be confounded by skill × memorization interaction; not citable as a skill-effect claim."* See §4 for the rationale.

**v1 grand total:** 100 tasks, respecting the §9 anti-pattern #6 ceiling. v2 commits to migrate the SWE-bench task family from Lite to Pro + Live (per ADR-0011 commitment, retained by ADR-0014).

### 3.2 Why these three, and not others

- **Need a baseline.** A 100-task set with a no-skill baseline is the minimum statistical floor for detecting a skill-induced delta of ~5 percentage points at 95% confidence over 5 seeds. Smaller and we lose signal; larger and the harness becomes prohibitive to run.
- **Need a skill-discriminating core.** The 20 hand-curated tasks (see [`tasks/skill-specific-v1/README.md`](../tasks/skill-specific-v1/README.md)) are explicitly designed so that a "good" skill should outperform "no skill" or a "bad" skill — otherwise we have no signal to measure. Existing benchmarks weren't designed with this discrimination in mind.
- **Need breadth.** SWE-bench-Lite and TAU-Bench cover dev-tooling and customer-service tool use respectively. Together they span enough of real agentic-coding workflows to make claims like "skill X is robust across tasks" defensible.
- **Need ≤5 min per task.** Per master prompt §3.3. This rules out long-horizon METR-style tasks (we'll add a separate `agenteval-long-v1` in v2 if there's demand).

### 3.3 What we explicitly do NOT measure in v1

- **Code style / aesthetics.** Linter pass is part of style-adherence tasks (4 of the 20 skill-specific), but we don't grade "is this Pythonic". That's LLM-as-judge territory.
- **Long-horizon (>5 min) task quality.** METR-style. v2.
- **Multi-modal.** Voice, vision, UI navigation. v2+.
- **Open-ended creative writing.** Not our wedge.
- **Safety / alignment.** Critical, but a different benchmark.

---

## 4. Contamination audit (per Phase 0 §3.2)

### 4.1 The empirical situation

As of late 2025, the SWE-bench family is materially contaminated. The strongest evidence comes from OpenAI's announcement (`openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/`, December 2025), which we paraphrase from secondary sources because the direct URL gates fetch attempts: under appropriate elicitation prompts, every major frontier model (GPT-5.2, Claude Opus 4.5, Gemini 3 Flash) can reproduce *verbatim* gold patches from SWE-bench Verified, indicating presence in pretraining or fine-tuning data. OpenAI explicitly ceased reporting Verified scores as a result.

**Implication for `agenteval`:** SWE-bench-Lite, being a subset of the same source distribution, is contaminated at least as much as Verified, possibly more (because Lite was selected for "well-behaved" task properties that may correlate with public visibility).

### 4.2 What we do about it

We adopt a **four-layer mitigation** (revised; see ADR-0014 superseding ADR-0011):

1. **We demote SWE-bench-Lite to a secondary "informative but contaminated" panel.** Adversarial self-review of the original "delta is contamination-invariant" claim found two flaws:
   - *Contamination is not skill-invariant.* Skills can name files, repos, or patterns in ways that disproportionately activate memorized SWE-bench solutions vs. the no-skill baseline. The delta then mixes the genuine skill effect with a skill × memorization interaction and is no longer cleanly interpretable.
   - *Contamination shrinks variance.* Memorized solutions are reproduced deterministically; pass/fail flips are rare. This artificially tightens CIs and inflates apparent statistical significance of small deltas.

   Therefore SWE-bench-Lite is not used for the primary leaderboard or for any headline / workshop-paper claim. It is rendered as a secondary panel with a banner: *"Contaminated benchmark — delta may be confounded by skill × memorization interaction; not citable as a skill-effect claim."*

2. **The primary panel uses skill-specific-v1 + TAU-Bench-v1 (70 tasks).** These are either author-curated (no contamination by construction) or post-cutoff for most pretraining runs (low contamination).

3. **We disclose contamination flags from upstream literature.** In `tasks/swe-bench-lite-v1/CONTAMINATION.md` we list per-task flags we found in Mohammadi et al.'s survey and OpenAI's reports. Researchers consulting the secondary panel can subset to "low-suspicion" tasks if desired.

4. **We commit to migrating to SWE-bench Pro and SWE-bench-Live in v2.** SWE-bench Pro had materially less contamination in OpenAI's internal audit; SWE-bench-Live publishes monthly new tasks, capping the contamination half-life. ADR-0011 (preserved by ADR-0014) holds this commitment.

### 4.3 What we explicitly do NOT do

- We do not run our own contamination detection. The state of the art (verbatim-patch elicitation, distributional fingerprinting) is unsettled, and rolling our own would itself need methodological defense. We rely on upstream evidence.
- We do not exclude tasks that pretraining-cutoff-dated models may have seen. Doing so introduces a selection bias that's hard to defend (we'd be picking tasks the model is bad at).

### 4.4 TAU-Bench contamination

TAU-Bench is newer (mid-2024) and the data is synthetic-policy-document plus simulated user — less subject to pre-training inclusion. We adopt it without the same caveat banner, but with a footnote in the methodology that says "we have not independently audited TAU-Bench for contamination beyond the upstream authors' claims."

---

## 5. Metrics

Full per-metric spec lives in [`metrics.md`](metrics.md). Summary here.

### 5.1 Primary

- **pass@1** — single-sample success rate. Mean across seeds with bootstrapped 95% CIs.
- **pass@5** — Chen et al. unbiased estimator over n=5 seeds. With per-task CIs.
- **pass^5** (TAU-Bench-style) — fraction of tasks where the agent succeeds on **all** 5 seeds. Captures reliability; sensitive to volatility.

### 5.2 Cost & efficiency

- **cost ($)** — token counts × current `pricing.yaml`, per task. Reported as median + 95th percentile across seeds. Pricing pinned and dated; rerun cost computation if pricing changes (re-publish under a new entry hash; do not silently update).
- **latency (s)** — wall clock per task. Median + 95th percentile. Includes agent thinking + tool calls + sandboxed code execution.
- **tool_calls** — count of tool invocations per task. A skill that triples this for the same pass-rate is suspect.
- **timeout_rate** — fraction of (task, seed) pairs that hit `time_budget_s` without producing a final result (per ADR-0016). Distinguishes capability-failure from time-out-failure. A skill with high `timeout_rate` is visibly distinct from one with high `1 − pass@1`; both should be inspected, for different reasons.

### 5.3 Adversarial / quality flags

These are flags, not rankings — they appear on the leaderboard row as badges.

- **`high-variance`** — flagged if pass@5 ≥ 2 × pass^5 (where pass^5 is the all-5-seeds-pass reliability metric, ADR-0012). Indicates skill is buying success through nondeterminism rather than reasoning improvement.
- **`talkative`** — flagged if median output tokens ≥ 2 × baseline. Talkativeness inflates cost and latency without obvious quality gain.
- **`tool-storm`** — flagged if median `tool_calls` per task ≥ 2 × baseline.
- **`pricing-stale`** — flagged if `pricing.yaml` is more than 30 days old at submission time (ADR-0013).
- **`model-drift`** — flagged if the provider-side response fingerprint (`system_fingerprint` for OpenAI, equivalent for Anthropic, "n/a" for Google) differs between submission and re-verification (ADR-0016). Even though the API model string is identical, the underlying weights have shifted; deltas across drift are not directly comparable.
- **`borderline-stability`** — flagged if a single task's pass/fail flips between submission and re-verification (per §7).

See [`adversarial.md`](adversarial.md) for the design of each flag and the synthetic pathological-skill tests that exercise them.

### 5.4 What we do NOT report as primary

- **LLM-as-judge scores.** Per ADR-0006, no LLM judgments in v1.
- **Subjective "style" scores.** Linter passes are objective; "style quality" is not.
- **Aggregate-rank scalar.** We sort the leaderboard by any column, but we refuse to publish "the agenteval score" as a scalar. Goodhart's Law (§10.1) is non-negotiable on this point.

---

## 6. Sandbox and threat model

### 6.1 Sandbox spec

Every task runs in a fresh Docker container with:

- A **pinned** Python base image (image SHA recorded in the run metadata; see [`reproducibility.md`](reproducibility.md)).
- **1 CPU, 2 GB RAM**, default 5-minute wall-time. Task spec may override wall-time up to 10 min for tau-bench-v1 tasks.
- **Network disabled by default.** Task spec may opt in to network access (rare; only for tasks where network is essential).
- **No host filesystem mount** outside the task working directory, which is mounted read-write but discarded after the task.
- The skill bundle is **injected** at `~/.claude/skills/` inside the container.

### 6.2 Threat model

We assume:
- Skill authors are not actively malicious — the threat model targets *accidental* side effects (e.g., a skill that runs `rm -rf` on a typo, or a skill that exfiltrates env vars).
- Graders are trusted code maintained by the project; agent-produced code is not trusted.
- The container is a soft boundary, not a hardened one. We do not defend against deliberate sandbox escape (kernel exploits, Docker breakout). A determined adversary with a skill submission could probably escape; that's a known limit.

If skill authors abuse this in practice, we'll revisit (e.g., gVisor or Firecracker microVMs). For v1, Docker is the right cost/value tradeoff.

### 6.3 What this means for cross-platform

Docker on macOS uses a Linux VM under the hood and has known performance issues (slow filesystem mounts, network plumbing). We recommend running full task runs on Linux. The harness will emit a warning if it detects Docker-Desktop-on-macOS and the task budget exceeds 20 tasks. See [`reproducibility.md`](reproducibility.md) §Cross-platform.

---

## 7. Reproducibility protocol

Full spec in [`reproducibility.md`](reproducibility.md). Summary here.

### 7.1 Content addressing

Every leaderboard entry is identified by:

```
entry_hash = sha256(
    skill_bundle_hash || task_set_hash || model || temperature || seed_list || pricing_yaml_hash
)
```

- `skill_bundle_hash`: SHA256 of the normalized tarball of `.claude/skills/` (sorted file order, stripped trailing whitespace, no timestamps).
- `task_set_hash`: SHA256 of the task-set tarball, same normalization.
- `model`: exact API model string (e.g., `claude-opus-4-7`, `gpt-5.2`, `gemini-3-pro`).
- `temperature`: float. **Must be 0.0** for leaderboard entries.
- `seed_list`: list of integers used. **For primary-leaderboard entries this must be exactly `[1, 2, 3, 4, 5]`** (canonical, per ADR-0015). Non-canonical seed lists are rejected at the API gate; users wanting capability sweeps over many seeds use `agenteval eval --exploratory` which produces a non-leaderboard result. Rationale: prevents the cherry-pick attack where a submitter runs many seeds, selects the favorable 5, and submits — the verifier reproduces those 5 by definition.
- `pricing_yaml_hash`: SHA256 of the `pricing.yaml` used to compute cost (ADR-0013). Cost-recomputation under a new pricing.yaml produces a new entry hash, not a silent overwrite.

Adjacent to the entry hash we record but do **not** hash:

- `model_response_fingerprint`: the provider-side fingerprint exposed in responses (`system_fingerprint` for OpenAI, equivalent for Anthropic). Stored for drift detection (ADR-0016); not part of the hash because providers update it independently of the user-facing API string. Mismatch across re-verifications triggers the `model-drift` flag.

### 7.2 Verifier

`agenteval verify ./result.json` performs an independent re-run from scratch in a clean Docker environment. It compares:

- **Structured features:** per-task pass/fail per seed, token counts, tool-call counts. Comparison is by equality.
- **Cost and latency:** within a stated tolerance (cost ±5%, latency ±25%) — accommodating provider-side latency jitter and minor token-counting drift.
- **Trajectory text:** **not** compared bit-exactly. LLM determinism is partial even at T=0 (provider-side batching, model fingerprint drift, tokenizer edge cases). We document this honestly rather than pretending otherwise.

Any submission that fails verification is listed as `verified: false` and not surfaced in the default leaderboard view. Re-submission is supported.

Per anti-pattern #10: every leaderboard entry is verified by running the verifier in **two different VMs** (different cloud zones). Agreement is required.

### 7.3 What partial determinism means honestly

LLM determinism is, frankly, not solved. At T=0 with the same model, the same prompt, the same prompt-cache state, you can still get slightly different outputs across (a) provider-side model version updates, (b) provider-side batch composition affecting numerics, (c) tokenizer or normalization version drift. Our protocol tolerates this on cost and latency, refuses it on pass/fail. If a model's pass/fail flips between submission and verification on the same task, that's a real signal of borderline behavior — we flag the entry `borderline-stability` rather than silently agreeing.

---

## 8. Adversarial analysis (preview)

The full treatment is in [`adversarial.md`](adversarial.md), which is the master prompt's specific anti-pattern #2 requirement: *"Don't release without the adversarial section."*

Categories of pathological skill behavior we expect and have synthetic tests for:

1. **Pass@k gaming via nondeterminism.** A skill that emits highly-variable output may have high pass@5 but low pass@1. Detected by `high-variance` flag and pass^5 reporting.
2. **Cost gaming via excessive context.** A skill that pads the system prompt with retrieval-like content may improve pass-rate while burning tokens. Detected by `talkative` flag and explicit cost reporting.
3. **Tool-storm gaming.** A skill that encourages many small tool calls may improve pass-rate but at latency/cost. Detected by `tool-storm` flag.
4. **Grader gaming.** Skills could try to write outputs that match grader regexes without solving the task. Mitigation: graders verify *behavior* (test pass, linter pass, state-diff), not text patterns, wherever possible. We red-team each grader against this.
5. **Skill-bundle-contamination of model.** A skill could include the gold answer for a known task. Mitigation: skill bundles are static and content-addressed; if a skill changes for a given submission, the hash changes, the entry is re-verified. We do not (yet) audit skill content for task-answer leakage; v2 may add a grep-style check.

Each pathology has at least one synthetic skill in `tests/test_metrics.py::adversarial` that exercises and verifies the flag.

---

## 9. Leaderboard design

### 9.1 Leaderboard pre-mortem (per Phase 0 §3.4)

Failure modes for benchmark leaderboards, with our mitigations:

| Failure | Mitigation |
|---|---|
| **Goodhart's Law:** skills overfit to the public task set. | (a) Hidden holdout tasks rotated quarterly. (b) Per-category reporting so cross-category robustness is visible. (c) No published scalar rank. |
| **Submission gaming:** author claims a result they can't reproduce. | (a) Verifier re-runs every submission from scratch in clean VMs (two of them, per anti-pattern #10). (b) Entries that fail verification are marked `verified: false` and hidden by default. |
| **Seed cherry-picking:** submitter runs many seeds, selects the best 5. | **Canonical seed list `[1,2,3,4,5]` is required for primary-leaderboard entries** (ADR-0015). Non-canonical seed lists are rejected at the API gate. Exploratory runs use a separate non-leaderboard mode. |
| **Ranking instability:** same skill, different seed, different rank. | (a) Mandatory canonical 5-seed runs. (b) 95% bootstrapped CIs reported on every metric. (c) Sortable, not ranked. |
| **Cost gaming:** a skill wins on pass-rate by burning $100/task. | (a) Pareto-frontier visualization (success × cost). (b) Cost reported as a first-class column; not buried. |
| **Pricing drift:** stale pricing makes cost comparisons unfair. | (a) `pricing.yaml` is part of the entry hash. (b) `pricing-stale` flag if a submission uses a pricing.yaml >30 days old. |
| **Contamination drift:** SWE-bench-Lite gets more contaminated over time. | (a) Contaminated benchmark is **demoted to a secondary panel** (ADR-0014); never used for headline claims. (b) Public commitment to migrate to SWE-bench Pro + SWE-bench-Live in v2. |
| **Model-version drift:** provider updates `claude-opus-4-7` silently mid-leaderboard; entries with identical hashes diverge. | **Response fingerprint snapshotting** (ADR-0016). `model-drift` flag on re-verification mismatch. |
| **Timeout-rate masking:** skill silently fails by exhausting wall-time rather than producing a wrong answer. | **`timeout_rate` is a first-class metric column** (ADR-0016), not folded into "fail." |
| **Cross-provider asymmetry:** Anthropic, OpenAI, Google have different implicit system prompts and default reasoning settings, so "no-skills baseline" is not equivalent across providers. | **Normalized per-provider baseline protocol** (ADR-0016). Pinned per-provider `no-skills/<provider>.yaml`. All cross-provider comparisons are delta-from-baseline, not absolute. |
| **Skill-author opt-out controversy:** Pocock, obra, or others may not want to be on the leaderboard. | (a) Yes, we comply — listed transparently in `docs/opt-outs.md`. (b) We don't run someone's skill without consent if they object. See open question §10 of master prompt. |

### 9.2 Holdout rotation

We commit to maintaining a *private* holdout task set, ~10 tasks per major category, rotated **quarterly**. Submissions are evaluated on both the public set and the current holdout; the holdout score is reported alongside the public score. A skill whose public-vs-holdout gap exceeds 15 percentage points is flagged `holdout-divergence`. The current holdout's contents are released after rotation. This is the strongest anti-Goodhart structural defense.

(Open question: cadence — quarterly vs. aligned with major model releases. Decision deferred to user input; see master prompt §10.)

### 9.3 Visualization

- Default view: sortable table, all metrics + flags + verification status.
- Pareto plot: success (pass@1) × cost. Selectable model and task category filters.
- Per-entry detail: skill-bundle SHA, submission JSON, verification log, date.

No scalar "agenteval score". Intentional.

---

## 10. Causal language and ablation

Anti-pattern #5 of the master prompt is binding: we do not say "skill X *caused* a 12% improvement"; we say "with skill X, pass@1 was 12 points higher than the no-skill baseline on this task set, with the model, temperature, and seeds held constant." This distinction is not pedantic — it's the difference between a defensible measurement and a marketing claim.

When skill authors quote our numbers, we ask them to do the same. We provide a `quote-this.md` per entry that gives the verbatim attribution sentence.

For genuine causal claims (e.g., "this skill *causes* better TDD behavior because it makes the agent write tests first"), the agenteval harness emits trajectory traces that can be inspected — but we don't pre-compute causal scores. v2 may add an ablation-mode (drop one section of the skill at a time and re-measure) for skill authors who want internal evidence.

---

## 11. Limitations (deliberately listed up front)

1. **Single-language code skew.** v1 tasks are predominantly Python. Skills that help on Python but not other languages get inflated credit. v2 adds JS/TS, Go, Rust task families.
2. **No long-horizon eval.** Per §3.3. METR-style time-horizon work is its own benchmark.
3. **Partial LLM determinism.** Per §7.3. We document it; we don't pretend to solve it.
4. **Sandbox is soft.** Per §6.2. Not a defense against adversarial sandbox escape.
5. **No human-baseline anchoring.** METR has human times; we don't. We anchor against no-skill baseline instead.
6. **Three providers only in v1.** Anthropic, OpenAI, Google. Local-model evaluation (Llama, Qwen, etc.) is v2.
7. **No LLM-as-judge.** Per ADR-0006. Restricts task design to mechanically gradable tasks. The constraint is intentional and we hold it after adversarial review — the determinism gain is worth the task-design narrowness for v1. v2 may introduce LLM-as-judge as an explicitly experimental, ranking-excluded metric, with a separate badge.
8. **Skill snapshots can age.** A skill submitted as a pinned snapshot may not reflect the live upstream skill. We surface the snapshot SHA and date prominently; we do not auto-update.
9. **Cross-provider baselines are not perfectly symmetric.** Per ADR-0016, we publish a normalized `no-skills/<provider>.yaml` per provider, but providers' implicit defaults still differ in ways we cannot fully erase. Cross-provider comparisons are always delta-from-baseline, never absolute.
10. **SWE-bench-Lite results are secondary-panel only.** Per ADR-0014. They appear on the leaderboard but cannot be cited as primary skill-effect evidence. Reviewers and readers who want SWE-bench-style breadth should look at the secondary panel for descriptive context, not the primary panel.

---

## 12. Future work

- **v2:** SWE-bench Pro + SWE-bench-Live migration. Multi-language task families. Optional LLM-as-judge (clearly flagged "experimental"). Local-model runners. Long-horizon task family.
- **v3:** Multi-modal eval (skills that interact with screenshots, voice, etc.). Real-OS-environment tasks (à la macOSWorld, TheAgentCompany).
- **Always-on:** Holdout rotation; pricing.yaml refresh; contamination audit.

---

## References

BibTeX entries for every reference in this section live at [`references.bib`](references.bib). The numbered links below are the methodology-recon sources surfaced during Phase 0. Sections above cite them inline by author/year.

1. Liang et al., *Holistic Evaluation of Language Models (HELM)*, 2022. `arxiv.org/abs/2211.09110`.
2. Srivastava et al., *Beyond the Imitation Game (BIG-bench)*, 2022. `arxiv.org/abs/2206.04615`.
3. Chen et al., *Evaluating Large Language Models Trained on Code (HumanEval, pass@k)*, 2021. `arxiv.org/abs/2107.03374`.
4. Jimenez et al., *SWE-bench*, 2024. SWE-bench-Lite at `github.com/SWE-bench/SWE-bench`.
5. OpenAI, *Why we no longer evaluate SWE-bench Verified*, 2025. `openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/`.
6. SWE-bench Pro (Scale Labs), 2026. `labs.scale.com/leaderboard/swe_bench_pro_public`.
7. SWE-bench-Live, 2026. `swe-bench-live.github.io`.
8. Yao et al., *τ-bench (TAU-Bench)*, 2024. `arxiv.org/abs/2406.12045`. Sierra Research τ²-bench at `github.com/sierra-research/tau2-bench`.
9. Kwa et al., *Measuring AI Ability to Complete Long Software Tasks (METR HCAST/RE-Bench)*, 2025. `arxiv.org/abs/2503.14499`. Time-Horizon 1.1 update at `metr.org/blog/2026-1-29-time-horizon-1-1/`.
10. Mohammadi et al., *Evaluation and Benchmarking of LLM Agents: A Survey*, 2025. `arxiv.org/html/2507.21504v1`.
11. NeurIPS 2025 computer-use-agents roundup, Cua. `cua.ai/blog/neurips-2025-cua-papers`.
12. Lee, *Statistics for AI/ML, Part 4: pass@k and Unbiased Estimator*, 2025. `leehanchung.github.io/blogs/2025/09/08/pass-at-k/`.
13. Anthropic, *Extend Claude with skills*, 2025–2026. `code.claude.com/docs/en/skills`.
14. Sohl-Dickstein, *Too much efficiency makes everything worse: overfitting and the strong version of Goodhart's law*, 2022. `sohl-dickstein.github.io/2022/11/06/strong-Goodhart.html`.

---

## Reviewer checklist (self-check)

Before declaring this doc Phase-0-complete:

- [x] Related work covers HELM, BIG-bench, HumanEval, SWE-bench family, TAU-Bench, METR, NeurIPS-2025 agent eval survey
- [x] pass@k estimator is correctly stated (Chen et al. 2021, U-statistic formulation)
- [x] Contamination is addressed honestly, with citations
- [x] Goodhart's-Law mitigations are concrete, not handwaved
- [x] Sandbox threat model states what we do *not* defend against
- [x] Reproducibility protocol acknowledges partial LLM determinism
- [x] Limitations section exists and isn't tucked at the bottom
- [x] No scalar leaderboard rank is promised
- [x] Causal vs. correlational language is explicitly disciplined
- [ ] Reviewed by ≥2 IR/ML PhDs (pending; before launch)
- [ ] Adversarial.md cross-references match
- [ ] Metrics.md cross-references match
