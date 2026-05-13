# Adversarial analysis

> Phase 0 stub. Authored during Phase 2 M4 when adversarial test cases are implemented. This file is required at launch per master prompt anti-pattern #2 ("Don't release without the adversarial section").

## Purpose

For each metric in [`metrics.md`](metrics.md), spell out:

1. The pathological skill that would game it.
2. The detector (flag) we publish.
3. The synthetic-skill test case in `tests/test_metrics.py` that exercises the detector.

The full set is enumerated in [`methodology.md`](methodology.md) §8. This document expands each pathology into a worked example with the synthetic skill bundle.

## Pathologies (preview, to be expanded)

### P1. Pass@k gaming via nondeterminism

A skill emits varied output across seeds. pass@5 inflates; pass@1 lags; pass^5 (reliability) tanks. **Detector:** `high-variance` flag when pass@5 ≥ 2 × pass^5. **Test:** `tests/adversarial/skill_nondeterministic_oracle/`.

### P2. Cost gaming via context inflation

A skill pads the system prompt with hundreds of lines of "retrieved" content. Pass-rate may rise; cost balloons. **Detector:** `talkative` flag. **Test:** `tests/adversarial/skill_context_padder/`.

### P3. Tool-storm gaming

A skill encourages many small redundant tool calls. **Detector:** `tool-storm` flag. **Test:** `tests/adversarial/skill_tool_storm/`.

### P4. Grader-pattern gaming

A skill teaches the agent to emit text that matches grader regexes without actually solving the task. **Detector:** graders verify *behavior* (test pass, linter pass, state-diff) wherever possible, not surface text. **Test:** `tests/adversarial/skill_regex_parroter/`.

### P5. Skill-bundle contamination of task answers

A skill contains hard-coded task solutions. **Detector:** v1 = none beyond manual review; v2 = grep-style audit against task-id strings. **Test:** `tests/adversarial/skill_answer_leak/`.

### P6. Pricing-stale gaming

A skill is submitted with an old `pricing.yaml` that under-counts cost. **Detector:** `pricing-stale` flag at 30 days. **Test:** `tests/adversarial/pricing_stale_submission/`.

## To-do for Phase 2 M4

- [ ] Build each synthetic-skill bundle under `tests/adversarial/`.
- [ ] Verify each detector flags its corresponding pathology.
- [ ] Verify each detector does NOT flag the no-skill baseline.
- [ ] Document any false-positive rates observed.
- [ ] Cross-link from [`methodology.md`](methodology.md) §8.
