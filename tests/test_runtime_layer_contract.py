from __future__ import annotations

import json
from pathlib import Path

from blueprint_contracts.runtime_layer_contract import (
    build_canonical_render_policy,
    build_presentation_variance_policy,
    build_protected_regions_manifest,
    classify_region,
    load_runtime_layer_bundle,
    validate_runtime_layer_spec,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_classify_region_thresholds() -> None:
    assert classify_region(grounding_level="observed", confidence=0.9) == "locked"
    assert classify_region(grounding_level="reconstructed", confidence=0.72) == "uncertain"
    assert classify_region(grounding_level="reconstructed", confidence=0.72, task_critical=True) == "locked"


def test_build_protected_regions_manifest_marks_ungrounded_empty_index() -> None:
    manifest = build_protected_regions_manifest(
        scene_id="scene-1",
        capture_id="capture-1",
        object_geometry_manifest={"status": "missing_object_index", "objects": []},
        task_anchor_manifest={"tasks": []},
    )
    assert manifest["grounding_status"] == "ungrounded"


def test_validate_and_load_runtime_layer_bundle(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    protected_path = root / "protected.json"
    render_path = root / "render.json"
    variance_path = root / "variance.json"
    _write_json(protected_path, {"schema_version": "v1", "regions": []})
    _write_json(render_path, build_canonical_render_policy())
    _write_json(variance_path, build_presentation_variance_policy())
    spec = {
        "canonical_package_version": "pkg-v1",
        "runtime_layer_policy": {
            "protected_regions_manifest_uri": "gs://bucket/protected.json",
            "canonical_render_policy_uri": "gs://bucket/render.json",
            "presentation_variance_policy_uri": "gs://bucket/variance.json",
            "protected_regions_manifest_path": str(protected_path),
            "canonical_render_policy_path": str(render_path),
            "presentation_variance_policy_path": str(variance_path),
        },
    }
    assert validate_runtime_layer_spec(spec) == []
    bundle = load_runtime_layer_bundle(spec)
    assert bundle["canonical_render_policy"]["schema_version"] == "v1"
