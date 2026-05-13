# FAQ

Pre-drafted responses to criticisms we expect at launch and afterward. Mirrors the master prompt §6.4 table, expanded.

---

## Methodology

### "Your tasks are biased / unrepresentative of real Claude Code workflows."

Agree — they're a slice. v1 is a 100-task ceiling per [ADR-0009](../DECISIONS.md) (20 hand-curated skill-specific + 50 TAU-Bench subset + 30 SWE-bench-Lite subset). The slice was chosen for **deterministic gradability** (no LLM-as-judge in v1 per [ADR-0006](../DECISIONS.md)), not for representativeness. We surface this in [`docs/methodology.md`](methodology.md) §11 (Limitations). Submit additional tasks via PR — the task YAML schema is locked at [`docs/tasks.md`](tasks.md) §1.

### "Goodhart's Law — skills will overfit to your benchmark."

Three structural defenses:
1. **Per-category reporting.** A skill that crushes one category and tanks another is visibly different from a skill that helps uniformly.
2. **Hidden holdout tasks rotated quarterly.** Submissions are evaluated against both the public set and the current quarterly holdout; the `holdout-divergence` flag triggers at >15 pp gap.
3. **No scalar rank published.** Every metric is sortable; nothing is ranked. There is no "agenteval score" to optimize against.

### "LLM eval is unreliable; this is noise."

We report bootstrapped 95% CIs over 10 000 iterations resampling tasks, and require the canonical 5-seed list `[1,2,3,4,5]` for leaderboard entries ([ADR-0015](../DECISIONS.md)). Pass^5 (TAU-Bench reliability) is reported alongside pass@k so any nondeterminism shows up as the `high-variance` flag. Partial LLM determinism at temperature=0 is documented honestly in [`docs/methodology.md`](methodology.md) §7.3.

### "You're picking on Pocock's skills" (or any other named author).

We rank by metrics, not authors. All baselines run identically. If a skill author requests removal, we comply transparently — opt-outs are listed at [`docs/opt-outs.md`](opt-outs.md) (when applicable) with a brief, neutral note. We don't run someone's skill without consent if they object.

### "Why aren't models X, Y, Z evaluated?"

v1 supports Anthropic + OpenAI + Google. Adding a fourth provider is a project-level decision, not a user one ([ADR-0004](../DECISIONS.md)). PRs welcome to extend `src/agenteval/runners/`.

### "Why aren't skill bundles X, Y, Z on the leaderboard?"

They haven't submitted. Submission is PR-based (no SaaS, no gatekeeping). See "How to evaluate your own skill bundle" in the [README](../README.md). Anyone can submit; gating happens via reproducibility, not curation.

---

## Reproducibility & verification

### "How do I trust the numbers?"

Every leaderboard entry is content-addressed:

```
entry_hash = sha256(
    skill_bundle_hash    || task_set_hash       ||
    model                || temperature          ||
    seed_list            || pricing_yaml_hash
)
```

