# Task YAML format and grader interface

> Phase 1 §4.2 deliverable. Locks the schema and the grader interface that Phase 2 M1 implements against. Any change in v1 produces a new task-set version (e.g., `skill-specific-v2`); we do not edit task semantics in place.

## 1. Schema

```yaml
# Required fields

id: tdd-enforcement-01            # kebab-case; unique within the task set; pattern: ^[a-z][a-z0-9-]*[a-z0-9]$
category: tdd-enforcement         # one of: tdd-enforcement | code-review | style-adherence | refactor | multi-file
                                  # (additional categories require a new task-set version)
description: "≤200 char one-liner shown in CLI output and on the leaderboard"
license: MIT                      # SPDX identifier; tasks must be permissively licensed
prompt: |                         # the literal prompt the agent receives
  Implement fizzbuzz using strict test-driven development. Write tests first,
  watch them fail, then implement until they pass.

# Sandbox setup

setup:
  files:                          # files materialized in sandbox cwd at t=0; map path -> literal content
    "fizzbuzz.py": "def fizzbuzz(n): pass\n"
    "pytest.ini": "[pytest]\ntestpaths = .\n"
  # optional: install packages into the per-task container via pinned spec
  pip_install:
    - "pytest==8.3.2"

# Grader (the deterministic decision procedure)

grader:
  type: python                    # only "python" supported in v1 (ADR-0006: no LLM-as-judge)
  script: |                       # the grader body; see §3 for the interface contract
    from agenteval.grading import GraderResult, file_modified_order, count_assertions

    def grade(workdir, trajectory, final_state):
        # ... return GraderResult(passed=..., details={...})

# Budget and constraints

time_budget_s: 300                # max wall-time per (task, seed) attempt; ≤300 in v1
expected_tokens: 5000             # for cost-normalisation; informational, not a hard cap
network: false                    # default false; opt-in only when essential

# Panel assignment

panel: primary                    # primary | secondary; if omitted, inherits from task-set meta.yaml
```

### 1.1 Required vs optional

| Field | Required | Default |
|---|---|---|
| `id` | yes | — |
| `category` | yes | — |
| `description` | yes | — |
| `license` | yes | — |
| `prompt` | yes | — |
| `grader.type` | yes | — |
| `grader.script` | yes | — |
| `setup.files` | no | `{}` |
| `setup.pip_install` | no | `[]` |
| `time_budget_s` | no | 300 |
| `expected_tokens` | no | 5000 |
| `network` | no | `false` |
| `panel` | no | inherits from task-set `meta.yaml` |

### 1.2 Validation

Loaders use Pydantic v2 with `strict=True`. Unknown top-level keys are rejected (forward-compatibility is achieved via task-set versioning, not by ignoring unknown keys). Validation errors carry a structured path (e.g., `setup.files."fizzbuzz.py"`) for editor integration.

### 1.3 Task-set meta.yaml

Every task-set directory has a top-level `meta.yaml`:

```yaml
name: skill-specific-v1
version: "1"                # bumped on any task semantic change
panel: primary              # default panel for tasks in this set
description: "20 hand-curated tasks discriminating skill behaviour across 5 categories."
license: Apache-2.0         # task set licensing umbrella; individual tasks may override
generator: hand-curated     # vs. "adapted-from:swe-bench-lite", "adapted-from:tau-bench", etc.
contamination_notes: |      # secondary-panel sets only; primary sets may omit
  See CONTAMINATION.md for per-task flags.
```

### 1.4 Task-set hashing

`task_set.hash` = SHA256 of the normalized tarball of the entire task-set directory (including `meta.yaml`, all task YAMLs, any auxiliary files referenced from `setup.files`). Normalization: sorted file order, stripped trailing whitespace, timestamps zeroed, permissions normalized.

Any change — including a typo fix in `description` — yields a new hash. A new hash implies a new task-set version: bump `meta.yaml` `version` and publish under a new directory (`skill-specific-v2/`). The old version stays addressable. See `docs/reproducibility.md`.

---

## 2. Examples (one per category)

### 2.1 TDD enforcement

