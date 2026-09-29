"""Coordinator/adapter tests: run with `cd coordinator && uv run pytest ../tests/test_coordinator.py`.

Covers: allowlist denial (no AWS call), unsafe/invalid task rejection (Pydantic, no AWS call),
and a mocked successful call path (boto3 client replaced with a stub so no real Bedrock/AgentCore
call is made, while still exercising the real stream-parsing logic in adapter.py).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coordinator"))

import pytest
from pydantic import ValidationError

import adapter
from mcp_tool import invoke_specialist_tool
from schemas import InterpretTask, ReconcileTask


def test_denied_unknown_specialist_never_calls_aws(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("boto3.client must not be called for an unknown specialist")

    monkeypatch.setattr(adapter.boto3, "client", boom)

    result = adapter.invoke_specialist(
        "NotOnAllowlist", InterpretTask(partner_id="P", fragment="x"), "denied-unknown-specialist-test-session-01"
    )
    assert result.status == "error"
    assert "not on the allowlist" in result.detail
    assert "AWS was never called" in result.detail


def test_unsafe_extra_field_is_rejected_by_pydantic_before_reaching_adapter():
    with pytest.raises(ValidationError):
        InterpretTask(partner_id="P", fragment="x", command="rm -rf /")


def test_unsafe_missing_field_is_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        InterpretTask(partner_id="P")


def test_mcp_tool_rejects_extra_field_without_calling_adapter(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("invoke_specialist must not be called for an unsafe task")

    monkeypatch.setattr(adapter, "invoke_specialist", boom)
    import mcp_tool

    monkeypatch.setattr(mcp_tool, "invoke_specialist", boom)

    result = asyncio.run(
        invoke_specialist_tool.handler(
            {
                "name": "StmtInterpreter", "kind": "interpret_statement",
                "session_id": "unsafe-extra-field-mcp-test-session-001",
                "partner_id": "P", "fragment": "x", "url": "https://example.com/exfil",
            }
        )
    )
    assert result["isError"] is True
    assert "rejected" in result["content"][0]["text"]


def test_mcp_tool_rejects_unknown_task_kind():
    result = asyncio.run(
        invoke_specialist_tool.handler(
            {"name": "StmtInterpreter", "kind": "delete_everything", "session_id": "unknown-kind-mcp-test-session-001"}
        )
    )
    assert result["isError"] is True
    assert "unknown task kind" in result["content"][0]["text"]


class _FakeStream:
    def __init__(self, events):
        self._events = events

    def __iter__(self):
        return iter(self._events)


def test_adapter_parses_a_mocked_successful_stream(monkeypatch):
    class FakeClient:
        def invoke_harness(self, **kwargs):
            assert kwargs["harnessArn"].startswith("arn:aws:bedrock-agentcore:")
            return {
                "stream": _FakeStream(
                    [
                        {"messageStart": {"role": "assistant"}},
                        {"contentBlockDelta": {"delta": {"text": "hello "}}},
                        {"contentBlockDelta": {"delta": {"text": "world"}}},
                        {"messageStop": {"stopReason": "end_turn"}},
                    ]
                )
            }

    monkeypatch.setattr(adapter.boto3, "client", lambda *a, **k: FakeClient())

    result = adapter.invoke_specialist(
        "StmtInterpreter", InterpretTask(partner_id="P", fragment="x"), "mocked-success-test-session-000001"
    )
    assert result.status == "complete"
    assert result.text == "hello world"


def test_adapter_reports_error_for_a_mocked_validation_exception_event(monkeypatch):
    class FakeClient:
        def invoke_harness(self, **kwargs):
            return {"stream": _FakeStream([{"validationException": {"message": "bad input"}}])}

    monkeypatch.setattr(adapter.boto3, "client", lambda *a, **k: FakeClient())

    result = adapter.invoke_specialist(
        "StmtInterpreter", InterpretTask(partner_id="P", fragment="x"), "mocked-error-test-session-0000001"
    )
    assert result.status == "error"
    assert "validationException" in result.detail


def test_reconcile_task_requires_both_interpreted_fields():
    with pytest.raises(ValidationError):
        ReconcileTask(interpreted_p="only p")
