"""Structured JSON-line evidence logging for the Mode B coordinator, same shape as
`../mode_a/evidence.py` and `ParallelPatternsDemo/app/ParallelPatternsDemo/parallel_patterns/telemetry.py`.
Kept as an independent copy (not a shared import) so this project has no code dependency on
any other project in this repository, matching the isolation of every prior project here.
"""

import json
import logging
import os
import time

_logger = logging.getLogger("mode_b_coordinator")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.propagate = False


def emit(record: dict) -> None:
    _logger.info(json.dumps(record, sort_keys=True, default=str))


def log_event(event: str, *, run_id: str, start: float, specialist: str | None = None, **fields) -> dict:
    now = time.monotonic()
    record = {
        "event": event,
        "run_id": run_id,
        "specialist": specialist,
        "pid": os.getpid(),
        "monotonic_ts": now,
        "elapsed_ms": round((now - start) * 1000, 3),
        **fields,
    }
    emit(record)
    return record
