from __future__ import annotations

import json
from pathlib import Path

from blueprint_contracts.canonical_package import (
    CANONICAL_PACKAGE_HASH_INPUTS,
    compute_canonical_package_version,
    normalized_json_bytes,
    verify_canonical_package_version,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_inputs() -> dict:
    return {
        "scene_memory_manifest": {"schema_version": "v1", "scene_id": "scene-1"},
        "conditioning_bundle": {"schema_version": "v1", "capture_id": "capture-1"},
        "object_geometry_manifest": {"schema_version": "v1", "objects": []},
        "task_anchor_manifest": {"schema_version": "v1", "tasks": []},
        "protected_regions_manifest": {"schema_version": "v1", "regions": []},
        "canonical_render_policy": {"schema_version": "v1", "mode": "canonical"},
        "presentation_variance_policy": {"schema_version": "v1", "allowed_variable_inputs": []},
        "site_world_spec": {
            "schema_version": "v1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
            "task_anchor_manifest_path": "",
            "conditioning": {},
            "geometry": {},
        },
    }


def test_normalized_json_bytes_is_order_independent() -> None:
    assert normalized_json_bytes({"b": 2, "a": 1}) == normalized_json_bytes({"a": 1, "b": 2})


def test_compute_canonical_package_version_ignores_spec_version_field() -> None:
    inputs = _base_inputs()
    spec_a = dict(inputs["site_world_spec"], canonical_package_version="first")
    spec_b = dict(inputs["site_world_spec"], canonical_package_version="second")
    version_a = compute_canonical_package_version(
        scene_memory_manifest=inputs["scene_memory_manifest"],
        conditioning_bundle=inputs["conditioning_bundle"],
        object_geometry_manifest=inputs["object_geometry_manifest"],
        task_anchor_manifest=inputs["task_anchor_manifest"],
        site_world_spec=spec_a,
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )
    version_b = compute_canonical_package_version(
        scene_memory_manifest=inputs["scene_memory_manifest"],
        conditioning_bundle=inputs["conditioning_bundle"],
        object_geometry_manifest=inputs["object_geometry_manifest"],
        task_anchor_manifest=inputs["task_anchor_manifest"],
        site_world_spec=spec_b,
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )
    assert version_a == version_b


def test_compute_canonical_package_version_changes_when_hash_inputs_change() -> None:
    inputs = _base_inputs()
    baseline = compute_canonical_package_version(
        scene_memory_manifest=inputs["scene_memory_manifest"],
        conditioning_bundle=inputs["conditioning_bundle"],
        object_geometry_manifest=inputs["object_geometry_manifest"],
        task_anchor_manifest=inputs["task_anchor_manifest"],
        site_world_spec=inputs["site_world_spec"],
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )
    changed = compute_canonical_package_version(
        scene_memory_manifest=inputs["scene_memory_manifest"],
        conditioning_bundle=inputs["conditioning_bundle"],
        object_geometry_manifest={"schema_version": "v1", "objects": [{"object_id": "obj-1"}]},
        task_anchor_manifest=inputs["task_anchor_manifest"],
        site_world_spec=inputs["site_world_spec"],
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )
    assert baseline != changed


def test_verify_canonical_package_version_handles_missing_inputs(tmp_path: Path) -> None:
    spec = {
        "schema_version": "v1",
        "scene_id": "scene-1",
        "capture_id": "capture-1",
        "canonical_package_version": "pkg-v1",
        "conditioning": {
            "scene_memory_manifest_path": str(tmp_path / "missing-scene-memory.json"),
            "conditioning_bundle_path": str(tmp_path / "missing-conditioning.json"),
            "local_paths": {},
        },
        "geometry": {
            "object_geometry_manifest_path": str(tmp_path / "missing-geometry.json"),
        },
        "task_anchor_manifest_path": str(tmp_path / "missing-tasks.json"),
    }
    assert (
        verify_canonical_package_version(
            spec=spec,
            protected_regions_manifest={"schema_version": "v1", "regions": []},
            canonical_render_policy={"schema_version": "v1"},
            presentation_variance_policy={"schema_version": "v1"},
        )
        == "canonical_package_verification_inputs_missing"
    )


def test_compute_and_verify_canonical_package_version(tmp_path: Path) -> None:
    inputs = _base_inputs()
    scene_memory_manifest_path = tmp_path / "scene_memory_manifest.json"
    conditioning_bundle_path = tmp_path / "conditioning_bundle.json"
    object_geometry_manifest_path = tmp_path / "object_geometry_manifest.json"
    task_anchor_manifest_path = tmp_path / "task_anchor_manifest.json"
    for path, payload in (
        (scene_memory_manifest_path, inputs["scene_memory_manifest"]),
        (conditioning_bundle_path, inputs["conditioning_bundle"]),
        (object_geometry_manifest_path, inputs["object_geometry_manifest"]),
        (task_anchor_manifest_path, inputs["task_anchor_manifest"]),
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
        scene_memory_manifest=inputs["scene_memory_manifest"],
        conditioning_bundle=inputs["conditioning_bundle"],
        object_geometry_manifest=inputs["object_geometry_manifest"],
        task_anchor_manifest=inputs["task_anchor_manifest"],
        site_world_spec=spec,
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )

    assert (
        verify_canonical_package_version(
            spec=spec,
            protected_regions_manifest=inputs["protected_regions_manifest"],
            canonical_render_policy=inputs["canonical_render_policy"],
            presentation_variance_policy=inputs["presentation_variance_policy"],
        )
        is None
    )


def test_verify_canonical_package_version_reports_mismatch(tmp_path: Path) -> None:
    inputs = _base_inputs()
    scene_memory_manifest_path = tmp_path / "scene_memory_manifest.json"
    conditioning_bundle_path = tmp_path / "conditioning_bundle.json"
    object_geometry_manifest_path = tmp_path / "object_geometry_manifest.json"
    task_anchor_manifest_path = tmp_path / "task_anchor_manifest.json"
    for path, payload in (
        (scene_memory_manifest_path, inputs["scene_memory_manifest"]),
        (conditioning_bundle_path, inputs["conditioning_bundle"]),
        (object_geometry_manifest_path, inputs["object_geometry_manifest"]),
        (task_anchor_manifest_path, inputs["task_anchor_manifest"]),
    ):
        _write_json(path, payload)
    spec = {
        "schema_version": "v1",
        "scene_id": "scene-1",
        "capture_id": "capture-1",
        "canonical_package_version": "not-the-real-value",
        "conditioning": {
            "scene_memory_manifest_path": str(scene_memory_manifest_path),
            "conditioning_bundle_path": str(conditioning_bundle_path),
            "local_paths": {},
        },
        "geometry": {
            "object_geometry_manifest_path": str(object_geometry_manifest_path),
        },
        "task_anchor_manifest_path": str(task_anchor_manifest_path),
    }
    mismatch = verify_canonical_package_version(
        spec=spec,
        protected_regions_manifest=inputs["protected_regions_manifest"],
        canonical_render_policy=inputs["canonical_render_policy"],
        presentation_variance_policy=inputs["presentation_variance_policy"],
    )
    assert mismatch is not None
    assert mismatch.startswith("canonical_package_version_mismatch:")


def test_hash_input_order_is_documented() -> None:
    assert CANONICAL_PACKAGE_HASH_INPUTS == (
        "scene_memory_manifest",
        "conditioning_bundle",
        "object_geometry_manifest",
        "task_anchor_manifest",
        "site_world_spec_without_canonical_package_version",
        "protected_regions_manifest",
        "canonical_render_policy",
        "presentation_variance_policy",
    )
