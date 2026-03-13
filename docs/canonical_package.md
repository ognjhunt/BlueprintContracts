# `canonical_package`

## Purpose

`canonical_package` owns deterministic versioning and lightweight contract validation for the authoritative site-world package.

The canonical package is the shared truth consumed by `BlueprintValidation` and downstream hosting/runtime decisions. It must preserve truth and uncertainty rather than filling gaps with presentation-only completion.

## Supported Public API

- `CANONICAL_PACKAGE_HASH_INPUTS`
- `normalized_json_bytes`
- `compute_canonical_package_version`
- `verify_canonical_package_version`
- `verify_canonical_package_version_details`
- `validate_canonical_package_contract`

## Hash Inputs

Hash order is fixed:

1. scene memory manifest
2. conditioning bundle
3. object geometry manifest
4. task anchor manifest
5. site-world spec without `canonical_package_version`
6. protected regions manifest
7. canonical render policy
8. presentation variance policy

`canonical_package_version` is excluded from the hashed spec copy so the digest does not become self-referential.

## Verification Semantics

`verify_canonical_package_version_details()` returns:

- `verified`
- `mismatch`
- `inputs_missing`
- `expected_version_missing`

Payload shape:

```json
{
  "status": "verified",
  "expected_version": "pkg-v1",
  "observed_version": "pkg-v1",
  "error": null
}
```

Compatibility wrapper behavior:

- `verify_canonical_package_version()` returns `None` for `verified`
- `verify_canonical_package_version()` returns `None` for `expected_version_missing` to preserve existing additive `v1` behavior
- it returns the legacy string error format for `inputs_missing` and `mismatch`

## Canonical Contract Validation

`validate_canonical_package_contract()` enforces the minimum authoritative package boundary:

- canonical packages must declare `canonical_package_version`
- `canonical_output.authoritative_record` must be `true`
- `presentation_output.authoritative_record` must be `false`
- canonical package provenance must not claim `canonical_truth` without evidence
- canonical packages must not be marked `presentation_only`

This validator is intentionally lightweight. Site-world bundle validation performs the stronger cross-artifact consistency checks.

## Example: Verified Canonical Package

```json
{
  "canonical_package_version": "2a6d5c...",
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

## Example: Version Missing Vs Inputs Missing

Expected version missing:

```json
{
  "status": "expected_version_missing",
  "expected_version": null,
  "observed_version": "2a6d5c...",
  "error": null
}
```

Verification inputs missing:

```json
{
  "status": "inputs_missing",
  "expected_version": "2a6d5c...",
  "observed_version": null,
  "error": "canonical_package_verification_inputs_missing"
}
```
