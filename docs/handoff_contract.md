# `handoff_contract`

## Purpose

This module defines the shared validation boundary for qualified opportunity handoffs exchanged between Pipeline and Validation.

## Supported Public API

- `QUALIFIED_OPPORTUNITY_SCHEMA_VERSION`
- `RICH_HANDOFF_MODE`
- `LEGACY_THIN_HANDOFF_MODE`
- `LEGACY_THIN_COMPATIBILITY_MODE`
- `ALLOWED_QUALIFICATION_STATES`
- `QualifiedOpportunityValidationError`
- `validate_qualified_opportunity_handoff`
- `load_and_validate_qualified_opportunity_handoff`

## Accepted Input Modes

### Rich handoff

Required fields:

- `schema_version == "v1"`
- `site_submission_id`
- `opportunity_id`
- `qualification_state`
- `downstream_evaluation_eligibility`
- `operator_approved_summary`
- `scoped_task_definition`
- `site_constraints`

Optional fields:

- `target_robot_team`
- `scene_memory_package`
- `geometry_package`
- `scene_package`
- `qualification_focus`

Normalization behavior:

- `qualification_state` is lowercased
- `qualification_focus` defaults to `neutral_site_readiness`
- `requires_robot_team_for_execution` is derived from whether `target_robot_team` is present
- `source_contract` is always `qualified_opportunity_v1`

### Legacy thin handoff

Required fields:

- `schema_version == "v1"`
- `scene_id`
- `capture_id`
- `readiness_state`
- `match_ready`

Optional fields:

- `summary`
- `constraints`
- `scene_memory_package`
- `geometry_package`
- `scene_package`

Normalization behavior:

- `readiness_state` is normalized into `qualification_state`
- `match_ready` is normalized into `downstream_evaluation_eligibility`
- `site_submission_id` is derived from `capture_id`
- `opportunity_id` is derived from `scene_id`
- `operator_approved_summary` falls back to a deterministic synthesized summary when `summary` is missing
- `source_contract` is always `capture_pipeline_thin_v1`
- `compatibility_mode` is always `legacy_thin_handoff`

## Rejection Rules

- Mixed payloads that contain both rich-mode and thin-mode fields are rejected as ambiguous.
- Invalid or missing nested fields return actionable field-path-based error messages.
- `qualification_state` must be one of `ready`, `risky`, or `not_ready_yet`.
