from __future__ import annotations

from typing import Any

from openclaw_yolo.constants import SEARCH_SPACE
from openclaw_yolo.core.constraints import validate_param_value


class ProposalValidationError(ValueError):
    pass


def validate_proposal(proposal: dict[str, Any], target_reached: bool = False) -> dict[str, Any]:
    decision = proposal.get("decision")
    if decision not in {"continue", "stop"}:
        raise ProposalValidationError("decision must be 'continue' or 'stop'")

    param_updates = proposal.get("param_updates") or {}
    if not isinstance(param_updates, dict):
        raise ProposalValidationError("param_updates must be an object")
    if len(param_updates) > 3:
        raise ProposalValidationError("no more than 3 params may be updated in one iteration")
    normalized_updates: dict[str, Any] = {}
    for key, value in param_updates.items():
        if key not in SEARCH_SPACE:
            raise ProposalValidationError(f"param '{key}' is not in the search space")
        try:
            normalized_updates[key] = validate_param_value(key, value)
        except ValueError as exc:
            raise ProposalValidationError(str(exc)) from exc

    if target_reached and decision == "continue":
        raise ProposalValidationError("target score already reached; cannot continue")

    reason = proposal.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ProposalValidationError("reason must be a non-empty string")

    return {
        "decision": decision,
        "param_updates": normalized_updates,
        "reason": reason.strip(),
    }
