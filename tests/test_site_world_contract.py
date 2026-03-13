from __future__ import annotations

import json
from pathlib import Path

import pytest

from blueprint_contracts.site_world_contract import (
    DEFAULT_TRAJECTORY,
    SITE_WORLD_SCHEMA_VERSION,
    SiteWorldIntakeError,
    load_site_world_bundle,
    normalize_trajectory_payload,
    validate_site_world_bundle,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_registration(root: Path) -> Path:
    registration_path = root / "site_world_registration.json"
    _write_json(
        registration_path,
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
        },
    )
    return registration_path


def _production_spec(
    root: Path,
    *,
    launchable: bool,
    readiness_state: str,
    blockers: list[str] | None = None,
    grounding_status: str = "grounded",
    include_evidence: bool = True,
) -> dict:
    blockers = blockers or []
    spec = {
        "schema_version": "v1",
        "site_world_id": "siteworld-1",
        "scene_id": "scene-1",
        "capture_id": "capture-1",
        "canonical_package_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
        "canonical_package_version": "pkg-v1",
        "qualification_state": "ready",
        "downstream_evaluation_eligibility": True,
        "grounding_status": grounding_status,
        "ungrounded_reason": "missing_object_index" if grounding_status == "ungrounded" else None,
        "runtime_layer_policy": {
            "protected_regions_manifest_uri": "gs://bucket/protected.json",
            "canonical_render_policy_uri": "gs://bucket/render.json",
            "presentation_variance_policy_uri": "gs://bucket/variance.json",
            "protected_regions_manifest_path": str(root / "protected.json"),
            "canonical_render_policy_path": str(root / "render.json"),
            "presentation_variance_policy_path": str(root / "variance.json"),
            "grounding_status": grounding_status,
            "ungrounded_reason": "missing_object_index" if grounding_status == "ungrounded" else None,
        },
        "runtime_eligibility": {
            "launchable": launchable,
            "readiness_state": readiness_state,
            "blockers": list(blockers),
            "warnings": [],
            "grounding_status": grounding_status,
            "ungrounded_reason": "missing_object_index" if grounding_status == "ungrounded" else None,
        },
        "canonical_output": {
            "canonical_artifact_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
            "presentation_artifact_uri": "gs://bucket/presentation_world/presentation_world_manifest.json",
            "derivation_mode": "grounding_first",
            "authoritative_record": True,
            "output_policy": {"world_model_output_policy": "grounding_first"},
        },
        "presentation_output": {
            "canonical_artifact_uri": "gs://bucket/evaluation_prep/site_world_spec.json",
            "presentation_artifact_uri": "gs://bucket/presentation_world/runtime_demo_manifest.json",
            "derivation_mode": "limited",
            "authoritative_record": False,
            "output_policy": {"world_model_output_policy": "grounding_first"},
        },
        "qualification_references": {
            "qualified_opportunity_handoff_uri": "gs://bucket/evaluation_prep/qualified_opportunity_handoff.json",
        },
        "world_model_policy": {"world_model_output_policy": "grounding_first"},
        "provenance": {
            "grounding_level": "observed",
            "confidence": 0.95,
            "evidence_sources": ["gs://bucket/scene_memory/scene_memory_manifest.json"] if include_evidence else [],
            "observation_coverage": {"runtime_launchable": launchable},
            "canonical_truth": True,
            "presentation_only": False,
        },
        "generated_at": "2026-03-13T12:00:00Z",
    }
    _write_json(root / "protected.json", {"schema_version": "v1", "grounding_status": grounding_status, "region_count": 0, "regions": []})
    _write_json(root / "render.json", {"schema_version": "v1", "compositing_mode": "runtime_layer_grounded"})
    _write_json(root / "variance.json", {"schema_version": "v1", "allowed_variable_inputs": ["trajectory"]})
    return spec


def test_load_site_world_bundle_with_spec(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "launchable": True,
        },
    )
    _write_json(
        root / "site_world_spec.json",
        {
            "schema_version": "v1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
            "canonical_package_version": "pkg-v1",
            "task_catalog": [{"id": "task-1"}],
            "scenario_catalog": [{"id": "scenario-1"}],
            "start_state_catalog": [{"id": "start-1"}],
            "robot_profiles": [{"id": "robot-1"}],
        },
    )
    bundle = load_site_world_bundle(registration_path, require_spec=True)
    assert bundle.resolved["canonical_package_version"] == "pkg-v1"
    assert bundle.grounding["task_catalog_count"] == 1


def test_load_registration_only_when_spec_not_required(tmp_path: Path) -> None:
    registration_path = _write_registration(tmp_path / "bundle")
    bundle = load_site_world_bundle(registration_path, require_spec=False)
    assert bundle.spec == {}
    assert bundle.grounding["missing_required"] == []


def test_reject_missing_registration() -> None:
    missing = Path("/tmp/does-not-exist/site_world_registration.json")
    with pytest.raises(SiteWorldIntakeError, match="registration not found"):
        load_site_world_bundle(missing, require_spec=False)


