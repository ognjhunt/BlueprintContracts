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

### Legacy thin handoff

Required fields:

- `schema_version == "v1"`
- `scene_id`
- `capture_id`
- `readiness_state`
- `match_ready`
