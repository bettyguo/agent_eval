# Blog post — long-form launch piece

**Send:** ~48 hours before launch on the user's personal site, syndicated to the project blog.
**Target length:** ~2500 words.
**Tone:** thoughtful, methodology-first, build-in-public. The other channels point here for depth.

---

## Title

> **How I built a reproducible benchmark for Claude Code skills**

Plain, descriptive, optimized for Google + HN front page.

## Subtitle / dek

> Eight weeks, 120 hours, one workshop paper draft. Apache-2.0. Why measurement-first is the only sustainable answer for the skills ecosystem.

---

## Outline

### I. The problem (300 words)

> In late 2025 the Claude Code Skills ecosystem went vertical. `mattpocock/skills`, `obra/superpowers`, `andrej-karpathy-skills` — each tens of thousands of stars. The cultural pattern: a maintainer posts a SKILL.md, screenshots a successful agent run, and claims a quantitative improvement: *"95% reliability vs. 60-70%."*
>
> The problem isn't that the claim is wrong. It's that there is no protocol under which it's even defined. Pass-rate of what? Across what task population? With what control? At what cost? Under which model? The skill ecosystem isn't measuring; it's vibes-measuring.
>
> This is the gap. The PhD-thesis answer is "you need a benchmark." But the existing agentic-coding benchmarks — SWE-bench, HumanEval, TAU-Bench — weren't designed to discriminate skill bundles. They measure whether a model can solve a coding task; they don't isolate the marginal effect of a bundle of context the user appended.
>
> Also, by late 2025, OpenAI announced something startling: SWE-bench Verified is contaminated across every frontier model. Verbatim gold patches reproduce under appropriate elicitation. Whatever benchmark we end up shipping has to account for that.
>
> So I spent eight weeks building one.

### II. The design constraints (300 words)

> Three rules I refused to compromise:
>
> **1. Methodological rigor is the product.** Any measurement choice that can't survive a NeurIPS reviewer doesn't ship in v1. This is the rule that drove out LLM-as-judge grading, scalar leaderboard ranks, and absolute capability claims on contaminated tasks.
>
> **2. No SaaS gatekeeping.** Anyone can submit; gating happens via reproducibility, not curation. Submissions are PRs. CI re-verifies in two cloud zones before listing.
>
> **3. Content-addressed everything.** Every leaderboard entry can be re-verified by anyone with the bundle SHA, task-set SHA, model, temperature, seed list, and pricing.yaml SHA. No "trust me" claims.
>
> Three deliberate refusals these constraints produced:
>
> - **No LLM-as-judge.** Couples agent biases with judge biases; deterministic Python graders only in v1.
> - **No scalar rank.** Goodhart non-negotiable. Every column is sortable; nothing is ranked overall.
> - **No absolute claims on SWE-bench-Lite.** Demoted to a secondary "informative but contaminated" panel that explicitly cannot be cited.

### III. The two-panel leaderboard (400 words)

