"""Structured evidence capture for the Mode A (Claude Agent SDK alone) control.

Two distinct kinds of evidence are captured, deliberately kept separate:

1. **Timing evidence** (`log_event`) proves concurrency actually happens --
   the same shape of proof already used in this repository
   (`ParallelPatternsDemo/app/ParallelPatternsDemo/parallel_patterns/telemetry.py`):
   structured JSON events with monotonic timestamps per run/worker.
2. **Host/environment evidence** (`host_fingerprint`) proves the
   same-host/shared-environment limitation *by inspecting actual process
   state* -- PID, hostname, cwd, and a non-secret AWS identity ARN -- not by
   asserting it. No secret value (access key, session token) is ever read
   or printed; `aws_identity()` calls STS only to obtain the caller's ARN,
   which is not a credential.
"""

import json
import logging
import os
import socket
import time

_logger = logging.getLogger("mode_a")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.propagate = False


def emit(record: dict) -> None:
    _logger.info(json.dumps(record, sort_keys=True, default=str))


def log_event(event: str, *, run_id: str, mode: str, start: float, worker_id: str | None = None, **fields) -> dict:
    now = time.monotonic()
    record = {
        "event": event,
        "run_id": run_id,
        "mode": mode,
        "worker_id": worker_id,
        "pid": os.getpid(),
        "monotonic_ts": now,
        "elapsed_ms": round((now - start) * 1000, 3),
        **fields,
    }
    emit(record)
    return record


def host_fingerprint() -> dict:
    """Non-secret process/host identity snapshot. Safe to log and to include verbatim in
    customer-facing evidence: no credential value, only a caller ARN (identity, not a secret)."""
    return {
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "cwd": os.getcwd(),
        "aws_profile_env_var_set": "AWS_PROFILE" in os.environ,
        "aws_region_env_var_set": "AWS_REGION" in os.environ or "AWS_DEFAULT_REGION" in os.environ,
    }


def aws_identity() -> dict | None:
    """Caller identity ARN/account only -- never a credential value. Returns None if the STS
    call fails (e.g. no credentials configured); callers must not treat that as fatal."""
    try:
        import boto3

        sts = boto3.client("sts")
        ident = sts.get_caller_identity()
        return {"Account": ident["Account"], "Arn": ident["Arn"]}
    except Exception as error:
        return {"error": type(error).__name__}
