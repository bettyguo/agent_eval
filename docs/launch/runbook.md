# Launch-day runbook

> Phase 4 §7.3 deliverable. **Generic** — the master prompt references a `paper-skills §7.3` template that's not accessible; this is built from first principles.

---

## T - 14 days

- Post `docs/launch/twitter-teaser.md` (quiet pre-launch tease)
- Confirm `pricing.yaml` `last_audited` is current (within 30 days; refresh if not — `pricing-stale` flag will fire on every submission otherwise)
- Sanity-check the no-skills baseline reproduces under canonical seeds against the current Anthropic model
- Cache-warm the methodology doc on the public URL host (Google rendering, especially)

## T - 10 days

- Send outreach emails from `docs/launch/outreach/` to skill authors. Sequence per `docs/launch/outreach/README.md`:
  1. Matt Pocock + Safi Shamsi (highest engagement expected)
  2. obra + Forrest Chang (specialist maintainers)
  3. Karpathy (long shot)
- Track replies in a private note. Any opt-out goes into `docs/opt-outs.md` immediately and removes the bundle from launch-day leaderboard snapshots.

## T - 7 days

- Post `docs/launch/twitter-thread.md` (8-tweet methodology thread)
- Verify outreach replies; revise methodology if anything substantive surfaces
- Run the full primary panel against ≥1 reference skill bundle + the no-skills baseline; pin the result for the launch-day screenshot

## T - 48 hours

- Publish blog post (`docs/launch/blog-post.md`) on personal site
- Re-run + re-verify the launch-day leaderboard entries; ensure CI is green
- Re-read `docs/faq.md` end-to-end; rehearse the top 3 expected criticisms

## T - 24 hours

- Lock the repo to `main` for the launch day (no new merges)
- Make sure all public URLs resolve: README, methodology, FAQ, leaderboard, repo
- Re-read the outreach replies; queue any "thanks for reaching out" follow-ups

## T - 4 hours

- Have these tabs open: `docs/methodology.md`, `docs/faq.md`, `docs/adversarial.md`, `DECISIONS.md`, the leaderboard, the Show HN draft, the announce tweet draft
- Verify `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` + `GOOGLE_API_KEY` are set in CI secrets
- Confirm `agenteval verify` works on a known-good submitted entry

## T - 0 (launch)

In this order, ~30 minutes apart:

1. **Show HN** (`docs/launch/show-hn-post.md`). Within 2 minutes, post the first comment (`docs/launch/show-hn-first-comment.md`).
2. **Twitter announce** (`docs/launch/twitter-announce.md`) with the leaderboard screenshot
3. **r/MachineLearning [P] post** (`docs/launch/reddit-ml.md`)
4. **r/ClaudeAI + r/MCP** posts (`docs/launch/reddit-claude.md`)
5. **Direct outreach** to the skill authors emailed at T-10d: a one-line "agenteval is live, your bundle is on the leaderboard at <URL>"

## During the launch (first 24 hours)

**Reply policy:**

- **Methodology questions:** link to the relevant `docs/methodology.md` section. Quote verbatim; don't paraphrase. Saying "see methodology.md §3.2" is a stronger move than typing a fresh answer that risks contradicting the doc.
- **Reproduction questions:** if someone says "I ran it and got X," ask for their submission JSON. Don't speculate.
- **Hostile criticism:** the FAQ pre-drafts most of these. Quote the FAQ entry; don't engage on emotional terms.
- **Skill author DMs:** if a bundle has flags fired and the author asks about it — *"we report numbers, you decide. Flags are descriptive badges, not penalties."*

**What NOT to do:**

- Don't editorialize on which skill is "best." There is no overall rank.
- Don't promise features under pressure. "Submit an issue" is the right answer.
- Don't apologize for the LLM-as-judge or no-scalar-rank decisions. Those are the spine of the project.
- Don't push code changes during the launch unless something is actively broken (e.g., the leaderboard doesn't render). Methodology-affecting fixes wait for T+24.

## T + 24 hours

- Tally engagement: HN points, Reddit karma, Twitter impressions. (Sanity-check only — these aren't success metrics.)
- Real success metrics:
  - Number of independent submissions to the leaderboard
  - Number of methodology-substantive replies (from anyone)
  - Number of follow-on PRs against the task set or the metrics module
- Write a public "what worked / what didn't" thread at T+72h. Be honest about the gap between projected and observed.

## T + 7 days

- Sync the outreach list: any skill author who hasn't replied gets a one-line follow-up offering to discuss / remove their bundle
- First holdout rotation: pull 5 hidden tasks from a tracked draft and start the verifier-B pipeline

## T + 30 days

- Workshop paper submission. Target venue chosen during the T-7 to T+0 window.

---

## Things that will go wrong (predict + mitigate)

| Failure mode | Probability | Mitigation |
|---|---|---|
| Leaderboard renders broken on launch day | Low (frontend was tested) | Have a static fallback HTML in `frontend/static-fallback/` |
| Show HN gets buried | Medium (timing-sensitive) | The Twitter thread is the backup channel; reddit posts are tertiary |
| A skill author who didn't reply pre-launch sees their bundle and pushes back publicly | Medium | The opt-out path is documented and trivially actionable; remove + log in `docs/opt-outs.md` within an hour |
| Methodology criticism we hadn't anticipated | High | This is the point. The FAQ + ADR log is the audit trail; any substantive critique gets a new ADR within 48 hours |
| CI verify-submission flakes under load | Medium | The two-VM rule lets one VM fail without invalidating the entry; degraded mode is documented |
| Real-API spending spikes from a viral attempt at running the harness | Low (cost is on submitter, not us) | Document the dry-run estimate prominently in the README |
| Anthropic does an Apple-style "we have a problem with this" | Very low | The project is positioning-agnostic re. Anthropic; the multi-provider stance is the natural defense |
