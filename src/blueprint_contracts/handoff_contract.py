"""Contract helpers for qualified-opportunity handoff payloads.

This module owns the portable validation boundary between BlueprintCapturePipeline
and BlueprintValidation for qualified opportunity handoffs.

Qualified opportunity handoffs are qualification inputs only. They can influence
canonical launch gating through ``qualification_state`` and
``downstream_evaluation_eligibility``, but they are never authoritative
site-world packages and they do not imply runtime readiness, canonical truth, or
canonical package verification.

Accepted contract modes:

- ``RICH_HANDOFF_MODE``: the explicit downstream handoff with scoped task and site
  constraints.
- ``LEGACY_THIN_HANDOFF_MODE``: the compatibility payload produced by
  BlueprintCapturePipeline during the initial extraction.

Validation is intentionally explicit. Inputs are normalized only where the shared
contract requires deterministic behavior across repos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping


QUALIFIED_OPPORTUNITY_SCHEMA_VERSION = "v1"
RICH_HANDOFF_MODE = "qualified_opportunity_v1"
LEGACY_THIN_HANDOFF_MODE = "capture_pipeline_thin_v1"
LEGACY_THIN_COMPATIBILITY_MODE = "legacy_thin_handoff"
ALLOWED_QUALIFICATION_STATES = frozenset({"ready", "risky", "not_ready_yet"})

_RICH_MODE_SENTINEL_FIELDS = (
    "qualification_state",
    "downstream_evaluation_eligibility",
    "scoped_task_definition",
    "site_constraints",
    "target_robot_team",
)
_THIN_MODE_REQUIRED_FIELDS = (
    "scene_id",
    "capture_id",
    "readiness_state",
    "match_ready",
)


class QualifiedOpportunityValidationError(RuntimeError):
    """Raised when a qualified opportunity handoff is invalid."""


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _as_mapping(payload: Any, *, manifest_path: Path | None) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        where = f" ({manifest_path})" if manifest_path is not None else ""
        raise QualifiedOpportunityValidationError(
            f"Qualified opportunity handoff must be a JSON object{where}"
        )
    return dict(payload)


def _field_where(where: str, field_path: str) -> str:
    return f" at '{field_path}'{where}"


def _require_text(payload: Mapping[str, Any], key: str, *, where: str, field_path: str | None = None) -> str:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise QualifiedOpportunityValidationError(
            f"Missing non-empty text field{_field_where(where, field_path or key)}"
        )
    return value


def _require_bool(payload: Mapping[str, Any], key: str, *, where: str, field_path: str | None = None) -> bool:
    if key not in payload or not isinstance(payload.get(key), bool):
        raise QualifiedOpportunityValidationError(
            f"Missing boolean field{_field_where(where, field_path or key)}"
        )
    return bool(payload[key])


def _require_mapping(
    payload: Mapping[str, Any],
    key: str,
    *,
    where: str,
    field_path: str | None = None,
) -> Dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise QualifiedOpportunityValidationError(
            f"Missing object field{_field_where(where, field_path or key)}"
        )
    return dict(value)


def _require_present(value: Any, *, where: str, field_path: str) -> None:
    if value is None:
        raise QualifiedOpportunityValidationError(
            f"Missing required field{_field_where(where, field_path)}"
        )
    if isinstance(value, str) and not value.strip():
        raise QualifiedOpportunityValidationError(
            f"Missing non-empty text field{_field_where(where, field_path)}"
        )
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        raise QualifiedOpportunityValidationError(
            f"Missing non-empty collection field{_field_where(where, field_path)}"
        )


def _normalize_qualification_state(raw_value: Any, *, where: str, field_path: str) -> str:
    qualification_state = str(raw_value or "").strip().lower()
    if qualification_state not in ALLOWED_QUALIFICATION_STATES:
        allowed = ", ".join(sorted(ALLOWED_QUALIFICATION_STATES))
        raise QualifiedOpportunityValidationError(
            f"Invalid qualification_state at '{field_path}'{where}; expected one of: {allowed}"
        )
    return qualification_state


def _optional_mapping(
    payload: Mapping[str, Any],
    key: str,
    *,
    where: str,
    field_path: str | None = None,
) -> Dict[str, Any] | None:
    if key not in payload or payload[key] is None:
        return None
    value = payload[key]
    if not isinstance(value, Mapping):
        raise QualifiedOpportunityValidationError(
            f"Expected object field{_field_where(where, field_path or key)}"
        )
    return dict(value)


def _has_rich_mode_signals(payload: Mapping[str, Any]) -> bool:
    return any(key in payload for key in _RICH_MODE_SENTINEL_FIELDS)


def _has_thin_mode_shape(payload: Mapping[str, Any]) -> bool:
    return all(key in payload for key in _THIN_MODE_REQUIRED_FIELDS)


def _validate_rich_handoff(data: Mapping[str, Any], *, where: str) -> Dict[str, Any]:
    normalized = dict(data)
    site_submission_id = _require_text(normalized, "site_submission_id", where=where)
    opportunity_id = _require_text(normalized, "opportunity_id", where=where)
    qualification_state = _normalize_qualification_state(
        _require_text(normalized, "qualification_state", where=where),
        where=where,
        field_path="qualification_state",
    )
    downstream_evaluation_eligibility = _require_bool(
        normalized,
        "downstream_evaluation_eligibility",
        where=where,
    )
    operator_approved_summary = _require_text(normalized, "operator_approved_summary", where=where)

    scoped_task = _require_mapping(
        normalized,
        "scoped_task_definition",
        where=where,
    )
    _require_text(
        scoped_task,
        "task_id",
        where=where,
        field_path="scoped_task_definition.task_id",
    )
    _require_text(
        scoped_task,
        "scoped_task_statement",
        where=where,
        field_path="scoped_task_definition.scoped_task_statement",
    )
    _require_present(
        scoped_task.get("success_criteria"),
        where=where,
        field_path="scoped_task_definition.success_criteria",
    )
    _require_present(
        scoped_task.get("in_scope_zone"),
        where=where,
        field_path="scoped_task_definition.in_scope_zone",
    )

    site_constraints = _require_mapping(normalized, "site_constraints", where=where)
    for key in (
        "operating_constraints",
        "privacy_security_constraints",
        "known_blockers",
    ):
        _require_present(
            site_constraints.get(key),
            where=where,
            field_path=f"site_constraints.{key}",
        )

    target_robot_team = _optional_mapping(normalized, "target_robot_team", where=where)
    if target_robot_team is not None:
        for key in ("team_name_or_id", "robot_platform", "embodiment_notes"):
            _require_text(
                target_robot_team,
                key,
                where=where,
                field_path=f"target_robot_team.{key}",
            )

    for optional_mapping in ("scene_memory_package", "geometry_package", "scene_package"):
        _optional_mapping(normalized, optional_mapping, where=where)

    normalized["site_submission_id"] = site_submission_id
    normalized["opportunity_id"] = opportunity_id
    normalized["qualification_state"] = qualification_state
    normalized["downstream_evaluation_eligibility"] = downstream_evaluation_eligibility
    normalized["operator_approved_summary"] = operator_approved_summary
    normalized["qualification_focus"] = (
        str(normalized.get("qualification_focus") or "neutral_site_readiness").strip()
        or "neutral_site_readiness"
    )
    normalized["target_robot_team"] = target_robot_team
    normalized["requires_robot_team_for_execution"] = target_robot_team is None
    normalized["source_contract"] = RICH_HANDOFF_MODE
    return normalized


def _validate_capture_pipeline_handoff(data: Mapping[str, Any], *, where: str) -> Dict[str, Any]:
    normalized = dict(data)
    scene_id = _require_text(normalized, "scene_id", where=where)
    capture_id = _require_text(normalized, "capture_id", where=where)
    qualification_state = _normalize_qualification_state(
        _require_text(normalized, "readiness_state", where=where, field_path="readiness_state"),
        where=where,
        field_path="readiness_state",
    )
    downstream_evaluation_eligibility = _require_bool(
        normalized,
        "match_ready",
        where=where,
        field_path="match_ready",
    )
    operator_approved_summary = (
        str(normalized.get("summary", "") or "").strip()
        or f"BlueprintCapturePipeline handoff for scene {scene_id} capture {capture_id}"
    )

    for optional_mapping in ("constraints", "scene_memory_package", "geometry_package", "scene_package"):
        _optional_mapping(normalized, optional_mapping, where=where)

    normalized["site_submission_id"] = capture_id
    normalized["opportunity_id"] = scene_id
    normalized["qualification_state"] = qualification_state
    normalized["downstream_evaluation_eligibility"] = downstream_evaluation_eligibility
    normalized["operator_approved_summary"] = operator_approved_summary
    normalized["source_contract"] = LEGACY_THIN_HANDOFF_MODE
    normalized["compatibility_mode"] = LEGACY_THIN_COMPATIBILITY_MODE
    return normalized


def validate_qualified_opportunity_handoff(
    payload: Any,
    *,
    manifest_path: Path | None = None,
) -> Dict[str, Any]:
    """Validate and normalize a qualified-opportunity handoff payload."""
    where = f" ({manifest_path})" if manifest_path is not None else ""
    data = _as_mapping(payload, manifest_path=manifest_path)

    schema_version = _require_text(data, "schema_version", where=where)
    if schema_version != QUALIFIED_OPPORTUNITY_SCHEMA_VERSION:
        raise QualifiedOpportunityValidationError(
            f"Unsupported qualified opportunity schema_version '{schema_version}'{where}; "
            f"expected '{QUALIFIED_OPPORTUNITY_SCHEMA_VERSION}'"
        )

    has_rich_mode_signals = _has_rich_mode_signals(data)
    has_thin_mode_shape = _has_thin_mode_shape(data)
    if has_rich_mode_signals and has_thin_mode_shape:
        raise QualifiedOpportunityValidationError(
            "Qualified opportunity handoff mixes rich and legacy thin fields"
            f"{where}; provide either the rich fields "
            "(site_submission_id, opportunity_id, qualification_state, "
            "downstream_evaluation_eligibility, operator_approved_summary, "
            "scoped_task_definition, site_constraints) or the thin fields "
            "(scene_id, capture_id, readiness_state, match_ready), but not both"
        )
    if has_rich_mode_signals:
        return _validate_rich_handoff(data, where=where)
    if has_thin_mode_shape:
        return _validate_capture_pipeline_handoff(data, where=where)
    raise QualifiedOpportunityValidationError(
        "Qualified opportunity handoff must include either the rich downstream fields "
        "(site_submission_id, opportunity_id, qualification_state, "
        "downstream_evaluation_eligibility, operator_approved_summary, "
        "scoped_task_definition, site_constraints, optional target_robot_team) "
        "or the BlueprintCapturePipeline thin fields "
        f"(scene_id, capture_id, readiness_state, match_ready){where}"
    )


def load_and_validate_qualified_opportunity_handoff(path: Path) -> Dict[str, Any]:
    """Load a handoff JSON file from disk and validate it."""
    payload = _read_json(path)
    return validate_qualified_opportunity_handoff(payload, manifest_path=path)


__all__ = [
    "ALLOWED_QUALIFICATION_STATES",
    "LEGACY_THIN_COMPATIBILITY_MODE",
    "LEGACY_THIN_HANDOFF_MODE",
    "QUALIFIED_OPPORTUNITY_SCHEMA_VERSION",
    "QualifiedOpportunityValidationError",
    "RICH_HANDOFF_MODE",
    "load_and_validate_qualified_opportunity_handoff",
    "validate_qualified_opportunity_handoff",
]
