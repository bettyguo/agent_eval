# Show HN — title + body

**Send:** launch day, mid-morning Pacific.
**Strategy:** lead with the *question*, not the answer.

---

## Title options (pick one)

### Recommended
> **Show HN: agenteval – A reproducible benchmark for Claude Code skills**

Plain, descriptive, won't tip the algorithm into "marketing." HN works better with restraint.

### Alternative (riskier, more clickable)
> **Show HN: Do Claude Code skills actually work? A leaderboard says…**

The question framing is more compelling but invites "you're being inflammatory about Pocock's skills" pushback. Use only if the launch outreach has already confirmed no opt-outs.

### Avoid
- ❌ "Show HN: I tested all the popular Claude skills…" (clickbait, sets up disappointment)
- ❌ "Show HN: skills are overhyped" (inflammatory, methodology becomes secondary)

---

## Body (≤2000 chars HN limit)

> The Claude Code Skills ecosystem (mattpocock/skills, obra/superpowers, andrej-karpathy-skills) has billions of stars combined and zero credible measurement. Claims like "95% reliability vs 60-70%" circulate with no defined task population, no control, no CIs.
>
> agenteval is an open-source harness that fixes that. It takes a `.claude/skills/` directory, runs it on a fixed 100-task set across Anthropic / OpenAI / Google in a hardened Docker sandbox, and reports pass@1, pass@5, pass^5 (TAU-Bench reliability), cost, latency, tool calls, timeout rate, and 8 adversarial flags — all with bootstrapped 95% CIs. No scalar rank, no LLM-as-judge.
>
> Every leaderboard entry is content-addressed:
>
>     entry_hash = sha256(bundle_hash || task_set_hash || model || temp || seed_list || pricing_yaml_hash)
>
> Anyone can re-run + verify. CI re-verifies every submission in two cloud zones.
>
> The big methodological choices that took the longest:
>
> 1. Two-panel leaderboard. Primary (uncontaminated): 20 hand-curated skill-specific tasks + 50 TAU-Bench tasks. Secondary (informative-but-contaminated): SWE-bench-Lite, with a banner explicitly NOT citable as a skill-effect claim. Driven by OpenAI's Dec 2025 announcement that SWE-bench Verified is contaminated across all frontier models.
>
> 2. Canonical seed list [1,2,3,4,5] for leaderboard entries. Closes the cherry-pick attack ("submit your best 5 of 100 seeds"). Exploratory mode is supported but produces non-leaderboard results.
>
> 3. pass^k (TAU-Bench reliability) reported alongside pass@k. A skill that improves pass@1 by 5 points but tanks pass^5 is buying success through nondeterminism, not capability. The `high-variance` flag fires when pass@5 ≥ 2 × pass^5.
>
> Apache-2.0. Workshop paper draft within 30 days.
>
> Methodology doc (~7k words): <URL>
> Code + leaderboard: <URL>

---

## Posting strategy

1. **Time:** 8–10 AM Pacific Tuesday or Wednesday. Avoid Mondays (queue is long) and Fridays (weekend dropoff).
2. **First comment:** post `docs/launch/show-hn-first-comment.md` as your own first reply within ~2 minutes of posting.
3. **Keep tabs open:** `docs/methodology.md` + `docs/faq.md` + `docs/adversarial.md`. Quote sections verbatim in replies; don't paraphrase.
4. **Don't argue rankings.** If someone asks "why isn't X #1," explain that there is no ranking, then link to methodology §10 (causal-vs-correlational discipline).
5. **Don't claim what's not measured.** "Skills work for Y" is not what the harness measures; it measures "pass@1 on this task set under these conditions."
6. **Methodology criticisms get a doc link, not a fresh defense.** Saying "see methodology.md §3.2" is stronger than retyping an answer that risks contradicting the doc.

---

## Halt note

Substitute real URLs (repo, leaderboard, methodology) before posting. The current placeholders are intentional — they should not be visible to HN visitors.
