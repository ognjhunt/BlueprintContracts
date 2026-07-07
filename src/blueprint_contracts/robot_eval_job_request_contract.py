"""Shared robot-eval job request contract constants and JSON Schemas.

This module is intentionally structural. Runtime scheduling, HTTP routes,
database writes, simulator execution, and buyer workflow logic stay in the
consumer repos. The JSON Schema files are the portable source that Python and
TypeScript consumers can both load.
"""

from __future__ import annotations

import copy
import json
from importlib import resources
from typing import Any, Dict, Mapping


ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION = "robot_eval_job_request.v1"
ROBOT_EVAL_JOB_REQUEST_INBOX_CONTRACT = "robot_eval_job_request_inbox.v1"
ROBOT_EVAL_JOB_REQUEST_SCHEMA_FILE = "robot_eval_job_request.v1.schema.json"
ROBOT_EVAL_JOB_REQUEST_INBOX_SCHEMA_FILE = "robot_eval_job_request_inbox.v1.schema.json"

POLICY_MODALITIES = (
    "policy_api_endpoint",
    "docker_container",
    "recorded_action_trace",
    "high_level_skill_trace",
    "teleop_demo",
    "sim_controller_plugin",
)

PROOF_BOUNDARY_FALSE_FIELDS = (
    "simulator_execution_proven",
    "rank_fidelity_result_proven",
    "robot_policy_execution_proven",
    "physics_contact_validated",
    "non_ranking_operational_claim_validated",
    "virtual_evaluation_proves_evaluation_readiness",
    "virtual_evaluation_proves_non_ranking_operational_claim",
    "public_claim_upgrade_allowed",
)

REQUIRED_SITE_PACKAGE_FIELDS = (
    "site_slug",
    "site_id",
    "site_submission_id",
    "capture_job_id",
    "capture_id",
    "buyer_request_id",
    "capture_root",
    "package_uri",
    "task_thresholds_uri",
    "publication_readiness_uri",
)

REQUIRED_ARTIFACT_CONTRACT_OUTPUTS = (
    "scenario_eval_matrix.json",
    "policy_ranking_scorecard.json",
    "candidate_selection_report.json",
    "wam_eval_claim_boundary.json",
    "post_training_data_package_export_manifest.json",
    "proof_boundary.json",
    "proof_boundaries.json",
)


def _schema_payload(file_name: str) -> Dict[str, Any]:
    text = (
        resources.files("blueprint_contracts.schemas")
        .joinpath(file_name)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(text)
    return dict(payload) if isinstance(payload, Mapping) else {}


def robot_eval_job_request_schema() -> Dict[str, Any]:
    """Return a deep copy of the shared ``robot_eval_job_request.v1`` JSON Schema."""

    return copy.deepcopy(_schema_payload(ROBOT_EVAL_JOB_REQUEST_SCHEMA_FILE))


def robot_eval_job_request_inbox_schema() -> Dict[str, Any]:
    """Return a deep copy of the shared inbox envelope JSON Schema."""

    return copy.deepcopy(_schema_payload(ROBOT_EVAL_JOB_REQUEST_INBOX_SCHEMA_FILE))


def validate_robot_eval_job_request_constants(payload: Mapping[str, Any]) -> list[str]:
    """Small stdlib guard for critical constants before optional JSON Schema validation.

    Consumers that already depend on ``jsonschema`` should validate with
    :func:`robot_eval_job_request_schema`. This guard keeps the package
    dependency-free while still catching the highest-risk cross-repo drift.
    """

    errors: list[str] = []
    if payload.get("schema_version") != ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION}"
        )
    proof_boundary = payload.get("proof_boundary")
    if not isinstance(proof_boundary, Mapping):
        errors.append("proof_boundary is required")
    else:
        for field in PROOF_BOUNDARY_FALSE_FIELDS:
            if field in proof_boundary and proof_boundary[field] is not False:
                errors.append(f"proof_boundary.{field} must be false")
    execution_request = payload.get("execution_request")
    if not isinstance(execution_request, Mapping):
        errors.append("execution_request is required")
    else:
        if execution_request.get("webapp_role") != "queue_and_forward_only":
            errors.append("execution_request.webapp_role must be queue_and_forward_only")
        if execution_request.get("scheduler_owner") != "BlueprintCapturePipeline":
            errors.append("execution_request.scheduler_owner must be BlueprintCapturePipeline")
    return errors


__all__ = [
    "POLICY_MODALITIES",
    "PROOF_BOUNDARY_FALSE_FIELDS",
    "REQUIRED_ARTIFACT_CONTRACT_OUTPUTS",
    "REQUIRED_SITE_PACKAGE_FIELDS",
    "ROBOT_EVAL_JOB_REQUEST_INBOX_CONTRACT",
    "ROBOT_EVAL_JOB_REQUEST_INBOX_SCHEMA_FILE",
    "ROBOT_EVAL_JOB_REQUEST_SCHEMA_FILE",
    "ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION",
    "robot_eval_job_request_inbox_schema",
    "robot_eval_job_request_schema",
    "validate_robot_eval_job_request_constants",
]
