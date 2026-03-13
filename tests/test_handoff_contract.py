from __future__ import annotations

import json

import pytest

from blueprint_contracts.canonical_package import validate_canonical_package_contract
from blueprint_contracts.handoff_contract import (
    ALLOWED_QUALIFICATION_STATES,
    LEGACY_THIN_COMPATIBILITY_MODE,
    LEGACY_THIN_HANDOFF_MODE,
    QUALIFIED_OPPORTUNITY_SCHEMA_VERSION,
    RICH_HANDOFF_MODE,
    QualifiedOpportunityValidationError,
    load_and_validate_qualified_opportunity_handoff,
    validate_qualified_opportunity_handoff,
)


def _valid_handoff() -> dict:
    return {
        "schema_version": "v1",
        "site_submission_id": "site-sub-001",
        "opportunity_id": "opp-001",
        "qualification_state": "READY",
        "downstream_evaluation_eligibility": True,
        "operator_approved_summary": "Qualified warehouse tote-pick lane",
        "scoped_task_definition": {
            "task_id": "task-001",
            "scoped_task_statement": "Pick tote from shelf bay 3",
            "success_criteria": ["grasp tote", "clear shelf"],
            "in_scope_zone": "bay-3",
        },
        "site_constraints": {
            "operating_constraints": ["night shift only"],
            "privacy_security_constraints": ["no worker faces"],
            "known_blockers": ["reflective wrap on two pallets"],
        },
    }


def _thin_handoff() -> dict:
    return {
        "schema_version": "v1",
        "scene_id": "scene-demo-001",
        "capture_id": "capture-demo-001",
        "match_ready": True,
        "readiness_state": "ready",
    }


def test_validate_rich_handoff() -> None:
    payload = validate_qualified_opportunity_handoff(_valid_handoff())
    assert payload["source_contract"] == RICH_HANDOFF_MODE
    assert payload["qualification_state"] == "ready"
    assert payload["requires_robot_team_for_execution"] is True


def test_validate_thin_handoff() -> None:
    payload = validate_qualified_opportunity_handoff(_thin_handoff())
    assert payload["site_submission_id"] == "capture-demo-001"
    assert payload["operator_approved_summary"].startswith("BlueprintCapturePipeline handoff")
    assert payload["source_contract"] == LEGACY_THIN_HANDOFF_MODE
    assert payload["compatibility_mode"] == LEGACY_THIN_COMPATIBILITY_MODE


def test_reject_missing_required_nested_field() -> None:
    payload = _valid_handoff()
    del payload["site_constraints"]["known_blockers"]
    with pytest.raises(QualifiedOpportunityValidationError, match=r"site_constraints\.known_blockers"):
        validate_qualified_opportunity_handoff(payload)


def test_reject_ambiguous_mixed_mode_payload() -> None:
    payload = _thin_handoff()
    payload["qualification_state"] = "ready"
    payload["site_constraints"] = {
        "operating_constraints": ["a"],
        "privacy_security_constraints": ["b"],
        "known_blockers": ["c"],
    }
    payload["scoped_task_definition"] = {
        "task_id": "task-1",
        "scoped_task_statement": "Do the thing",
        "success_criteria": ["done"],
        "in_scope_zone": "zone-a",
    }
    with pytest.raises(QualifiedOpportunityValidationError, match="mixes rich and legacy thin fields"):
        validate_qualified_opportunity_handoff(payload)


def test_reject_invalid_schema_version() -> None:
    payload = _valid_handoff()
    payload["schema_version"] = "v2"
    with pytest.raises(QualifiedOpportunityValidationError, match="expected 'v1'"):
        validate_qualified_opportunity_handoff(payload)


def test_reject_invalid_qualification_state() -> None:
    payload = _valid_handoff()
    payload["qualification_state"] = "unknown"
    with pytest.raises(QualifiedOpportunityValidationError, match="expected one of"):
        validate_qualified_opportunity_handoff(payload)


def test_load_and_validate_from_disk(tmp_path) -> None:
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(_valid_handoff()), encoding="utf-8")
    payload = load_and_validate_qualified_opportunity_handoff(path)
    assert payload["opportunity_id"] == "opp-001"


def test_public_constants_are_explicit() -> None:
    assert QUALIFIED_OPPORTUNITY_SCHEMA_VERSION == "v1"
    assert ALLOWED_QUALIFICATION_STATES == frozenset({"ready", "risky", "not_ready_yet"})


def test_handoff_normalization_remains_qualification_only() -> None:
    payload = validate_qualified_opportunity_handoff(_valid_handoff())
    errors = validate_canonical_package_contract(payload)
    assert "missing_canonical_package_version" in errors
    assert "missing_canonical_output" in errors
