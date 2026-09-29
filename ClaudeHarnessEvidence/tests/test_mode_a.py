"""Mode A tests: run with `cd mode_a && uv run pytest ../tests/test_mode_a.py`.

`partner_reconciliation.query` is monkeypatched with a controlled async stub -- same technique
as `ParallelPatternsDemo/tests/test_timing.py` -- so these tests are fast, deterministic, and
make no real Bedrock call, while still exercising the real `run_serial`/`run_concurrent`/
`run_worker` code paths.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mode_a"))

import partner_reconciliation as pr
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

DELAY = 0.08


def _stub_message(worker_fragment_key: str):
    return AssistantMessage(
        content=[TextBlock(text=f"stub interpretation for {worker_fragment_key}")],
        model="stub", parent_tool_use_id=None,
    )


async def _stub_query(*, prompt: str, options):
    await asyncio.sleep(DELAY)
    worker_key = "P" if "Partner P" in prompt else "Q"
    yield _stub_message(worker_key)
    yield ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
        session_id="stub", result="ok",
    )


def test_serial_is_additive_and_concurrent_is_overlapped(monkeypatch):
    monkeypatch.setattr(pr, "query", _stub_query)

    serial = asyncio.run(pr.run_serial())
    concurrent = asyncio.run(pr.run_concurrent())

    assert serial["total_elapsed_ms"] >= 1.5 * DELAY * 1000
    assert concurrent["total_elapsed_ms"] < 1.5 * DELAY * 1000
    assert serial["total_elapsed_ms"] > concurrent["total_elapsed_ms"]


def test_same_host_evidence_is_identical_pid_across_serial_and_concurrent(monkeypatch):
    monkeypatch.setattr(pr, "query", _stub_query)

    serial = asyncio.run(pr.run_serial())
    concurrent = asyncio.run(pr.run_concurrent())

    pids = {w.pid_at_start for w in serial["workers"]} | {w.pid_at_end for w in serial["workers"]}
    pids |= {w.pid_at_start for w in concurrent["workers"]} | {w.pid_at_end for w in concurrent["workers"]}

    assert len(pids) == 1, "every worker, serial or concurrent, must observe the same OS process id"


def test_worker_results_carry_the_stub_text():
    async def run():
        return await pr.run_worker("P", "test-run", "serial", 0.0)

    async def stub(*, prompt, options):
        yield _stub_message("P")
        yield ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
            session_id="stub", result="ok",
        )

    import pytest

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pr, "query", stub)
        record = asyncio.run(run())

    assert record.status == "complete"
    assert record.result_text == "stub interpretation for P"