```yaml
id: tdd-enforcement-01
category: tdd-enforcement
description: "Implement fizzbuzz(n) using strict TDD; tests must fail before any implementation is written."
license: MIT
prompt: |
  Implement `fizzbuzz(n)` (standard FizzBuzz rules for 1 ≤ n ≤ 100) using strict
  test-driven development. Write tests first, run them to observe failures, then
  implement. Final state: all your tests pass.
setup:
  files:
    "fizzbuzz.py": "def fizzbuzz(n):\n    pass\n"
    "pytest.ini": "[pytest]\ntestpaths = .\n"
  pip_install:
    - "pytest==8.3.2"
grader:
  type: python
  script: |
    from agenteval.grading import (
        first_modify_time, count_assertions, ran_pytest_failure_then_success
    )
    def grade(workdir, trajectory, final_state):
        t_tests = first_modify_time(trajectory, "test_fizzbuzz.py")
        t_impl  = first_modify_time(trajectory, "fizzbuzz.py", body_change=True)
        if t_tests is None or t_impl is None or t_tests >= t_impl:
            return {"passed": False, "details": {"reason": "impl preceded tests"}}
        if not ran_pytest_failure_then_success(trajectory):
            return {"passed": False, "details": {"reason": "no failing-test observation"}}
        if count_assertions(workdir / "test_fizzbuzz.py") < 4:
            return {"passed": False, "details": {"reason": "insufficient assertions"}}
        # final-state checks: pytest passes, mutated impl is caught by tests
        ...
        return {"passed": True, "details": {}}
time_budget_s: 240
expected_tokens: 4000
network: false
```

### 2.2 Code review

```yaml
id: code-review-01
category: code-review
description: "Review a small Python function and flag an off-by-one in slice bounds."
license: MIT
prompt: |
  Review the following function and identify any bugs. Be explicit about the line
  number and the nature of the bug:
  <inline-snippet>
setup:
  files:
    "buggy.py": "<the planted-bug code>"
grader:
  type: python
  script: |
    from agenteval.grading import grep_final_message, localizes_to_line
    def grade(workdir, trajectory, final_state):
        msg = final_state.assistant_final_message
        if not grep_final_message(msg, [r"off.by.one", r"slice", r"\bbound", r"\binclusiv"]):
            return {"passed": False, "details": {"reason": "did not flag off-by-one"}}
        if not localizes_to_line(msg, "buggy.py", expected_line=7):
            return {"passed": False, "details": {"reason": "did not localise to the buggy line"}}
        return {"passed": True, "details": {}}
time_budget_s: 120
expected_tokens: 2500
network: false
```

### 2.3 Style adherence

```yaml
id: style-adherence-01
category: style-adherence
description: "Rewrite a small Python module to pass ruff with select=ALL and zero suppressions."
license: MIT
prompt: |
  Rewrite the module `app.py` so that `ruff check --select=ALL app.py` reports
  zero violations. You may not edit `pyproject.toml`. You may not add `# noqa`
  comments.
setup:
  files:
    "app.py": "<style-violating source>"
    "pyproject.toml": "<pinned ruff config with select=ALL>"
  pip_install:
    - "ruff==0.6.9"
grader:
  type: python
  script: |
    from agenteval.grading import run_command, assert_unchanged, no_suppressions
    def grade(workdir, trajectory, final_state):
        assert_unchanged(workdir / "pyproject.toml", expected_sha=...)
        if not no_suppressions(workdir / "app.py", forbidden=["noqa", "type: ignore"]):
            return {"passed": False, "details": {"reason": "used suppression markers"}}
        rc, out = run_command(["ruff", "check", "--select=ALL", "app.py"], cwd=workdir)
        if rc != 0:
            return {"passed": False, "details": {"ruff": out}}
        return {"passed": True, "details": {}}
```

### 2.4 Refactor

```yaml
id: refactor-01
category: refactor
description: "Behaviour-preserving extract-method on a 60-line function; pre/post tests must both pass."
license: MIT
prompt: |
  Refactor `service.py` to extract the body of the inner while-loop into a
  dedicated function. The existing test suite must continue to pass.