def test_reject_missing_required_spec(tmp_path: Path) -> None:
    registration_path = _write_registration(tmp_path / "bundle")
    with pytest.raises(SiteWorldIntakeError, match="adjacent site-world spec not found"):
        load_site_world_bundle(registration_path, require_spec=True)


def test_reject_registration_missing_identity_fields(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = root / "site_world_registration.json"
    _write_json(
        registration_path,
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "scene_id": "scene-1",
        },
    )
    with pytest.raises(SiteWorldIntakeError, match="capture_id"):
        load_site_world_bundle(registration_path)


def test_reject_mismatched_spec_identity(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_spec.json",
        {
            "schema_version": "v1",
            "scene_id": "scene-2",
            "capture_id": "capture-1",
            "canonical_package_version": "pkg-v1",
        },
    )
    with pytest.raises(SiteWorldIntakeError, match="scene_id"):
        load_site_world_bundle(registration_path, require_spec=True)


def test_reject_health_mismatched_site_world_id(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-other",
        },
    )
    with pytest.raises(SiteWorldIntakeError, match="site_world_id does not match registration"):
        load_site_world_bundle(registration_path)


def test_grounding_summary_reports_missing_local_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_spec.json",
        {
            "schema_version": "v1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
            "canonical_package_version": "pkg-v1",
            "conditioning": {
                "keyframe_uri": "gs://bucket/frame.png",
                "local_paths": {
                    "arkit_poses_path": str(root / "missing-poses.json"),
                },
            },
            "geometry": {
                "object_geometry_manifest_path": str(root / "missing-geometry.json"),
            },
            "qualification_references": {"handoff": "present"},
        },
    )
    bundle = load_site_world_bundle(registration_path, require_spec=True)
    assert bundle.grounding["missing_required"] == ["visual_source", "arkit_poses", "arkit_intrinsics"]
    assert "object_geometry" in bundle.grounding["missing_optional"]
    assert bundle.grounding["checks"]["qualification_refs"] is True


def test_normalize_trajectory_payload_variants() -> None:
    assert normalize_trajectory_payload("arc") == {"trajectory": "arc"}
    assert normalize_trajectory_payload(None) == {"trajectory": DEFAULT_TRAJECTORY}
    assert normalize_trajectory_payload("") == {"trajectory": DEFAULT_TRAJECTORY}
    assert normalize_trajectory_payload({"speed": "slow"}) == {
        "speed": "slow",
        "trajectory": DEFAULT_TRAJECTORY,
    }


def test_public_constants_are_explicit() -> None:
    assert SITE_WORLD_SCHEMA_VERSION == "v1"
    assert DEFAULT_TRAJECTORY == "static"


def test_validate_site_world_bundle_launchable_canonical_bundle(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "launchable": True,
            "grounding_status": "grounded",
            "canonical_package_version": "pkg-v1",
            "authoritative_record": True,
        },
    )
    _write_json(root / "site_world_spec.json", _production_spec(root, launchable=True, readiness_state="launchable"))

    bundle = load_site_world_bundle(registration_path, require_spec=True)
    assert validate_site_world_bundle(bundle, production_mode=True) == []
    assert bundle.resolved["runtime_eligibility"]["readiness_state"] == "launchable"
    assert bundle.resolved["canonical_output"]["authoritative_record"] is True
    assert bundle.resolved["presentation_output"]["authoritative_record"] is False
    assert bundle.resolved["provenance"]["canonical_truth"] is True


def test_validate_site_world_bundle_blocked_canonical_bundle(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "launchable": False,
            "grounding_status": "grounded",
            "canonical_package_version": "pkg-v1",
            "authoritative_record": True,
            "blockers": ["qualification_state:risky"],
        },
    )
    _write_json(
        root / "site_world_spec.json",
        _production_spec(
            root,
            launchable=False,
            readiness_state="blocked",
            blockers=["qualification_state:risky"],
        ),
    )

    bundle = load_site_world_bundle(registration_path, require_spec=True)
    assert validate_site_world_bundle(bundle, production_mode=True) == []


def test_validate_site_world_bundle_incomplete_canonical_bundle(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "launchable": False,
            "grounding_status": "grounded",
            "canonical_package_version": "pkg-v1",
            "authoritative_record": True,
        },
    )
    _write_json(
        root / "site_world_spec.json",
        _production_spec(
            root,
            launchable=False,
            readiness_state="incomplete",
            blockers=[],
        ),
    )

    bundle = load_site_world_bundle(registration_path, require_spec=True)
    assert validate_site_world_bundle(bundle, production_mode=True) == []


def test_validate_site_world_bundle_rejects_canonical_truth_without_evidence(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    registration_path = _write_registration(root)
    _write_json(
        root / "site_world_health.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "launchable": True,
            "grounding_status": "grounded",
            "canonical_package_version": "pkg-v1",
            "authoritative_record": True,
        },
    )
    _write_json(
        root / "site_world_spec.json",
        _production_spec(
            root,
            launchable=True,
            readiness_state="launchable",
            include_evidence=False,
        ),
    )

    bundle = load_site_world_bundle(registration_path, require_spec=True)
    errors = validate_site_world_bundle(bundle, production_mode=True)
    assert "provenance:canonical_truth_requires_evidence_sources" in errors
