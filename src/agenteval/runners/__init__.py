"""Runner backends.

The runner is the agent-loop driver: it sends the task prompt + tool
definitions to the model provider, dispatches tool calls to the Sandbox,
collects the trajectory, and returns a `RunOutcome`. M1 ships
`AnthropicRunner` and `MockRunner`; `OpenAIRunner` and `GoogleRunner` land in
M3.
"""

from agenteval.runners.anthropic import AnthropicRunner
from agenteval.runners.base import RunOutcome, Runner
from agenteval.runners.google import GoogleRunner
from agenteval.runners.mock import MockRunner, MockScript
from agenteval.runners.openai import OpenAIRunner

__all__ = [
    "AnthropicRunner",
    "GoogleRunner",
    "MockRunner",
    "MockScript",
    "OpenAIRunner",
    "RunOutcome",
    "Runner",
]
