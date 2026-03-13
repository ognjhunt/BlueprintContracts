# `runtime_layer_contract`

## Purpose

`runtime_layer_contract` owns the shared semantics that decide:

- what counts as grounded canonical truth
- what is safe to treat as editable or presentation-only
- how runtime launchability is expressed in a stable machine-readable way

It does not own runtime execution. It owns the contract both repos must agree on.

## Supported Public API

- `ALLOWED_GROUNDING_LEVELS`
- `ALLOWED_GROUNDING_STATUSES`
- `ALLOWED_RUNTIME_READINESS_STATES`
- shared threshold constants
- `grounding_fields_from_provenance`
- `validate_grounding_provenance`
- `validate_output_linkage`
- `validate_runtime_eligibility`
- `with_grounding_fields`
- `task_critical_object_ids`
- `classify_region`
- `build_protected_regions_manifest`
- `build_canonical_render_policy`
- `build_presentation_variance_policy`
- `validate_runtime_layer_spec`
- `load_runtime_layer_bundle`

## Canonical vs Presentation Semantics

### Provenance

Shared provenance fields:

- `grounding_level`
- `confidence`
- `evidence_sources`
- `observation_coverage`
- `canonical_truth`
- `presentation_only`

Validation rules:

- `canonical_truth=true` requires evidence-backed provenance
- `presentation_only=true` requires `canonical_truth=false`
- `observed` and `reconstructed` provenance require non-empty `evidence_sources`
- missing evidence must not be represented as grounded canonical truth

### Output Linkage

Canonical packages and derivatives expose shared linkage fields:

- `canonical_artifact_uri`
- `presentation_artifact_uri`
- `derivation_mode`
- `authoritative_record`

Required meaning:

- canonical outputs are authoritative
- presentation outputs are non-authoritative derivatives
- presentation/demo artifacts may use more permissive completion, but may not override canonical truth

## Machine-Readable Launchability

`runtime_eligibility` is the authoritative launch gate.

Required fields:

- `launchable`
- `readiness_state`
- `blockers`
- `warnings`
- `grounding_status`

Optional fields:

- `ungrounded_reason`
- `empty_index_cause`
- `runtime_base_url`
- `websocket_base_url`
- `launchable_backends`
- `default_backend`

Consistency rules:

- `launchable=true` requires `readiness_state=="launchable"` and no blockers
- `launchable=false` with blockers requires `readiness_state=="blocked"`
- `launchable=false` without blockers requires `readiness_state=="incomplete"`
- `grounding_status=="ungrounded"` requires `ungrounded_reason` and cannot be launchable

`status` is not a substitute for `readiness_state`. Producers may keep informational status elsewhere, but `runtime_eligibility.readiness_state` is the required cross-repo contract field.

## Runtime-Layer Spec Validation

`validate_runtime_layer_spec()` now validates both references and meaning:

- `canonical_package_version` exists
- runtime-layer policy URIs and local paths exist
- referenced policy files exist and carry `schema_version == "v1"`
- `runtime_eligibility`, `canonical_output`, `presentation_output`, and `provenance` are present and internally valid
- grounding status is consistent across `spec`, `runtime_layer_policy`, `runtime_eligibility`, and `protected_regions_manifest`
- canonical site-world specs cannot be both `ungrounded` and launchable

## Example: Protected Canonical Runtime

```json
{
  "runtime_eligibility": {
    "launchable": true,
    "readiness_state": "launchable",
    "blockers": [],
    "warnings": [],
    "grounding_status": "grounded",
    "launchable_backends": ["neoverse"],
    "default_backend": "neoverse"
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
```

## Example: Presentation-Only Derivative

```json
{
  "canonical_artifact_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
  "presentation_artifact_uri": "gs://bucket/presentation_world/runtime_demo_manifest.json",
  "derivation_mode": "limited",
  "authoritative_record": false,
  "provenance": {
    "grounding_level": "generated",
    "evidence_sources": [
      "gs://bucket/evaluation_prep/site_world_spec.json",
      "gs://bucket/presentation_world/presentation_world_manifest.json"
    ],
    "canonical_truth": false,
    "presentation_only": true
  }
}
```
