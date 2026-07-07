import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION = "robot_eval_job_request.v1";
export const ROBOT_EVAL_JOB_REQUEST_INBOX_CONTRACT = "robot_eval_job_request_inbox.v1";
export const ROBOT_EVAL_JOB_REQUEST_SCHEMA_FILE = "robot_eval_job_request.v1.schema.json";
export const ROBOT_EVAL_JOB_REQUEST_INBOX_SCHEMA_FILE = "robot_eval_job_request_inbox.v1.schema.json";
export const POLICY_MODALITIES = Object.freeze([
  "policy_api_endpoint",
  "docker_container",
  "recorded_action_trace",
  "high_level_skill_trace",
  "teleop_demo",
  "sim_controller_plugin",
]);
export const PROOF_BOUNDARY_FALSE_FIELDS = Object.freeze([
  "simulator_execution_proven",
  "rank_fidelity_result_proven",
  "robot_policy_execution_proven",
  "physics_contact_validated",
  "non_ranking_operational_claim_validated",
  "virtual_evaluation_proves_evaluation_readiness",
  "virtual_evaluation_proves_non_ranking_operational_claim",
  "public_claim_upgrade_allowed",
]);
export const REQUIRED_SITE_PACKAGE_FIELDS = Object.freeze([
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
]);
export const REQUIRED_ARTIFACT_CONTRACT_OUTPUTS = Object.freeze([
  "scenario_eval_matrix.json",
  "policy_ranking_scorecard.json",
  "candidate_selection_report.json",
  "wam_eval_claim_boundary.json",
  "post_training_data_package_export_manifest.json",
  "proof_boundary.json",
  "proof_boundaries.json",
]);

const moduleDir = path.dirname(fileURLToPath(import.meta.url));
const schemaDir = path.resolve(moduleDir, "../src/blueprint_contracts/schemas");

function readSchema(fileName) {
  return JSON.parse(fs.readFileSync(path.join(schemaDir, fileName), "utf8"));
}

export function robotEvalJobRequestSchema() {
  return readSchema(ROBOT_EVAL_JOB_REQUEST_SCHEMA_FILE);
}

export function robotEvalJobRequestInboxSchema() {
  return readSchema(ROBOT_EVAL_JOB_REQUEST_INBOX_SCHEMA_FILE);
}

function hasObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateRobotEvalJobRequestConstants(payload) {
  const errors = [];
  if (!hasObject(payload)) {
    return ["request must be an object"];
  }
  if (payload.schema_version !== ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION) {
    errors.push(`schema_version must be ${ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION}`);
  }

  const proofBoundary = payload.proof_boundary;
  if (!hasObject(proofBoundary)) {
    errors.push("proof_boundary is required");
  } else {
    for (const field of PROOF_BOUNDARY_FALSE_FIELDS) {
      if (field in proofBoundary && proofBoundary[field] !== false) {
        errors.push(`proof_boundary.${field} must be false`);
      }
    }
  }

  const executionRequest = payload.execution_request;
  if (!hasObject(executionRequest)) {
    errors.push("execution_request is required");
  } else {
    if (executionRequest.webapp_role !== "queue_and_forward_only") {
      errors.push("execution_request.webapp_role must be queue_and_forward_only");
    }
    if (executionRequest.scheduler_owner !== "BlueprintCapturePipeline") {
      errors.push("execution_request.scheduler_owner must be BlueprintCapturePipeline");
    }
  }

  return errors;
}