> The single most-contested decision was the contamination panel split.
>
> My original v0 design had SWE-bench-Lite on the primary leaderboard with a "skill-induced delta is interpretable" argument: contamination affects with-skill and without-skill conditions equally, so the delta is still meaningful.
>
> Adversarial self-review killed this. Two failures:
>
> 1. **Contamination is not skill-invariant.** A skill that names files, repos, or patterns disproportionately activates memorized solutions. The delta then mixes the genuine skill effect with a skill × memorization interaction.
> 2. **Contamination shrinks variance.** Memorized solutions are reproduced deterministically. This artificially tightens CIs and inflates apparent statistical significance.
>
> So the primary panel uses only the 20 hand-curated skill-specific tasks (new by construction) + 50 TAU-Bench tasks (post-cutoff for most pretraining). SWE-bench-Lite is on a secondary panel with the banner *"Contaminated benchmark — delta may be confounded by skill × memorization interaction; not citable as a skill-effect claim."*
>
> Every leaderboard view distinguishes the two visually. Every reference document distinguishes them. The workshop paper will not cite secondary-panel numbers.
>
> v2 migrates the SWE-bench task family to SWE-bench Pro (less contamination per OpenAI's audit) + SWE-bench-Live (monthly rotation caps contamination half-life).

### IV. The metrics (500 words)

> Seven primary metrics + eight adversarial flags. The interesting ones:
>
> **pass^k (TAU-Bench reliability).** The Yao 2024 paper introduced this for tool-agent-user interactions: fraction of tasks where the agent succeeds on ALL k seeds. We report pass^5 alongside the Chen-2021 pass@k unbiased estimator because they answer different questions: pass@k measures capability, pass^k measures reliability. A skill that improves pass@1 by 5 points but tanks pass^5 is buying success through nondeterminism, not reasoning improvement. The `high-variance` flag fires at pass@5 ≥ 2 × pass^5.
>
> **timeout_rate.** First-class column, not folded into pass-rate. Distinguishes "wrong answer in 30 seconds" from "ran out of time entirely." Lets us flag `passive` skills — ones that improve reliability by silently bailing on hard tasks.
>
> **model-drift detection.** Provider response fingerprints (`system_fingerprint` for OpenAI, equivalent for Anthropic) are stored on every entry but NOT included in the hash. If the fingerprint changes between submission and re-verification, the `model-drift` flag fires. Same applies to `sandbox-drift` when the Docker image SHA shifts. Hashing them would mass-invalidate the leaderboard on routine provider/security updates; flagging-not-rejecting is the operational tradeoff.
>
> **No scalar score.** Worth saying again. The default leaderboard view is a sortable table. Sorting by pass@1 shows one thing; sorting by cost_usd_median shows another. If you want "best overall," you have to choose what tradeoff "best" means. That's the point.

### V. Reproducibility and the cherry-pick attack (300 words)

> The interesting attack vector: a submitter runs 100 seeds, picks the best 5, submits them. The verifier re-runs those exact 5 seeds and reproduces the result. Fraud not detected.
>
> Mitigation: canonical seed lock. Primary-leaderboard entries MUST use `seeds = [1, 2, 3, 4, 5]`. The API gate rejects anything else. Want to do a seed sweep? `agenteval eval --exploratory --seeds 25` produces a result tagged `leaderboard: false` that cannot be promoted.
>
> Two-VM rule: every primary-leaderboard entry is re-verified in two different cloud zones before being marked `verified: true`. Agreement required on strict-equality fields; cost ±5%, latency ±25% (LLM determinism at T=0 is genuinely partial — documented honestly in §7.3 of the methodology doc).
>
> The verifier re-runs from scratch in a fresh Docker container. Skill bundle hash, task-set hash, model string, temperature, seeds, pricing.yaml hash all go into the entry hash. Sandbox image SHA is stored on the side; mismatch surfaces a flag rather than rejecting the entry.

### VI. What I expect to be wrong about (300 words)

> Some of the 20 hand-curated tasks will turn out to be solvable in ways I didn't anticipate. The `tasks/skill-specific-v1/README.md` adversarial counterpoint table is my best guess at how a bad-faith skill author would game each grader; reality will surface failures I missed.
>
> The 100-task total is also a slice. Defensible? Yes — the minimum statistical floor for detecting ~5 percentage-point deltas at 95% confidence over 5 seeds. But it's a slice. The structural defense is quarterly hidden-holdout rotation; the `holdout-divergence` flag fires at >15 pp gap between public and holdout.
>
> The deterministic-grader constraint excludes task categories where the "correctness" is genuinely judgmental (e.g., did this code review explain its reasoning well?). v2 may add LLM-as-judge as an explicitly experimental, ranking-excluded metric.
>
> Three providers in v1 is a slice. Local-model evaluation (Llama, Qwen, the open Chinese ecosystem) is v2.
>
> The cross-provider asymmetry — each provider has different default reasoning settings and implicit system prompts — is real. We publish a normalized per-provider no-skills baseline and report deltas; we don't pretend cross-provider absolutes are comparable.

### VII. What's next (200 words)

> Workshop paper submission within 30 days of launch. Target venues: NeurIPS Agents (Sep deadline), ICLR Open Science (Oct), EMNLP Industry (Oct), AAAI Bridges (later).
>
> v1.1 priorities: holdout-task rotation (first cycle), GHCR-published sandbox image, PyPI publication, mypy strict, JS-variant sandbox image for the TypeScript task.
>
> v2 directions: LLM-as-judge as an experimental metric. Multi-language task families (JS/TS, Go, Rust). Local-model runners. Long-horizon task family (METR-style time horizons).
>
> The goal is not to "win" the agentic-eval space. The goal is for the next time someone claims "this skill improves Claude by 30%," the response is "show me the agenteval submission." That's what we built.

### VIII. Acknowledgments + repo (100 words)

> Apache-2.0 throughout. Skill snapshots used as references retain their upstream licenses; opt-out is supported and transparent.
>
> Methodology doc: <URL>
> Repo: <URL>
> Leaderboard: <URL>
> FAQ: <URL>
>
> Thanks to the skill authors who reviewed the methodology pre-launch: <NAMES>. Any errors are mine.

---

## Notes

- **2500 words is a guideline.** Section II + III + V + VI are the load-bearing parts; the rest can flex.
- **Don't include a screenshot of the leaderboard with fabricated numbers.** Either ship with real-API numbers or describe the surface without screenshots.
- **The "what I expect to be wrong about" section is what makes this worth posting.** Surface limitations earnestly; reviewers will read this as the project's intellectual honesty test.
- Cross-link the FAQ in places where someone might object: at the contamination panel, at the no-LLM-judge decision, at the no-scalar-rank decision.

## Halt note

Don't publish until: methodology doc URL resolves, repo is public, skill-author outreach has had a week to land. Acknowledgments section needs real names (only with consent — see the outreach drafts for opt-out language).
