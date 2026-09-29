"""CLI entrypoint: run Mode A serial then concurrent, print structured evidence, and write a
timestamped evidence JSON file under ../evidence/.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import evidence
from partner_reconciliation import run_concurrent, run_serial

EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence"


async def main() -> dict:
    coordinator_fingerprint = evidence.host_fingerprint()
    coordinator_identity = evidence.aws_identity()
    print("=== Coordinator host fingerprint (captured once; identical for every worker below) ===", file=sys.stderr)
    print(json.dumps({"host_fingerprint": coordinator_fingerprint, "aws_identity": coordinator_identity}, indent=2), file=sys.stderr)

    serial_result = await run_serial()
    concurrent_result = await run_concurrent()

    all_fingerprints = [coordinator_fingerprint] + [w.host_fingerprint for r in (serial_result, concurrent_result) for w in r["workers"]]
    all_pids = {fp["pid"] for fp in all_fingerprints}

    summary = {
        "coordinator_host_fingerprint": coordinator_fingerprint,
        "coordinator_aws_identity": coordinator_identity,
        "serial": {k: v for k, v in serial_result.items() if k != "workers"},
        "serial_workers": [w.__dict__ for w in serial_result["workers"]],
        "concurrent": {k: v for k, v in concurrent_result.items() if k != "workers"},
        "concurrent_workers": [w.__dict__ for w in concurrent_result["workers"]],
        "same_host_evidence": {
            "distinct_pids_observed_across_coordinator_and_all_workers": sorted(all_pids),
            "single_shared_pid": len(all_pids) == 1,
        },
        "timing_evidence": {
            "serial_total_elapsed_ms": serial_result["total_elapsed_ms"],
            "concurrent_total_elapsed_ms": concurrent_result["total_elapsed_ms"],
            "concurrent_faster_than_serial": concurrent_result["total_elapsed_ms"] < serial_result["total_elapsed_ms"],
        },
    }
    return summary


if __name__ == "__main__":
    result = asyncio.run(main())
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / f"mode_a_run_{int(time.time())}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nWrote evidence file: {out_path}", file=sys.stderr)
    print(json.dumps(result["same_host_evidence"], indent=2))
    print(json.dumps(result["timing_evidence"], indent=2))
