"""MockRunner: deterministic runner driven by a scripted callable.

Used by tests/test_demo_path.py to exercise the harness wiring without spending
API tokens. The script callable receives the conversation-so-far and returns
the next assistant move; the harness loop then dispatches any tool calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from agenteval.grading.types import FinalState, TrajectoryStep
from agenteval.runners.base import RunOutcome, Runner
from agenteval.runners.tools import dispatch_tool
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task


@dataclass
class MockTurn:
    """One scripted assistant turn.

    - `text`: the assistant's textual reply (becomes `assistant_final_message`
      after the last turn).
    - `tool_calls`: list of {name, input} dicts; the harness dispatches each
      to the sandbox and records a trajectory step.
    - `tokens_in`, `tokens_out`: synthetic accounting.
    - `stop`: if True, this is the final turn (mock equivalent of stop_reason!=tool_use).
    """

    text: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    stop: bool = False


MockScript = Callable[[Task, Sequence[MockTurn]], MockTurn]


class MockRunner(Runner):
    """A runner driven by a script callable.

    Construct with either:
      - `MockRunner(script=callable)` where callable(task, history) -> MockTurn
      - `MockRunner(turns=[MockTurn(...), ...])` for a fixed sequence
    """

    name = "mock"

    def __init__(
        self,
        *,
        script: MockScript | None = None,
        turns: list[MockTurn] | None = None,
        fingerprint: str | None = "mock-fingerprint",
    ) -> None:
        if (script is None) == (turns is None):
            raise ValueError("provide exactly one of `script` or `turns`")
        self._script: MockScript | None = script
        self._turns: list[MockTurn] | None = list(turns) if turns is not None else None
        self._fingerprint = fingerprint

    def run(
        self,
        *,
        bundle: SkillBundle,
        task: Task,
        sandbox: Sandbox,
        seed: int,
    ) -> RunOutcome:
        trajectory: list[TrajectoryStep] = []
        total_in = 0
        total_out = 0
        final_text = ""
        timed_out = False
        history: list[MockTurn] = []
        start = time.time()
        budget_s = float(task.meta.time_budget_s)

        turn_idx = 0
        while True:
            elapsed = time.time() - start
            if elapsed >= budget_s:
                timed_out = True
                break

            if self._script is not None:
                turn = self._script(task, history)
            else:
                assert self._turns is not None
                if turn_idx >= len(self._turns):
                    break
                turn = self._turns[turn_idx]
                turn_idx += 1

            history.append(turn)
            total_in += turn.tokens_in
            total_out += turn.tokens_out
            if turn.text:
                final_text = turn.text

            for tc in turn.tool_calls or []:
                t_call = time.time() - start
                tool_name = tc.get("name", "Other")
                tool_args = dict(tc.get("input", {}) or {})
                result = dispatch_tool(tool_name, tool_args, sandbox)
                trajectory.append(
                    TrajectoryStep(
                        t=t_call,
                        tool=_norm_name(tool_name),
                        args=tool_args,
                        result=result,
                        tokens_in=turn.tokens_in,
                        tokens_out=turn.tokens_out,
                    )
                )

            if turn.stop or not (turn.tool_calls):
                # No tool calls means the agent has finished its turn.
                break

        latency_s = time.time() - start
        final_state = FinalState(
            assistant_final_message=final_text,
            file_hashes=sandbox.file_hashes(),
            timed_out=timed_out,
            raw_response_fingerprint=self._fingerprint,
        )
        return RunOutcome(
            trajectory=tuple(trajectory),
            final_state=final_state,
            tokens_in=total_in,
            tokens_out=total_out,
            latency_s=latency_s,
            tool_calls=len(trajectory),
            model_response_fingerprint=self._fingerprint,
        )


def _norm_name(name: str) -> str:
    known = {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}
    return name if name in known else "Other"
