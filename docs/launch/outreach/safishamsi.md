# Outreach draft — Safi Shamsi (`graphify`)

**Status:** DRAFT. Personalize before sending. Verify recipient details.

---

**Subject:** Reproducible benchmark for Claude Code skills — flag for graphify

Hi Safi,

Quick heads-up — I'm building **agenteval**, an open-source reproducible benchmark for Claude Code Skills, launching in ~7–10 days. Wanted to flag it because `graphify` and the surrounding work will be referenced in the launch ecosystem framing.

The 30-second pitch: the skills space has anecdotal claims like *"95% reliability vs. 60–70%"* with zero credible methodology. agenteval is the rigorous baseline — content-addressed leaderboard entries, canonical seed list, two-VM re-verification, deterministic graders (no LLM-as-judge in v1), no scalar rank.

Methodology doc: <PUBLIC_URL_PLACEHOLDER/docs/methodology.md>.

Two things before launch:

1. **Methodology pushback.** If anything in §3 (task selection), §5 (metrics + adversarial flags), or §9 (leaderboard pre-mortem) looks off to you, this is the moment to flag it. I'd rather adjust than respond in a launch thread.

2. **Reference baseline.** If `graphify` (or any of your other skill work) should be a reference snapshot on the launch leaderboard, I can pin a specific commit SHA — your call which one. Opt-out is supported and transparent.

The harness's primary panel uses uncontaminated tasks only (20 hand-curated + 50 TAU-Bench subset); SWE-bench-Lite is on a separate "informative but contaminated" panel that's explicitly not used for headline claims. So whatever your bundle's numbers are, they'd land on a fair surface.

No bandwidth pressure — even "no concerns" is useful at launch.

— <YOUR NAME>
<YOUR HANDLE / EMAIL>

---

## Internal notes (not for sending)

- "safishamsi (graphify)" attribution from master prompt §6.3 — verify the recipient and the `graphify` project URL before sending.
- The pitch leans into the contamination/two-panel split because it shows methodological seriousness without spending the email on it.
- If she engages, she's a useful methodology reviewer; if she doesn't, that's also fine.
