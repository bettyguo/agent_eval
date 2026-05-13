# Good first issues

Ten well-scoped contribution opportunities. Each is bounded, has a clear "definition of done," and doesn't require deep methodology debate. Numbered for cross-reference from `.github/workflows/ci.yml` and elsewhere.

> **Format.** Title — *scope, expected effort, files involved, DoD.*
>
> **Note.** Don't create real GitHub issues from these yet — the project may want to reword for the public repo. These are drafts for the human maintainer to file at launch.

---

## 1. ~~Burn down `mypy --strict` debt~~ **DONE in Phase 3 polish**

`mypy src` now passes with zero errors. CI runs it as a blocking step (`.github/workflows/ci.yml`). Struck-through here to show the issue list is maintained and to leave a paper trail for first-time contributors comparing this doc against the master prompt's §6.5 checklist.

---

## 2. ~~Pre-built `agenteval-sandbox:base` image published to GHCR~~ **WORKFLOW DRAFTED**

`.github/workflows/publish-sandbox-image.yml` ships the build-+-push step on changes to `sandbox/Dockerfile.base` or `sandbox/image.lock`. The workflow pushes two tags (the git SHA and `:base`) under `ghcr.io/<owner>/agenteval-sandbox`. **Remaining work for a contributor:** wire the DockerSandbox to fall back to pulling from GHCR if the local image is missing.

---

## 3. `agenteval` Python package on PyPI

**Effort:** ~2 hr.
**Why:** `pip install agenteval` is in the quick-start; making it actually work needs a publish workflow.
**Files:** `.github/workflows/publish-pypi.yml` (new), `pyproject.toml` (version-bump policy).
**DoD:** Tagging `v0.1.0` on `main` publishes to PyPI via trusted-publisher OIDC (no API tokens). The published wheel works in a clean env: `pip install agenteval && agenteval version`.

---

## 4. Implement `agenteval leaderboard` (local view)

**Effort:** ~2 hr.
**Why:** The CLI surface in DESIGN.md §1.3 includes `agenteval leaderboard` for local rendering; it's not implemented yet.
**Files:** `src/agenteval/cli.py`.
**DoD:** `agenteval leaderboard` reads `frontend/public/data/leaderboard.json` and renders both panels as Rich tables in the terminal, including flag badges. Pass `--panel primary|secondary|all` to filter.

---

## 5. Pareto-frontier highlight in the frontend leaderboard

**Effort:** ~3 hr.
**Why:** `docs/leaderboard.md` specs a Pareto plot of success × cost; the frontend currently has only the sortable table.
**Files:** `frontend/app/leaderboard/pareto/page.tsx` (new), `frontend/components/ParetoPlot.tsx` (new).
**DoD:** A separate `/leaderboard/pareto` route renders a static SVG scatter with the Pareto frontier highlighted. Per-point hover shows the metrics tooltip. Server-side rendered (no client JS dependency on a charting library beyond what Next.js ships).

---

## 6. Add a small task-set `skill-specific-mini-v1` for fast iteration

**Effort:** ~1 hr.
**Why:** 20 tasks × 5 seeds × ~30 s per attempt makes the full primary panel ~50 minutes wall-time. A "mini" task set (3–5 tasks) lets contributors iterate on the harness in seconds.
**Files:** `tasks/skill-specific-mini-v1/` (new), `src/agenteval/tasks/registry.py` (add to `BUILTIN_TASK_SETS`).
**DoD:** `agenteval dry-run --tasks skill-specific-mini-v1 --skills none` plans 5 tasks (one per category, cheapest each), and a real run finishes in under 5 minutes against `claude-haiku-4-5-20251001`.

---

## 7. Document the JS-variant sandbox image for `style-adherence-04`

**Effort:** ~1 hr.
**Why:** `tasks/skill-specific-v1/style-adherence-04.yaml` needs TypeScript + ESLint + Jest. The base image only has Python. Either bake them into the base image (size cost) or ship a separate `agenteval-sandbox:js` and gate the task on `network: false` + the right image.
**Files:** `sandbox/Dockerfile.js` (new), `docs/sandbox.md` (update).
**DoD:** `docker build -f sandbox/Dockerfile.js -t agenteval-sandbox:js sandbox/` succeeds; the harness can be told to use the JS image for that task (e.g., via a task-spec `image` field — would require a small schema bump and a new ADR).

---

## 8. Add a `pass^1` (reliability-of-single-shot) report

**Effort:** ~1 hr.
**Why:** `pass^1` = fraction of tasks where seed 1 passes. Trivially derivable from existing data but not currently surfaced; useful for skills that promise "first-attempt correctness."
**Files:** `src/agenteval/metrics/pass_at_k.py`, `src/agenteval/metrics/summary.py`, `docs/metrics.md`.
**DoD:** `pass^1` appears in `MetricSummary` and on the frontend table. Tests cover the trivial-equivalence case (`pass@1 == pass^1` always, given canonical seeds).

---

## 9. Pareto-frontier export as CSV alongside the JSON leaderboard

**Effort:** ~1 hr.
**Why:** Researchers will want to load the leaderboard data into a notebook. JSON is fine but a flattened CSV is friendlier.
**Files:** `src/agenteval/leaderboard_export.py`.
**DoD:** `export_leaderboard` also writes `frontend/public/data/leaderboard.csv` with one row per entry, columns flattened (pass@1, pass@1_lo, pass@1_hi, …). Both files are produced atomically.

---

## 10. Add `agenteval pricing audit` to bump `last_audited` after a manual price check

**Effort:** ~1 hr.
**Why:** `pricing-stale` flag triggers at >30 days. Users / maintainers need an easy way to refresh `last_audited` after confirming the YAML against current provider pricing.
**Files:** `src/agenteval/cli.py`.
**DoD:** `agenteval pricing audit --confirm` updates `pricing.yaml.last_audited` to today's date and writes a one-line attestation file `pricing.audited.log` recording (date, user, git SHA, pricing.yaml SHA before/after). Without `--confirm` it dry-runs (shows what would change).

---

## Stretch (for later, not v1.0)

- Replace LocalSubprocessSandbox with [bubblewrap](https://github.com/containers/bubblewrap)-based isolation on Linux when Docker is unavailable.
- Live demo: run a tiny task subset on user-supplied skill bundles in the browser via WebContainers.
- `agenteval bisect`: given a no-skills baseline + a skill bundle, automatically ablate one SKILL.md at a time and report which contributes most.
