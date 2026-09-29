"""Authenticated invocation adapter: the coordinator's only path to a specialist Harness.

Two independent safety properties, both enforced in code before any AWS call:

1. **Allowlist enforcement.** `invoke_specialist` looks up the caller's requested specialist
   *name* in `resources.json`'s allowlist. An unknown name is rejected immediately -- boto3 is
   never invoked. This is the "denied unknown specialist" proof: the rejection happens in this
   adapter's own code, not because IAM happened to deny it (defense in depth, not a substitute
   for IAM, which is a separate, real boundary -- see docs/README.md's boundary table).
2. **Typed, redacted results only.** The adapter never returns the raw `InvokeHarness` stream
   object, a stack trace, or unbounded text -- only a `SpecialistResult` with a length-capped
   `text` field and a closed `status` literal.

Verified API note: `bedrock_agentcore.invoke_agent_runtime` against a harness's *underlying*
runtime ARN is explicitly rejected by AWS ("managed by a harness and cannot be invoked
directly... Use the InvokeHarness API"). `invoke_harness(harnessArn=..., runtimeSessionId=...,
messages=[...])` against the *harness* ARN is the real, confirmed, working API -- confirmed by
a direct call against the deployed StmtInterpreter harness in this project. Nothing here is a
fabricated SDK method.
"""

import json

import boto3

from resources import load_allowlist
from schemas import SpecialistResult, SpecialistTask

MAX_RESULT_CHARS = 2000


def _messages_for(task: SpecialistTask) -> list[dict]:
    """Build the InvokeHarness `messages` payload deterministically from typed fields only --
    never from arbitrary caller-supplied text beyond what the Pydantic schema already validated."""
    if task.kind == "interpret_statement":
        text = task.fragment
    else:
        text = (
            f"Partner P interpreted invoices:\n{task.interpreted_p}\n\n"
            f"Partner Q interpreted invoices:\n{task.interpreted_q}"
        )
    return [{"role": "user", "content": [{"text": text}]}]


def invoke_specialist(name: str, task: SpecialistTask, session_id: str) -> SpecialistResult:
    """The adapter. Raises no exception for an unknown specialist name or a harness-side
    error -- both are reported as a typed `SpecialistResult(status="error")` so callers (the
    coordinator's tool wrapper, or a test) never need to catch an adapter-specific exception."""
    allowlist = load_allowlist()
    harness_arn = allowlist.get(name)
    if harness_arn is None:
        return SpecialistResult(
            specialist=name, session_id=session_id, status="error",
            text=None, detail=f"specialist '{name}' is not on the allowlist; AWS was never called",
        )

    client = boto3.client("bedrock-agentcore")
    try:
        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=_messages_for(task),
        )
    except Exception as error:
        return SpecialistResult(
            specialist=name, session_id=session_id, status="error",
            text=None, detail=f"invoke_harness call failed: {type(error).__name__}",
        )

    text_parts: list[str] = []
    saw_error = False
    error_detail = None
    try:
        for event in response["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    text_parts.append(delta["text"])
            for error_key in ("validationException", "internalServerException", "runtimeClientError"):
                if error_key in event:
                    saw_error = True
                    error_detail = f"{error_key}: {json.dumps(event[error_key])[:200]}"
    except Exception as error:
        saw_error = True
        error_detail = f"stream read failed: {type(error).__name__}"

    if saw_error:
        return SpecialistResult(specialist=name, session_id=session_id, status="error", text=None, detail=error_detail)

    full_text = "".join(text_parts)
    return SpecialistResult(
        specialist=name, session_id=session_id, status="complete",
        text=full_text[:MAX_RESULT_CHARS],
        detail="truncated" if len(full_text) > MAX_RESULT_CHARS else None,
    )
