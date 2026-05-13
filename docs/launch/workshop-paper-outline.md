# Workshop paper outline (4 pages)

> Phase 4 §7.4 deliverable. Submit within 30 days of public launch. Target venues: **NeurIPS 2026 Agents/Tool-Use workshop** (deadline likely Sep 2026), **ICLR 2027 Open Science/Reproducibility workshop**, **EMNLP 2026 Industry track** (Oct), **AAAI 2026 Bridges**. Pick based on whichever deadline lands first after launch.

The 4-page workshop format means tight prose. Sources: `docs/methodology.md` (the 7k-word backbone), `tasks/skill-specific-v1/README.md`, real-API numbers from the post-launch run.

---

## Title (working)

> **agenteval: A Reproducible Benchmark for LLM Skill Bundles**

Crisp. Mentions the *what* without overclaiming the *first*.

## Abstract (150 words)

(Already drafted in `docs/methodology.md` § Abstract — lightly compressed for the workshop format.)

## 1. Introduction (~0.5 pages)

- The skills phenomenon (2025–2026): explosive GitHub category, anecdotal claims (~80 words)
- The measurement gap: no defined task population, no controls, no CIs (~80 words)
- Our contribution: a content-addressed, reproducibility-first harness with three deliberate v1 refusals (LLM-as-judge, scalar rank, contaminated-headline claims) (~100 words)
- Position vs. related work: this is narrowly about skill bundles, not a general LM eval framework (~60 words)

## 2. Related work (~0.5 pages)

Compressed from `docs/methodology.md` §2:

- HELM (Liang+ 2022) — multi-metric reporting; we steal this.
- BIG-bench (Srivastava+ 2022) — category-level scores; we steal this.
- HumanEval / pass@k (Chen+ 2021) — pass@k unbiased estimator; we steal this verbatim.
- SWE-bench (Jimenez+ 2024) + the OpenAI contamination announcement (Dec 2025) — drove our two-panel architecture.
- τ-bench (Yao+ 2024) — pass^k reliability metric; we steal this.
- METR HCAST/RE-Bench (Kwa+ 2025) — time-horizon framing; we don't steal (out of scope).
- `lm-evaluation-harness` (EleutherAI) — we explicitly don't extend (scope-creep).

Each gets 1–2 sentences max in workshop format.

## 3. Methodology (~1.0 pages — the dense core)

### 3.1 Task selection
- 100-task v1 ceiling
- Two-panel split (primary = uncontaminated 70 tasks; secondary = SWE-bench-Lite 30 tasks)
- Per-category breakdown (5 categories × 4 hand-curated tasks each)
- Deterministic grader constraint (ADR-0006: no LLM-as-judge)

### 3.2 Metrics
- pass@1, pass@5 (Chen estimator), pass^5 (τ-bench reliability)
- Efficiency: cost, latency, tool_calls, timeout_rate
- 8 adversarial flags (briefly enumerate); detailed treatment in supplementary materials
- 95% bootstrapped CIs (10k iter, resampling tasks)

### 3.3 Reproducibility
- Entry-hash construction
- Canonical seed-list lock [1,2,3,4,5] (closes cherry-pick attack)
- Two-VM verifier rule
- Partial-determinism honesty: tolerances on cost/latency, strict on pass/fail
- Sandbox: pinned Docker image, network off, non-root, no host mount

### 3.4 Sandbox + threat model
- One paragraph; defer details to supplementary

## 4. Experiments (~1.0 pages)

Requires **real-API numbers** from post-launch run. Structure:

### 4.1 Baseline (no-skills)
- Per-provider pass@1 / pass@5 / pass^5 on the primary panel
- A bar chart (or just a table) with cross-provider deltas-from-baseline-zero

### 4.2 Reference skill bundles
- mattpocock/skills, obra/superpowers, andrej-karpathy-skills (consent-gated; see launch outreach)
- Each bundle × each provider × primary panel: pass@1 / pass@5 / pass^5 / cost_usd_median / timeout_rate / flags
- One figure: pass@1 vs. cost (the Pareto plot, faithfully reproducing the leaderboard view)

