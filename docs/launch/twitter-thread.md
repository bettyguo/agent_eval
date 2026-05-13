# Twitter — build-in-public methodology thread

**Send:** ~1 week before launch.
**Tone:** denser. The thread does the work of pre-empting the most common methodology criticisms before launch day.

---

## Thread (8 tweets)

**1/**
> The Claude Code skills ecosystem grew explosively this year. Anecdotal claims like "95% reliability vs 60-70%" circulate with no defined task population, no control, no CIs.
>
> Next week I'm launching **agenteval** — the first reproducible benchmark for `.claude/skills/` directories. Sharing the methodology now so it gets stress-tested before it's public.

**2/**
> Two design constraints that drove everything:
> 1. **Methodological rigor is the product.** If a measurement choice can't survive a NeurIPS reviewer, it's not in v1.
> 2. **No SaaS gating.** Anyone can submit; gating happens via reproducibility, not curation.

**3/**
> The leaderboard has **two panels**:
>
> - Primary: `skill-specific-v1` (20 hand-curated tasks) + `tau-bench-v1` (50 tasks). Uncontaminated. Every cite-worthy claim lives here.
> - Secondary: SWE-bench-Lite, with a banner: *"contaminated; not citable as a skill-effect claim."*
>
> OpenAI's Dec 2025 announcement drove this split.

**4/**
> 8 metrics per entry, all with bootstrapped 95% CIs:
> - pass@1, pass@5 (Chen-2021 unbiased estimator)
> - pass^5 (TAU-Bench reliability)
> - cost_usd, latency_s, tool_calls, timeout_rate
>
> + 8 adversarial flags. `high-variance` = pass@5 ≥ 2 × pass^5. `talkative` = output tokens ≥ 2 × baseline. Etc.

**5/**
> The cherry-pick attack: submit your best 5 of 100 seeds.
>
> Mitigation: **canonical seed lock**. Primary leaderboard entries MUST use `[1, 2, 3, 4, 5]`. Exploratory sweeps run separately and can't be promoted.

**6/**
> Reproducibility:
>
> `entry_hash = sha256(bundle || task_set || model || temp || seed_list || pricing_yaml)`
>
> Verifier re-runs in two cloud VMs. Pass/fail compared strictly. Cost ±5%, latency ±25% (LLM determinism is partial, documented honestly).

**7/**
> Three things v1 deliberately refuses:
>
> 1. LLM-as-judge grading (would couple agent + judge biases)
> 2. A scalar "agenteval score" (Goodhart non-negotiable)
> 3. Absolute capability claims on contaminated benchmarks
>
> Each refusal earned through adversarial self-review.

**8/**
> Apache-2.0. Anthropic + OpenAI + Google runners from day one. Workshop submission within 30 days of launch.
>
> Repo + methodology doc: <PUBLIC_URL_PLACEHOLDER>
>
> If you maintain a popular `.claude/skills/` bundle and your work will be a reference baseline, I've reached out separately. Concerns welcome before launch.

---

## Notes

- **Tweet 5 is the killer.** The cherry-pick attack mitigation isn't obvious until you've thought about it. Leading with that earns credibility.
- **Tweet 3 explicitly names the contamination panel split.** Reviewers will press on it; surfacing it preempts.
- **Tweet 7 is the most defensible part of the project.** The deliberate refusals are what distinguishes agenteval from "yet another benchmark."
- If a high-profile account quote-tweets the thread skeptically, the response is "see methodology.md §<N> — pushback welcome, but the doc names this." Quote the doc; don't paraphrase.

## Posting checklist

- [ ] Methodology doc URL is publicly resolvable
- [ ] Outreach emails sent ≥48 hr earlier
- [ ] Repo is public-ready (README, LICENSE, working CI)
- [ ] Have `docs/faq.md` open in a tab for replies
