# `site_world_contract`

## Purpose

`site_world_contract` defines the shared canonical site-world package boundary between `BlueprintCapturePipeline` and `BlueprintValidation`.

Public product boundary: `site_world` remains a compatibility/schema term for canonical artifacts. It supports Task Evaluation Runs, Post-Training Data Packages, hosted review, and validation, but it is not the primary public offer by itself.

The package is grounding-first and authoritative:

- `site_world_registration.json` is the authoritative runtime registration record
- `site_world_health.json` is the authoritative machine-readable health and launchability record
- `site_world_spec.json` is the authoritative canonical package definition

Presentation and demo artifacts may derive from the canonical package, but they are not authoritative site-world records.

## Supported Public API

- `SITE_WORLD_SCHEMA_VERSION`
- `DEFAULT_TRAJECTORY`
- `SiteWorldBundle`
- `SiteWorldIntakeError`
- `adjacent_site_world_paths`
- `normalize_trajectory_payload`
- `merge_site_world_definition`
- `grounding_summary`
- `load_site_world_bundle`
- `validate_site_world_bundle`

## Required Bundle Semantics

`load_site_world_bundle()` keeps additive `v1` compatibility. It validates identity and returns the adjacent bundle.

`validate_site_world_bundle(..., production_mode=True)` hardens the narrowed production workflow:

- canonical packages must declare `canonical_package_uri` and `canonical_package_version`
- canonical packages must declare `qualification_state` and `downstream_evaluation_eligibility`
- canonical packages must carry `runtime_layer_policy`, `runtime_eligibility`, `canonical_output`, `presentation_output`, and `provenance`
- `runtime_eligibility.readiness_state` is required and authoritative for machine-readable launch gating
- allowed `runtime_eligibility.readiness_state` values are `launchable`, `blocked`, and `incomplete`
- `health.launchable` must exist and match `runtime_eligibility.launchable`
- canonical package versions must agree across registration, health, and spec when present
- canonical records must not be `presentation_only`
- `grounding_status == "ungrounded"` requires `ungrounded_reason` and cannot be launchable

`status` remains informational. Machine-readable launch gating is owned by `runtime_eligibility`, and consumer repos must not emit `status` in place of `readiness_state`.

## Resolved Bundle Behavior

`merge_site_world_definition()` anchors identity on registration and overlays spec-owned canonical fields, including:

- `runtime_eligibility`
- `qualification_references`
- `canonical_output`
- `presentation_output`
- `world_model_policy`
- `provenance`
- `generated_at`
- `empty_index_cause`

This keeps `bundle.resolved` faithful to the downstream canonical package shape already emitted by Pipeline.

## Example: Launchable Canonical Package

```json
{
  "site_world_registration.json": {
    "schema_version": "v1",
    "site_world_id": "siteworld-1",
    "scene_id": "scene-1",
    "capture_id": "capture-1",
    "canonical_package_version": "pkg-v1",
    "authoritative_record": true
  },
  "site_world_health.json": {
    "schema_version": "v1",
    "site_world_id": "siteworld-1",
    "launchable": true,
    "grounding_status": "grounded",
    "canonical_package_version": "pkg-v1",
    "authoritative_record": true
  },
  "site_world_spec.json": {
    "schema_version": "v1",
    "site_world_id": "siteworld-1",
    "scene_id": "scene-1",
    "capture_id": "capture-1",
    "canonical_package_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
    "canonical_package_version": "pkg-v1",
    "qualification_state": "ready",
    "downstream_evaluation_eligibility": true,
    "grounding_status": "grounded",
    "runtime_eligibility": {
      "launchable": true,
      "readiness_state": "launchable",
      "blockers": [],
      "warnings": [],
      "grounding_status": "grounded"
    },
    "canonical_output": {
      "canonical_artifact_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
      "presentation_artifact_uri": "gs://bucket/presentation_world/presentation_world_manifest.json",
      "derivation_mode": "grounding_first",
      "authoritative_record": true
    },
    "presentation_output": {
      "canonical_artifact_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
      "presentation_artifact_uri": "gs://bucket/presentation_world/runtime_demo_manifest.json",
      "derivation_mode": "limited",
      "authoritative_record": false
    },
    "provenance": {
      "grounding_level": "observed",
      "evidence_sources": ["gs://bucket/scene_memory/scene_memory_manifest.json"],
      "canonical_truth": true,
      "presentation_only": false
    }
  }
}
```

## Example: Blocked Or Incomplete Canonical Package

Blocked canonical package:

```json
{
  "runtime_eligibility": {
    "launchable": false,
    "readiness_state": "blocked",
    "blockers": ["qualification_state:risky"],
    "warnings": [],
    "grounding_status": "grounded"
  }
}
```

Incomplete canonical package:

```json
{
  "runtime_eligibility": {
    "launchable": false,
    "readiness_state": "incomplete",
    "blockers": [],
    "warnings": ["occupancy_path_missing"],
    "grounding_status": "grounded"
  }
}
```

Ungrounded canonical package:

```json
{
  "grounding_status": "ungrounded",
  "ungrounded_reason": "missing_object_index",
  "runtime_eligibility": {
    "launchable": false,
    "readiness_state": "blocked",
    "blockers": ["runtime_grounding:missing_object_index"],
    "warnings": [],
    "grounding_status": "ungrounded",
    "ungrounded_reason": "missing_object_index"
  }
}
```
