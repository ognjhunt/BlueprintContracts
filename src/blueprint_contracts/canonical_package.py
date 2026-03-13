"""Canonical package version helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


def normalized_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _optional_path(*values: Any) -> Optional[Path]:
    for value in values:
        text = str(value or "").strip()
        if text:
            return Path(text).resolve()
    return None


def compute_canonical_package_version(
    *,
    scene_memory_manifest: Mapping[str, Any],
    conditioning_bundle: Mapping[str, Any],
    object_geometry_manifest: Mapping[str, Any],
    task_anchor_manifest: Mapping[str, Any],
    site_world_spec: Mapping[str, Any],
    protected_regions_manifest: Mapping[str, Any],
    canonical_render_policy: Mapping[str, Any],
    presentation_variance_policy: Mapping[str, Any],
) -> str:
    normalized_spec = dict(site_world_spec)
    normalized_spec.pop("canonical_package_version", None)
    digest = hashlib.sha256()
    for payload in (
        scene_memory_manifest,
        conditioning_bundle,
        object_geometry_manifest,
        task_anchor_manifest,
        normalized_spec,
        protected_regions_manifest,
        canonical_render_policy,
        presentation_variance_policy,
    ):
        digest.update(normalized_json_bytes(payload))
    return digest.hexdigest()


def verify_canonical_package_version(
    *,
    spec: Mapping[str, Any],
    protected_regions_manifest: Mapping[str, Any],
    canonical_render_policy: Mapping[str, Any],
    presentation_variance_policy: Mapping[str, Any],
) -> Optional[str]:
    conditioning = dict(spec.get("conditioning") or {}) if isinstance(spec.get("conditioning"), Mapping) else {}
    geometry = dict(spec.get("geometry") or {}) if isinstance(spec.get("geometry"), Mapping) else {}
    local_paths = dict(conditioning.get("local_paths") or {}) if isinstance(conditioning.get("local_paths"), Mapping) else {}

    scene_memory_manifest_path = _optional_path(
        conditioning.get("scene_memory_manifest_path"),
        local_paths.get("scene_memory_manifest_path"),
    )
    conditioning_bundle_path = _optional_path(
        conditioning.get("conditioning_bundle_path"),
        local_paths.get("conditioning_bundle_path"),
    )
    object_geometry_manifest_path = _optional_path(geometry.get("object_geometry_manifest_path"))
    task_anchor_manifest_path = _optional_path(spec.get("task_anchor_manifest_path"))
    if not all(
        path is not None and path.is_file()
        for path in (
            scene_memory_manifest_path,
            conditioning_bundle_path,
            object_geometry_manifest_path,
            task_anchor_manifest_path,
        )
    ):
        return "canonical_package_verification_inputs_missing"
    observed = compute_canonical_package_version(
        scene_memory_manifest=_read_json(scene_memory_manifest_path),
        conditioning_bundle=_read_json(conditioning_bundle_path),
        object_geometry_manifest=_read_json(object_geometry_manifest_path),
        task_anchor_manifest=_read_json(task_anchor_manifest_path),
        site_world_spec=spec,
        protected_regions_manifest=protected_regions_manifest,
        canonical_render_policy=canonical_render_policy,
        presentation_variance_policy=presentation_variance_policy,
    )
    expected = str(spec.get("canonical_package_version") or "").strip()
    if expected and observed != expected:
        return f"canonical_package_version_mismatch:{observed}"
    return None
