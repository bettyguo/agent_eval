"""Tool definitions and the dispatch fn used by all runners.

The tool vocabulary is normalized across providers per docs/tasks.md §3.2 so
graders don't need to know which provider ran the agent.
"""

from __future__ import annotations

from typing import Any

from agenteval.sandbox.base import Sandbox

# Public JSON-schema tool definitions, suitable for any provider's tool API.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "Read",
        "description": "Read a UTF-8 text file from the working directory. Returns the file's contents.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path to read."}},
            "required": ["path"],
        },
    },
    {
        "name": "Write",
        "description": "Write a UTF-8 text file to the working directory. Overwrites if it exists. Creates parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "Edit",
        "description": "Replace one unique occurrence of old_string with new_string in a file. Fails if old_string does not appear exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "Bash",
        "description": "Run a shell command in the working directory. Returns exit_code, stdout, stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute."},
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds; defaults to 30s, capped by the task budget.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "Glob",
        "description": "List files matching a glob pattern (e.g. '**/*.py').",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "Grep",
        "description": "Search file contents with a regex. Returns list of {path, line, match}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {
                    "type": "string",
                    "description": "Optional path or directory; defaults to whole workdir.",
                },
            },
            "required": ["pattern"],
        },
    },
]


def dispatch_tool(
    name: str,
    args: dict[str, Any],
    sandbox: Sandbox,
    *,
    default_bash_timeout: float = 30.0,
    max_bash_timeout: float = 300.0,
) -> dict[str, Any]:
    """Dispatch a single tool call to the sandbox. Returns a JSON-serializable dict.

    Errors are returned as `{"error": "..."}` rather than raised, so the agent
    can recover and the trajectory captures the failure rather than aborting.
    """
    try:
        if name == "Read":
            content = sandbox.read_file(args["path"])
            return {"path": args["path"], "content": content, "bytes": len(content.encode("utf-8"))}
        if name == "Write":
            return sandbox.write_file(args["path"], args["content"])
        if name == "Edit":
            return sandbox.edit_file(args["path"], args["old_string"], args["new_string"])
        if name == "Bash":
            timeout = float(args.get("timeout") or default_bash_timeout)
            timeout = min(timeout, max_bash_timeout)
            return sandbox.execute_bash(args["command"], timeout=timeout)
        if name == "Glob":
            return {"matches": sandbox.glob(args["pattern"])}
        if name == "Grep":
            return {"matches": sandbox.grep(args["pattern"], args.get("path"))}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"error": f"unknown tool: {name}"}


def format_tool_result_for_provider(result: dict[str, Any]) -> str:
    """Render a dispatch result as a string for the provider's tool_result block."""
    import json

    return json.dumps(result, indent=2)
