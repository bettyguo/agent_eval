# Leaderboard frontend design

> Phase 1 §4.6 deliverable. Methodology context in [`methodology.md`](methodology.md) §9.

## 1. Goals

- **Honest by construction.** Two clearly-separated panels — primary (citable) and secondary (informative-but-contaminated). No combined ranking.
- **Sortable, not ranked.** Every column is sortable; no scalar "agenteval score" is published.
- **Verification status visible.** Every row carries a `verified` / `pending` / `partial` / `failed` badge.
- **Static + edge.** No backend. Vercel edge cache. Refresh on `main` branch update.
- **No tracking.** No login. No telemetry. Privacy by absence.

## 2. Tech stack

- Next.js 14 (App Router).
- Tailwind CSS for layout; minimal custom CSS.
- Static export (`next export`); deployed to Vercel.
- Data: a single static JSON snapshot in `frontend/public/data/leaderboard.json`, produced by `agenteval leaderboard-export` from the DuckDB store (`src/agenteval/leaderboard_export.py`).
- No client-side analytics; no third-party scripts.

## 3. Page structure

### `/` — landing

Hero block: a clean screenshot/animation of the primary leaderboard table. One-line value prop: *"The first reproducible benchmark for Claude Code Skills."* Two CTA buttons: **Run on your skills** (→ `/docs/quickstart`) and **Submit a result** (→ `/docs/submitting`).

Below the hero: a 30-second TL;DR + the latest 5 verified entries from the primary panel.

### `/leaderboard` — the main view

A two-panel layout:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PRIMARY PANEL — skill-specific-v1 + tau-bench-v1                          │
│                                                                          │
│ Sortable table. Columns:                                                 │
│   Skill bundle | Model | pass@1 | pass@5 | pass^5 | cost  | latency      │
│                                                                          │
│ Plus flag badges to the right of each row: high-variance, talkative,     │
│ tool-storm, pricing-stale, model-drift, borderline-stability,            │
│ holdout-divergence, passive.                                             │
│                                                                          │
│ Plus a "verified" badge: green tick / amber pending / red failed.        │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ SECONDARY PANEL — swe-bench-lite-v1  ⚠ Informative but contaminated      │
│                                                                          │
│ "Contaminated benchmark — delta may be confounded by skill ×             │
│  memorization interaction; not citable as a skill-effect claim."         │
│                                                                          │
│ Same table structure as primary. Visually de-emphasized:                 │
│   - muted background colour                                              │
│   - section heading carries an info icon with hover-card                 │
│   - collapsed by default; click "Show secondary panel" to expand         │
└──────────────────────────────────────────────────────────────────────────┘
```

Filter bar above each panel: by model, by runner, by category (`tdd-enforcement`, `code-review`, …). Filters apply within the panel only.

Sort header on every column. Default sort: primary panel by `pass@1` descending; secondary panel by `pass@1` descending. No "overall" or "agenteval-score" column.

### `/leaderboard/pareto` — Pareto plot view

Scatter plot:
- X-axis: `cost_usd` median per task.
- Y-axis: `pass@1`.
- Each point = one leaderboard entry.
- Pareto frontier highlighted in colour.
- Hover: skill name, model, exact values, flag badges.
- Filter dropdowns: panel, model, runner, category.

Plot library: `Plot` (Observable Plot) for static SVG; no client interactivity beyond hover. Plot rendered server-side via `@observablehq/plot` SSR; the static export ships the SVG.

### `/entry/[hash]` — entry detail

For a given `entry_hash`:

- Skill bundle header: name, snapshot SHA, upstream URL, license summary per skill, submitted-at.
- Task-set header: name, version, hash, panel.
- Runner header: provider, model, `model_response_fingerprint` (with `model-drift` warning if applicable), temperature, seed list.
- Pricing header: `pricing.yaml` `last_audited` date, SHA.
- Metrics block: full table with per-category breakdowns + bootstrapped CIs.
- Flags block: each flag with one-paragraph explanation linking to `docs/metrics.md`.
- Verification block: status, two-VM agreement matrix, link to the JSON report.
- Per-task drill-down: one row per task, click expands to per-seed pass/fail + trajectory summary.
- Raw JSON link + download.

### `/docs/methodology` — embeds `docs/methodology.md`

Rendered Markdown; full document searchable in-page. Section anchor links work.

### `/docs/submitting` — submission instructions

PR-based: fork the repo, run `agenteval eval` locally, run `agenteval submit`, commit the resulting JSON under `frontend/data/submissions/`, open a PR. CI re-verifies (two-VM) and approves automatically if verification passes.

### `/docs/opt-outs` — opt-out registry

A short page listing any skill authors who have requested removal, with a brief, neutral note: *"At the author's request, `<skill>` is not displayed on the leaderboard."*

## 4. Wireframe — primary panel table row

```
┌───────────────────────┬─────────────────┬──────┬──────┬──────┬─────────┬─────────┬──────────────────────┐
│ mattpocock/skills@abc │ claude-opus-4-7 │ 0.42 │ 0.71 │ 0.31 │  $0.18  │  43 s   │ [✓ verified]         │
│                       │                 │ ±0.06│ ±0.05│ ±0.07│ ±$0.02  │ ±5s     │ [⚠ high-variance]    │
└───────────────────────┴─────────────────┴──────┴──────┴──────┴─────────┴─────────┴──────────────────────┘
```

- First line: point estimate.
- Second line: 95% CI half-width.
- Right-cell stack of badges: verification + flags.

Click anywhere on a row → entry detail page.

## 5. Data pipeline

```
DuckDB results store
    ↓ src/agenteval/leaderboard_export.py
frontend/public/data/leaderboard.json   (versioned, schema-validated)
    ↓ Next.js static export
Vercel edge cache
```

The export script is deterministic given the DuckDB contents and the export schema version. A schema change requires a frontend deploy in lockstep.

## 6. Accessibility

- All tables are real `<table>` elements with `scope` attributes.
- Sortable columns have ARIA `aria-sort` attributes.
- Flag badges have `title` and `aria-label` attributes that explain the flag.
- Pareto plot has a sibling `<table>` rendering the same data for screen-readers.

## 7. Performance budget

- TTFB on Vercel edge: <200 ms (per master prompt §8 DoD).
- LCP: <1.5 s on a 4G connection.
- Total page weight (HTML + CSS + JS + JSON): <300 KB for `/` and `/leaderboard`.
- No client-side JS framework beyond what Next.js ships; no client-side data fetching (the JSON is inlined or fetched as a single static asset).

## 8. Implementation references

- Code: `frontend/app/` (App Router pages), `frontend/components/` (table, pareto, badges), `frontend/data/` (build-time data fetch).
- Phase 2 M6 implements this; deployed under a subdomain like `leaderboard.agenteval.dev` (placeholder; domain not yet registered).
- Phase 3 §6.1 produces the launch-ready screenshot of the primary panel.
