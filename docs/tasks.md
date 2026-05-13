# Task YAML format and grader interface

The schema for task files and the contract a grader script must satisfy. The
schema is versioned; any semantic change is a new task-set version rather
than an in-place edit.

## 1. Schema

```yaml
# Required

id: tdd-enforcement-01            # kebab-case; unique within the task set
                                  # pattern: ^[a-z][a-z0-9-]*[a-z0-9]$
category: tdd-enforcement         # tdd-enforcement | code-review | style-adherence
                                  # | refactor | multi-file
description: "<=200 char one-liner shown in CLI output and leaderboard"
license: MIT                      # SPDX identifier
prompt: |
  Implement fizzbuzz using strict TDD. Write tests first, watch them fail,
  then implement until they pass.

# Sandbox setup

setup:
  files:                          # files materialised in sandbox cwd at t=0
    "fizzbuzz.py": "def fizzbuzz(n): pass\n"
    "pytest.ini": "[pytest]\ntestpaths = .\n"
  pip_install:                    # optional; pinned specs
    - "pytest==8.3.2"

# Grader

grader:
  type: python                    # only "python" supported in v1
  script: |
    from agenteval.grading import GraderResult, first_modify_time, count_assertions

    def grade(workdir, trajectory, final_state):
        # return GraderResult(passed=..., details={...})
        ...

# Budget

time_budget_s: 300                # max wall-time per (task, seed); <=300 in v1
expected_tokens: 5000             # informational, used for cost-estimation
network: false                    # default false
panel: primary                    # primary | secondary; inherits from meta.yaml if omitted
```

### 1.1 Required vs optional

| Field | Required | Default |
|---|---|---|
| `id` | yes | |
| `category` | yes | |
| `description` | yes | |
| `license` | yes | |
| `prompt` | yes | |
| `grader.type` | yes | |
| `grader.script` | yes | |
| `setup.files` | no | `{}` |
| `setup.pip_install` | no | `[]` |
| `time_budget_s` | no | 300 |
| `expected_tokens` | no | 5000 |
| `network` | no | `false` |
| `panel` | no | inherits from `meta.yaml` |

### 1.2 Validation

Pydantic v2 in strict mode; unknown top-level keys are rejected (forward
compatibility is via task-set versioning, not key tolerance). Validation
errors carry a structured path for editor integration.

### 1.3 Task-set `meta.yaml`

Every task-set directory has a top-level `meta.yaml`:

```yaml
name: skill-specific-v1
version: "1"                # bumped on any task semantic change
panel: primary
description: "20 hand-curated tasks across 5 categories."
license: Apache-2.0
generator: hand-curated     # or "adapted-from:swe-bench-lite", etc.
contamination_notes: |      # secondary-panel sets only
  See CONTAMINATION.md for per-task flags.
```

### 1.4 Hashing

`task_set.hash` is the SHA256 of the normalised tarball of the entire
task-set directory: sorted file order, stripped trailing whitespace, zeroed
timestamps, normalised permissions. Any change yields a new hash. A new
hash means a new task-set version: bump `meta.yaml.version` and publish
under a new directory; the old version stays addressable.

## 2. Examples (one per category)

### 2.1 TDD enforcement

```yaml
id: tdd-enforcement-01
category: tdd-enforcement
description: "Implement fizzbuzz(n) via TDD; tests must fail before implementation."
license: MIT
prompt: |
  Implement `fizzbuzz(n)` for 1 <= n <= 100 using strict TDD. Write tests
  first, run them to observe failures, then implement. All tests must pass.
setup:
  files:
    "fizzbuzz.py": "def fizzbuzz(n):\n    pass\n"
    "pytest.ini": "[pytest]\ntestpaths = .\n"
  pip_install:
    - "pytest==8.3.2"
grader:
  type: python
  script: |
    def grade(workdir, trajectory, final_state):
        t_tests = first_modify_time(trajectory, "test_fizzbuzz.py")
        t_impl = first_modify_time(trajectory, "fizzbuzz.py", body_change=True)
        if t_tests is None or t_impl is None or t_tests >= t_impl:
            return {"passed": False, "details": {"reason": "impl preceded tests"}}
        if not ran_pytest_failure_then_success(trajectory):
            return {"passed": False, "details": {"reason": "no failing-test observation"}}
        if count_assertions(workdir / "test_fizzbuzz.py") < 4:
            return {"passed": False, "details": {"reason": "insufficient assertions"}}
        return {"passed": True, "details": {}}
time_budget_s: 240
expected_tokens: 4000
```

### 2.2 Code review

```yaml
id: code-review-01
category: code-review
description: "Review a Python function and flag an off-by-one in slice bounds."
license: MIT
prompt: |
  Review the following function and identify any bugs. Be explicit about the
  line number and the nature of the bug.
setup:
  files:
    "buggy.py": "<planted-bug code>"
grader:
  type: python
  script: |
    def grade(workdir, trajectory, final_state):
        msg = final_state.assistant_final_message
        if not grep_final_message(msg, [r"off.by.one", r"slice", r"\bbound"]):
            return {"passed": False, "details": {"reason": "did not flag off-by-one"}}
        if not localizes_to_line(msg, "buggy.py", expected_line=7):
            return {"passed": False, "details": {"reason": "did not localise to the buggy line"}}
        return {"passed": True, "details": {}}
time_budget_s: 120
expected_tokens: 2500
```

### 2.3 Style adherence

```yaml
id: style-adherence-01
category: style-adherence
description: "Rewrite a Python module to pass ruff --select=ALL with zero suppressions."
license: MIT
prompt: |
  Rewrite `app.py` so that `ruff check --select=ALL app.py` reports zero
  violations. Don't edit `pyproject.toml`. Don't add `# noqa` comments.
