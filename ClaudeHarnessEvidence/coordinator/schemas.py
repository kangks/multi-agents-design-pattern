"""Strict, serializable contracts for the coordinator's specialist tasks.

`extra="forbid"` plus closed `Literal` fields is the safety boundary: a task
carrying a free-form field, a URL, a credential, a command, or an
unrecognized `kind` fails validation before the adapter ever calls AWS.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InterpretTask(StrictModel):
    kind: Literal["interpret_statement"] = "interpret_statement"
    partner_id: Literal["P", "Q"]
    fragment: str


class ReconcileTask(StrictModel):
    kind: Literal["reconcile"] = "reconcile"
    interpreted_p: str
    interpreted_q: str


SpecialistTask = InterpretTask | ReconcileTask


class SpecialistResult(StrictModel):
    specialist: str
    session_id: str
    status: Literal["complete", "error"]
    text: str | None
    """Typed, length-capped text extracted from the harness's response stream. Never the raw
    stream object, never a stack trace, never anything beyond the model's own reply text."""
    detail: str | None = None
