# Leaderboard frontend

Methodology context in [methodology.md](methodology.md) §9.

## Goals

- Two clearly-separated panels: primary (citable) and secondary
  (informative-but-contaminated). No combined ranking.
- Sortable, not ranked. No "agenteval score" published.
- Every row carries a verification badge (`verified` / `pending` /
  `partial` / `failed`).
- Static + edge. No backend; Vercel edge cache. Refreshes on `main`.
- No tracking, no login, no telemetry.

## Stack

- Next.js 14 (App Router), Tailwind CSS, static export via `next export`.
- Data: a single static JSON in `frontend/public/data/leaderboard.json`,
  produced by `src/agenteval/leaderboard_export.py`.
- No client-side analytics, no third-party scripts.

## Pages

### `/` — landing

Hero block with a leaderboard screenshot, a one-line value prop, and two
CTAs: "Run on your skills" and "Submit a result". Below: a short TL;DR and
the latest verified primary-panel entries.

### `/leaderboard` — main view

Two-panel layout.

```
┌─ PRIMARY: skill-specific-v1 + tau-bench-v1 ────────────────────────┐
│ Sortable table:                                                    │
│   Skill bundle | Model | pass@1 | pass@5 | pass^5 | cost | latency │
│ Plus flag badges per row + verification badge.                     │
└────────────────────────────────────────────────────────────────────┘

┌─ SECONDARY: swe-bench-lite-v1  (Informative but contaminated) ─────┐
│ Same columns; visually de-emphasised; collapsed by default.        │
│ Banner: "Contaminated benchmark; not citable as a skill-effect     │
│ claim."                                                            │
└────────────────────────────────────────────────────────────────────┘
```

Filter bar per panel (model, runner, category). Filters scope to their
panel. Every column header sorts. Default sort: pass@1 descending.

### `/leaderboard/pareto`

Scatter plot of `cost_usd` (x) vs `pass@1` (y); Pareto frontier
highlighted. Hover shows skill name, model, values, flags. Filters mirror
the table view. Plot rendered server-side as SVG (Observable Plot); no
client interactivity beyond hover.

### `/entry/[hash]`

Per-entry detail page. Bundle, task-set, runner, pricing headers; metrics
table with per-category breakdowns and CIs; flag block linking to
metrics.md; verification block with the two-VM agreement matrix; per-task
drill-down with per-seed pass/fail; raw JSON link.

### `/docs/methodology`

Renders [methodology.md](methodology.md); section anchors work.

### `/docs/submitting`

Submission instructions. Fork, run `agenteval eval`, run
`agenteval submit`, commit the result under
`frontend/data/submissions/`, open a PR. CI re-verifies; merge after the
two-VM verifier agrees.

### `/docs/opt-outs`

Short page listing any skill authors who have requested removal, neutral
phrasing per request.

## Wireframe — primary-panel row

```
┌──────────────────────┬─────────────────┬──────┬──────┬──────┬─────────┬─────────┬─────────────────┐
│ mattpocock/skills@…  │ claude-opus-4-7 │ 0.42 │ 0.71 │ 0.31 │  $0.18  │  43 s   │ [verified]      │
│                      │                 │ ±0.06│ ±0.05│ ±0.07│  ±$0.02 │  ±5s    │ [high-variance] │
└──────────────────────┴─────────────────┴──────┴──────┴──────┴─────────┴─────────┴─────────────────┘
```

Top line is the point estimate; bottom line the 95% CI half-width. Right
cell stacks badges. Clicking a row routes to the entry detail page.

## Data pipeline

```
DuckDB results store
    ↓ src/agenteval/leaderboard_export.py
frontend/public/data/leaderboard.json
    ↓ Next.js static export
Vercel edge cache
```

The export is deterministic given the DuckDB contents and export schema
version. Schema changes require a frontend deploy in lockstep.

## Accessibility

- Real `<table>` elements with `scope` attributes.
- `aria-sort` on sortable columns.
- `title` + `aria-label` on flag badges.
- The Pareto plot has a sibling `<table>` rendering the same data for
  screen readers.

## Performance budget

- TTFB on Vercel edge: <200 ms.
- LCP: <1.5 s on a 4G connection.
- Total page weight for `/` and `/leaderboard`: <300 KB.
- No client-side data fetching; the JSON is inlined or loaded as a single
  static asset.

## Implementation

- `frontend/app/` (App Router pages), `frontend/components/`,
  `frontend/data/`.
- Deployed under a subdomain (e.g. `leaderboard.agenteval.dev` — domain
  placeholder; not yet registered).
