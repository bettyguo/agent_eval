# Reproducibility protocol

> Phase 1 §4.5 deliverable. Methodology context in [`methodology.md`](methodology.md) §7. ADRs 0008, 0013, 0015, 0016 govern the design.

## 1. Entry hash

```
entry_hash = sha256(
    skill_bundle_hash       # SHA256 of normalized tarball of .claude/skills/
    || task_set_hash        # SHA256 of normalized task-set tarball
    || model                # exact API model string (e.g., "claude-opus-4-7")
    || temperature          # MUST be 0.0 for leaderboard entries
    || seed_list            # MUST be [1,2,3,4,5] for primary-leaderboard entries (ADR-0015)
    || pricing_yaml_hash    # SHA256 of pricing.yaml used (ADR-0013)
)
```

Concatenation is canonical: each component is serialized to a fixed UTF-8 string with explicit delimiters; the `seed_list` is rendered as `"[1,2,3,4,5]"` (no spaces); `temperature` as a fixed-precision string `"0.000"`.

Stored alongside but **not hashed**:

- `model_response_fingerprint` — provider-side fingerprint at run time (ADR-0016). Used for `model-drift` detection.
- `submitted_at` — ISO 8601 timestamp.

## 2. Normalization (for the tarballs)

When computing `skill_bundle_hash` or `task_set_hash`:

1. Enumerate files in lexicographic order.
2. Reject symlinks (raise `BundleError`).
3. Strip trailing whitespace from text files (UTF-8 detected by content sniffing).
4. Set permissions to `0644` for files, `0755` for directories.
5. Zero timestamps in the tar header.
6. Tar with `--format=ustar`, no compression (avoid gzip's timestamp noise).
7. Hash the resulting byte sequence.

This is implemented in `src/agenteval/reproducibility/normalize.py` and tested against a corpus of intentionally-fragile inputs (whitespace permutations, mixed line endings, file permission noise).

## 3. Verifier

`agenteval verify ./result.json` performs an independent re-run:

1. Reconstruct the run config from the entry.
2. Pull the pinned sandbox image SHA; refuse if unavailable.
3. Execute every (task, seed) in a fresh sandbox.
4. Compare:

| Field | Comparison |
|---|---|
| per-task pass/fail per seed | **strict equality** |
| trajectory step count per (task, seed) | informational, not blocking |
| `tokens_in`, `tokens_out` | strict equality |
| `tool_calls` count | strict equality |
| `cost_usd` median, p95 | within ±5% tolerance |
| `latency_s` p50, p95 | within ±25% tolerance |
| `trajectory` text | **not compared** |
| `model_response_fingerprint` | logged; mismatch raises `model-drift` flag |

5. Emit a `VerificationReport` with the diff.

## 4. Two-VM rule

Per anti-pattern #10 of the master prompt: every primary-panel leaderboard entry is verified in **two different cloud zones** before being marked `verified: true`. The two verifiers must agree on the strict-equality fields. Disagreement raises `borderline-stability` on any flipping task and re-runs once; persistent disagreement on the same task is logged in the entry's verification report and the entry is marked `verified: partial`.

CI implementation (Phase 2 M5):
- Verifier-A: GitHub Actions runner.
- Verifier-B: Hetzner VPS via SSH.

## 5. Partial-determinism honesty

LLM determinism at T=0 is partial. Known sources of drift:

- **Provider model-version drift.** Same API string, different fingerprint week-to-week. Detected by `model_response_fingerprint`. Mitigation: `model-drift` flag.
- **Provider batch-composition numerics.** Floating-point summation order in attention layers can vary by batch. No mitigation possible from our side; documented.
- **Tokenizer or normalization drift.** Provider may update tokenizer or pre-processing; can produce a different output for the same input. Same provider-side mitigation gap.

Our protocol *tolerates* this on cost/latency, *refuses* it on pass/fail. A pass/fail flip between submission and re-verification produces the `borderline-stability` flag and is shown in the entry's verification report. We do not invalidate such entries — they're real signal about the task's boundary nature — but the flag warns readers.

## 6. The cherry-pick attack and its mitigation

Per ADR-0015. Suppose a submitter runs many seeds, picks the best 5, and submits. The verifier re-runs those exact 5 seeds and reproduces the result. Fraud not detected.

**Mitigation.** Primary-leaderboard entries MUST use `seed_list = [1, 2, 3, 4, 5]`. The API gate enforces this at `to_leaderboard_entry()`; the CLI's `submit` enforces it again; the verifier checks it on receipt.

Users wanting capability sweeps over many seeds use `agenteval eval --exploratory --seeds N`, which produces a result tagged `leaderboard: false`. Exploratory results are useful for skill authors tuning their work; they cannot be promoted to leaderboard entries.

## 7. Re-publishing under new pricing

When `pricing.yaml` is updated (ADR-0013):

1. The updated yaml has a new SHA → new `pricing_yaml_hash` → new `entry_hash`.
2. Old entries retain their original `pricing_yaml_hash`; their cost numbers stay frozen.
3. To re-publish under new pricing, the submitter re-runs `agenteval submit` with the new pricing.yaml; this produces a new entry. The old entry is not silently overwritten.
4. The leaderboard frontend shows the most-recent entry for each (bundle, task-set, model) tuple by default; older entries are accessible via the entry detail page.

## 8. Implementation references

- Code: `src/agenteval/reproducibility/__init__.py`, `normalize.py`, `verify.py`.
- Phase 2 M5 implements this; tests in `tests/test_reproducibility.py` include tampered-result detection, two-VM disagreement injection, and `pricing.yaml` change cycles.
