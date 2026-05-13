"""GoogleRunner: drives the agent loop against Gemini's function-calling API.

Uses `google-genai` (>= 0.3). Skill bundles are injected via the system
instruction parameter; Gemini has no native skills feature (ADR-0004,
docs/methodology.md §2.4).
"""

from __future__ import annotations

import time
from typing import Any, cast

from agenteval.errors import RunnerError
from agenteval.grading.types import FinalState, TrajectoryStep, TrajectoryTool
from agenteval.runners.base import Runner, RunOutcome
from agenteval.runners.tools import (
    TOOL_DEFINITIONS,
    dispatch_tool,
)
from agenteval.sandbox.base import Sandbox
from agenteval.skills.bundle import SkillBundle
from agenteval.tasks.registry import Task

DEFAULT_MAX_TOKENS = 4096
DEFAULT_TURN_CAP = 50


class GoogleRunner(Runner):
    name = "google"

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
            from google import genai
        except ImportError as exc:
            raise RunnerError(
                "`google-genai` SDK not installed; run `pip install google-genai`",
                provider="google",
            ) from exc
        try:
            return genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        except Exception as exc:
            raise RunnerError(
                f"failed to construct google-genai client: {exc}",
                provider="google",
            ) from exc

    def run(
        self,
        *,
        bundle: SkillBundle,
        task: Task,
        sandbox: Sandbox,
        seed: int,
    ) -> RunOutcome:
        from google.genai import types as gtypes

        client = self._client()
        system_text = _build_system_prompt(bundle)
        # Provider-SDK stubs are stricter than the wire-level reality; cast
        # through Any rather than fight the FunctionDeclaration coercion.
        google_tools: Any = [gtypes.Tool(function_declarations=_to_google_function_decls())]  # type: ignore[arg-type]

        chat = client.chats.create(
            model=self.model,
            config=gtypes.GenerateContentConfig(
                temperature=self.temperature,
                system_instruction=system_text if system_text else None,
                tools=google_tools,
                max_output_tokens=self.max_tokens_per_turn,
                seed=seed,
            ),
        )

        trajectory: list[TrajectoryStep] = []
        total_in = 0
        total_out = 0
        final_text = ""
        fingerprint: str | None = None
        timed_out = False
        start = time.time()
        budget_s = float(task.meta.time_budget_s)
        message: Any = task.meta.prompt

        for _turn in range(self.turn_cap):
            if time.time() - start >= budget_s:
                timed_out = True
                break

            try:
                response = chat.send_message(message)
            except Exception as exc:
                raise RunnerError(
                    f"google-genai API call failed: {exc}", provider="google"
                ) from exc

            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                total_in += int(getattr(usage, "prompt_token_count", 0) or 0)
                total_out += int(getattr(usage, "candidates_token_count", 0) or 0)
            fingerprint = getattr(response, "response_id", None) or fingerprint

            # Extract any text + function calls from the response.
            response_text = ""
            function_calls: list[Any] = []
            for candidate in getattr(response, "candidates", []) or []:
                for part in getattr(candidate.content, "parts", []) or []:
                    if getattr(part, "text", None):
                        response_text += part.text
                    if getattr(part, "function_call", None):
                        function_calls.append(part.function_call)
            if response_text:
                final_text = response_text

            if not function_calls:
                break

            # Dispatch each function call and build the next message.
            function_responses: list[Any] = []
            for fc in function_calls:
                t_call = time.time() - start
                tool_name = fc.name
                args = dict(fc.args or {})
                result = dispatch_tool(tool_name, args, sandbox)
                trajectory.append(
                    TrajectoryStep(
                        t=t_call,
                        tool=_norm_name(tool_name),
                        args=args,
                        result=result,
                    )
                )
                function_responses.append(
                    gtypes.Part.from_function_response(
                        name=tool_name,
                        response={"result": result},
                    )
                )
            message = function_responses

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


def _to_google_function_decls() -> list[dict[str, Any]]:
    """Translate our normalized tool list into Google's function-declaration format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        }
        for t in TOOL_DEFINITIONS
    ]


def _norm_name(name: str) -> TrajectoryTool:
    if name in {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}:
        return cast(TrajectoryTool, name)
    return "Other"