setup:
  files:
    "service.py": "<source with extractable block>"
    "test_service.py": "<pre-existing tests>"
grader:
  type: python
  script: |
    from agenteval.grading import (
        run_command, ast_function_count, ast_normalised_equal
    )
    def grade(workdir, trajectory, final_state):
        rc_pre  = ...  # ran against pre-state; recorded by the harness
        rc_post, _ = run_command(["pytest", "-q"], cwd=workdir)
        if rc_pre != 0 or rc_post != 0:
            return {"passed": False, "details": {"pre": rc_pre, "post": rc_post}}
        if ast_function_count(workdir / "service.py") < 2:
            return {"passed": False, "details": {"reason": "no extracted function"}}
        # AST-normalised equality of pre vs post is *not* required (otherwise refactor isn't allowed);
        # what we require is: same external test behaviour + new function exists.
        return {"passed": True, "details": {}}
```

### 2.5 Multi-file

```yaml
id: multi-file-01
category: multi-file
description: "Rename a function across 5 files; all callers must be updated; tests must pass."
license: MIT
prompt: |
  Rename `legacy_parse(input)` to `parse(input)` everywhere it appears. Update
  all imports and call sites. Tests must pass at the end.
setup:
  files:
    "core/parser.py": "..."
    "core/__init__.py": "..."
    "cli/main.py": "..."
    "tests/test_parser.py": "..."
    "tests/test_cli.py": "..."
grader:
  type: python
  script: |
    from agenteval.grading import run_command, grep_repo
    def grade(workdir, trajectory, final_state):
        # No stale references remain.
        if grep_repo(workdir, "legacy_parse"):
            return {"passed": False, "details": {"reason": "stale reference remains"}}
        rc, _ = run_command(["pytest", "-q"], cwd=workdir)
        if rc != 0:
            return {"passed": False, "details": {"reason": "tests fail after rename"}}
        return {"passed": True, "details": {}}
```

---

## 3. Grader interface contract

### 3.1 Function signature

```python
def grade(
    workdir: pathlib.Path,           # final filesystem state after agent's run; read-only by convention
    trajectory: list[TrajectoryStep], # tool-call log, see §3.2
    final_state: FinalState,         # see §3.3
) -> GraderResult:
    ...
```

Graders return a `GraderResult`:

```python
@dataclass
class GraderResult:
    passed: bool
    details: dict[str, Any]          # arbitrary structured details for the run record
```

### 3.2 `TrajectoryStep` records

Each step in the trajectory is a dict:

```python
{
    "t": float,                       # seconds since task start
    "tool": str,                      # one of: "Read", "Write", "Edit", "Bash", "Glob", "Grep", or a runner-specific name
    "args": dict,                     # tool input as the agent provided it
    "result": dict,                   # tool output: {"exit_code": int, "stdout": str, "stderr": str} for Bash;
                                      #              {"path": str, "bytes_written": int} for Write/Edit; etc.
    "tokens_in": int,                 # tokens consumed by this turn's request (when known)
    "tokens_out": int,                # tokens produced
}
```

The trajectory's `tool` vocabulary is normalized across providers — graders should not have to know whether the underlying provider was Anthropic, OpenAI, or Google. The runner-specific shim translates provider tool calls into the normalized vocabulary; the original provider response is also stored in `result["raw_provider_response"]` for debugging but graders should not depend on it.

### 3.3 `FinalState`

```python
@dataclass
class FinalState:
    assistant_final_message: str              # the last assistant turn's textual content
    file_hashes: dict[str, str]               # path -> sha256 of final contents
    timed_out: bool                           # True if the task hit time_budget_s
    raw_response_fingerprint: str | None      # provider-side fingerprint at end of run
