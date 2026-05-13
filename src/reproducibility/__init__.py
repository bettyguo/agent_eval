"""Content-addressing for agenteval entries (DESIGN.md §5, ADR-0008/0013/0015)."""

from agenteval.reproducibility.hash import (
    compute_entry_hash,
    hash_normalized_directory,
)

__all__ = ["compute_entry_hash", "hash_normalized_directory"]
