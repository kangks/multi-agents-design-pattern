"""Loads the coordinator's canonical specialist allowlist from resources.json."""

import json
from pathlib import Path

_RESOURCES_PATH = Path(__file__).resolve().parent / "resources.json"


def load_allowlist() -> dict[str, str]:
    data = json.loads(_RESOURCES_PATH.read_text())
    return dict(data["specialists"])