```

### 3.4 Grader privileges

- Graders run in the *grader sandbox*, separate from the agent sandbox. They have read access to `workdir`, no write access.
- Graders may execute commands via `agenteval.grading.run_command`, which spawns a fresh subprocess sandbox (no shell expansion, no network, same 1-CPU/2-GB constraints). This is used for `pytest`, `ruff`, `mypy`, etc.
- Graders may NOT make external API calls. (If they need to, that's a sign the grader should be LLM-as-judge, which v1 forbids.)
- Graders are subject to a hard 30-second wall-time. A grader that times out marks the task as a grader-failure (distinct from a task-failure) — surfaced as a `grader-timeout` annotation in the result.

### 3.5 Shared grader utilities

To keep grader scripts short and consistent across the 20 hand-curated tasks (and beyond), Phase 2 M1 implements a small library in `src/agenteval/grading/`:

| Utility | Purpose |
|---|---|
| `first_modify_time(trajectory, path, body_change=False)` | Earliest trajectory `t` at which `path` was written/edited. Optional `body_change` requires the change to alter the function body (vs. e.g., adding a docstring). |
| `ran_pytest_failure_then_success(trajectory)` | True iff trajectory contains a `Bash` invocation of `pytest` that exited non-zero, strictly followed by a later invocation that exited zero. |
| `count_assertions(path)` | Count `Assert` AST nodes in a Python source file. |
| `grep_final_message(msg, patterns)` | True iff any regex in `patterns` matches `msg` (case-insensitive). |
| `localizes_to_line(msg, file, expected_line, tolerance=2)` | True iff `msg` mentions `file` with a line number within `tolerance` of `expected_line`. |
| `run_command(argv, cwd, timeout=...)` | Spawn a subprocess in the grader sandbox; return `(exit_code, combined_output)`. |
| `assert_unchanged(path, expected_sha)` | Raise if `path`'s SHA256 differs from `expected_sha`. |
| `no_suppressions(path, forbidden)` | True iff none of `forbidden` substrings appears in `path` content. |
| `ast_function_count(path)` | Count top-level + nested function definitions in a Python source file. |
| `ast_normalised_equal(path_a, path_b)` | Equal after formatting normalization and docstring stripping. Used by behaviour-preserving-refactor graders sparingly. |
| `grep_repo(root, pattern, exclude=())` | Recursive grep across the workdir for a regex pattern. |

These utilities are tested independently in `tests/test_grading_utils.py` so individual task graders can rely on them without re-testing each.

---

## 4. Versioning and change policy

- The schema in §1 is **locked**. Adding new fields requires a schema-version bump and a migration note.
- Adding a new task to an existing task-set version (without bumping `meta.yaml` `version`) is **forbidden** — the task-set hash would change silently and break entry reproducibility. New tasks land in a new version directory.
- Bug fixes that change a grader's behaviour are likewise new-version events. Bug fixes that don't change behaviour (e.g., comment edits, dead-code removal) are not allowed in-place either, because the hash would change. They go through a normal version bump.
- Old versions remain in the repo indefinitely. Old leaderboard entries continue to reference their version's hash.

---

## 5. Forbidden patterns

- Tasks that require network access without `network: true` opt-in. The opt-in is for tasks where network is essential (e.g., a task that reads a public API in a controlled way); even then, network access must be auditable.
- Tasks whose grader makes external API calls.
- Tasks whose grader is LLM-as-judge (ADR-0006). This is enforced syntactically: any grader script importing `anthropic`, `openai`, or `google.generativeai` is rejected at task-set load time.
- Tasks whose `setup.files` contain answers (e.g., a TDD task whose `setup.files` already includes complete tests). The task-set loader scans `setup.files` for grader-pattern signatures (a Phase 2 M4 add) and rejects matches.
- Tasks that depend on the current date/time (the sandbox clock is pinned to the task-set's release date to keep results reproducible).

---

## 6. To-do (Phase 2 M1)

- [ ] Pydantic schema implementation in `src/agenteval/tasks/schema.py`.
- [ ] Task-set loader in `src/agenteval/tasks/registry.py` with normalization + hashing.
- [ ] Grader utility library in `src/agenteval/grading/`.
- [ ] First 5 task YAMLs in `tasks/skill-specific-v1/` (one per category).
- [ ] Snapshot tests for grader behaviour on canned trajectories.
