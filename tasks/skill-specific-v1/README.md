# `skill-specific-v1` — Task-Set Specification

> Phase 0 §3.3 deliverable. This is the **design document** for the 20 hand-curated tasks that form one third of the v1 task budget (per ADR-0009). The actual YAML files are implemented in Phase 2 M1 (first 5) and M4 (remaining 15). This document is the contract those implementations must satisfy.

---

## 1. Preamble

### 1.1 What this task set is

`skill-specific-v1` is a hand-curated suite of 20 tasks designed for **one purpose**: to discriminate between agents augmented with a "good" Claude Code skill, agents augmented with a "bad" or pathological skill, and agents with no skill at all. Each task targets a specific behaviour a skill might plausibly claim to enforce (test-first development, bug detection, style adherence, behaviour-preserving refactoring, cross-file consistency) and grades the agent's run with a **deterministic Python procedure**. There is no LLM-as-judge anywhere in this task set (ADR-0006).

The complementary 30+50 tasks in `swebench-lite-v1/` and `tau-bench-v1/` exercise raw agentic-coding competence on existing literature benchmarks; this task set, in contrast, exists because the existing benchmarks do **not** probe the specific claims skill authors make. A skill that claims "I will make Claude write tests first" must be measured on a task that fails when tests are written second — and no public benchmark does that today.

### 1.2 What this task set is *not*

- It is not an attempt to evaluate general code-generation quality (HumanEval / SWE-bench cover that).
- It is not an attempt to evaluate long-horizon agent planning (TAU-Bench, METR HCAST).
- It is not exhaustive. 20 tasks is the minimum size at which a 5-category-by-4-task balance is meaningful; v2 may expand to ~40.
- It is not contamination-resistant. Some tasks (e.g., "find off-by-one in slicing") use patterns the model has seen in training. We accept this because we are comparing skill ablations, not raw model power (see `docs/methodology.md` §contamination).

### 1.3 Reference: task YAML schema (locked, §4.2 of master prompt)

Every task in this directory will be a YAML file conforming to this schema (reproduced here for reference; canonical lives in master prompt §4.2 and `src/agenteval/tasks/registry.py`):

```yaml
id: tdd-enforcement-01                # kebab-case, unique within task set
category: tdd-enforcement             # one of the 5 category slugs
description: "≤200 char one-liner."
license: MIT                          # SPDX identifier
setup:
  files:                              # files materialized in sandbox cwd at t=0
    "path/file.ext": "literal content\n"
prompt: |                             # the prompt fed to the agent
  Multi-line agent prompt.
grader:
  type: python                        # only "python" supported in v1
  script: |                           # has access to:
                                      #   - workdir/  (filesystem state)
                                      #   - trajectory.jsonl  (tool-call log)
                                      #   - returns {"passed": bool, "details": {...}}
    ...
time_budget_s: 300                    # ≤300 in v1
expected_tokens: 5000                 # for cost-normalisation; not a hard cap
network: false                        # false (the default in v1) unless explicitly opted in
```

### 1.4 Threat model

Graders execute **trusted code** maintained by this project. Agent-produced artefacts (skill bundles, generated source files) execute inside the Docker sandbox described in ADR-0005: 1 CPU, 2 GB RAM, network off, no host mount. Graders themselves are not adversarial inputs: they live in this repo, are reviewed by maintainers, and pin their dependencies. We defend against accidental side effects and metric-gaming skills; we do **not** defend against deliberate sandbox escape. See `docs/methodology.md` for the full threat-model discussion.

### 1.5 Why five categories of four tasks

