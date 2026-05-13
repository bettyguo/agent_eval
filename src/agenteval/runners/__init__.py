"""Runner backends.

The runner is the agent-loop driver: it sends the task prompt + tool
definitions to the model provider, dispatches tool calls to the Sandbox,
collects the trajectory, and returns a `RunOutcome`.
"""

from agenteval.runners.anthropic import AnthropicRunner
from agenteval.runners.base import Runner, RunOutcome
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
