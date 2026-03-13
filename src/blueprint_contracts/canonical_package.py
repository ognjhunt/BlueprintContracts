"""Canonical package version helpers.

Hash order is stable and intentional:

1. scene memory manifest
2. conditioning bundle
3. object geometry manifest
4. task anchor manifest
5. site-world spec without ``canonical_package_version``
6. protected regions manifest
7. canonical render policy
8. presentation variance policy

The ``canonical_package_version`` field is excluded from the hashed spec copy so
the version does not become self-referential.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


CANONICAL_PACKAGE_HASH_INPUTS = (
    "scene_memory_manifest",
    "conditioning_bundle",
    "object_geometry_manifest",
    "task_anchor_manifest",
    "site_world_spec_without_canonical_package_version",
    "protected_regions_manifest",
    "canonical_render_policy",
    "presentation_variance_policy",
)


def normalized_json_bytes(payload: Any) -> bytes:
    """Serialize JSON-compatible payloads into stable canonical bytes."""
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
    """Compute the stable canonical package version hash."""
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
    """Verify a spec's canonical package version against local referenced inputs."""
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


__all__ = [
    "CANONICAL_PACKAGE_HASH_INPUTS",
    "compute_canonical_package_version",
    "normalized_json_bytes",
    "verify_canonical_package_version",
]