setup:
  files:
    "app.py": "<style-violating source>"
    "pyproject.toml": "<pinned ruff config>"
  pip_install:
    - "ruff==0.6.9"
grader:
  type: python
  script: |
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
description: "Behaviour-preserving extract-method; pre/post tests must both pass."
license: MIT
prompt: |
  Refactor `service.py` to extract the inner while-loop body into a dedicated
  function. The existing test suite must continue to pass.
setup:
  files:
    "service.py": "<source with extractable block>"
    "test_service.py": "<pre-existing tests>"
grader:
  type: python
  script: |
    def grade(workdir, trajectory, final_state):
        rc_post, _ = run_command(["pytest", "-q"], cwd=workdir)
        if rc_post != 0:
            return {"passed": False, "details": {"post": rc_post}}
        if ast_function_count(workdir / "service.py") < 2:
            return {"passed": False, "details": {"reason": "no extracted function"}}
        return {"passed": True, "details": {}}
```

### 2.5 Multi-file

```yaml
id: multi-file-01
category: multi-file
description: "Rename a function across 5 files; all callers updated; tests pass."
license: MIT
prompt: |
  Rename `legacy_parse(input)` to `parse(input)` everywhere it appears.
  Update all imports and call sites. Tests must pass.
setup:
  files:
    "core/parser.py": "..."
    "core/__init__.py": ""
    "cli/main.py": "..."
    "tests/test_parser.py": "..."
    "tests/test_cli.py": "..."
grader:
  type: python
  script: |
    def grade(workdir, trajectory, final_state):
        if grep_repo(workdir, r"\blegacy_parse\b"):
            return {"passed": False, "details": {"reason": "stale reference remains"}}
        rc, _ = run_command(["pytest", "-q"], cwd=workdir)
        if rc != 0:
            return {"passed": False, "details": {"reason": "tests fail after rename"}}
        return {"passed": True, "details": {}}
```

## 3. Grader interface

### 3.1 Signature

```python
def grade(
    workdir: pathlib.Path,
    trajectory: list[TrajectoryStep],
    final_state: FinalState,
) -> GraderResult:
    ...
```

Returns:

```python
@dataclass
class GraderResult:
    passed: bool
    details: dict[str, Any]
```

### 3.2 `TrajectoryStep`

```python
{
    "t": float,        # seconds since task start
    "tool": str,       # Read | Write | Edit | Bash | Glob | Grep
    "args": dict,      # tool input
    "result": dict,    # tool output (e.g. exit_code/stdout/stderr for Bash)
    "tokens_in": int,
    "tokens_out": int,
}
```

The tool vocabulary is normalised across providers so graders don't have to
know whether Anthropic, OpenAI, or Google ran the agent.

### 3.3 `FinalState`

```python
@dataclass
class FinalState:
    assistant_final_message: str
    file_hashes: dict[str, str]
    timed_out: bool
    raw_response_fingerprint: str | None
```

### 3.4 Grader privileges

- Graders run in a separate sandbox from the agent. Read access to
  `workdir`; no write access.
- Graders may execute commands via `agenteval.grading.run_command`, which
  spawns a fresh subprocess (no shell expansion, no network, same resource
  caps). Used for `pytest`, `ruff`, `mypy`.
- No external API calls from graders.
- Hard 30-second wall-time per grader. A timeout marks the task as a
  grader-failure (not a task-failure).

### 3.5 Shared utilities

The grader namespace pre-imports a small library to keep scripts short:

| Utility | Purpose |
|---|---|
| `first_modify_time(trajectory, path, body_change=False)` | Earliest `t` at which `path` was written/edited. |
| `ran_pytest_failure_then_success(trajectory)` | True iff trajectory has a failing pytest run strictly followed by a passing one. |
| `count_assertions(path)` | Count `Assert` AST nodes. |
| `grep_final_message(msg, patterns)` | Case-insensitive regex match against final message. |
| `localizes_to_line(msg, file, expected_line, tolerance=2)` | Message mentions `file` with a line number within tolerance. |
| `run_command(argv, cwd, timeout=...)` | Spawn subprocess; return `(exit_code, combined_output)`. |
| `assert_unchanged(path, expected_sha)` | Raise if `path`'s SHA256 differs from expected. |
| `no_suppressions(path, forbidden)` | True iff no `forbidden` substring appears in `path`. |
| `ast_function_count(path)` | Count function definitions. |
| `ast_normalised_equal(path_a, path_b)` | Equal after format-normalisation and docstring stripping. |
| `grep_repo(root, pattern, exclude=())` | Recursive grep across `root`. |

These are tested independently in `tests/test_grading_utils.py`.

## 4. Versioning policy

- The schema in §1 is locked. New fields require a schema-version bump.
- Adding a task to an existing task-set version (without bumping
  `meta.yaml.version`) is forbidden; the task-set hash would change
  silently and break entry reproducibility. New tasks go into a new
  version directory.
- Grader bug fixes are also new-version events (they change behaviour, hence
  the hash). Old versions remain addressable.

## 5. Forbidden patterns

- Tasks needing network access without `network: true`. The opt-in is for
  tasks where network is essential and auditable.
- Graders making external API calls.
- LLM-as-judge graders. Enforced syntactically: any grader script importing
  `anthropic`, `openai`, or `google.generativeai` is rejected at task-set
  load time.
- `setup.files` containing answers (a TDD task whose setup already includes
  complete tests, for instance).
- Tasks that depend on the current date/time. The sandbox clock is pinned
  to the task-set's release date.
