# agenteval frontend

Static Next.js leaderboard. Deployed to Vercel; no backend, no tracking.

## Local dev

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Build the static export

```bash
npm run build   # writes ./out/
```

## Updating the data

The leaderboard reads `public/data/leaderboard.json`. Regenerate from the
project's submissions directory with:

```bash
# from the repo root:
python -c "from agenteval.leaderboard_export import export_leaderboard; \
  export_leaderboard('frontend/data/submissions', 'frontend/public/data/leaderboard.json')"
```

## Submitting an entry

1. Run `agenteval eval` to produce a leaderboard-eligible JSON.
2. Run `agenteval submit ./result.json` to canonicalize it (writes `result.entry.json`).
3. Open a PR adding the entry file under `frontend/data/submissions/<short-name>.entry.json`.
4. CI re-verifies and merges if the two-VM verifier agrees.
