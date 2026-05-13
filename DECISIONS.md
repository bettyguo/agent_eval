# DECISIONS — Architecture Decision Record

> Append-only log of methodological and architectural decisions. Each entry: ID, date, status, context, decision, consequences. Never reverse a decision in place — supersede with a new entry pointing back.

---

## ADR-0001 — Project name: `agenteval`

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Master prompt uses `agenteval` (aka `skillbench`). Need one canonical name for repo, PyPI package, CLI command, leaderboard subdomain.
- **Decision:** Canonical name is **`agenteval`**. `skillbench` is a tagline/alias only; not used in code, package, or URLs. Rationale: `agenteval` is broader and more enduring; if v2 expands beyond skills, the name still fits.
- **Consequences:** PyPI: `agenteval`. CLI: `agenteval`. Leaderboard subdomain: `leaderboard.agenteval.dev` (placeholder; domain not yet registered).

---

## ADR-0002 — License: Apache 2.0

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** §1 master prompt mandates Apache 2.0 — more enterprise-friendly than MIT for a benchmark.
- **Decision:** Apache 2.0 for the harness, tasks, frontend. Skill bundle snapshots retain their upstream licenses; we record each in the bundle metadata.
- **Consequences:** `LICENSE` is Apache 2.0. Contributions imply Apache-2.0 grant via standard inbound=outbound (no separate CLA in v1).

---

## ADR-0003 — Python 3.11+ for the harness

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Master prompt §1 mandates Python 3.11+.
- **Decision:** Minimum supported Python = 3.11. Tested on 3.11 and 3.12. Type-checked with mypy/pyright in strict mode.
- **Consequences:** `pyproject.toml` `requires-python = ">=3.11"`. CI matrix: 3.11, 3.12.

---

## ADR-0004 — Multi-provider runner support from day one

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Skills are an Anthropic-specific concept, but cross-provider numbers are what give the benchmark teeth (e.g., "skill X helps Claude but not GPT, ergo it's Claude-specific tuning"). Master prompt §1 mandates Anthropic + OpenAI + Google.
- **Decision:** Three runners: `anthropic`, `openai`, `google`. For providers without native skills support, we document an emulation protocol (skill markdown injected into the system prompt) and clearly label results as "emulated skills" on the leaderboard.
- **Consequences:** §M3 (12 hr) is the cross-provider milestone. Emulation methodology needs its own §in `docs/methodology.md`.

---

## ADR-0005 — Docker sandbox; no host filesystem; network off by default

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Skills can include executable code that the agent will run. Running on the host is unsafe. Network access leaks task answers (HumanEval contamination via web search is a known failure mode).
- **Decision:** Every task runs in a fresh Docker container. 1 CPU, 2 GB RAM, 5-min wall-time default, network disabled by default (opt-in per task), no host filesystem mount. Threat model: defend against accidental side effects, NOT deliberate sandbox escape (documented in `docs/methodology.md`).
- **Consequences:** macOS Docker is slow — `docs/methodology.md` will recommend a Linux VPS for full runs. Container image SHAs are pinned (§Phase 3.6 reproducibility hardening).

---

## ADR-0006 — No LLM-as-judge in v1

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** LLM-as-judge would let us evaluate many more task types cheaply, but it introduces non-deterministic grading and a confound (the judge model's biases vs. the agent model's outputs).
- **Decision:** v1 = deterministic graders only. Every task's grader is a Python script returning `{"passed": bool, "details": {...}}`. LLM-as-judge deferred to v2 with explicit "experimental" flag.
- **Consequences:** Task design is constrained — we can only grade what we can write a decision procedure for. This is intentional. Documented in `docs/methodology.md` and `docs/faq.md`.

---

## ADR-0007 — Storage: DuckDB for results; static JSON export for leaderboard

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Per master prompt §1. DuckDB is fast for analytical queries on result data; static JSON keeps the leaderboard cacheable on Vercel edge with zero server cost.
- **Decision:** Runs write to DuckDB. `leaderboard_export.py` snapshots DuckDB to static JSON consumed by the Next.js frontend.
- **Consequences:** No live submission API in v1 — submissions are PRs that drop a result JSON into `frontend/data/`. v2 may add a hosted submission API if demand exists.

---

## ADR-0008 — Reproducibility: content-addressed hashing; verifier re-runs from scratch

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** A leaderboard whose entries can't be reproduced has failed the *one* job a benchmark has. Submissions must be re-verifiable.
- **Decision:** Every leaderboard entry is hashed as `sha256(skill_bundle_hash || task_set_hash || model || temperature || seed_list)`. Temperature MUST be 0.0 for leaderboard entries. Verifier re-runs from scratch in a clean VM and compares structured features (pass/fail per task per seed). Bit-exact trajectory comparison is **not** required (acknowledging partial LLM determinism); any entry that fails re-verification is flagged "failed" and not listed.
- **Consequences:** §M5 milestone implements this. CI re-verifies on submission. Per anti-pattern #10, every entry is re-verified in TWO different VMs.

---

