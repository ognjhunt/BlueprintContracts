# `site_world_contract`

## Purpose

This module validates and loads the adjacent site-world artifact set used as the shared boundary between Capture Pipeline outputs and Validation intake.

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

## Artifact Ownership

### Registration

Authoritative identity document. Required fields:

- `schema_version == "v1"`
- `site_world_id`
- `scene_id`
- `capture_id`

### Health

Optional adjacent artifact at `site_world_health.json`.

If present:

- `schema_version == "v1"`
- `site_world_id` must match registration

### Spec

Optional adjacent artifact at `site_world_spec.json`, unless `require_spec=True`.

If present:

- `schema_version == "v1"`
- `scene_id` must match registration
- `capture_id` must match registration
- `canonical_package_version` must be present

## Structural Behavior

- `load_site_world_bundle()` always anchors identity on registration.
- `merge_site_world_definition()` overlays spec-owned fields onto the registration copy.
- `grounding_summary()` checks only local file existence for portable artifact completeness; remote URIs are not treated as existing local files.
- Missing required local grounding artifacts are reported under `missing_required`.
- Missing optional local grounding artifacts are reported under `missing_optional`.

## Trajectory Normalization

- string input becomes `{"trajectory": "<value>"}`
- empty or `None` becomes `{"trajectory": "static"}`
- mapping input is copied; missing `trajectory` defaults to `static`