The five categories were chosen from §3.3 of the master prompt because each maps to a **distinct claim** real-world skills currently make on GitHub (mattpocock/skills, obra/superpowers, etc.). Four tasks per category gives enough variance to detect both (a) skills that legitimately help on the category and (b) skills that happen to game one task but not the other three. Fewer than 3 tasks per category would let lucky single-task wins dominate the category subscore; more than 5 would push the total task budget above the 100-task ceiling (anti-pattern #6).

All 20 tasks below are deterministically gradable. None required us to fall back on a 21st task or to drop below 4 per category.

### 1.6 Conventions used in the specs below

- "Trajectory" = the JSONL log of tool calls the agent made, in order, written by the harness during the run. Every entry has at minimum `{"t": float_seconds_since_start, "tool": str, "args": {...}, "result": {...}}`. The `Write` / `Edit` / `Create` tool calls in particular are the basis for the file-write-order graders below.
- "Workdir" = the path inside the sandbox where the task's `setup.files` were materialized. After the agent finishes, this is the final filesystem state.
- "Agent's final message" = the last assistant turn's textual content (excluding tool calls), used by the **code-review** category to look for flagged-issue strings.
- "AST diff" = comparison of two Python ASTs after normalisation (formatting stripped, docstrings preserved). Detailed in §Appendix B.

---

## 2. Task specifications

### 2.1 Category: TDD enforcement (4 tasks)

**Claim under test:** "This skill makes the agent write tests before implementation."

The discriminator across all four tasks is **trajectory order**: a TDD-enforcing skill should cause the agent to write/extend the test file before writing the implementation file, *and* the tests should fail at least once before the implementation succeeds. A non-TDD agent will typically write the implementation first, then a test that passes immediately.

---

#### `tdd-enforcement-01` — Fizzbuzz, classic

- **One-sentence description:** Implement `fizzbuzz(n)` using strict TDD; tests must exist and fail before any implementation is written.
- **Pre-state:** `fizzbuzz.py` exists with `def fizzbuzz(n): pass`. `test_fizzbuzz.py` does **not** exist. A `pytest.ini` is provided with `testpaths = .`.
- **Prompt to agent:** "Implement `fizzbuzz(n)` (standard FizzBuzz rules for 1 ≤ n ≤ 100) using strict test-driven development. Write tests first; run them and observe failures; then implement. Final state: all your tests pass."
- **Pass criterion:** Grader inspects the trajectory and the filesystem.
  1. Trajectory must contain at least one `Write`/`Edit` to `test_fizzbuzz.py` whose timestamp is **strictly earlier** than the first `Write`/`Edit` to `fizzbuzz.py` that changes the body of `fizzbuzz` (i.e., a non-`pass` body).
  2. Trajectory must contain at least one `Bash` invocation of `pytest` whose `result` indicates a failure (exit code non-zero, or stdout contains `failed`), strictly between the test-file write and the implementation write.
  3. Final filesystem state: `pytest -q` exits 0 in the workdir, *and* `test_fizzbuzz.py` contains ≥4 distinct `assert` statements (parsed via Python `ast` module; each `Assert` node counted once).
  4. Fail otherwise. Edge case: if the agent writes tests + impl in the same tool call (single multi-file write), grader treats them as simultaneous → fail (TDD requires observing red).
- **Why a skilled agent should outperform:** A TDD skill should cause the agent to author `test_fizzbuzz.py` first and run pytest to see red before authoring the implementation; the trajectory inspector detects this ordering directly. A no-skill baseline will typically write the implementation first or skip the failing-test step.
- **Adversarial counterpoint:** A pathological skill could emit a `test_fizzbuzz.py` containing `assert True` four times and call that "tests first". Mitigation: assertion-count threshold (≥4) and the **post-impl assertion-strength check** — grader requires that mutating one of the impl's three branches (`%3`, `%5`, `%15`) causes at least one test in the file to fail when re-run; if a tampered impl still passes, tests are insufficient and the task fails.
- **License:** MIT.

---

#### `tdd-enforcement-02` — Roman-numeral converter

- **One-sentence description:** Implement `to_roman(n: int) -> str` for 1 ≤ n ≤ 3999 using TDD; tests must precede implementation.
- **Pre-state:** `roman.py` with `def to_roman(n): raise NotImplementedError`. No test file. `pytest.ini` provided.
- **Prompt to agent:** "Implement `to_roman(n)` for integers 1–3999 returning standard Roman numerals (e.g., 1994 → 'MCMXCIV'). Use test-driven development: write tests, watch them fail, implement."
- **Pass criterion:** Same trajectory checks as 01 (test file written before impl body change; ≥1 failing pytest run in between). Final-state checks:
  1. Tests exist (≥6 `Assert` nodes — Roman demands more coverage than fizzbuzz).
  2. `pytest -q` exits 0.
  3. A grader-owned **hidden test bank** of 25 (input, expected) pairs is executed against the agent's `to_roman`; ≥24/25 must pass. The hidden tests are not visible to the agent (loaded by the grader, not present in the workdir).
  4. Fail if hidden-test pass rate < 24/25 even if local tests pass (catches under-tested implementations).
- **Why a skilled agent should outperform:** Same TDD-trajectory argument as 01, plus hidden tests punish skills that write minimal tests just to satisfy the assertion-count gate.
- **Adversarial counterpoint:** Skill could write strong tests then implement a `to_roman` that hard-codes the 13 standard pairs. Mitigation: hidden tests include edge values (1, 4, 9, 40, 49, 400, 900, 3999) chosen to require correct decomposition, not lookup.
- **License:** MIT.

---

#### `tdd-enforcement-03` — Bugfix-first refactor

- **One-sentence description:** A function has a known bug; the agent must add a failing test that reproduces the bug *before* changing any implementation code.
- **Pre-state:** `discount.py` contains `def apply_discount(price, pct): return price - price * pct` (note: missing the `/100` for percent). `test_discount.py` exists with two passing tests that use fractional `pct` (0.1, 0.25), masking the bug. The agent is told users report wrong totals when `pct=10`.
- **Prompt to agent:** "Users report that `apply_discount(100, 10)` returns -900 instead of 90. Reproduce the bug with a failing test, then fix it. Do not modify `discount.py` before you have a failing test demonstrating the bug."
- **Pass criterion:**
  1. Trajectory: the first `Write`/`Edit` to `test_discount.py` (adding the new failing test) must occur strictly before the first `Write`/`Edit` to `discount.py`.
  2. Trajectory: between (1) and the first `discount.py` edit, there must be a `pytest` call whose `result` shows ≥1 test failing (stdout regex `\b[1-9]\d* failed\b`).
  3. Final state: `pytest -q` exits 0; the test file contains a test that invokes `apply_discount` with an integer `pct` ≥ 1 (parsed via AST: looking for an `assert`-targeted `Call` to `apply_discount` whose second positional arg is a `Constant` with `value >= 1`).
  4. Final state: `apply_discount(100, 10) == 90` (grader runs this directly).
- **Why a skilled agent should outperform:** A TDD/bugfix skill specifically teaches "red-test before patch", which the trajectory and integer-pct check capture mechanically.
- **Adversarial counterpoint:** Skill could write the failing test with `assert apply_discount(100, 10) == -900` to make it pass before patching, satisfying the temporal order trivially. Mitigation: criterion (3) requires the test to use integer pct ≥ 1 *and* criterion (4) checks the final behaviour — if the agent silently kept the buggy impl by writing a buggy test, criterion (4) fails.
- **License:** MIT.

---

#### `tdd-enforcement-04` — Stack with capacity

- **One-sentence description:** Implement a capacity-limited stack class via TDD; the test file must define behaviours one-at-a-time across multiple write events.
- **Pre-state:** `stack.py` with `class BoundedStack:\n    def __init__(self, capacity): pass`. No test file.
- **Prompt to agent:** "Implement `BoundedStack` with `push`, `pop`, `peek`, `__len__`, and raise `OverflowError` on push past capacity, `IndexError` on pop/peek when empty. Use TDD, one behaviour per cycle: write a test for behaviour N, see it fail, implement, see it pass, then move to behaviour N+1."
- **Pass criterion:**
  1. Trajectory: ≥3 distinct `Write`/`Edit` events to `test_stack.py` with `pytest` invocations interleaved between them, of which ≥2 pytest invocations show failure (regex `\b\d+ failed\b`). This detects iterative TDD vs. one-shot test authoring.
  2. Final state: `pytest -q` exits 0 with ≥5 distinct test functions (parsed via AST: count `FunctionDef` nodes in `test_stack.py` whose name starts with `test_`).
  3. Final state: a grader-supplied hidden test (`hidden_test_stack.py`, imported by the grader, not the agent) exercises all 5 behaviours and must fully pass.
  4. Edge case: if the trajectory has ≥3 test-file writes but no interleaved pytest failures, the agent merely fragmented authorship without observing red → fail.
- **Why a skilled agent should outperform:** A rigorous TDD skill enforces the red-green-refactor cycle per behaviour, producing multiple interleaved write/run events — exactly what this grader counts.
- **Adversarial counterpoint:** Skill could fake interleaving by adding a meaningless test, running pytest, then adding the real tests. Mitigation: pytest failure must reference a `test_` function defined in `test_stack.py` at that point — grader parses the failing-test name out of pytest output and confirms it was *added* in the immediately prior write event.
- **License:** MIT.

---

### 2.2 Category: Code review (4 tasks)

**Claim under test:** "This skill makes the agent flag a specific class of bug in code review."

The discriminator is **whether the agent's final textual output flags a planted bug** in language the grader can detect via case-insensitive substring matching against a curated keyword set (with synonym fallback). All four tasks plant exactly one bug of known taxonomy, and the agent is asked to review the file — not to fix it. (Mixing review with fix complicates grading; we keep them separate.)

---

#### `code-review-01` — Off-by-one in range slicing

- **One-sentence description:** Review a paginate function that slices `items[start:start+page_size-1]`; agent must flag the off-by-one.
- **Pre-state:** `paginate.py` with a 12-line `paginate(items, page, page_size)` function whose return is `items[start:start+page_size-1]` (off-by-one — should be `start+page_size`).
- **Prompt to agent:** "Review `paginate.py`. Describe any bugs you find. Do not modify the file."
- **Pass criterion:** Agent's final message (the last assistant turn's textual content) must contain **at least one** of the following case-insensitive substrings: `off-by-one`, `off by one`, `page_size - 1`, `page_size-1`, `last item`, `one item short`, `missing item`, `loses an item`, `loses one`. AND the message must reference the slicing expression (regex: `start\s*\+\s*page_size` OR `items\[.*:.*\]`). Both conditions must hold. Fail otherwise. Workdir must be unchanged (grader hashes `paginate.py` before and after; SHAs must match — agent disobeying "do not modify" is a fail).
- **Why a skilled agent should outperform:** A code-review skill should sensitise the agent to slicing arithmetic, which a no-skill agent might overlook in a 12-line function.
- **Adversarial counterpoint:** Skill could output a giant bullet-list of every possible bug taxonomy (off-by-one, race condition, null deref, …) regardless of code, gaming substring match. Mitigation: the second clause requires the agent's message to localise the bug to the actual slicing expression. A shotgun list with no localization fails. A `tool-call-count` per-task metric (collected harness-wide, surfaced in `metrics/`) also flags suspiciously high output length.
- **License:** MIT.