## ADR-0009 — v1 task budget: 20 hand-curated + 30 SWE-bench-Lite subset + 50 TAU-Bench subset = 100 tasks

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Master prompt anti-pattern #6: "Don't include too many tasks." 100 is the v1 ceiling.
- **Decision:** v1 task set = 20 (skill-specific) + 30 (SWE-bench-Lite well-behaved subset) + 50 (TAU-Bench subset) = 100 tasks.
- **Consequences:** Phase 2 M4 (12 hr) implements adapters for the 30 + 50; M1 implements first 5 of the 20.

---

## ADR-0011 — SWE-bench-Lite in v1 despite known contamination; migrate to Pro + Live in v2

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** During Phase 0 §3.2 contamination audit, surfaced OpenAI's December 2025 announcement that they no longer report SWE-bench Verified scores due to demonstrated contamination across all major frontier models (GPT-5.2, Claude Opus 4.5, Gemini 3 Flash can reproduce verbatim gold patches). SWE-bench-Lite is a subset of the same source distribution and contaminated at least as much. Cleaner alternatives — SWE-bench Pro (Scale Labs) and SWE-bench-Live (monthly rotation) — exist as of 2026.
- **Decision:** Keep SWE-bench-Lite in v1 task set with explicit caveats. Justification: our reported axis is *skill-induced delta* over a fixed model; contamination is held constant across with-skill and without-skill conditions, so the delta remains interpretable. Mitigations:
  1. Every SWE-bench-Lite leaderboard row gets a banner: *"Contaminated benchmark — interpret as skill-induced delta only, not as a capability score."*
  2. Per-task contamination flags from upstream literature published in `tasks/swe-bench-lite-v1/CONTAMINATION.md`.
  3. Absolute SWE-bench-Lite scores must NOT be cited as model-capability ranking, in our docs, in launch posts, or in the workshop paper.
  4. **Commit to migrating the SWE-bench task family to SWE-bench Pro + SWE-bench-Live in v2.** v2 milestone exit criterion: deprecate `swe-bench-lite-v1` once `swe-bench-pro-v1` and `swe-bench-live-v1` are stable.
- **Consequences:** docs/methodology.md §4 spells this out. `tasks/swe-bench-lite-v1/CONTAMINATION.md` to be authored during Phase 2 M4. Launch posts must include the caveat verbatim.

---

## ADR-0012 — Report pass^k (TAU-Bench-style reliability) alongside pass@k

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** During Phase 0 §3.1 methodology recon, observed that TAU-Bench (Yao et al. 2024) introduced pass^k — fraction of tasks where the agent succeeds on **all** k independent trials — explicitly as a reliability metric distinct from pass@k (capability). For skill evaluation this is doubly important: a skill that improves pass@1 by 5 points but tanks pass^5 is buying success through nondeterminism, not capability.
- **Decision:** Report pass^5 as a first-class metric alongside pass@1 and pass@5. Use it as the basis of the `high-variance` adversarial flag (flagged if pass@5 ≥ 2 × pass^5, indicating nondeterminism-driven gains).
- **Consequences:** docs/metrics.md must include pass^k spec. The metric registry in `src/agenteval/metrics/` adds a `pass_caret_at_k.py` module in Phase 2 M3.

---

## ADR-0013 — pricing.yaml is part of the entry hash; stale-pricing flag at 30 days

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Anti-pattern #8 of the master prompt: "Don't forget pricing changes." Token prices for the three providers shift frequently in 2026 (model-tier reshuffles, discount tiers, Batch-API rebates). If `pricing.yaml` is updated silently and old entries' cost columns are recomputed, the leaderboard becomes non-reproducible.
- **Decision:** Include `sha256(pricing.yaml)` as a component of `entry_hash`. Any pricing.yaml change yields a new entry hash; old entries are NOT silently recomputed — they carry the pricing.yaml SHA they were submitted under. Additionally, raise a `pricing-stale` adversarial flag on submissions whose `pricing.yaml` is more than 30 days old at submission time.
- **Consequences:** docs/reproducibility.md and docs/methodology.md §5.2 reflect this. `pricing.yaml` carries a top-of-file `last_audited: YYYY-MM-DD` field.

---

## ADR-0014 — Demote SWE-bench-Lite to a secondary panel; primary leaderboard = skill-specific + TAU-Bench (supersedes ADR-0011)

- **Date:** 2026-05-13
- **Status:** Accepted (supersedes ADR-0011)
- **Context:** ADR-0011 said "keep SWE-bench-Lite in v1 with banner caveats because skill-induced delta is interpretable even on a contaminated benchmark." Adversarial self-review found two problems with that argument:
  1. **Contamination is not skill-invariant.** Skills can name files, repos, or patterns in ways that disproportionately activate memorized SWE-bench solutions vs. the no-skill baseline. The delta then mixes (skill effect) with (skill × memorization interaction) — uninterpretable.
  2. **Contamination shrinks variance.** Memorized solutions are deterministically reproduced; pass/fail flips are rare. This artificially tightens CIs and inflates apparent statistical significance of small deltas.
