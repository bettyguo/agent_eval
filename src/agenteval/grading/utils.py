"""Shared grader utilities (docs/tasks.md §3.5).

Each utility is pure (no network, no side effects on the host outside the
optional grader subprocess). Tested in tests/test_grading_utils.py with
synthetic inputs.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path

from agenteval.grading.types import TrajectoryStep


def first_modify_time(
    trajectory: Sequence[TrajectoryStep],
    path: str,
    *,
    body_change: bool = False,
) -> float | None:
    """Earliest trajectory `t` at which `path` was written/edited.

    If `body_change=True`, only count edits that changed the body of a function
    (heuristic: the resulting file contains a function whose body is not `pass`
    or `raise NotImplementedError`). Tracked via the step's result["body_changed"]
    where the harness sets that flag.
    """
    normalised = _norm(path)
    for step in trajectory:
        if step.tool not in ("Write", "Edit"):
            continue
        step_path = step.args.get("path") or step.args.get("file_path") or ""
        if _norm(step_path) != normalised:
            continue
        if body_change and not step.result.get("body_changed", True):
            # If the harness didn't annotate, default to True (treat any edit as a body change).
            continue
        return step.t
    return None


def ran_pytest_failure_then_success(trajectory: Sequence[TrajectoryStep]) -> bool:
    """True iff trajectory contains a failing pytest run strictly followed by a passing one."""
    seen_failure = False
    for step in trajectory:
        if step.tool != "Bash":
            continue
        cmd = (step.args.get("command") or "").strip()
        if "pytest" not in cmd:
            continue
        exit_code = step.result.get("exit_code", 0)
        if not seen_failure:
            if exit_code != 0:
                seen_failure = True
        else:
            if exit_code == 0:
                return True
    return False


def count_assertions(path: str | Path) -> int:
    """Count `Assert` AST nodes in a Python source file. 0 on parse error."""
    p = Path(path)
    if not p.exists():
        return 0
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))


def grep_final_message(msg: str, patterns: Iterable[str]) -> bool:
    """True iff any regex in `patterns` matches `msg` (case-insensitive)."""
    if not msg:
        return False
    for pat in patterns:
        if re.search(pat, msg, re.IGNORECASE):
            return True
    return False


def localizes_to_line(
    msg: str,
    file: str,
    expected_line: int,
    tolerance: int = 2,
) -> bool:
    """True iff `msg` mentions `file` with a line number within `tolerance` of `expected_line`.

    Looks for patterns like `file:LINE`, `line LINE`, `at line LINE`, `(LINE,...)`.
    """
    if not msg:
        return False
    file_name = Path(file).name
    if file_name.lower() not in msg.lower():
        return False
    # Try several common line-number forms
    candidates: list[int] = []
    candidates += [int(m) for m in re.findall(rf"{re.escape(file_name)}:(\d+)", msg, re.IGNORECASE)]
    candidates += [int(m) for m in re.findall(r"line\s+(\d+)", msg, re.IGNORECASE)]
    candidates += [int(m) for m in re.findall(r"L(\d+)", msg)]
    for line in candidates:
        if abs(line - expected_line) <= tolerance:
            return True
    return False


def run_command(
    argv: Sequence[str],
    cwd: str | Path,
    *,
    timeout: float = 60.0,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Spawn a subprocess; return (exit_code, combined_stdout+stderr).

    No shell expansion. Used by graders to invoke pytest, ruff, mypy. The
    sandbox layer enforces the actual isolation (see src/agenteval/sandbox/).
    """
    try:
        proc = subprocess.run(
            list(argv),
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {' '.join(argv)}"
    combined = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, combined


def assert_unchanged(path: str | Path, expected_sha: str) -> None:
    """Raise AssertionError if `path`'s SHA256 differs from `expected_sha`."""
    p = Path(path)
    if not p.exists():
        raise AssertionError(f"expected unchanged file does not exist: {p}")
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    if actual != expected_sha:
        raise AssertionError(
            f"{p} hash mismatch: expected {expected_sha[:12]}…, got {actual[:12]}…"
        )


def no_suppressions(path: str | Path, forbidden: Iterable[str]) -> bool:
    """True iff none of the `forbidden` substrings appears in the file content."""
    p = Path(path)
    if not p.exists():
        return True  # no file, no suppressions
    text = p.read_text(encoding="utf-8")
    for tag in forbidden:
        if tag in text:
            return False
    return True


def ast_function_count(path: str | Path) -> int:
    """Count top-level + nested function/method definitions in a Python source file."""
    p = Path(path)
    if not p.exists():
        return 0
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    return sum(
        1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def ast_normalised_equal(path_a: str | Path, path_b: str | Path) -> bool:
    """True iff two Python files have equal ASTs after normalization.

    Normalization here is conservative: strip docstrings and whitespace, parse,
    dump with the standard `ast.dump`. Cosmetic reformatting (blank lines,
    indentation, comments) does not affect AST equality.
    """
    a = _ast_dump_no_docstrings(Path(path_a))
    b = _ast_dump_no_docstrings(Path(path_b))
    return a == b


def grep_repo(
    root: str | Path,
    pattern: str,
    *,
    exclude: Iterable[str] = (),
) -> list[tuple[Path, int, str]]:
    """Recursive regex grep across `root`. Returns [(path, lineno, line), ...]."""
    root_path = Path(root)
    excluded = set(exclude)
    regex = re.compile(pattern)
    matches: list[tuple[Path, int, str]] = []
    for f in root_path.rglob("*"):
        if not f.is_file():
            continue
        if any(part in excluded for part in f.parts):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append((f, i, line))
    return matches


# ---------- internal helpers ----------


def _norm(path: str) -> str:
    return path.replace("\\", "/").lstrip("./").rstrip("/")


def _ast_dump_no_docstrings(path: Path) -> str:
    if not path.exists():
        return f"<missing:{path}>"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return ast.dump(tree, annotate_fields=False, include_attributes=False)
