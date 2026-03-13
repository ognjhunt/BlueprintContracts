# `runtime_layer_contract`

## Purpose

This module defines portable runtime-layer policy shared by Pipeline and Validation. It does not own runtime execution.

## Supported Public API

- `PROTECTED_OBSERVED_THRESHOLD`
- `PROTECTED_RECONSTRUCTED_THRESHOLD`
- `EDITABLE_LOW_CONFIDENCE_THRESHOLD`
- `TASK_CRITICAL_OVERRIDE_THRESHOLD`
- `TASK_CRITICAL_DILATION_PX`
- `DEGRADED_EDITABLE_RATIO_THRESHOLD`
- `LOCK_VIOLATION_RETRY_BUDGET`
- `grounding_fields_from_provenance`
- `with_grounding_fields`
- `task_critical_object_ids`
- `classify_region`
- `build_protected_regions_manifest`
- `build_canonical_render_policy`
- `build_presentation_variance_policy`
- `validate_runtime_layer_spec`
- `load_runtime_layer_bundle`

## Shared Thresholds

- `PROTECTED_OBSERVED_THRESHOLD = 0.85`
  Observed geometry at or above this confidence is locked.
- `PROTECTED_RECONSTRUCTED_THRESHOLD = 0.80`
  Reconstructed geometry at or above this confidence is locked.
- `EDITABLE_LOW_CONFIDENCE_THRESHOLD = 0.65`
  Anything below this confidence is editable.
- `TASK_CRITICAL_OVERRIDE_THRESHOLD = 0.70`
  Task-critical objects at or above this confidence are locked even before the normal observed/reconstructed threshold.
- `TASK_CRITICAL_DILATION_PX = 3`
  Shared render policy dilation around locked task-critical masks.
- `DEGRADED_EDITABLE_RATIO_THRESHOLD = 0.40`
  Shared quality label threshold for editable-heavy presentations.
- `LOCK_VIOLATION_RETRY_BUDGET = 1`
  Shared fallback retry budget after locked-region violations.

## Classification Semantics

- Missing provenance is editable.
- Missing grounding level or confidence is editable.
- `observed` is locked only when confidence is at least `PROTECTED_OBSERVED_THRESHOLD`.
- `reconstructed` is locked at or above `PROTECTED_RECONSTRUCTED_THRESHOLD`, uncertain between the editable threshold and reconstructed threshold, and editable below the editable threshold.
- `task_critical=True` locks at or above `TASK_CRITICAL_OVERRIDE_THRESHOLD`.
- `inferred` and `generated` remain editable.

## Runtime-Layer Spec Validation

`validate_runtime_layer_spec()` checks:

- `canonical_package_version` is present
- all required runtime-layer URIs are present
- all required local runtime-layer file paths are present
- referenced local policy files actually exist