---

#### `code-review-02` — Mutable default argument

- **One-sentence description:** Review a function with `def append_log(entry, log=[]):` — the classic mutable-default-argument Python pitfall — agent must flag it.
- **Pre-state:** `logger.py` defining `def append_log(entry, log=[]): log.append(entry); return log` plus 30 lines of unrelated helper code (to make the bug non-trivial to spot).
- **Prompt to agent:** "Review `logger.py` and describe any bugs. Do not modify the file."
- **Pass criterion:** Agent's final message must contain **at least one** of: `mutable default`, `default argument`, `shared default`, `default mutable`, `mutable default argument`, `B006` (the ruff rule code). AND must reference `log` or `append_log` by name (case-insensitive). File must be unchanged.
- **Why a skilled agent should outperform:** A code-review skill drilled on Python idioms will reliably flag this; a fresh model is hit-and-miss in a 30-line file.
- **Adversarial counterpoint:** Skill could prepend "Mutable default argument detected" boilerplate to every review. Mitigation: must reference `log`/`append_log` by name; grader checks both substrings.
- **License:** MIT.

---

#### `code-review-03` — SQL injection via f-string

- **One-sentence description:** Review a function that builds a SQL query via `f"SELECT * FROM users WHERE name = '{name}'"`; agent must flag SQL injection.
- **Pre-state:** `db.py` with a 20-line module containing a `find_user(conn, name)` function that uses an f-string SQL query.
- **Prompt to agent:** "Review `db.py` for security issues. Do not modify the file."
- **Pass criterion:** Agent's final message must contain **at least one** of: `sql injection`, `sqli`, `parameterised`, `parameterized`, `prepared statement`, `bind parameter`, `placeholder`, `bobby tables`. AND must reference `f"SELECT` OR `find_user` OR the literal `name` parameter. File unchanged.
- **Why a skilled agent should outperform:** A security-focused review skill should catch this trivially; no-skill is also likely to catch it, but the discriminator is **consistency across seeds** — we measure pass@5, and a skill should narrow variance.
- **Adversarial counterpoint:** Skill could spam security keywords. Mitigation: as above, must localise to the function/string literal.
- **License:** MIT.

---

#### `code-review-04` — Race condition in lazy init

- **One-sentence description:** Review a singleton class with non-thread-safe lazy initialisation (classic double-checked locking absence); agent must flag the race.
- **Pre-state:** `cache.py` with a `Cache` class using `_instance = None` and a classmethod `get_instance` that does `if cls._instance is None: cls._instance = Cache()` with no lock.
- **Prompt to agent:** "Review `cache.py` assuming it will be used from multiple threads. Do not modify the file."
- **Pass criterion:** Agent's final message must contain **at least one** of: `race condition`, `thread safe`, `thread-safe`, `not thread safe`, `lock`, `mutex`, `concurrent`, `multiple instances`, `double-checked locking`, `tocttou`. AND must reference `get_instance`, `_instance`, or `Cache`. File unchanged.
- **Why a skilled agent should outperform:** Concurrency bugs are a known weak spot for LLMs out-of-the-box; a code-review skill that flags concurrency patterns is the kind of skill we want to detect.
- **Adversarial counterpoint:** Skill could prepend "may have race conditions" boilerplate. Mitigation: localisation requirement as above; in addition, the agent must explain the failure mode at least once (regex match for `two|both|multiple` near `instance` to confirm understanding, not just keyword bingo). Grader uses a 50-char window between the two substrings.
- **License:** MIT.

