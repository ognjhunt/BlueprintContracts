from __future__ import annotations

import json

import pytest

from blueprint_contracts.handoff_contract import (
    QualifiedOpportunityValidationError,
    load_and_validate_qualified_opportunity_handoff,
    validate_qualified_opportunity_handoff,
)


def _valid_handoff() -> dict:
    return {
        "schema_version": "v1",
        "site_submission_id": "site-sub-001",
        "opportunity_id": "opp-001",
        "qualification_state": "ready",
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
    assert payload["source_contract"] == "qualified_opportunity_v1"


def test_validate_thin_handoff() -> None:
    payload = validate_qualified_opportunity_handoff(_thin_handoff())
    assert payload["site_submission_id"] == "capture-demo-001"
    assert payload["operator_approved_summary"].startswith("BlueprintCapturePipeline handoff")


def test_reject_missing_required_fields() -> None:
    payload = _valid_handoff()
    del payload["site_constraints"]["known_blockers"]
    with pytest.raises(QualifiedOpportunityValidationError, match="known_blockers"):
        validate_qualified_opportunity_handoff(payload)


def test_load_and_validate_from_disk(tmp_path) -> None:
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(_valid_handoff()), encoding="utf-8")
    payload = load_and_validate_qualified_opportunity_handoff(path)
    assert payload["opportunity_id"] == "opp-001"
