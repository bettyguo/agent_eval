"""Static JSON export for the leaderboard frontend.

Reads leaderboard-entry JSONs from a directory and produces a single
`leaderboard.json` consumed by the Next.js frontend (M6). DuckDB-backed
storage lands in a later milestone; M6 ships the simpler PR-driven flow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LeaderboardExport:
    """The shape consumed by `frontend/app/leaderboard/page.tsx`."""

    generated_at: str
    schema_version: str
    primary: list[dict[str, Any]]
    secondary: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "primary": self.primary,
            "secondary": self.secondary,
        }


def export_leaderboard(
    submissions_dir: str | Path,
    out_path: str | Path,
) -> LeaderboardExport:
    """Aggregate every `*.entry.json` under `submissions_dir` into the export."""
    submissions = Path(submissions_dir)
    entries: list[dict[str, Any]] = []
    if submissions.exists():
        for path in sorted(submissions.glob("**/*.entry.json")):
            try:
                entries.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue

    primary = [e for e in entries if e.get("task_set", {}).get("panel") == "primary"]
    secondary = [e for e in entries if e.get("task_set", {}).get("panel") == "secondary"]

    # Project each into the row shape the frontend wants.
    primary_rows = [_row(e) for e in primary]
    secondary_rows = [_row(e) for e in secondary]

    export = LeaderboardExport(
        generated_at=datetime.now(UTC).isoformat(),
        schema_version="1",
        primary=primary_rows,
        secondary=secondary_rows,
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export.to_dict(), indent=2), encoding="utf-8")
    return export


def _row(entry: dict[str, Any]) -> dict[str, Any]:
    metrics = entry.get("metrics", {}) or {}
    runner = entry.get("runner", {}) or {}
    pricing = entry.get("pricing", {}) or {}
    flags = [f.get("name") for f in entry.get("flags", []) or []]
    return {
        "entry_hash": entry.get("entry_hash"),
        "bundle_hash": entry.get("bundle", {}).get("hash"),
        "task_set_name": entry.get("task_set", {}).get("name"),
        "task_set_hash": entry.get("task_set", {}).get("hash"),
        "panel": entry.get("task_set", {}).get("panel"),
        "model": runner.get("model"),
        "provider": runner.get("provider"),
        "pass_at_1": _point(metrics.get("pass@1")),
        "pass_at_5": _point(metrics.get("pass@5")),
        "pass_caret_5": _point(metrics.get("pass^5")),
        "cost_usd_median": metrics.get("cost_usd", {}).get("median"),
        "latency_s_p50": metrics.get("latency_s", {}).get("p50"),
        "timeout_rate": _point(metrics.get("timeout_rate")),
        "flags": flags,
        "verified": entry.get("verification", {}).get("verified", False),
        "pricing_last_audited": pricing.get("last_audited"),
    }


def _point(metric: Any) -> Any:
    if isinstance(metric, dict):
        return metric.get("point")
    return metric
