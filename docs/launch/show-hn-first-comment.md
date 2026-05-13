# Show HN — first comment (post immediately as the OP)

**Send:** within ~2 minutes of the Show HN post going live.
**Purpose:** preempt the most predictable methodology criticisms before they snowball.

---

## Comment body

> A few methodology choices I made deliberately, with the reasoning:
>
> **Why no LLM-as-judge.** v1 grades with deterministic Python procedures only. LLM-as-judge would couple agent biases with judge biases — when one model is better at understanding what another model produced, you can't tell whether you measured skill quality, model capability, or judge sympathy. v2 may add it as a clearly experimental, ranking-excluded metric. ADR-0006.
>
> **Why two panels, not one.** OpenAI announced in late 2025 that SWE-bench Verified is contaminated — every frontier model can reproduce verbatim gold patches. SWE-bench-Lite is the same source distribution, so my original "skill-induced delta is still interpretable" claim failed adversarial review: contamination can interact with skill content (skills that name files/repos may activate memorized solutions disproportionately) and shrinks variance, inflating apparent significance. So SWE-bench-Lite is on a separate "informative but contaminated" panel that's NOT used for headline claims. ADR-0014.
>
> **Why canonical seeds.** Submit-your-best-5-of-100 is a real attack vector. Locking the seed list to [1,2,3,4,5] for primary-leaderboard entries closes it. Exploratory sweeps with custom seeds are supported but produce results tagged `leaderboard: false`. ADR-0015.
>
> **Why no scalar rank.** Goodhart's Law. Every column on the leaderboard is sortable; nothing is ranked overall. A "best skill" rank would attract overfitting and become uninterpretable within a quarter.
>
> **What I expect to be wrong about.** Some of the 20 hand-curated tasks will turn out to be solvable in ways I didn't anticipate. The adversarial counterpoint table in `tasks/skill-specific-v1/README.md` is my best guess at how a bad-faith skill author would game each grader; reality will surface failures I missed. I'd rather hear about those as PRs against the task YAMLs than as silent overfitting. Holdout-task rotation (quarterly) is the structural backstop.
>
> Methodology doc: <URL>
> FAQ pre-drafting every criticism I could anticipate: <URL>

---

## Notes

- **Tone:** confident-but-humble. Reviewers smell defensiveness from a kilometer away.
- **Surface the limitations.** "What I expect to be wrong about" is genuinely useful and disarms a lot of the predictable "this is biased" replies.
- **Cite ADR numbers.** Makes it clear there's a paper trail.
- **Don't apologize for the LLM-as-judge refusal.** It's the most defensible v1 choice; lean into it.

## Halt note

The URLs must be live before posting. The doc cross-references (ADR-0006, ADR-0014, ADR-0015) all need to point at the public DECISIONS.md.
