"""Wraps `adapter.invoke_specialist` as a Claude Agent SDK in-process MCP tool.

This is the coordinator's *only* tool. `ClaudeAgentOptions.allowed_tools` in
`run_mode_b.py` is restricted to exactly this tool's name -- the coordinator
has no bash, no file, no web tool, nothing beyond "invoke one allowlisted
specialist with a typed task."
"""

import json

import pydantic
from claude_agent_sdk import create_sdk_mcp_server, tool

from adapter import invoke_specialist
from schemas import InterpretTask, ReconcileTask

INVOKE_SPECIALIST_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Specialist harness name, e.g. StmtInterpreter or LedgerReconciler"},
        "kind": {"type": "string", "enum": ["interpret_statement", "reconcile"]},
        "partner_id": {"type": "string", "enum": ["P", "Q"], "description": "Required for kind=interpret_statement"},
        "fragment": {"type": "string", "description": "Required for kind=interpret_statement"},
        "interpreted_p": {"type": "string", "description": "Required for kind=reconcile"},
        "interpreted_q": {"type": "string", "description": "Required for kind=reconcile"},
        "session_id": {"type": "string", "description": "A stable, unique, >=33 character session id for this call"},
    },
    "required": ["name", "kind", "session_id"],
}


@tool(
    "invoke_specialist",
    "Invoke one allowlisted AgentCore Harness specialist with a typed, validated task. "
    "Unknown specialist names and malformed/unsafe task fields are rejected before any AWS call.",
    INVOKE_SPECIALIST_SCHEMA,
)
async def invoke_specialist_tool(args: dict) -> dict:
    name = args.get("name", "")
    session_id = args.get("session_id", "")
    kind = args.get("kind")

    # Build the typed task from *only* the fields Pydantic's extra="forbid" schema declares --
    # any unexpected field the model (or a prompt-injection attempt) adds is rejected here,
    # before invoke_specialist / boto3 is ever reached.
    task_fields = {k: v for k, v in args.items() if k not in ("name", "kind", "session_id")}
    try:
        if kind == "interpret_statement":
            task = InterpretTask(**task_fields)
        elif kind == "reconcile":
            task = ReconcileTask(**task_fields)
        else:
            return {
                "content": [{"type": "text", "text": f"rejected: unknown task kind {kind!r}"}],
                "isError": True,
            }
    except pydantic.ValidationError as error:
        return {
            "content": [{"type": "text", "text": f"rejected: unsafe or invalid task input: {error}"}],
            "isError": True,
        }

    result = invoke_specialist(name, task, session_id)
    return {
        "content": [{"type": "text", "text": json.dumps(result.model_dump())}],
        "isError": result.status == "error",
    }


def build_server():
    return create_sdk_mcp_server(name="specialists", tools=[invoke_specialist_tool])
