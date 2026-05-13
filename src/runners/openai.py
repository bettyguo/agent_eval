"""OpenAIRunner: drives the agent loop against OpenAI's chat-completions tool-use API.

Skill bundles are injected via the system prompt; OpenAI has no native
"skills" feature, so this is the agreed-upon emulation protocol per ADR-0004
and `docs/methodology.md` §2.4.
"""

from __future__ import annotations

import json
import time
from typing import Any, cast

from agenteval.errors import RunnerError
from agenteval.grading.types import FinalState, TrajectoryStep, TrajectoryTool
from agenteval.runners.base import Runner, RunOutcome
from agenteval.runners.tools import (
    TOOL_DEFINITIONS,
    dispatch_tool,
    format_tool_result_for_provider,
)
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TURN_CAP = 50


class OpenAIRunner(Runner):
    name = "openai"

    def __init__(
        self,
        *,
        model: str,
        temperature: float = 0.0,
        api_key: str | None = None,
        max_tokens_per_turn: int = DEFAULT_MAX_TOKENS,
        turn_cap: int = DEFAULT_TURN_CAP,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.max_tokens_per_turn = max_tokens_per_turn
        self.turn_cap = turn_cap

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RunnerError(
                "openai SDK not installed; run `pip install openai`",
                provider="openai",
            ) from exc
        try:
            return OpenAI(api_key=self.api_key) if self.api_key else OpenAI()
        except Exception as exc:
            raise RunnerError(
                f"failed to construct OpenAI client: {exc}",
                provider="openai",
            ) from exc

    def run(
        self,
        *,
        bundle: SkillBundle,
        task: Task,
        sandbox: Sandbox,
        seed: int,
    ) -> RunOutcome:
        client = self._client()
        system_prompt = _build_system_prompt(bundle)
        openai_tools = _to_openai_tools()

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": task.meta.prompt})

        trajectory: list[TrajectoryStep] = []
        total_in = 0
        total_out = 0
        final_text = ""
        fingerprint: str | None = None
        timed_out = False
        start = time.time()
        budget_s = float(task.meta.time_budget_s)

        for _turn in range(self.turn_cap):
            if time.time() - start >= budget_s:
                timed_out = True
                break

            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens_per_turn,
                    seed=seed,
                )
            except Exception as exc:
                raise RunnerError(f"OpenAI API call failed: {exc}", provider="openai") from exc

            usage = getattr(response, "usage", None)
            if usage is not None:
                total_in += int(getattr(usage, "prompt_tokens", 0) or 0)
                total_out += int(getattr(usage, "completion_tokens", 0) or 0)
            fingerprint = getattr(response, "system_fingerprint", None) or fingerprint

            choice = response.choices[0]
            msg = choice.message
            if msg.content:
                final_text = msg.content

            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                break

            # Append the assistant message.
            assistant_dict: dict[str, Any] = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_dict)

            # Dispatch each tool call.
            for tc in tool_calls:
                t_call = time.time() - start
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = dispatch_tool(tool_name, args, sandbox)
                trajectory.append(
                    TrajectoryStep(
                        t=t_call,
                        tool=_norm_name(tool_name),
                        args=args,
                        result=result,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": format_tool_result_for_provider(result),
                    }
                )

        latency_s = time.time() - start
        final_state = FinalState(
            assistant_final_message=final_text,
            file_hashes=sandbox.file_hashes(),
            timed_out=timed_out,
            raw_response_fingerprint=fingerprint,
        )
        return RunOutcome(
            trajectory=tuple(trajectory),
            final_state=final_state,
            tokens_in=total_in,
            tokens_out=total_out,
            latency_s=latency_s,
            tool_calls=len(trajectory),
            model_response_fingerprint=fingerprint,
        )


def _build_system_prompt(bundle: SkillBundle) -> str:
    if not bundle.skills:
        return ""
    parts: list[str] = []
    for skill in bundle.skills:
        parts.append(f"# Skill: {skill.name}\n\n{skill.description}\n\n{skill.body.strip()}")
    return "\n\n---\n\n".join(parts)


def _to_openai_tools() -> list[dict[str, Any]]:
    """Translate our normalized tool list into OpenAI's function-tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_DEFINITIONS
    ]


def _norm_name(name: str) -> TrajectoryTool:
    if name in {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}:
        return cast(TrajectoryTool, name)
    return "Other"
