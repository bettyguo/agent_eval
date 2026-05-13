"""Cost metric + pricing.yaml loader (docs/metrics.md §1.2, ADR-0013)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from agenteval.errors import AgentevalError

DEFAULT_PRICING_PATH = Path(__file__).resolve().parents[3] / "pricing.yaml"
STALE_THRESHOLD_DAYS = 30


@dataclass(frozen=True)
class PricingTable:
    """Per-(provider, model) token prices in USD per million tokens."""

    last_audited: date
    prices: dict[tuple[str, str], dict[str, float]]
    yaml_hash: str

    def lookup(self, provider: str, model: str) -> dict[str, float]:
        key = (provider.lower(), model.lower())
        if key not in self.prices:
            raise AgentevalError(
                f"no pricing entry for provider={provider!r}, model={model!r}",
                provider=provider,
                model=model,
            )
        return self.prices[key]

    def is_stale(self, *, on: date | None = None) -> bool:
        as_of = on or datetime.now(timezone.utc).date()
        return (as_of - self.last_audited).days > STALE_THRESHOLD_DAYS


def load_pricing(path: str | Path | None = None) -> PricingTable:
    p = Path(path) if path is not None else DEFAULT_PRICING_PATH
    if not p.exists():
        raise AgentevalError(f"pricing.yaml not found: {p}", path=str(p))
    raw_bytes = p.read_bytes()
    yaml_hash = hashlib.sha256(raw_bytes).hexdigest()
    doc = yaml.safe_load(raw_bytes.decode("utf-8")) or {}

    last_audited_raw = doc.get("last_audited")
    if not last_audited_raw:
        raise AgentevalError(
            "pricing.yaml missing top-level `last_audited: YYYY-MM-DD`",
            path=str(p),
        )
    if isinstance(last_audited_raw, str):
        last_audited = date.fromisoformat(last_audited_raw)
    elif isinstance(last_audited_raw, date):
        last_audited = last_audited_raw
    else:
        raise AgentevalError(
            f"pricing.yaml last_audited must be a date, got {type(last_audited_raw).__name__}",
            path=str(p),
        )

    providers = doc.get("providers") or {}
    prices: dict[tuple[str, str], dict[str, float]] = {}
    for provider, models in providers.items():
        for model, entry in (models or {}).items():
            prices[(provider.lower(), model.lower())] = {
                "input_per_mtok": float(entry["input_per_mtok"]),
                "output_per_mtok": float(entry["output_per_mtok"]),
            }

    return PricingTable(
        last_audited=last_audited, prices=prices, yaml_hash=yaml_hash
    )


def compute_cost_per_attempt(
    *,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    pricing: PricingTable,
) -> float:
    rates = pricing.lookup(provider, model)
    return (
        tokens_in * rates["input_per_mtok"] / 1_000_000.0
        + tokens_out * rates["output_per_mtok"] / 1_000_000.0
    )
