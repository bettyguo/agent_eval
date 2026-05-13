# Twitter — launch-day announce

**Send:** launch day, alongside Show HN going live.
**Lead with the leaderboard screenshot.**

---

## Announce post

> **agenteval is live.**
>
> The first reproducible benchmark for Claude Code skills. Content-addressed leaderboard, two cloud-VM re-verification, no scalar rank, deterministic graders, all metrics bootstrapped.
>
> Methodology + 5 reference skill bundles + 3 cross-provider runs:
> <PUBLIC_LEADERBOARD_URL>
>
> Show HN: <HN_URL>

**Attached image:** primary leaderboard table screenshot, ~1200×675px, dark theme, showing 3–6 entries with a real-but-honest delta between with-skill and no-skill conditions. Crop tight; legible at 1× retina.

---

## Reply chain (first 3 replies, queued)

**Reply 1 (technical):**
> Three things v1 deliberately refuses, each earned by adversarial self-review:
> - LLM-as-judge grading
> - A scalar "agenteval score"
> - Absolute capability claims on contaminated benchmarks
>
> Why each: <link-to-methodology-section>

**Reply 2 (operational):**
> Run on your own skill bundle:
>
> ```
> pip install agenteval
> agenteval eval --skills ./.claude/skills/ --tasks skill-specific-v1 --model claude-opus-4-7 --out result.json
> agenteval submit ./result.json
> ```
>
> Submission is a PR; CI re-verifies in two cloud zones.

**Reply 3 (sourcing):**
> Reference baselines used in the launch leaderboard, with author opt-in:
> - mattpocock/skills @ <SHA>
> - obra/superpowers @ <SHA>
> - andrej-karpathy-skills @ <SHA>
>
> The no-skills control + per-provider normalized baselines from `skills-baseline/`.

---

## Notes

- **Lead with the screenshot.** The image is 80% of engagement.
- **Don't editorialize on which bundle "won."** The leaderboard does that visually; commentary turns the rest of Twitter into the comments section of the leaderboard.
- If a skill author whose bundle has a flag fired (e.g., `talkative`) DMs you, the response is in `docs/faq.md` — *"we report numbers, you decide. Flags are descriptive badges, not penalties."*
- **Don't promise a scalar ranking just because someone asks for one.** Goodhart non-negotiable.

## Halt note

The image needs to be a real screenshot from a real leaderboard with real numbers. That requires a real-API smoke run. Not generated automatically.
