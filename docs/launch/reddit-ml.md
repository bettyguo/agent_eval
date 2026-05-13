# Reddit — r/MachineLearning [P] post

**Send:** launch day, after the Show HN settles.
**Tone:** academic. Lead with the methodology, not the demo.

---

## Title

> **[P] agenteval — a reproducible benchmark for Claude Code skills, with two-panel leaderboard and canonical-seed lock**

The `[P]` tag (Project) is required by r/MachineLearning's rules. Use `[R]` (Research) only if there's a paper attached on launch day; otherwise [P] is safer.

---

## Body

> Posting the v1.0 release of agenteval, an open-source eval harness for Claude Code Skills (the `.claude/skills/` directory format that's taken over GitHub this year).
>
> **Methodology doc** (~7k words, workshop-paper backbone): <URL>
> **Repo + leaderboard:** <URL>
>
> **Tl;dr design decisions worth scrutiny:**
>
> - **Two leaderboard panels.** Primary (uncontaminated): 20 hand-curated skill-specific tasks + 50 TAU-Bench tasks. Secondary (informative-but-contaminated): SWE-bench-Lite, with an explicit "delta may be confounded by skill × memorization interaction; not citable" banner. Driven by OpenAI's December 2025 announcement that Verified is contaminated.
>
> - **Metrics:** pass@1, pass@5 (Chen et al. 2021 unbiased estimator), pass^k (TAU-Bench reliability, Yao et al. 2024), cost, latency, tool_calls, timeout_rate. All point estimates carry 95% bootstrapped CIs over 10k iterations resampling tasks. 8 deterministic adversarial flags.
>
> - **Reproducibility:** `entry_hash = sha256(bundle || task_set || model || temp || seed_list || pricing_yaml)`. Canonical seed list `[1,2,3,4,5]` for primary entries. Verifier re-runs in two cloud zones; pass/fail compared strictly, cost ±5%, latency ±25%.
>
> - **Sandbox:** pinned Docker image, network off by default, cpu/memory capped, non-root user, no host mount.
>
> - **Deliberate refusals in v1:** no LLM-as-judge grading; no scalar leaderboard rank; no absolute capability claims on contaminated benchmarks.
>
> **What I want from r/MachineLearning specifically:**
>
> 1. The methodology section that's most likely to be wrong is **§4 (contamination audit)**. If you've thought hard about contamination interactions in benchmarks, please push back. My current position is that contamination is NOT skill-invariant (so even delta-style claims need the secondary-panel demotion). If you disagree, I want to hear why before the workshop submission.
>
> 2. The adversarial flag set in **§5.3 + `docs/adversarial.md`**. Eight flags is the v1 set; what's missing? Synthetic pathological-skill tests are landing in v1.1.
>
> 3. **§7.3 partial-determinism honesty.** I document that LLM determinism at T=0 is partial (provider model-version drift, batch composition, tokenizer drift). The tolerance design (strict pass/fail, ±5% cost, ±25% latency) was the result of an explicit tradeoff. Critique welcome.
>
> Apache-2.0. Workshop paper draft within 30 days of launch.

---

## Notes

- **r/ML's standard:** "this is a reproducible benchmark with a real methodology" is much more credible than "this is the best benchmark." Lead with limitations.
- **The "what I want from this subreddit specifically" framing.** Treats the audience as the reviewers they actually are.
- **Cite Chen 2021 and Yao 2024 by name.** The Chen pass@k estimator is well-known; Yao's TAU-Bench pass^k less so. Naming both signals you've actually read the literature.
- Avoid the phrase "state of the art." We measure deltas, not absolute capability.
- If someone says "why not just use SWE-bench?" — the contamination response is the entire §4 of the methodology doc. Link, don't paraphrase.

## Halt note

The post needs the real URLs. Worth waiting until the methodology doc is publicly resolvable.
