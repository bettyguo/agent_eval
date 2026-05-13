# Outreach draft — Forrest Chang

**Status:** DRAFT. Personalize before sending. Verify recipient details.

---

**Subject:** Reproducible benchmark for Claude Code skills — flag for your work

Hi Forrest,

Quick note — I'm building **agenteval**, an open-source reproducible benchmark for Claude Code Skills, launching in ~7–10 days. Wanted to flag it because your work in the skills ecosystem will be referenced in the launch materials.

The harness:
- Evaluates `.claude/skills/` directories on a fixed task set across Anthropic, OpenAI, Google.
- Content-addresses leaderboard entries so anyone can re-verify by re-running the exact (skill-bundle SHA + task-set SHA + canonical seeds + pricing.yaml SHA).
- Reports pass@k, pass^k (TAU-Bench reliability), cost, latency, tool_calls, timeout_rate, and 8 adversarial flags — all with bootstrapped 95% CIs and no scalar rank.

Methodology doc here: <PUBLIC_URL_PLACEHOLDER/docs/methodology.md>. The most relevant section for the skills ecosystem is probably §9 (leaderboard pre-mortem), which lays out our Goodhart / cherry-pick / drift defenses.

Two things I'd appreciate before launch:

1. **Methodology pushback** — anything you'd push on, especially around task selection (§3) and the adversarial-flag thresholds (§5). I'd rather adjust now than respond to it in a launch thread.

2. **If your own bundle should be on the leaderboard** — I'd love to pin a SHA. Or if you'd rather *not* be listed, that's fully supported (opt-outs are transparent).

No pressure — if you don't have bandwidth, a one-line "no concerns" is fine. Just wanted to give you visibility before this is public.

— <YOUR NAME>
<YOUR HANDLE / EMAIL>

---

## Internal notes (not for sending)

- "forrest from forrestchang" attribution from master prompt §6.3 — verify the handle is `@forrestchang` or similar before sending.
- His specific contribution to the skills ecosystem isn't fully specified in the master prompt; the draft is intentionally generic so it works whether his work is a skill bundle, a meta-tool, or commentary.
- If he replies with criticism of the protocol, take it seriously and offer to ship a v1.1.
