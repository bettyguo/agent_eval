"""AnthropicRunner: drives the agent loop against Anthropic's Messages API.

Uses the `anthropic` SDK's tool-use protocol. System prompt is assembled by
concatenating skill bundle bodies (M1 minimal injection; M2 will use the
proper `~/.claude/skills/` directory layout in the Docker sandbox).
"""

from __future__ import annotations

import time
from typing import Any

from agenteval.errors import RunnerError
from agenteval.grading.types import FinalState, TrajectoryStep
from agenteval.runners.base import RunOutcome, Runner
from agenteval.runners.tools import (
    TOOL_DEFINITIONS,
    dispatch_tool,
    format_tool_result_for_provider,
)
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TURN_CAP = 50  # safety stop in case the agent loops without progress


class AnthropicRunner(Runner):
    name = "anthropic"

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
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RunnerError(
                "anthropic SDK not installed; run `pip install anthropic`",
                provider="anthropic",
            ) from exc
        try:
            return anthropic.Anthropic(api_key=self.api_key) if self.api_key else anthropic.Anthropic()
        except Exception as exc:
            raise RunnerError(
                f"failed to construct Anthropic client: {exc}",
                provider="anthropic",
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
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": task.meta.prompt}
        ]

        trajectory: list[TrajectoryStep] = []
        total_in = 0
        total_out = 0
        final_text = ""
        fingerprint: str | None = None
        timed_out = False
        start = time.time()
        budget_s = float(task.meta.time_budget_s)

        for _turn in range(self.turn_cap):
            elapsed = time.time() - start
            if elapsed >= budget_s:
                timed_out = True
                break

            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "max_tokens": self.max_tokens_per_turn,
                    "messages": messages,
                    "tools": TOOL_DEFINITIONS,
                    "temperature": self.temperature,
                }
                # `system` is omitted entirely when empty (per Anthropic API ergonomics).
                if system_prompt:
                    kwargs["system"] = system_prompt
                response = client.messages.create(**kwargs)
            except Exception as exc:
                raise RunnerError(
                    f"Anthropic API call failed: {exc}",
                    provider="anthropic",
                ) from exc

            usage = getattr(response, "usage", None)
            if usage is not None:
                total_in += int(getattr(usage, "input_tokens", 0) or 0)
                total_out += int(getattr(usage, "output_tokens", 0) or 0)
            fingerprint = getattr(response, "id", None) or fingerprint

            # Capture text content (the latest text block is the "final message").
            for block in response.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    final_text = getattr(block, "text", "")

            if response.stop_reason != "tool_use":
                break

            assistant_content = list(response.content)
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                tool_name = getattr(block, "name", "Other")
                tool_args = dict(getattr(block, "input", {}) or {})
                t_call = time.time() - start
                result = dispatch_tool(tool_name, tool_args, sandbox)
                trajectory.append(
                    TrajectoryStep(
                        t=t_call,
                        tool=_normalise_tool_name(tool_name),
                        args=tool_args,
                        result=result,
                        tokens_in=int(getattr(usage, "input_tokens", 0) or 0) if usage else 0,
                        tokens_out=int(getattr(usage, "output_tokens", 0) or 0) if usage else 0,
                    )
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": getattr(block, "id", ""),
                        "content": format_tool_result_for_provider(result),
                    }
                )

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        latency_s = time.time() - start
        file_hashes = sandbox.file_hashes()
        final_state = FinalState(
            assistant_final_message=final_text,
            file_hashes=file_hashes,
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
    """Concatenate skill bodies into a system prompt. Empty for SkillBundle.empty()."""
    if not bundle.skills:
        return ""
    parts: list[str] = []
    for skill in bundle.skills:
        header = f"# Skill: {skill.name}\n\n{skill.description}\n\n"
        parts.append(header + skill.body.strip())
    return "\n\n---\n\n".join(parts)


def _normalise_tool_name(name: str) -> str:
    known = {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}
    return name if name in known else "Other"