---

### 2.3 Category: Style / convention adherence (4 tasks)

**Claim under test:** "This skill makes the agent produce code that passes our chosen linter / style checker."

The discriminator is **the linter's exit code on the final filesystem**. All four tasks have the agent author or modify code; the grader runs an off-the-shelf, deterministic tool (`ruff`, `mypy`, `eslint`, `black --check`) inside the sandbox; pass = exit 0 with no findings, fail = any finding. Linter versions are pinned in the sandbox image (ADR-0005 + Phase 3.6).

---

#### `style-adherence-01` — PEP 8 via ruff strict

- **One-sentence description:** Implement a small `validators.py` module from a docstring spec; the file must pass `ruff check --select ALL` with zero findings.
- **Pre-state:** Empty `validators.py` plus a `SPEC.md` describing three validators (`is_email`, `is_phone_e164`, `is_hex_color`). `pyproject.toml` configures ruff with `select = ["ALL"]` and `ignore = ["D203", "D213", "COM812", "ISC001"]` (the conventional conflict-pair exceptions). A `pytest`-runnable behavioural test file is provided so the agent can confirm correctness.
- **Prompt to agent:** "Implement the three validators in `validators.py` per `SPEC.md`. Code must pass `ruff check` with zero findings under the configuration in `pyproject.toml`. The behavioural tests in `test_validators.py` must also pass."
- **Pass criterion:**
  1. `pytest -q` exits 0.
  2. `ruff check validators.py` exits 0 with empty output.
  3. The final `validators.py` is non-empty and contains `def is_email`, `def is_phone_e164`, `def is_hex_color` (AST parse: three `FunctionDef` nodes with those names at module scope).
- **Why a skilled agent should outperform:** A style-enforcing skill that internalises ruff's rule set produces cleaner code on the first attempt; a no-skill agent often emits code that violates docstring, naming, or annotation rules.
- **Adversarial counterpoint:** Skill could blanket-disable ruff rules in `pyproject.toml`. Mitigation: grader hashes `pyproject.toml` before and after (SHAs must match); if the agent modifies the config, fail. Same for any `# noqa` comments — grader greps `validators.py` for `noqa` and fails if any appear (the prompt does not authorise suppressions).
- **License:** MIT.

---

#### `style-adherence-02` — Strict mypy

- **One-sentence description:** Add complete type annotations and any necessary helpers to `geometry.py` until `mypy --strict` reports zero errors, without changing runtime behaviour.
- **Pre-state:** `geometry.py` contains three functions (`area_circle`, `area_triangle`, `centroid`) with partial / wrong type hints. A `test_geometry.py` exercises them. `mypy.ini` pins strict mode with `python_version = 3.11`.
- **Prompt to agent:** "Make `mypy --strict geometry.py` pass with zero errors. All `test_geometry.py` tests must still pass. Do not change function signatures' parameter *names* or runtime return types — only annotations and (if needed) internal restructuring."
- **Pass criterion:**
  1. `mypy --strict geometry.py` exits 0, output contains `Success`.
  2. `pytest -q test_geometry.py` exits 0.
  3. For each of the three public functions, the parameter-name tuple is identical to the pre-state (grader extracts via AST: `[arg.arg for arg in FunctionDef.args.args]` must match the pre-state tuple).
  4. The runtime return type for at least one canonical call per function matches the pre-state (grader imports both versions in subprocesses and compares `type(result).__name__`).
- **Why a skilled agent should outperform:** A typing-discipline skill produces correct-on-first-try annotations; a no-skill agent often forgets `-> None`, generic parameters, or trips on `Any`-leakage.
- **Adversarial counterpoint:** Skill could add `# type: ignore` to every line. Mitigation: grader greps for `type: ignore` in the final `geometry.py` and fails if any are present (mypy strict + zero ignores is the bar).
- **License:** MIT.

---

#### `style-adherence-03` — Black-compatible formatting via `ruff format`

- **One-sentence description:** Reformat a deliberately ugly module so that `ruff format --check` passes, without altering AST.
- **Pre-state:** `messy.py` (a 60-line module with inconsistent quotes, mixed indentation, missing/extra blank lines, long lines) that is syntactically valid Python. `pyproject.toml` sets `line-length = 88`.
- **Prompt to agent:** "Reformat `messy.py` so that `ruff format --check messy.py` passes. The module's AST (functions, classes, control flow, literal values) must be unchanged."
- **Pass criterion:**
  1. `ruff format --check messy.py` exits 0.
  2. AST equality: grader parses pre-state and post-state with `ast.parse` and compares via `ast.dump(node, annotate_fields=True, include_attributes=False)`. The two dumps must be identical (this catches semantic changes while ignoring whitespace).
  3. File still imports cleanly (`python -c "import messy"` exits 0).
- **Why a skilled agent should outperform:** A formatting skill triggers the agent to run the formatter or to write formatter-compliant code by default. A no-skill agent often "fixes" formatting and accidentally renames a variable or changes a literal.
- **Adversarial counterpoint:** Skill could just call `ruff format` and overwrite the file blindly. That actually *passes* this task — which is fine, because passing means the goal is met. The adversarial concern is the *opposite*: skill modifies the AST. The AST-equality check is the mitigation.
- **License:** MIT.

---

#### `style-adherence-04` — TypeScript `tsc --strict` + ESLint zero-findings

