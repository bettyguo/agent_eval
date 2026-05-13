# Reproducibility

Methodology context in [methodology.md](methodology.md) §7.

## 1. Entry hash

```
entry_hash = sha256(
    skill_bundle_hash      # SHA256 of normalised tarball of .claude/skills/
    || task_set_hash       # SHA256 of normalised task-set tarball
    || model               # exact API model string
    || temperature         # must be 0.0 for leaderboard entries
    || seed_list           # must be [1,2,3,4,5] for primary-leaderboard entries
    || pricing_yaml_hash   # SHA256 of pricing.yaml used
)
```

Concatenation is canonical: each component is serialised to a fixed UTF-8
string with explicit delimiters; `seed_list` is rendered without spaces
(`"[1,2,3,4,5]"`); `temperature` as fixed precision (`"0.000"`).

Stored alongside but not hashed:

- `model_response_fingerprint`: provider-side fingerprint at run time
  (e.g. OpenAI's `system_fingerprint`). Used for `model-drift` detection.
- `sandbox_image_sha`: the Docker base-image digest. Mismatch on
  re-verification fires `sandbox-drift` rather than rejecting the entry.
- `submitted_at`: ISO 8601 timestamp.

## 2. Tarball normalisation

For `skill_bundle_hash` and `task_set_hash`:

1. Enumerate files in lexicographic order.
2. Reject symlinks (raise `SkillBundleError` / `TaskSetError`).
3. Strip trailing whitespace from text files (UTF-8 sniff).
4. Permissions normalised to 0644 for files, 0755 for directories.
5. Zero timestamps in the tar header.
6. `tar --format=ustar`, no compression.
7. SHA256 the resulting byte sequence.

Implementation in `src/agenteval/reproducibility/hash.py`; tests cover
whitespace permutations, mixed line endings, permission noise.

## 3. Verifier

`agenteval verify ./result.json` performs an independent re-run:

1. Reconstruct the run config from the entry.
2. Pull the pinned sandbox image; refuse if unavailable.
3. Execute every (task, seed) in a fresh sandbox.
4. Compare:

| Field | Comparison |
|---|---|
| per-task pass/fail per seed | strict equality |
| `tokens_in`, `tokens_out` | strict equality |
| `tool_calls` count | strict equality |
| `cost_usd` median, p95 | within +/-5% |
| `latency_s` p50, p95 | within +/-25% |
| trajectory text | not compared |
| `model_response_fingerprint` | logged; mismatch fires `model-drift` |

5. Emit a `VerificationReport` with the diff.

## 4. Two-VM rule

Every primary-panel leaderboard entry is verified in two different cloud
zones before being marked `verified: true`. The two verifiers must agree on
the strict-equality fields. Disagreement fires `borderline-stability` on
the flipping task and re-runs once; persistent disagreement marks the entry
`verified: partial`.

CI implementation: verifier-A on GitHub Actions, verifier-B on a Hetzner
VPS via SSH.

## 5. Partial determinism

LLM determinism at T=0 is partial. Known sources of drift:

- Provider model-version updates: same API string, different fingerprint
  week to week. Detected by the response fingerprint.
- Provider batch-composition numerics: floating-point summation order in
  attention can vary by batch. No client-side mitigation; documented.
- Tokenizer or pre-processing drift: same input, different output.

The protocol tolerates this on cost/latency, refuses it on pass/fail. A
pass/fail flip between submission and re-verification fires
`borderline-stability` and is shown in the verification report. We don't
invalidate such entries; the flag is the warning.

## 6. Cherry-pick mitigation

Without a constraint, a submitter could run many seeds, pick the favourable
five, and submit; the verifier would reproduce those exact five by
definition.

Primary-leaderboard entries must use `seed_list = [1, 2, 3, 4, 5]`. The
API gate enforces this at `to_leaderboard_entry()`; the CLI's `submit`
enforces it again; the verifier checks it on receipt.

`agenteval eval --exploratory --seeds N` is the escape hatch for capability
sweeps; results are tagged `leaderboard: false` and can't be promoted.

## 7. Re-publishing under new pricing

When `pricing.yaml` is updated:

1. The new yaml has a new SHA, hence a new `pricing_yaml_hash` and a new
   `entry_hash`.
2. Old entries keep their original `pricing_yaml_hash`; their cost numbers
   stay frozen.
3. To re-publish under new pricing, re-submit; this produces a new entry.
   The old entry isn't silently overwritten.
4. The frontend shows the most-recent entry per (bundle, task-set, model)
   by default; older entries remain accessible via the detail page.

## 8. Implementation

- `src/agenteval/reproducibility/hash.py`
- `src/agenteval/submit.py` (verifier)
- Tests in `tests/test_reproducibility.py` and `tests/test_submit_verify.py`.
