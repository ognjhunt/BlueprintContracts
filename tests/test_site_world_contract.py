from __future__ import annotations

import json
from pathlib import Path

import pytest

from blueprint_contracts.site_world_contract import (
    SiteWorldIntakeError,
    load_site_world_bundle,
    normalize_trajectory_payload,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_load_site_world_bundle(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_json(
        root / "site_world_registration.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
        },
    )
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
    bundle = load_site_world_bundle(root / "site_world_registration.json", require_spec=True)
    assert bundle.resolved["canonical_package_version"] == "pkg-v1"
    assert bundle.grounding["task_catalog_count"] == 1


def test_reject_mismatched_spec_identity(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    _write_json(
        root / "site_world_registration.json",
        {
            "schema_version": "v1",
            "site_world_id": "siteworld-1",
            "scene_id": "scene-1",
            "capture_id": "capture-1",
        },
    )
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
        load_site_world_bundle(root / "site_world_registration.json", require_spec=True)


def test_normalize_trajectory_payload() -> None:
    assert normalize_trajectory_payload("arc") == {"trajectory": "arc"}