- **One-sentence description:** Implement a small TypeScript utility module that passes `tsc --strict --noEmit` and `eslint --max-warnings=0` with the project's pinned configs.
- **Pre-state:** A minimal `package.json` (deps pre-installed in the sandbox image, no network needed at run time), `tsconfig.json` with `strict: true`, `.eslintrc.json` with `@typescript-eslint/recommended` + a few stylistic rules, an empty `src/parse-duration.ts`, and a `src/parse-duration.test.ts` (Jest, also pre-installed) that exercises the spec.
- **Prompt to agent:** "Implement `parseDuration` in `src/parse-duration.ts` to convert strings like `'1h30m'`, `'45s'`, `'2d'` into milliseconds. It must satisfy the tests, pass `tsc --strict --noEmit`, and pass `eslint --max-warnings=0`."
- **Pass criterion:**
  1. `npx tsc --strict --noEmit` exits 0.
  2. `npx eslint src/parse-duration.ts --max-warnings=0` exits 0.
  3. `npx jest src/parse-duration.test.ts` exits 0.
  4. Grader hashes `tsconfig.json`, `.eslintrc.json`, `package.json` before/after — agent must not have weakened the configs.
- **Why a skilled agent should outperform:** A TS-style skill removes `any`, adds proper type narrowing, and avoids the lint pitfalls (unused vars, non-null assertions, etc.). This is a known weak spot of base models on first attempt.
- **Adversarial counterpoint:** Skill could `// @ts-ignore` or `/* eslint-disable */`. Mitigation: grader greps the final file for `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `// eslint` and fails on any match.
- **License:** MIT. Node modules pinned in image: TypeScript 5.x, ESLint 9.x, Jest 29.x — exact versions captured in image SHA per Phase 3.6.

---

### 2.4 Category: Refactoring (4 tasks)

**Claim under test:** "This skill makes the agent refactor without breaking behaviour."

The discriminator is **(pre-test-suite passes) AND (post-test-suite passes) AND (a structural change actually occurred)**. The first two clauses verify behaviour preservation; the third prevents the trivial "do nothing" win. All four tasks ship a passing test suite the agent must not break.

---

#### `refactor-01` — Extract method