The verifier re-runs each entry from scratch in a fresh Docker container in **two different cloud VMs** (anti-pattern #10 of the master prompt) and compares structured features: per-task pass/fail per seed strictly, cost within ±5%, latency within ±25%. Entries that fail verification carry `verified: false` and are hidden from the default leaderboard view.

### "Why not bit-exact reproduction?"

Because LLM determinism at temperature=0 is partial — there are known sources of drift even with identical prompts and seeds: provider-side model-version updates, batch-composition numerics, tokenizer normalization. We document this honestly in [`docs/methodology.md`](methodology.md) §7.3 and tolerate it on cost/latency, refuse it on pass/fail. A flipping task triggers the `borderline-stability` flag.

### "What stops someone from running 100 seeds and submitting the best 5?"

The canonical seed list lock ([ADR-0015](../DECISIONS.md)): primary-leaderboard entries **must** use `seeds = [1, 2, 3, 4, 5]`. The API gate rejects non-canonical seed lists. For capability sweeps and exploration, `agenteval eval --exploratory` produces results tagged `leaderboard: false` that cannot be promoted to the leaderboard.

### "Why is SWE-bench-Lite on the leaderboard at all if it's contaminated?"

It's on the **secondary panel**, not the primary ([ADR-0014](../DECISIONS.md)). Every secondary-panel row carries the banner *"Contaminated benchmark — delta may be confounded by skill × memorization interaction; not citable as a skill-effect claim."* The primary panel (skill-specific-v1 + tau-bench-v1) is what we underwrite. We commit to migrating the SWE-bench task family to [SWE-bench Pro](https://labs.scale.com/leaderboard/swe_bench_pro_public) + [SWE-bench-Live](https://swe-bench-live.github.io/) in v2.

---

## Project scope

### "Why not just extend `lm-evaluation-harness`?"

`lm-evaluation-harness` assumes a generation-then-score loop, not a tool-using agent with a trajectory. Forking it would add heavyweight upstream coupling pulling us toward general LM eval — exactly the scope creep we're refusing per the non-goals in [README.md](../README.md). We do borrow conventions (semver task-set versioning, pinned task tarballs).

### "Why no LLM-as-judge?"

[ADR-0006](../DECISIONS.md), held after Phase 0 adversarial review. The determinism gain is worth the task-design narrowness for v1. We already have 20 cross-category skill-specific tasks respecting it. v2 may add LLM-as-judge as an **experimental, ranking-excluded** metric with a separate badge.

### "Why no SaaS submission API?"

Hosted submission is a v2 ask if there's demand. v1 = PR-based submissions, which (a) gives reviewers full visibility into what's being added, (b) requires zero infrastructure on our side, (c) makes the verification chain auditable.

### "Why no telemetry?"

We log nothing about who uses the harness. Submitters provide their own results + config; we verify by re-running. Privacy by absence.

---

## Practical use

### "How long does a full leaderboard run take? What does it cost?"

Depends on the bundle and model. As a rough order of magnitude on `claude-opus-4-7` against the full 70-task primary panel × 5 canonical seeds = 350 attempts:

- **Cost:** depends heavily on bundle size (skill content inflates input tokens). The no-skills baseline is a useful floor.
- **Latency:** the harness runs up to 4 tasks in parallel by default (`--parallelism`). Sandbox setup adds ~1 second per attempt.

Use `agenteval dry-run` to see the plan + a cost estimate before committing.

### "Can I evaluate on a subset?"

Yes — `agenteval eval --tasks <subset-dir>`. Subset evaluations are exploratory only; they cannot be promoted to leaderboard entries because the task-set hash differs from the canonical `skill-specific-v1`.

### "Can I run this on Windows?"

Yes, but Docker Desktop on Windows is materially slower than on Linux. The harness emits a warning above 20 tasks. For full runs, use a Linux VPS via `agenteval eval --remote <ssh-host>` (Phase 3 §6.7 feature; see [`docs/remote-runner.md`](remote-runner.md)).

### "Does the sandbox stop a malicious skill?"

We defend against **accidental** side effects, not deliberate sandbox escape. The container has `--network=none`, `--cap-drop=ALL`, `no-new-privileges`, a non-root user, no host filesystem mount outside the task workdir, and resource limits. A determined adversary with a deliberately malicious skill could still escape Docker via kernel exploits. If this becomes a real problem, we'll move to gVisor or Firecracker.

---

## Workshop / academic

### "Is there a paper?"

A workshop submission is planned within ~30 days of public launch. The methodology doc [`docs/methodology.md`](methodology.md) is the paper's backbone; the adversarial doc [`docs/adversarial.md`](adversarial.md) is the paper's experimental-defenses section.

### "Can I cite agenteval?"

When the workshop paper drops, please cite that. Until then: the GitHub repo + the methodology doc, with a date.

### "I want to add a task / metric / runner. Where do I start?"

[`docs/good-first-issues.md`](good-first-issues.md) lists 10 starter tickets. The harder constraints are in [`DESIGN.md`](../DESIGN.md): the task schema and metric registry are versioned and locked; additions go through a new task-set version or a new ADR.
