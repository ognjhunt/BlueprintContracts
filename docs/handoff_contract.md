# `handoff_contract`

## Purpose

`handoff_contract` validates the qualification handoff exchanged between `BlueprintCapturePipeline` and `BlueprintValidation`.

This handoff is not a canonical site-world package.

- it can influence canonical launch gating through `qualification_state`
- it can influence downstream readiness through `downstream_evaluation_eligibility`
- it does not prove canonical truth
- it does not imply runtime readiness
- it does not imply canonical package verification

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

Thin handoffs are normalized into the shared qualification fields for compatibility, but still remain qualification-only inputs.

## Normalization Guarantees

The validator normalizes:

- `qualification_state` to lowercase
- `source_contract`
- `compatibility_mode` for thin handoffs
- default summaries and execution flags where the shared contract requires deterministic behavior

It intentionally does not normalize a handoff into a canonical package, runtime registration, or verified site-world artifact.

## Example: Rich Handoff

```json
{
  "schema_version": "v1",
  "site_submission_id": "site-sub-001",
  "opportunity_id": "opp-001",
  "qualification_state": "ready",
  "downstream_evaluation_eligibility": true,
  "operator_approved_summary": "Qualified warehouse tote-pick lane",
  "scoped_task_definition": {
    "task_id": "task-001",
    "scoped_task_statement": "Pick tote from shelf bay 3",
    "success_criteria": ["grasp tote", "clear shelf"],
    "in_scope_zone": "bay-3"
  },
  "site_constraints": {
    "operating_constraints": ["night shift only"],
    "privacy_security_constraints": ["no worker faces"],
    "known_blockers": ["reflective wrap on two pallets"]
  }
}
```

## Example: Legacy Thin Handoff

```json
{
  "schema_version": "v1",
  "scene_id": "scene-demo-001",
  "capture_id": "capture-demo-001",
  "readiness_state": "ready",
  "match_ready": true
}
```
