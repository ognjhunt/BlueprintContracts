from __future__ import annotations

import json
from pathlib import Path

from blueprint_contracts.canonical_package import (
    compute_canonical_package_version,
    verify_canonical_package_version,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_compute_and_verify_canonical_package_version(tmp_path: Path) -> None:
    scene_memory_manifest = {"schema_version": "v1", "scene_id": "scene-1"}
    conditioning_bundle = {"schema_version": "v1", "capture_id": "capture-1"}
    object_geometry_manifest = {"schema_version": "v1", "objects": []}
    task_anchor_manifest = {"schema_version": "v1", "tasks": []}
    protected_regions_manifest = {"schema_version": "v1", "regions": []}
    canonical_render_policy = {"schema_version": "v1", "mode": "canonical"}
    presentation_variance_policy = {"schema_version": "v1", "allowed_variable_inputs": []}

    scene_memory_manifest_path = tmp_path / "scene_memory_manifest.json"
    conditioning_bundle_path = tmp_path / "conditioning_bundle.json"
    object_geometry_manifest_path = tmp_path / "object_geometry_manifest.json"
    task_anchor_manifest_path = tmp_path / "task_anchor_manifest.json"
    for path, payload in (
        (scene_memory_manifest_path, scene_memory_manifest),
        (conditioning_bundle_path, conditioning_bundle),
        (object_geometry_manifest_path, object_geometry_manifest),
        (task_anchor_manifest_path, task_anchor_manifest),
    ):
        _write_json(path, payload)

    spec = {
        "schema_version": "v1",
        "scene_id": "scene-1",
        "capture_id": "capture-1",
        "conditioning": {
            "scene_memory_manifest_path": str(scene_memory_manifest_path),
            "conditioning_bundle_path": str(conditioning_bundle_path),
            "local_paths": {
                "scene_memory_manifest_path": str(scene_memory_manifest_path),
                "conditioning_bundle_path": str(conditioning_bundle_path),
            },
        },
        "geometry": {
            "object_geometry_manifest_path": str(object_geometry_manifest_path),
        },
        "task_anchor_manifest_path": str(task_anchor_manifest_path),
    }
    spec["canonical_package_version"] = compute_canonical_package_version(
        scene_memory_manifest=scene_memory_manifest,
        conditioning_bundle=conditioning_bundle,
        object_geometry_manifest=object_geometry_manifest,
        task_anchor_manifest=task_anchor_manifest,
        site_world_spec=spec,
        protected_regions_manifest=protected_regions_manifest,
        canonical_render_policy=canonical_render_policy,
        presentation_variance_policy=presentation_variance_policy,
    )

    assert (
        verify_canonical_package_version(
            spec=spec,
            protected_regions_manifest=protected_regions_manifest,
            canonical_render_policy=canonical_render_policy,
            presentation_variance_policy=presentation_variance_policy,
        )
        is None
    )
