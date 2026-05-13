"""agenteval CLI (DESIGN.md §1.3).

M1 implements `eval`, `dry-run`, `inspect`, `version`. `submit`, `verify`,
`leaderboard` arrive in M5/M6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from agenteval import __version__
from agenteval.errors import AgentevalError
from agenteval.harness import CANONICAL_SEEDS, Harness
from agenteval.metrics import load_pricing
from agenteval.runners.anthropic import AnthropicRunner
from agenteval.runners.google import GoogleRunner
from agenteval.runners.openai import OpenAIRunner
from agenteval.skills.bundle import SkillBundle
from agenteval.submit import verify_entry
from agenteval.tasks.registry import BUILTIN_TASK_SETS, TaskSet

console = Console()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="agenteval")
def main() -> None:
    """agenteval — reproducible benchmark for Claude Code skills."""


@main.command()
def version() -> None:
    """Print the agenteval version."""
    click.echo(__version__)


@main.command(name="eval")
@click.option(
    "--skills",
    type=str,
    required=True,
    help="Path to a .claude/skills/ directory, a CLAUDE.md file, or the literal string 'none'.",
)
@click.option(
    "--tasks",
    type=str,
    required=True,
    help="Built-in task-set name (e.g. 'skill-specific-v1') or path to a task-set directory.",
)
@click.option(
    "--runner",
    type=click.Choice(["anthropic", "openai", "google"]),
    default="anthropic",
    show_default=True,
    help="Runner backend. M3+ supports all three.",
)
@click.option(
    "--model",
    type=str,
    required=True,
    help="Exact API model string (e.g. 'claude-opus-4-7').",
)
@click.option(
    "--temperature",
    type=float,
    default=0.0,
    show_default=True,
    help="Sampling temperature; must be 0.0 for leaderboard entries.",
)
@click.option(
    "--seeds",
    type=int,
    default=None,
    help="Number of seeds to use in exploratory mode. Omit for canonical leaderboard seeds [1,2,3,4,5].",
)
@click.option(
    "--exploratory",
    is_flag=True,
    default=False,
    help="Run in non-leaderboard exploratory mode (custom seeds, non-canonical).",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write result JSON to this path. Omit to print to stdout.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the run plan and exit without making API calls.",
)
@click.option(
    "--remote",
    type=str,
    default=None,
    help="SSH host (user@host or host) to run the eval on remotely. See docs/remote-runner.md.",
)
def eval_cmd(
    skills: str,
    tasks: str,
    runner: str,
    model: str,
    temperature: float,
    seeds: int | None,
    exploratory: bool,
    out: Path | None,
    dry_run: bool,
    remote: str | None,
) -> None:
    """Run an evaluation."""
    if remote is not None:
        if dry_run:
            _die(AgentevalError("--remote is incompatible with --dry-run"))
        if out is None:
            _die(AgentevalError("--remote requires --out <path>"))
        assert out is not None  # narrowed by _die() above but mypy doesn't infer NoReturn here
        from agenteval.remote import run_remote

        try:
            rc = run_remote(
                remote_host=remote,
                skill_bundle_path=skills,
                task_set=tasks,
                model=model,
                runner=runner,
                temperature=temperature,
                exploratory=exploratory,
                seeds=seeds,
                out_path=out,
            )
            sys.exit(rc)
        except AgentevalError as exc:
            _die(exc)

    try:
        bundle = _load_bundle(skills)
        task_set = _load_task_set(tasks)
    except AgentevalError as exc:
        _die(exc)

    if dry_run:
        _print_dry_run(bundle, task_set, model, runner)
        return

    if exploratory:
        canonical = False
        custom_seeds = list(range(1, (seeds or 1) + 1))
    else:
        if seeds is not None and seeds != len(CANONICAL_SEEDS):
            _die(
                AgentevalError(
                    f"leaderboard runs use canonical seeds {list(CANONICAL_SEEDS)} (5 seeds). "
                    f"For other seed counts, use --exploratory."
                )
            )
        canonical = True
        custom_seeds = None

    runner_obj: Any
    if runner == "anthropic":
        runner_obj = AnthropicRunner(model=model, temperature=temperature)
    elif runner == "openai":
        runner_obj = OpenAIRunner(model=model, temperature=temperature)
    elif runner == "google":
        runner_obj = GoogleRunner(model=model, temperature=temperature)
    else:
        _die(AgentevalError(f"unsupported runner: {runner!r}"))
        return

    try:
        pricing = load_pricing()
    except AgentevalError:
        pricing = None
    harness = Harness(
        runner=runner_obj,
        model=model,
        provider=runner,
        temperature=temperature,
        canonical_seeds=canonical,
        custom_seeds=custom_seeds,
        pricing=pricing,
    )

    try:
        result = harness.evaluate(bundle, task_set)
    except AgentevalError as exc:
        _die(exc)

    _print_summary(result)

    if out is not None:
        payload = (
            result.to_leaderboard_entry()
            if result.leaderboard_eligible
            else {
                "leaderboard": False,
                "summary": result.summary(),
                "per_attempt": [a.as_dict() for a in result.per_attempt],
                "task_set": result.task_set_name,
                "task_set_hash": result.task_set_hash,
                "bundle_hash": result.bundle_hash,
                "model": result.model,
                "temperature": result.temperature,
                "seeds": list(result.seeds),
            }
        )
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[green]wrote[/green] {out}")


@main.command(name="dry-run")
@click.option("--skills", required=True)
@click.option("--tasks", required=True)
@click.option("--model", required=True)
@click.option("--runner", default="anthropic", show_default=True)
def dry_run_cmd(skills: str, tasks: str, model: str, runner: str) -> None:
    """Show the plan + estimated cost without making API calls."""
    try:
        bundle = _load_bundle(skills)
        task_set = _load_task_set(tasks)
    except AgentevalError as exc:
        _die(exc)
    _print_dry_run(bundle, task_set, model, runner)


@main.command()
@click.argument("result_json", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--task", "task_id", required=True, help="Task id to inspect.")
@click.option("--seed", type=int, required=True, help="Seed of the attempt to inspect.")
def inspect(result_json: Path, task_id: str, seed: int) -> None:
    """Inspect a single (task, seed) attempt from a result JSON."""
    data = json.loads(result_json.read_text(encoding="utf-8"))
    attempts = data.get("per_attempt") or data.get("summary", {}).get("per_attempt") or []
    for a in attempts:
        if a.get("task_id") == task_id and a.get("seed") == seed:
            console.print_json(data=a)
            return
    _die(AgentevalError(f"no attempt with task={task_id!r} seed={seed} in {result_json}"))


@main.command()
@click.argument("result_json", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the canonical LeaderboardEntry JSON to this path (defaults to <result>.entry.json).",
)
def submit(result_json: Path, out: Path | None) -> None:
    """Convert a leaderboard-eligible result JSON into the canonical LeaderboardEntry.

    No network involved in v1 — the leaderboard accepts submissions via PR. This
    command produces the JSON the PR should add to `frontend/data/submissions/`.
    """
    data = json.loads(result_json.read_text(encoding="utf-8"))
    if data.get("leaderboard") is False:
        _die(AgentevalError("result is tagged leaderboard:false; was --exploratory used?"))
    if "entry_hash" in data:
        # Already a leaderboard entry — round-trip OK.
        entry = data
    else:
        # Reconstruct from the live Result-flavoured dict produced by `eval`.
        entry = data
        if "metrics" not in entry:
            _die(AgentevalError("input JSON does not look like a leaderboard-eligible result"))
    out_path = out or result_json.with_suffix(".entry.json")
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    console.print(f"[green]wrote[/green] {out_path}")


@main.command()
@click.argument("entry_json", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--skills",
    required=True,
    help="Path to a .claude/skills/ dir (or 'none') matching the entry's bundle hash.",
)
@click.option(
    "--tasks",
    required=True,
    help="Built-in task-set name or path; must match the entry's task_set hash.",
)
def verify(entry_json: Path, skills: str, tasks: str) -> None:
    """Re-run a submitted entry from scratch and compare structured features.

    Per anti-pattern #10: every leaderboard entry should be verified in TWO
    different cloud VMs. This command performs a single-VM verification; CI
    aggregates.
    """
    entry = json.loads(entry_json.read_text(encoding="utf-8"))
    try:
        bundle = _load_bundle(skills)
        task_set = _load_task_set(tasks)
    except AgentevalError as exc:
        _die(exc)

    report = verify_entry(entry, skill_bundle=bundle, task_set=task_set)
    console.print_json(data=report.as_dict())
    if not report.verified:
        sys.exit(4)


# ---------- helpers ----------


def _load_bundle(spec: str) -> SkillBundle:
    if spec == "none":
        return SkillBundle.empty()
    p = Path(spec)
    if p.is_file() and p.suffix.lower() == ".md":
        return SkillBundle.from_claude_md(p)
    if p.is_dir():
        # An empty dir under the no-skills convention is also OK.
        if not any(p.iterdir()):
            return SkillBundle.empty()
        return SkillBundle.from_dir(p)
    raise AgentevalError(f"--skills must be 'none', a CLAUDE.md file, or a directory; got {spec!r}")


def _load_task_set(spec: str) -> TaskSet:
    if spec in BUILTIN_TASK_SETS:
        return TaskSet.load(spec)
    p = Path(spec)
    if p.is_dir():
        return TaskSet.from_dir(p)
    raise AgentevalError(
        f"--tasks must be a built-in name ({sorted(BUILTIN_TASK_SETS)}) or a directory; got {spec!r}"
    )


def _print_dry_run(bundle: SkillBundle, task_set: TaskSet, model: str, runner: str) -> None:
    table = Table(title="agenteval — dry run")
    table.add_column("field")
    table.add_column("value")
    table.add_row("runner", runner)
    table.add_row("model", model)
    table.add_row("bundle.hash", bundle.hash[:16] + "…")
    table.add_row("bundle.source", bundle.source)
    table.add_row("bundle.skills", str(len(bundle.skills)))
    table.add_row("task_set.name", task_set.name)
    table.add_row("task_set.hash", task_set.hash[:16] + "…")
    table.add_row("task_set.panel", task_set.panel)
    table.add_row("task_set.tasks", str(len(task_set.tasks)))
    table.add_row("attempts (5 seeds)", str(len(task_set.tasks) * 5))
    table.add_row(
        "expected_tokens",
        str(sum(t.meta.expected_tokens for t in task_set.tasks) * 5),
    )
    console.print(table)


def _print_summary(result: Any) -> None:
    s = result.summary()
    table = Table(title=f"agenteval — {result.task_set_name} on {result.model}")
    for k, v in s.items():
        table.add_row(k, str(v))
    table.add_row("bundle_hash", result.bundle_hash[:16] + "…")
    table.add_row("task_set_hash", result.task_set_hash[:16] + "…")
    console.print(table)


def _die(exc: BaseException) -> None:
    msg = getattr(exc, "message", str(exc))
    code = getattr(exc, "code", "error")
    console.print(f"[red]error ({code})[/red]: {msg}")
    sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