- **One-sentence description:** A 60-line `process_order` function has a clear sub-block that should be extracted into a helper; refactor without changing behaviour.
- **Pre-state:** `orders.py` with a long `process_order(order)` function containing a 20-line tax-calculation sub-block. `test_orders.py` with 8 passing tests.
- **Prompt to agent:** "Refactor `process_order` in `orders.py` to extract the tax-calculation sub-block (lines computing `tax_amount`) into a separate helper function called `_compute_tax`. All existing tests must still pass. Do not change observable behaviour."
- **Pass criterion:**
  1. `pytest -q` exits 0 on the pre-state (grader runs once before handing off; if pre-state tests fail, the task is broken — flag, not the agent's fault).
  2. After the agent finishes, `pytest -q` exits 0 again.
  3. AST inspection of post-state `orders.py`: a `FunctionDef` named `_compute_tax` exists at module scope. The `process_order` function body must contain a `Call` to `_compute_tax`. The `process_order` function body length (in AST nodes, counted via `sum(1 for _ in ast.walk(fn))`) must be at most 70% of the pre-state length — confirms the sub-block was actually extracted, not duplicated.
  4. Edge case: agent could create `_compute_tax` but never call it. The `Call`-to-`_compute_tax` check catches that.
- **Why a skilled agent should outperform:** A refactor skill internalises "extract method" as a primitive and produces a clean result; a no-skill agent may over-refactor or break tests.
- **Adversarial counterpoint:** Skill could rename the existing tax-block as `_compute_tax` without restructuring, satisfying both the function-exists and the call-exists checks. Mitigation: the 70%-of-original-length check verifies real extraction; if the agent merely added a wrapper, the original function body shrinks below threshold.
- **License:** MIT.

---

#### `refactor-02` — Replace conditional with polymorphism

- **One-sentence description:** A `calculate_pay(employee)` function with a 4-branch `if/elif` on `employee.type` should be refactored into a polymorphic dispatch.
- **Pre-state:** `payroll.py` with `class Employee` and a `calculate_pay` function with `if employee.type == 'hourly': ... elif 'salaried' ... elif 'commission' ... elif 'contractor' ...`. 12 passing tests.
- **Prompt to agent:** "Refactor `payroll.py` to replace the conditional in `calculate_pay` with polymorphism: introduce subclasses (or a strategy registry) so that adding a new employee type does not require editing `calculate_pay`. All tests must still pass."
- **Pass criterion:**
  1. Pre-state tests pass (sanity check).
  2. Post-state tests pass.
  3. AST inspection: in the post-state `calculate_pay` function (or its replacement), the number of `If` nodes whose `test` is a `Compare` against `employee.type` (string literal) is **zero**. (Grader walks the AST looking for `Compare` with `Attribute(value=Name('employee'), attr='type')` as either side.)
  4. AST inspection: ≥4 new classes inheriting from a common base, **or** a module-level dict/registry mapping the four type-strings to callables exists.
- **Why a skilled agent should outperform:** This is a textbook refactor; skill content directly maps to the structural change.
- **Adversarial counterpoint:** Skill could keep the if/elif but rename the variable, evading the AST check. Mitigation: criterion (3) uses semantic AST inspection (any `Compare` with `.type` attribute, regardless of variable name reachable from the function's args). Also: criterion (4) requires the actual polymorphic structure to exist.
- **License:** MIT.

---

#### `refactor-03` — Pull-up duplicated code

- **One-sentence description:** Two classes contain a duplicated 15-line method; refactor by pulling the method up into a shared base class.
- **Pre-state:** `shapes.py` with `class Square` and `class Rectangle`, each with an identical `serialize_to_json(self)` method. 6 passing tests.
- **Prompt to agent:** "Refactor `shapes.py` so the duplicated `serialize_to_json` lives in a single shared base class. All tests must still pass."
- **Pass criterion:**
  1. Pre-state tests pass.
  2. Post-state tests pass.
  3. AST inspection: `serialize_to_json` is defined exactly once in the post-state module (count `FunctionDef` nodes with `name == 'serialize_to_json'`; must equal 1). It must be defined inside a `ClassDef` that is a parent (direct or via `bases`) of both `Square` and `Rectangle`.
  4. Edge case: agent could delete one of the duplicates and `serialize_to_json` would still exist once, but Square would no longer have access. Tests must still pass, which forces the inheritance link.
- **Why a skilled agent should outperform:** DRY-and-pull-up is a refactor skill's bread and butter.
- **Adversarial counterpoint:** Skill could move the method to a module-level function and have both classes call it. That doesn't satisfy criterion (3) (must be inside a ClassDef that is a base). The prompt is explicit about "shared base class".
- **License:** MIT.

---

#### `refactor-04` — Rename + introduce parameter object

- **One-sentence description:** A `send_notification` function with 7 positional parameters should be refactored to take a `NotificationRequest` dataclass; all 12 call sites across 3 files must be updated.
- **Pre-state:** `notifications.py` defining `send_notification(recipient, channel, subject, body, priority, attempt, dry_run)`. `mailer.py` and `webhook.py` each have call sites. `test_notifications.py` with 12 passing tests, each calling `send_notification` positionally.
- **Prompt to agent:** "Refactor `send_notification` in `notifications.py` to take a single `NotificationRequest` dataclass instead of 7 positional parameters. Update all call sites in `mailer.py` and `webhook.py` (and tests, if needed). All tests must still pass."
- **Pass criterion:**
  1. Pre-state tests pass.
  2. Post-state tests pass.
  3. AST inspection: `notifications.py` defines `class NotificationRequest` decorated with `@dataclass` (or a class containing the 7 expected attribute names: `recipient, channel, subject, body, priority, attempt, dry_run`).
  4. `send_notification` post-state has exactly one non-`self` parameter (AST walk: count `arg` nodes in `args.args` excluding `self`).
  5. AST inspection of `mailer.py` and `webhook.py`: every `Call` to `send_notification` has either exactly 1 positional arg OR a single keyword arg.
- **Why a skilled agent should outperform:** This is a cross-file refactor with consistent ripple-out — a "refactor-aware" skill insists on updating every call site. A no-skill agent often updates the definition and forgets one or two callers.
- **Adversarial counterpoint:** Skill could leave callers using positional 7-tuple-style by adding `**kwargs` to `send_notification`. Mitigation: criterion (4) caps the signature at one non-self parameter, no `*args` / `**kwargs`. Grader walks `args.vararg` and `args.kwarg` and fails if either is non-`None`.
- **License:** MIT.

---

### 2.5 Category: Multi-file reasoning (4 tasks)

**Claim under test:** "This skill helps the agent reason across multiple files."

The discriminator is **whether the agent's changes touch all required files**, detected by comparing the post-state to the pre-state per file (SHA changes for required files, SHA stable for forbidden files). All four tasks plant an inconsistency across 2+ files that must be jointly fixed.

---

#### `multi-file-01` — Rename + update all callers

- **One-sentence description:** Rename a function `compute_total` → `compute_subtotal` in its definition file; the agent must find and update all 7 callers in 4 other files.
- **Pre-state:** `pricing.py` defines `compute_total`. Files `cart.py`, `checkout.py`, `report.py`, `tests/test_pricing.py` import and call it (5, 1, 1, 1 callers respectively; sum = 8 references = 1 def + 7 calls). The test file is passing.
- **Prompt to agent:** "Rename the function `compute_total` to `compute_subtotal` throughout the codebase. All existing tests must still pass. Do not leave any reference to the old name."
- **Pass criterion:**
  1. `pytest -q` exits 0 post-state.
  2. Grader greps recursively for `\bcompute_total\b` across the workdir; zero matches required. (Regex with word boundaries to avoid partial-name false positives.)
  3. Grader greps for `\bcompute_subtotal\b`; count must equal pre-state's `compute_total` count (8).
  4. Each of `pricing.py`, `cart.py`, `checkout.py`, `report.py`, `tests/test_pricing.py` must have a different SHA than pre-state.
- **Why a skilled agent should outperform:** A multi-file-aware skill triggers a full-repo grep before declaring done; a no-skill agent may update only the obvious callers and miss one.
- **Adversarial counterpoint:** Skill could add `compute_total = compute_subtotal` alias at the bottom of `pricing.py`, leaving old call sites working — but criterion (2) (zero `compute_total` references) catches that.
- **License:** MIT.

---

#### `multi-file-02` — Schema drift between producer and consumer

- **One-sentence description:** A producer file emits JSON with key `user_id`; a consumer file reads key `userId`; add a key to the producer and the agent must update both ends consistently.
- **Pre-state:** `producer.py` builds `{"user_id": ..., "event": ...}` and `consumer.py` reads `data["user_id"]` and `data["event"]`. A `bridge_test.py` round-trips an event end-to-end and currently passes. The agent is told to add a new field `timestamp_ms`.
- **Prompt to agent:** "Extend the event schema with a new field `timestamp_ms` (int, Unix milliseconds). Update `producer.py` to emit it and `consumer.py` to read and use it (print `'event at <timestamp_ms>'`). All tests must still pass; add at least one new test asserting the field round-trips."
- **Pass criterion:**
  1. `pytest -q` exits 0.
  2. `producer.py` post-state contains the string literal `"timestamp_ms"` (in a dict-key context, verified by AST: a `Dict` node with a `Constant("timestamp_ms")` key).
  3. `consumer.py` post-state contains a subscript access whose `slice` is `Constant("timestamp_ms")`.
  4. `bridge_test.py` post-state contains an `Assert` (or `assert` statement) whose AST mentions the literal `"timestamp_ms"`.
  5. Grader runs a hidden round-trip script: `from producer import build_event; from consumer import handle_event; handle_event(build_event(...))` and inspects stdout for `'event at '`.
- **Why a skilled agent should outperform:** A cross-file-reasoning skill encourages the agent to grep the codebase for the schema shape before editing; a no-skill agent may update only the producer and forget the consumer end (or vice versa).
- **Adversarial counterpoint:** Skill could pass criteria (2) and (3) by literally inserting the substring `timestamp_ms` as a comment in both files. Mitigation: AST-context checks — must be a dict-key Constant in producer and a Subscript-slice Constant in consumer, not a comment.
- **License:** MIT.

---

#### `multi-file-03` — Migration: deprecate one helper, update three usages

- **One-sentence description:** Delete a deprecated helper in `utils.py` and migrate its three call sites (in 3 different files) to a documented replacement.
- **Pre-state:** `utils.py` defines `format_currency_old(amount)` (deprecated, marked with a `# DEPRECATED: use format_currency` comment) and `format_currency(amount, locale='en_US')`. Three files (`invoices.py`, `receipts.py`, `summary.py`) each call `format_currency_old`. Tests pass.
- **Prompt to agent:** "Remove `format_currency_old` from `utils.py` and migrate the three call sites in `invoices.py`, `receipts.py`, `summary.py` to use `format_currency` instead. Use the default `locale='en_US'`. Tests must still pass."
- **Pass criterion:**
  1. `pytest -q` exits 0.
  2. `format_currency_old` does not appear in `utils.py` (grep), and there is no `FunctionDef` with that name in the AST.
  3. Grader greps `\bformat_currency_old\b` across workdir: zero matches.
  4. Each of `invoices.py`, `receipts.py`, `summary.py` has a different SHA than pre-state, and each contains at least one `Call` to `format_currency` (AST: `Call(func=Name("format_currency"))` or `Call(func=Attribute(attr="format_currency"))`).
- **Why a skilled agent should outperform:** A migration-aware skill encourages "delete-and-replace, verify nothing references the dead symbol"; no-skill agents often delete the symbol and forget a caller, breaking tests.
- **Adversarial counterpoint:** Skill could shadow `format_currency_old` by aliasing it to `format_currency` in `utils.py` (e.g., `format_currency_old = format_currency`). Mitigation: criterion (2) explicitly rejects any reference to the name in `utils.py`; criterion (3) rejects it anywhere in the workdir.
- **License:** MIT.

---

#### `multi-file-04` — Type-signature change ripples through imports

- **One-sentence description:** A function's return type changes from `list[int]` to `tuple[int, ...]`; agent must update three importing modules and their tests so `mypy --strict` and `pytest` both pass.
- **Pre-state:** `core.py` defines `def get_values() -> list[int]:`. Three modules (`analytics.py`, `export.py`, `cache.py`) import and treat the return as a list (e.g., calling `.append`). `tests/` has tests that exercise each consumer. `mypy.ini` sets strict mode. Pre-state passes both `pytest` and `mypy --strict`.
- **Prompt to agent:** "Change `get_values` in `core.py` to return `tuple[int, ...]` instead of `list[int]`. Update all consumers (`analytics.py`, `export.py`, `cache.py`) and their tests so that `pytest` passes and `mypy --strict .` reports zero errors."
- **Pass criterion:**
  1. `pytest -q` exits 0 post-state.
  2. `mypy --strict .` exits 0 post-state.
  3. AST inspection of `core.py`: `get_values`'s return annotation is a `Subscript` whose `value` is `Name("tuple")` (or equivalent `typing.Tuple`).
  4. Each of `analytics.py`, `export.py`, `cache.py` has a different SHA than pre-state.
  5. Grader greps each consumer for `.append(` and `.extend(` — zero matches (tuples don't have these methods; lingering calls indicate incomplete migration even if mypy is satisfied somehow).
- **Why a skilled agent should outperform:** A cross-file-typing skill makes the agent run `mypy` and walk all errors before declaring done; a no-skill agent may patch the producer and miss two consumers.
- **Adversarial counterpoint:** Skill could cast the tuple back to a list at each consumer (`list(get_values())`) without restructuring — that is, technically, a valid fix. We accept this as a legitimate pass; the spirit of the task is "you noticed and propagated", not "you used the new type idiomatically". If we wanted to forbid it, we'd add a check; we explicitly do not, because banning legitimate workarounds rewards rigidity over correctness.
- **License:** MIT.

---

## 3. Appendix

### Appendix A — YAML schema stub (canonical: master prompt §4.2)

```yaml
id: <kebab-case-id>                   # e.g., tdd-enforcement-01
category: <category-slug>             # one of: tdd-enforcement, code-review,
                                      # style-adherence, refactor, multi-file
description: "≤200 char one-liner."
license: MIT                          # SPDX identifier
setup:
  files:                              # files materialized in sandbox cwd at t=0
    "path/relative/to/workdir.ext": |
      file contents, including trailing newline
prompt: |                             # the prompt fed to the agent (verbatim)
  Agent prompt, 1–3 sentences typically.
grader:
  type: python                        # only "python" supported in v1
  script: |
    # Receives:
    #   workdir:    pathlib.Path to the final filesystem state
    #   trajectory: list[dict] of tool-call records (see §1.6)
    #   prestate:   dict[str, bytes] of pre-state file contents (for SHA compare)
    # Returns: {"passed": bool, "details": {...}}
    ...
time_budget_s: 300                    # 60–300 in v1; default 300
expected_tokens: 5000                 # rough integer; used only by cost-normalisation
network: false                        # always false in v1
```

### Appendix B — Shared grader utilities (single module: `src/agenteval/grading/utils.py`)

To keep graders short and consistent, the M1/M4 implementation should land **one** utility module that every task's grader imports. Required helpers, derived from recurring patterns in §2:

1. `file_write_order(trajectory, paths) -> list[tuple[str, float]]` — returns the ordered list of (path, first-write timestamp) for the given paths, or raises if any path was never written. Used by all 4 TDD tasks.
2. `pytest_failures_between(trajectory, t0, t1) -> int` — counts `pytest` invocations whose `result.stdout` matches `\b(\d+) failed\b` between the two timestamps. Used by TDD-01, 02, 03, 04.
3. `count_ast_nodes(source, node_type, name=None) -> int` — wraps `ast.walk` for "how many `FunctionDef` nodes named `X`" patterns. Used by refactor and multi-file tasks.
4. `ast_equal(src_a, src_b) -> bool` — `ast.dump` comparison with attributes stripped. Used by style-adherence-03.
5. `sha256_of_file(path) -> str` — for pre/post-state hash comparison (style + multi-file tasks).
6. `grep_word(workdir, pattern, exclude_paths=()) -> int` — recursive ripgrep-equivalent with word-boundary support; returns match count. Used by multi-file tasks.
7. `run_in_workdir(cmd, workdir, timeout=60) -> CompletedProcess` — subprocess wrapper with hard timeout and combined stdout/stderr capture. Used by every linter / pytest invocation. Logs to grader's details dict on failure.
8. `match_keywords_with_localization(message, keywords, localization_regexes, window=200) -> bool` — used by all 4 code-review tasks to enforce "keyword present AND localised to the bug site within a 200-char window of the keyword match".
9. `assert_no_suppressions(source, markers) -> bool` — fails on `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `@ts-expect-error`. Used by style tasks.
10. `equivalent_runtime_behaviour(module_a, module_b, fixtures) -> bool` — imports both versions in isolated subprocesses, runs each through the fixtures, compares return types and string representations. Used by style-adherence-02 and (optionally) refactor tasks.

These are the **only** grader-side imports allowed beyond the Python standard library and the linters / pytest pinned in the sandbox image. No `numpy`, no LLM calls, no network.

### Appendix C — Adversarial summary table

The full adversarial-defence document for the project lives at `docs/adversarial.md` (stub; written in Phase 3.6). This table is the task-set-local extract: every gaming strategy a malicious skill could attempt against the 20 tasks above, and the grader-side mitigation. Mirrors the structure of `docs/adversarial.md` so the two can be cross-linked.

| # | Task(s) | Gaming strategy | Mitigation in grader |
|---|---|---|---|
| 1 | tdd-01 | Emit `assert True` × 4 to satisfy assertion-count gate. | Mutation-driven assertion-strength check; if mutating an impl branch leaves all tests green, fail. |
| 2 | tdd-02 | Hard-code Roman-numeral lookup table for visible tests. | Hidden test bank with edge values (4, 9, 40, 400, 3999) that require decomposition. |
| 3 | tdd-03 | Write the failing test with the buggy expected value (`== -900`) so the test trivially passes pre-fix. | Final-state check `apply_discount(100, 10) == 90` runs independently of agent tests. |
| 4 | tdd-04 | Fragment test authorship into ≥3 writes with a no-op test in between. | Grader requires each pytest failure to name a test_ function that was just *added* in the immediately prior write. |
| 5 | code-review-01..04 | Shotgun list every bug taxonomy regardless of code. | Localisation regex — keyword must co-occur with the literal symbol/expression within 200 chars. |
| 6 | code-review-01..04 | Modify the file under review despite "do not modify". | Pre/post SHA equality check on the reviewed file. |
| 7 | style-01 | Weaken `pyproject.toml` ruff config. | SHA of `pyproject.toml` (and `mypy.ini`, `.eslintrc.json`, `tsconfig.json` analogously) must equal pre-state. |
| 8 | style-01, 02, 04 | Add `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`. | `assert_no_suppressions` grep on the final agent-authored files. |
| 9 | style-03 | Reformat by overwriting with `ruff format` output blindly, including semantic changes. | `ast.dump` equality between pre- and post-state files (formatter must preserve AST). |
| 10 | refactor-01 | Create `_compute_tax` but never call it (or duplicate code). | AST check: `_compute_tax` must be `Call`-referenced from `process_order`, and `process_order` length must drop ≥30%. |
| 11 | refactor-02 | Keep if/elif but rename the discriminator variable. | Semantic AST scan for any `Compare` against `Attribute(attr='type')`. |
| 12 | refactor-03 | Move duplicated method to a module-level function instead of a base class. | AST check: single `FunctionDef` must live inside a `ClassDef` that is a base of both `Square` and `Rectangle`. |
| 13 | refactor-04 | Use `**kwargs` to keep old call shape working. | AST check: post-state signature must have exactly 1 non-self positional, no `vararg`, no `kwarg`. |
| 14 | multi-file-01 | Alias `compute_total = compute_subtotal` to keep callers working. | Repo-wide grep for `\bcompute_total\b` requires zero matches. |
| 15 | multi-file-02 | Insert `timestamp_ms` as a comment-only token in producer/consumer. | AST-context check: must be Dict-key Constant in producer, Subscript-slice Constant in consumer. |
| 16 | multi-file-03 | Re-bind `format_currency_old = format_currency` in `utils.py`. | Grep `\bformat_currency_old\b` across workdir requires zero matches. |
| 17 | multi-file-04 | Cast tuple back to list at each consumer (`list(get_values())`). | Accepted as legitimate; grader explicitly does not penalise. Documented above. |
| 18 | All categories | High-cost / high-token-count skill that grinds through every check by brute force. | Per-task cost and tool-call-count metrics surfaced harness-wide; the pareto-frontier display in the leaderboard frontend (master prompt §4.6) ensures cost-burning skills don't dominate single-axis ranking. |
| 19 | All categories | Skill bundles a pre-computed answer for one of the 20 tasks. | Phase 3.4 documents hidden-holdout-task rotation; v1 acknowledges this as a known limitation in `docs/methodology.md`. |
| 20 | All categories | Skill nondeterministically wins pass@5 but loses pass@1. | pass@1 and pass@5 both reported; pass@5 ≥ 2× pass@1 flags entry as "high-variance" (master prompt §4.3). |

---

End of `skill-specific-v1` task-set specification. Phase 2 M1 implements tasks 1 from each category (5 total: tdd-01, code-review-01, style-01, refactor-01, multi-file-01). Phase 2 M4 implements the remaining 15.
