# Reddit — r/ClaudeAI + r/MCP

**Send:** launch day, alongside the Show HN.
**Tone:** practical. These subreddits care less about methodology, more about whether they should use it.

---

## r/ClaudeAI post

### Title

> **agenteval — open-source benchmark for `.claude/skills/` bundles, with cross-provider runs (Anthropic / OpenAI / Google)**

### Body

> Hi r/ClaudeAI! Just released **agenteval**, an open-source benchmark for Claude Code Skills.
>
> **What it does:**
> - Run any `.claude/skills/` directory against a fixed 100-task set
> - Compare to no-skills baseline + reference bundles (mattpocock/skills, obra/superpowers, etc.)
> - Across Anthropic, OpenAI, Google
> - Get pass@1, pass@5, pass^5 (reliability), cost, latency, and 8 adversarial flags — all with confidence intervals
>
> **Why it exists:**
> Every "this skill makes Claude 30% better" claim you've seen has zero methodology behind it. agenteval is the rigorous version.
>
> **How to use it:**
>
> ```
> pip install agenteval
> agenteval eval --skills ./.claude/skills/ --tasks skill-specific-v1 --model claude-opus-4-7 --out result.json
> agenteval submit ./result.json
> ```
>
> Submission is a PR; CI re-verifies in two cloud VMs.
>
> **What's in v1:**
> - 20 hand-curated tasks (TDD enforcement, code review, style adherence, refactor, multi-file reasoning — 4 each)
> - Plus 50 TAU-Bench tasks (tool-use breadth)
> - SWE-bench-Lite is a secondary "informative but contaminated" panel
> - Three providers in v1
>
> **What's NOT measured:**
> - Code style / aesthetics
> - Long-horizon (>5 min) tasks
> - Multi-modal (voice, vision)
> - LLM-as-judge subjective grades (v2 maybe)
>
> Repo: <URL>
> Leaderboard: <URL>
> Methodology doc (if you want to push back before the workshop paper drops): <URL>
>
> Happy to answer questions — and please submit your own skill bundles if you have them. Apache-2.0.

---

## r/MCP variant

Same body, but lead with:

> Posting here because Claude Code skills + MCP servers occupy adjacent design space. agenteval is an open-source benchmark for the skills half; if you're maintaining an MCP server that gets used inside skill bundles, the cross-provider runs may be useful for you.

Then the same "What it does / Why / How / What's NOT measured" structure.

---

## Notes

- **r/ClaudeAI cares about:** real-world utility, "should I switch to this," low-friction quick-start. Lead with the pip-install one-liner.
- **r/MCP cares about:** technical correctness, protocol integrity, cross-provider compatibility. Lean into the normalized tool dispatch.
- **Avoid academic phrasing on these subreddits.** "pass^k (TAU-Bench reliability)" → "pass on all 5 seeds — measures consistency."
- If a community member runs the harness and gets a weird result, the response is the FAQ — *"open an issue with the reproduction, we'll investigate."* Don't editorialize before the data.
