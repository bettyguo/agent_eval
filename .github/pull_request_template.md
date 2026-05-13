## Summary

<!-- One-paragraph description of what this PR does and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature / new task / new metric
- [ ] Methodology change (requires ADR — see [DECISIONS.md](../DECISIONS.md))
- [ ] Documentation
- [ ] CI / repo hygiene
- [ ] Leaderboard entry submission (under `frontend/data/submissions/`)

## Methodology checklist (for methodology-affecting PRs)

- [ ] New ADR appended to [DECISIONS.md](../DECISIONS.md) with sequential ID
- [ ] [`docs/methodology.md`](../docs/methodology.md) updated where relevant
- [ ] No existing leaderboard entries are silently invalidated (or migration path documented)
- [ ] Adversarial test case added for any new metric or flag

## Submission checklist (for leaderboard entries)

- [ ] Generated via `agenteval submit`
- [ ] Entry JSON sits under `frontend/data/submissions/`
- [ ] Skill bundle SHA + task-set SHA referenced are publicly accessible
- [ ] Pricing.yaml `last_audited` is current
- [ ] CI verify-submission job passes

## Test plan

<!-- How did you test this? `pytest`, manual `agenteval eval` run, CI runs, etc. -->

## Reviewer's notes

<!-- Anything reviewers should pay particular attention to. -->
