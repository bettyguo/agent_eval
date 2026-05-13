# Outreach draft — Matt Pocock (`mattpocock/skills`)

**Status:** DRAFT. Personalize before sending. Verify recipient details.

---

**Subject:** Heads-up: a reproducible benchmark for Claude Code skills (and your bundle is a reference baseline)

Hi Matt,

Quick context: I've been building **agenteval** — an open-source reproducible benchmark for Claude Code Skills. It runs `.claude/skills/` directories against a fixed task set across Anthropic, OpenAI, and Google, with content-addressed leaderboard entries (anyone can re-verify by re-running the exact bundle hash + task-set hash + canonical seeds).

`mattpocock/skills` is going to be one of the reference snapshots on the launch leaderboard, alongside `obra/superpowers` and the no-skills baseline.

I wanted to flag this **7–10 days before launch** for two reasons:

1. **Methodology pushback.** I'd genuinely value your read on the protocol before it's public. The methodology doc is here: <PUBLIC_URL_PLACEHOLDER/docs/methodology.md>. It's ~7k words; the parts most likely to matter to you are §3 (task selection rationale), §5 (metrics — pass@k, pass^k, cost, the 8 adversarial flags), and §9 (the leaderboard pre-mortem). If anything looks unfair, I'd rather find out now than from a reviewer or HN thread.

2. **Snapshot consent.** I'm planning to pin a specific commit SHA of `mattpocock/skills` as the reference snapshot. Happy to use whichever release/tag you'd prefer, or to use HEAD as of <DATE>. If you'd rather *not* be on the leaderboard at all, that's fine too — opt-outs are transparent and supported.

The headline numbers won't include your bundle's name in marketing copy without your sign-off. The leaderboard does not publish a scalar rank (intentionally — Goodhart's-Law reasons in §10 of the methodology doc); every metric is sortable, nothing is overall-ranked.

Anything that worries you about the protocol, please push back. Even a "looks fine, don't change it" is useful as a signal at launch.

Thanks for the skills work either way — it's been one of the genuinely useful Claude Code patterns to land in the ecosystem this year.

— <YOUR NAME>
<YOUR HANDLE / EMAIL>

---

## Internal notes (not for sending)

- He's high-engagement; expect a substantive reply.
- If he pushes back on a specific task design, that's a free methodology audit — take it seriously.
- If he asks to be excluded, comply transparently (log in `docs/opt-outs.md`).
- If he asks "what does the leaderboard say about my skills" — defer until after he's read the methodology. "Numbers without methodology" framing is what we're trying to prevent.
