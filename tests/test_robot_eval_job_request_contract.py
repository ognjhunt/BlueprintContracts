from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from blueprint_contracts.robot_eval_job_request_contract import (
    REQUIRED_ARTIFACT_CONTRACT_OUTPUTS,
    ROBOT_EVAL_JOB_REQUEST_INBOX_CONTRACT,
    ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
    robot_eval_job_request_inbox_schema,
    robot_eval_job_request_schema,
    validate_robot_eval_job_request_constants,
)


ROOT = Path(__file__).resolve().parents[1]


def _valid_request() -> dict[str, object]:
    return {
        "schema_version": ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
        "job_id": "job-1",
        "buyer_request_id": "buyer-1",
        "site_package": {
            "site_slug": "site-1",
            "site_id": "site-1",
            "site_submission_id": "site-submission-1",
            "capture_job_id": "capture-job-1",
            "capture_id": "capture-1",
            "buyer_request_id": "buyer-1",
            "capture_root": "/captures/capture-1",
            "package_uri": "gs://bucket/package.json",
            "task_thresholds_uri": "gs://bucket/task_thresholds.json",
            "publication_readiness_uri": "gs://bucket/publication_readiness.json",
        },
        "policy_package": {
            "policy_api_endpoint": {"endpoint_url": "https://policy.example/run"}
        },
        "proof_boundary": {
            "simulator_execution_proven": False,
            "rank_fidelity_result_proven": False,
            "robot_policy_execution_proven": False,
            "physics_contact_validated": False,
            "non_ranking_operational_claim_validated": False,
            "virtual_evaluation_proves_evaluation_readiness": False,
            "virtual_evaluation_proves_non_ranking_operational_claim": False,
            "public_claim_upgrade_allowed": False,
        },
        "execution_request": {
            "schema_version": "blueprint.robot_eval_execution_request.v1",
            "webapp_role": "queue_and_forward_only",
            "scheduler_owner": "BlueprintCapturePipeline",
            "evaluation_scope": {
                "mode": "virtual_policy_evaluation",
                "physical_robot_deployment_claim_allowed": False,
            },
            "wam_evaluator_backend": "pipeline_selected",
            "allowed_evaluator_backends": [
                "wam_policy_runtime",
                "vla_policy_runtime",
            ],
            "proof_boundaries": {
                "virtual_evaluation_proves_evaluation_readiness": False,
                "virtual_evaluation_proves_non_ranking_operational_claim": False,
            },
            "queueing": {
                "mode": "async_job",
                "web_request_must_not_wait_for_simulator": True,
            },
            "preflight": {
                "cpu_preflight_required_before_gpu": True,
                "blocks_gpu_when_missing": True,
            },
            "simulator_routing": {
                "requested_backend": "pipeline_selected",
                "default_first_pass_backend": "mujoco",
                "default_first_gpu_backend": "mujoco",
            },
            "gpu_allocation": {
                "allocation_allowed_by_webapp": False,
                "gpu_spend_approved": False,
                "idle_shutdown_required": True,
            },
            "artifact_contract": {
                "expected_outputs": list(REQUIRED_ARTIFACT_CONTRACT_OUTPUTS),
                "webapp_queues_and_forwards_only": True,
                "pipeline_owns_execution_ranking_and_artifacts": True,
                "public_claim_upgrade_allowed": False,
                "startup_artifacts_are_advisory_until_owner_runtime_proof": True,
                "ranking_outputs_are_advisory_until_owner_system_proof": True,
                "ptdp_export_manifest_does_not_prove_delivery_or_training": True,
                "simulator_execution_proven_by_webapp": False,
            },
        },
    }


def test_robot_eval_job_request_schema_is_packaged_json_schema() -> None:
    schema = robot_eval_job_request_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_version"]["const"] == (
        ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION
    )
    assert "site_package" in schema["required"]
    assert "execution_request" in schema["required"]

    mutated = robot_eval_job_request_schema()
    mutated["properties"]["schema_version"]["const"] = "mutated"
    assert robot_eval_job_request_schema()["properties"]["schema_version"]["const"] == (
        ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION
    )