### 4.3 Adversarial-skill experiments
- Build the synthetic pathological skills from `docs/adversarial.md`: nondeterministic oracle, context padder, tool storm, regex parroter, answer leak, pricing-stale
- Show that each adversarial flag fires on its corresponding pathology and not on the legitimate bundles
- This is the section that distinguishes us from "yet another benchmark" — we explicitly defend against being gamed

### 4.4 Secondary panel (SWE-bench-Lite, contaminated)
- Same bundles, but with the contamination banner
- Show that the secondary-panel deltas are not interpretable as skill effects (e.g., bundles that hurt on primary may help on secondary due to memorization activation)
- The figure here is the case-in-point for §3.1's panel split

## 5. Limitations and future work (~0.3 pages)

Direct lift from `docs/methodology.md` §11 + §12:

- Single-language Python skew (v2: JS/TS, Go, Rust)
- No long-horizon eval
- Partial LLM determinism (honest documentation, not solved)
- Sandbox is soft (accidental, not adversarial)
- No human-baseline anchoring
- Three providers only in v1
- No LLM-as-judge (constraint, not bug)
- Skill snapshots can age
- Cross-provider baselines not perfectly symmetric
- SWE-bench-Lite is secondary-panel only

## 6. Discussion (~0.4 pages)

Three forward-looking themes:

### 6.1 Why measurement-first matters for the skills ecosystem
- The pattern of "viral skill bundle" → "anecdotal improvement claim" → "no protocol" is structurally similar to early-2010s deep-learning before reproducibility norms
- Without measurement, we can't tell over-tuning from genuine improvement; the eventual disillusionment is predictable

### 6.2 Cross-provider as a fairness mechanism
- Skills are an Anthropic-specific concept, but emulating them on OpenAI/Google reveals whether a skill is doing model-specific work or generally useful
- Surprising finding (placeholder until real numbers): some skills that help Claude actively HURT other providers, suggesting Claude-specific tuning that bundle authors may not intend

### 6.3 The role of the workshop community
- The project is Apache-2.0; the task set is versioned; v2 directions are open
- Holdout rotation is the structural Goodhart defense; community-contributed tasks accelerate this
- Open call for tasks under the documented YAML schema

## Acknowledgments

- Skill authors who reviewed the methodology pre-launch (with consent; see launch outreach drafts)
- Any IR/ML PhDs who reviewed `docs/methodology.md` (per §1 quality bar)
- Funding source (placeholder)

## References (bib)

See `docs/references.bib`. ~15 entries:
- Liang+ 2022 (HELM)
- Srivastava+ 2022 (BIG-bench)
- Chen+ 2021 (HumanEval)
- Jimenez+ 2024 (SWE-bench)
- OpenAI 2025 (SWE-bench Verified contamination announcement)
- Yao+ 2024 (TAU-bench)
- Kwa+ 2025 (METR HCAST/RE-Bench)
- Mohammadi+ 2025 (LLM agent evaluation survey)
- Sohl-Dickstein 2022 (strong Goodhart)
- Anthropic 2026 (Claude Code Skills docs)
- Scale Labs 2026 (SWE-bench Pro)
- SWE-bench-Live (continuous benchmark)
- + 3 supporting references on tool-use evaluation

## Supplementary materials (uploaded separately)

- Full `docs/methodology.md` (the 7k-word backbone)
- `docs/adversarial.md` (synthetic pathological-skill design)
- `docs/reproducibility.md` (full hashing + verifier protocol)
- 20-task spec in `tasks/skill-specific-v1/README.md`
- Code repo URL

---

## Notes

- **The Experiments section needs real numbers.** Without them, this is a methodology paper without empirical content. Run a full primary panel + 3 reference bundles + 6 adversarial skills before submission.
- **Cross-provider Discussion is the unusual angle.** Other agentic-eval papers stay within one provider; agenteval's cross-provider stance is the most workshop-worthy finding.
- **Don't oversell.** The honest claim is: "we built a reproducible benchmark, here are the methodology choices, here are early results, here's what we got wrong." Reviewers will reward that more than a "we win" framing.
- **Author list:** discuss co-authorship with the human maintainer. The master prompt §10 open-question on this is unresolved.

## Halt note

Submitting to a workshop is an external action. The outline above is for the maintainer to flesh out, run real-API experiments against, and submit when ready.
