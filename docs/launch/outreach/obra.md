# Outreach draft — obra (`obra/superpowers`)

**Status:** DRAFT. Personalize before sending. Verify recipient details.

---

**Subject:** Reproducible benchmark for Claude Code skills — your superpowers bundle is a reference

Hi obra,

Heads-up: I've been building **agenteval**, an open-source reproducible benchmark for Claude Code Skills. It evaluates `.claude/skills/` directories against a fixed task set across Anthropic, OpenAI, and Google, and content-addresses every leaderboard entry so anyone can re-verify.

`obra/superpowers` is going to be one of the launch baselines, alongside `mattpocock/skills` and a no-skills control.

Flagging this **7–10 days before launch** for two reasons:

1. **Methodology pushback.** I'd value your read before it's public. The methodology doc: <PUBLIC_URL_PLACEHOLDER/docs/methodology.md>. The sections most relevant: §3 (task selection), §5 (metrics — especially the 8 adversarial flags including `talkative` and `tool-storm`, which I expect a "superpowers"-style bundle to be visibly affected by), §7 (reproducibility protocol with the canonical seed lock and two-VM verifier), and §9 (leaderboard pre-mortem).

   The specific reason I want your eyes: `obra/superpowers` is a deliberately ambitious bundle, and some of the adversarial flags (`high-variance` from pass@5 ≥ 2·pass^5; `talkative` from output-tokens; `tool-storm` from tool-call count) are exactly the kind that an ambitious bundle might trip. I'd rather you know the trigger thresholds in advance than discover them on a leaderboard row.

2. **Snapshot consent.** I'm planning to pin a specific commit SHA. Happy to use whichever release/tag you prefer, or HEAD as of <DATE>. Opt-out supported and transparent if you'd rather not be on the leaderboard.

The harness does not publish a scalar rank — every metric is sortable, nothing is overall-ranked. The leaderboard's primary panel uses uncontaminated tasks (20 skill-specific + 50 TAU-Bench subset); SWE-bench-Lite is on a separate "contaminated" panel and never used for headline claims.

Any concerns about the protocol, please push back hard before launch. I'd rather adjust the methodology than be wrong in public.

Thanks for the skills work in any case — `superpowers` is one of the more interesting "what if you really lean into this" experiments in the ecosystem.

— <YOUR NAME>
<YOUR HANDLE / EMAIL>

---

## Internal notes (not for sending)

- "obra" attribution is tentative per master prompt — verify before sending. The master prompt has the parenthetical "(Bryan Cantrill / superpowers maintainer)" which is almost certainly wrong (Cantrill is Oxide). Confirm who actually maintains `obra/superpowers`.
- If `obra/superpowers` does end up with flags fired at launch, the response is *"we report numbers, you decide"* — not editorializing.
- The mention of `talkative` / `tool-storm` is a deliberate softener: showing the flags exist signals fairness without pre-judging.
