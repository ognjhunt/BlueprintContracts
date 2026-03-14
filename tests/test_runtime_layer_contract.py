from __future__ import annotations

import json
from pathlib import Path

from blueprint_contracts.runtime_layer_contract import (
    ALLOWED_GROUNDING_LEVELS,
    ALLOWED_GROUNDING_STATUSES,
    ALLOWED_RUNTIME_READINESS_STATES,
    DEGRADED_EDITABLE_RATIO_THRESHOLD,
    EDITABLE_LOW_CONFIDENCE_THRESHOLD,
    LOCK_VIOLATION_RETRY_BUDGET,
    PROTECTED_OBSERVED_THRESHOLD,
    PROTECTED_RECONSTRUCTED_THRESHOLD,
    TASK_CRITICAL_DILATION_PX,
    TASK_CRITICAL_OVERRIDE_THRESHOLD,
    build_canonical_render_policy,
    build_presentation_variance_policy,
    build_protected_regions_manifest,
    classify_region,
    load_runtime_layer_bundle,
    validate_grounding_provenance,
    validate_output_linkage,
    validate_runtime_eligibility,
    validate_runtime_layer_spec,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_classify_region_threshold_boundaries() -> None:
    assert classify_region(grounding_level="observed", confidence=PROTECTED_OBSERVED_THRESHOLD) == "locked"
    assert classify_region(grounding_level="observed", confidence=PROTECTED_OBSERVED_THRESHOLD - 0.01) == "editable"
    assert classify_region(grounding_level="reconstructed", confidence=PROTECTED_RECONSTRUCTED_THRESHOLD) == "locked"
    assert classify_region(grounding_level="reconstructed", confidence=EDITABLE_LOW_CONFIDENCE_THRESHOLD) == "uncertain"
    assert classify_region(grounding_level="reconstructed", confidence=EDITABLE_LOW_CONFIDENCE_THRESHOLD - 0.01) == "editable"
    assert classify_region(
        grounding_level="generated",
        confidence=TASK_CRITICAL_OVERRIDE_THRESHOLD,
        task_critical=True,
    ) == "locked"
    assert classify_region(grounding_level="observed", confidence=0.9, provenance_present=False) == "editable"


def test_build_protected_regions_manifest_marks_ungrounded_empty_index() -> None:
    manifest = build_protected_regions_manifest(
        scene_id="scene-1",
        capture_id="capture-1",
        object_geometry_manifest={"status": "missing_object_index", "objects": []},
        task_anchor_manifest={"tasks": []},
    )
    assert manifest["grounding_status"] == "ungrounded"
    assert manifest["ungrounded_reason"] == "missing_object_index"


def test_build_protected_regions_manifest_marks_task_critical_ids_and_thresholds() -> None:
    manifest = build_protected_regions_manifest(
        scene_id="scene-1",
        capture_id="capture-1",
        object_geometry_manifest={
            "status": "ready",
            "objects": [
                {
                    "object_id": "obj-1",
                    "label": "tote",
                    "provenance": {
                        "grounding_level": "generated",
                        "confidence": TASK_CRITICAL_OVERRIDE_THRESHOLD,
                    },
                }
            ],
        },
        task_anchor_manifest={
            "tasks": [
                {
                    "target_object_ids": ["obj-1"],
                }
            ]
        },
    )
    region = manifest["regions"][0]
    assert region["task_critical"] is True
    assert region["classification"] == "locked"
    assert manifest["thresholds"]["task_critical_dilation_px"] == TASK_CRITICAL_DILATION_PX


def test_validate_runtime_layer_spec_reports_missing_fields_and_files(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    spec = {
        "runtime_layer_policy": {
            "protected_regions_manifest_uri": "gs://bucket/protected.json",
            "canonical_render_policy_uri": "gs://bucket/render.json",
            "presentation_variance_policy_uri": "",
            "protected_regions_manifest_path": str(root / "protected.json"),
            "canonical_render_policy_path": "",
            "presentation_variance_policy_path": str(root / "variance.json"),
        },
    }
    errors = validate_runtime_layer_spec(spec)
    assert "missing_canonical_package_version" in errors
    assert "missing_runtime_layer_policy:presentation_variance_policy_uri" in errors
    assert "missing_runtime_layer_policy:canonical_render_policy_path" in errors
    assert "missing_runtime_layer_policy_file:protected.json" in errors
    assert "missing_runtime_layer_policy_file:variance.json" in errors


def test_validate_and_load_runtime_layer_bundle(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    protected_path = root / "protected.json"
    render_path = root / "render.json"
    variance_path = root / "variance.json"
    _write_json(protected_path, {"schema_version": "v1", "grounding_status": "grounded", "region_count": 0, "regions": []})
    _write_json(render_path, build_canonical_render_policy())
    _write_json(variance_path, build_presentation_variance_policy())
    spec = {
        "canonical_package_version": "pkg-v1",
        "grounding_status": "grounded",
        "runtime_eligibility": {
            "launchable": True,
            "readiness_state": "launchable",
            "blockers": [],
            "warnings": [],
            "grounding_status": "grounded",
        },
        "canonical_output": {
            "canonical_artifact_uri": "gs://bucket/spec.json",
            "presentation_artifact_uri": "gs://bucket/presentation_world_manifest.json",
            "derivation_mode": "grounding_first",
            "authoritative_record": True,
        },
        "presentation_output": {
            "canonical_artifact_uri": "gs://bucket/spec.json",
            "presentation_artifact_uri": "gs://bucket/runtime_demo_manifest.json",
            "derivation_mode": "limited",
            "authoritative_record": False,
        },
        "provenance": {
            "grounding_level": "observed",
            "confidence": 0.95,
            "evidence_sources": ["gs://bucket/scene_memory_manifest.json"],
            "canonical_truth": True,
            "presentation_only": False,
        },
        "runtime_layer_policy": {
            "protected_regions_manifest_uri": "gs://bucket/protected.json",
            "canonical_render_policy_uri": "gs://bucket/render.json",
            "presentation_variance_policy_uri": "gs://bucket/variance.json",
            "protected_regions_manifest_path": str(protected_path),
            "canonical_render_policy_path": str(render_path),
            "presentation_variance_policy_path": str(variance_path),
            "grounding_status": "grounded",
        },
    }
    assert validate_runtime_layer_spec(spec) == []
    bundle = load_runtime_layer_bundle(spec)
    assert bundle["canonical_render_policy"]["schema_version"] == "v1"


def test_shared_threshold_constants_are_locked() -> None:
    assert PROTECTED_OBSERVED_THRESHOLD == 0.85
    assert PROTECTED_RECONSTRUCTED_THRESHOLD == 0.80
    assert EDITABLE_LOW_CONFIDENCE_THRESHOLD == 0.65
    assert TASK_CRITICAL_OVERRIDE_THRESHOLD == 0.70
    assert TASK_CRITICAL_DILATION_PX == 3
    assert DEGRADED_EDITABLE_RATIO_THRESHOLD == 0.40
    assert LOCK_VIOLATION_RETRY_BUDGET == 1


def test_validate_grounding_provenance_rejects_canonical_truth_without_evidence() -> None:
    errors = validate_grounding_provenance(
        {
            "grounding_level": "observed",
            "confidence": 0.9,
            "evidence_sources": [],
            "canonical_truth": True,
            "presentation_only": False,
        }
    )
    assert "provenance:canonical_truth_requires_evidence_sources" in errors


def test_validate_output_linkage_rejects_authoritative_presentation_output() -> None:
    errors = validate_output_linkage(
        {
            "canonical_artifact_uri": "gs://bucket/spec.json",
            "presentation_artifact_uri": "gs://bucket/demo.json",
            "derivation_mode": "limited",
            "authoritative_record": True,
        },
        context="presentation_output",
        expected_authoritative=False,
    )
    assert "presentation_output:authoritative_record_expected_false" in errors


def test_validate_runtime_eligibility_enforces_state_and_blocker_consistency() -> None:
    errors = validate_runtime_eligibility(
        {
            "launchable": False,
            "readiness_state": "launchable",
            "blockers": ["missing_task_anchor_manifest"],
            "warnings": [],
            "grounding_status": "grounded",
        }
    )
    assert "runtime_eligibility:blocked_runtime_requires_blocked_state" in errors


def test_validate_runtime_layer_spec_rejects_ungrounded_launchable_spec(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    protected_path = root / "protected.json"
    render_path = root / "render.json"
    variance_path = root / "variance.json"
    _write_json(
        protected_path,
        {
            "schema_version": "v1",
            "grounding_status": "ungrounded",
            "ungrounded_reason": "missing_object_index",
            "region_count": 0,
            "regions": [],
        },
    )
    _write_json(render_path, build_canonical_render_policy())
    _write_json(variance_path, build_presentation_variance_policy())
    spec = {
        "canonical_package_version": "pkg-v1",
        "grounding_status": "ungrounded",
        "ungrounded_reason": "missing_object_index",
        "runtime_eligibility": {
            "launchable": True,
            "readiness_state": "launchable",
            "blockers": [],
            "warnings": [],
            "grounding_status": "ungrounded",
            "ungrounded_reason": "missing_object_index",
        },
        "canonical_output": {
            "canonical_artifact_uri": "gs://bucket/spec.json",
            "presentation_artifact_uri": "gs://bucket/presentation_world_manifest.json",
            "derivation_mode": "grounding_first",
            "authoritative_record": True,
        },
        "presentation_output": {
            "canonical_artifact_uri": "gs://bucket/spec.json",
            "presentation_artifact_uri": "gs://bucket/runtime_demo_manifest.json",
            "derivation_mode": "limited",
            "authoritative_record": False,
        },
        "provenance": {
            "grounding_level": "observed",
            "confidence": 0.95,
            "evidence_sources": ["gs://bucket/scene_memory_manifest.json"],
            "canonical_truth": True,
            "presentation_only": False,
        },
        "runtime_layer_policy": {
            "protected_regions_manifest_uri": "gs://bucket/protected.json",
            "canonical_render_policy_uri": "gs://bucket/render.json",
            "presentation_variance_policy_uri": "gs://bucket/variance.json",
            "protected_regions_manifest_path": str(protected_path),
            "canonical_render_policy_path": str(render_path),
            "presentation_variance_policy_path": str(variance_path),
            "grounding_status": "ungrounded",
            "ungrounded_reason": "missing_object_index",
        },
    }
    errors = validate_runtime_layer_spec(spec)
    assert errors == []


def test_allowed_contract_state_sets_are_explicit() -> None:
    assert ALLOWED_GROUNDING_LEVELS == frozenset({"observed", "reconstructed", "inferred", "generated"})
    assert ALLOWED_GROUNDING_STATUSES == frozenset({"grounded", "ungrounded"})
    assert ALLOWED_RUNTIME_READINESS_STATES == frozenset({"launchable", "blocked", "incomplete"})