def test_robot_eval_job_request_inbox_schema_references_request_schema() -> None:
    schema = robot_eval_job_request_inbox_schema()
    assert schema["properties"]["queue_contract"]["const"] == (
        ROBOT_EVAL_JOB_REQUEST_INBOX_CONTRACT
    )
    assert schema["properties"]["job_request"]["$ref"] == (
        "robot_eval_job_request.v1.schema.json"
    )


def test_robot_eval_job_request_constants_guard_catches_high_risk_drift() -> None:
    valid = _valid_request()
    assert validate_robot_eval_job_request_constants(valid) == []

    invalid = _valid_request()
    invalid["schema_version"] = "wrong"
    invalid["proof_boundary"]["simulator_execution_proven"] = True  # type: ignore[index]
    invalid["execution_request"]["webapp_role"] = "executes"  # type: ignore[index]

    assert validate_robot_eval_job_request_constants(invalid) == [
        "schema_version must be robot_eval_job_request.v1",
        "proof_boundary.simulator_execution_proven must be false",
        "execution_request.webapp_role must be queue_and_forward_only",
    ]


def test_node_entrypoint_loads_same_robot_eval_job_request_schema() -> None:
    script = """
      import {
        POLICY_MODALITIES,
        REQUIRED_ARTIFACT_CONTRACT_OUTPUTS,
        REQUIRED_SITE_PACKAGE_FIELDS,
        ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
        robotEvalJobRequestSchema,
        robotEvalJobRequestInboxSchema,
        validateRobotEvalJobRequestConstants,
      } from './js/robot-eval-job-request.mjs';
      const schema = robotEvalJobRequestSchema();
      const inbox = robotEvalJobRequestInboxSchema();
      const valid = JSON.parse(process.env.VALID_REQUEST_JSON);
      const invalid = {
        ...valid,
        schema_version: "wrong",
        proof_boundary: {
          ...valid.proof_boundary,
          simulator_execution_proven: true,
        },
        execution_request: {
          ...valid.execution_request,
          scheduler_owner: "Blueprint-WebApp",
        },
      };
      console.log(JSON.stringify({
        version: ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
        schemaConst: schema.properties.schema_version.const,
        inboxConst: inbox.properties.queue_contract.const,
        policyModalities: POLICY_MODALITIES,
        sitePackageFields: REQUIRED_SITE_PACKAGE_FIELDS,
        artifactOutputs: REQUIRED_ARTIFACT_CONTRACT_OUTPUTS,
        validErrors: validateRobotEvalJobRequestConstants(valid),
        invalidErrors: validateRobotEvalJobRequestConstants(invalid),
      }));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "VALID_REQUEST_JSON": json.dumps(_valid_request()),
        },
    )
    payload = json.loads(completed.stdout)
    assert payload["version"] == "robot_eval_job_request.v1"
    assert payload["schemaConst"] == "robot_eval_job_request.v1"
    assert payload["inboxConst"] == "robot_eval_job_request_inbox.v1"
    assert payload["policyModalities"] == [
        "policy_api_endpoint",
        "docker_container",
        "recorded_action_trace",
        "high_level_skill_trace",
        "teleop_demo",
        "sim_controller_plugin",
    ]
    assert payload["sitePackageFields"] == [
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
    ]
    assert payload["artifactOutputs"] == list(REQUIRED_ARTIFACT_CONTRACT_OUTPUTS)
    assert payload["validErrors"] == []
    assert payload["invalidErrors"] == [
        "schema_version must be robot_eval_job_request.v1",
        "proof_boundary.simulator_execution_proven must be false",
        "execution_request.scheduler_owner must be BlueprintCapturePipeline",
    ]