- **Decision:** Restructure the leaderboard into two panels:
  1. **Primary leaderboard.** Uses `skill-specific-v1` (20 tasks, uncontaminated by construction) + `tau-bench-v1` subset (50 tasks, low contamination concern per §4.4 of methodology.md). All headline claims, all rank-sortable metrics, all Pareto plots use this panel.
  2. **Secondary panel: "Informative but contaminated."** Renders SWE-bench-Lite results in a separate, clearly-labeled section. Shown for completeness, never used as headline numbers. Banner per entry: *"Contaminated benchmark — delta may be confounded by skill × memorization interaction; not citable as a skill-effect claim."*
- **Consequences:**
  - methodology.md §3.1 and §4 updated to reflect the panel split.
  - Workshop paper draft will report skill-specific + TAU-Bench as primary; SWE-bench-Lite as a sanity-check appendix only.
  - Phase 2 M4 still implements the SWE-bench-Lite adapter — but the adapter writes to the "secondary panel" data path, not the primary.
  - Migration to SWE-bench Pro + SWE-bench-Live in v2 remains committed (still helps both panels).

---

## ADR-0015 — Canonical seed list [1, 2, 3, 4, 5] for leaderboard entries (refines ADR-0008)

- **Date:** 2026-05-13
- **Status:** Accepted (refines ADR-0008 seed-list provision)
- **Context:** ADR-0008 said `seed_list` is part of the entry hash but did not constrain *which* seeds. This permits a cherry-picking attack: a submitter runs 100 seeds, picks the best 5, submits them; the verifier reproduces those exact 5 seeds and confirms — fraud not detected.
- **Decision:** Leaderboard entries (primary panel) MUST use exactly `seed_list = [1, 2, 3, 4, 5]`. Submissions with any other seed list are rejected at the API gate with an explicit error: *"Leaderboard entries require canonical seed list [1,2,3,4,5]. For exploratory runs, use `--exploratory` which produces a non-leaderboard result."* The verifier enforces this.
- **Consequences:**
  - `agenteval submit` validates seed list before producing a result JSON intended for the leaderboard.
  - `agenteval eval --exploratory --seeds N` is the escape hatch for users who want pass^k or capability sweeps with non-canonical seeds; results are tagged `leaderboard: false`.
  - Variability across seed choices is now studied via the `--exploratory` mode, kept distinct from leaderboard submission.
  - methodology.md §7.1 entry-hash spec updated; docs/reproducibility.md spec updated.

---

## ADR-0016 — Pin model response fingerprint; surface timeout-rate; normalized-baseline protocol per provider

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Three failure modes surfaced during Phase 0 review that the pre-mortem missed:
  1. **Silent model-version drift.** Provider may serve a different model fingerprint under the same API string week-to-week. An entry's `entry_hash` is identical but the underlying weights differ.
  2. **Timeout-rate masking.** A skill that hits the 5-min wall-time silently degrades to "failed task" without distinguishing capability failure from time-out exhaustion.
  3. **Asymmetric "no-skills baseline."** Providers differ in implicit system prompts and default reasoning behavior. A no-skill baseline on Anthropic is not the same control condition as a no-skill baseline on OpenAI. Comparisons across providers risk being apples-to-oranges.
- **Decision:**
  1. **Fingerprint snapshotting.** Every leaderboard entry records the provider-side response fingerprint where exposed (`system_fingerprint` for OpenAI; equivalent for Anthropic if exposed; documented "not available" for Google if unavailable). Fingerprint is shown in entry detail; mismatch across re-verifications is flagged `model-drift`.
  2. **Timeout-rate metric.** First-class column on the leaderboard: `timeout_rate` = fraction of (task, seed) pairs that hit wall-time without producing a final result. A high timeout-rate skill is visibly distinguished from a high-failure skill.
  3. **Normalized-baseline protocol.** For each provider, we define and publish a single "no-skills baseline" configuration (system prompt = empty or provider-default; reasoning settings = lowest tier; temperature = 0; canonical seeds). All cross-provider comparisons are *delta-from-baseline*, not absolute. The exact baselines live in `skills-baseline/no-skills/<provider>.yaml`. They are pinned and rotated with major API changes only (with a superseding entry hash).
- **Consequences:**
  - methodology.md §5 (metrics) adds `timeout_rate`. §6 (sandbox) adds fingerprint capture. §11 (limitations) adds the cross-provider asymmetry caveat.
  - docs/metrics.md adds `timeout_rate` to the flag/metric registry.
  - `skills-baseline/no-skills/` becomes a multi-file directory with per-provider baseline configs.


---

## ADR-0010 — Session bootstrapping protocol

- **Date:** 2026-05-13
- **Status:** Accepted
- **Context:** Multi-session project over ~8 weeks. State must survive between sessions without ambiguity.
- **Decision:** Every session begins by reading `STATUS.md` and `DECISIONS.md`. Every session ends by updating `STATUS.md` (snapshot + session log entry). New architectural decisions get a new ADR appended here; old ADRs are never edited in place, only superseded.
- **Consequences:** Codified in `STATUS.md` session-start checklist. Reflected in CLAUDE.md (when written).
