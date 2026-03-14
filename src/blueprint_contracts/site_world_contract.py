"""Contract helpers for site-world handoff artifacts.

Registration is the authoritative identity document. Health is optional. The
adjacent spec is optional unless ``require_spec=True``. When present, health and
spec must agree with the registration identity and schema version.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .canonical_package import validate_canonical_package_contract
from .runtime_layer_contract import (
    ALLOWED_GROUNDING_STATUSES,
    validate_grounding_provenance,
    validate_output_linkage,
    validate_runtime_eligibility,
)


SITE_WORLD_SCHEMA_VERSION = "v1"
DEFAULT_TRAJECTORY = "static"

_GROUNDING_EMPTY_SUMMARY = {
    "checks": {},
    "missing_required": [],
    "missing_optional": [],
    "qualification_state": "",
    "downstream_evaluation_eligibility": None,
    "task_catalog_count": 0,
    "scenario_catalog_count": 0,
    "start_state_catalog_count": 0,
    "robot_profile_count": 0,
}


class SiteWorldIntakeError(RuntimeError):
    """Raised when site-world handoff artifacts are incomplete or invalid."""


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _optional_path(value: Any) -> Optional[Path]:
    text = str(value or "").strip()
    if not text or text.startswith(("gs://", "http://", "https://")):
        return None
    return Path(text).resolve()


def _require_text(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise SiteWorldIntakeError(f"{label} missing '{key}'")
    return value


def _validate_registration_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    registration = dict(payload)
    schema_version = _require_text(registration, "schema_version", label="site_world_registration")
    if schema_version != SITE_WORLD_SCHEMA_VERSION:
        raise SiteWorldIntakeError(
            f"site_world_registration unsupported schema_version '{schema_version}'"
        )
    for key in ("site_world_id", "scene_id", "capture_id"):
        _require_text(registration, key, label="site_world_registration")
    return registration


def _validate_health_payload(
    health: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
) -> Dict[str, Any]:
    payload = dict(health)
    schema_version = _require_text(payload, "schema_version", label="site_world_health")
    if schema_version != SITE_WORLD_SCHEMA_VERSION:
        raise SiteWorldIntakeError(f"site_world_health unsupported schema_version '{schema_version}'")
    site_world_id = _require_text(payload, "site_world_id", label="site_world_health")
    registration_id = str(registration.get("site_world_id") or "").strip()
    if site_world_id != registration_id:
        raise SiteWorldIntakeError("site_world_health site_world_id does not match registration")
    return payload


def _validate_spec_payload(
    spec: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
) -> Dict[str, Any]:
    payload = dict(spec)
    schema_version = _require_text(payload, "schema_version", label="site_world_spec")
    if schema_version != SITE_WORLD_SCHEMA_VERSION:
        raise SiteWorldIntakeError(f"site_world_spec unsupported schema_version '{schema_version}'")
    for key in ("scene_id", "capture_id", "canonical_package_version"):
        _require_text(payload, key, label="site_world_spec")
    if str(payload.get("scene_id") or "").strip() != str(registration.get("scene_id") or "").strip():
        raise SiteWorldIntakeError("site_world_spec scene_id does not match registration")
    if str(payload.get("capture_id") or "").strip() != str(registration.get("capture_id") or "").strip():
        raise SiteWorldIntakeError("site_world_spec capture_id does not match registration")
    return payload


def adjacent_site_world_paths(registration_path: Path) -> tuple[Path, Path]:
    """Return the conventional adjacent health/spec paths for a registration file."""
    root = registration_path.parent
    return root / "site_world_health.json", root / "site_world_spec.json"


def normalize_trajectory_payload(trajectory: Mapping[str, Any] | str | None) -> Dict[str, Any]:
    """Normalize trajectory settings to a deterministic mapping payload."""
    if isinstance(trajectory, Mapping):
        payload = dict(trajectory)
        if "trajectory" not in payload:
            payload["trajectory"] = DEFAULT_TRAJECTORY
        return payload
    token = str(trajectory or "").strip()
    return {"trajectory": token or DEFAULT_TRAJECTORY}


def merge_site_world_definition(
    *,
    registration: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> Dict[str, Any]:
    """Merge spec-only fields onto the authoritative registration payload."""
    merged = copy.deepcopy(dict(registration))
    if not spec:
        return merged
    for key in (
        "canonical_package_uri",
        "canonical_package_version",
        "task_catalog",
        "scenario_catalog",
        "start_state_catalog",
        "robot_profiles",
        "qualification_state",
        "downstream_evaluation_eligibility",
        "grounding_status",
        "ungrounded_reason",
        "capture_source",
        "conditioning",
        "geometry",
        "runtime_layer_policy",
        "runtime_eligibility",
        "task_anchor_manifest_path",
        "qualification_references",
        "canonical_output",
        "presentation_output",
        "world_model_policy",
        "provenance",
        "generated_at",
        "empty_index_cause",
    ):
        if key in spec:
            merged[key] = copy.deepcopy(spec[key])
    return merged


def grounding_summary(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """Summarize which local grounding artifacts are actually present on disk."""
    conditioning = (
        dict(spec.get("conditioning") or {})
        if isinstance(spec.get("conditioning"), Mapping)
        else {}
    )
    local_paths = (
        dict(conditioning.get("local_paths") or {})
        if isinstance(conditioning.get("local_paths"), Mapping)
        else {}
    )
    geometry = dict(spec.get("geometry") or {}) if isinstance(spec.get("geometry"), Mapping) else {}
    qualification_references = (
        dict(spec.get("qualification_references") or {})
        if isinstance(spec.get("qualification_references"), Mapping)
        else {}
    )
    visuals = [
        _optional_path(local_paths.get("keyframe_path")),
        _optional_path(local_paths.get("raw_video_path")),
        _optional_path(conditioning.get("keyframe_uri")),
        _optional_path(conditioning.get("raw_video_uri")),
    ]
    arkit_poses = _optional_path(local_paths.get("arkit_poses_path")) or _optional_path(
        conditioning.get("arkit_poses_uri")
    )
    arkit_intrinsics = _optional_path(local_paths.get("arkit_intrinsics_path")) or _optional_path(
        conditioning.get("arkit_intrinsics_uri")
    )
    depth_path = _optional_path(local_paths.get("depth_path")) or _optional_path(
        conditioning.get("depth_uri")
    )
    occupancy_path = _optional_path(local_paths.get("occupancy_path")) or _optional_path(
        geometry.get("occupancy_path")
    )
    collision_path = _optional_path(local_paths.get("collision_path")) or _optional_path(
        geometry.get("collision_path")
    )
    object_index_path = _optional_path(local_paths.get("object_index_path")) or _optional_path(
        geometry.get("object_index_path")
    )
    object_geometry_path = _optional_path(
        local_paths.get("object_geometry_manifest_path")
    ) or _optional_path(geometry.get("object_geometry_manifest_path"))
    checks = {
        "visual_source": any(path is not None and path.exists() for path in visuals),
        "arkit_poses": bool(arkit_poses and arkit_poses.exists()),
        "arkit_intrinsics": bool(arkit_intrinsics and arkit_intrinsics.exists()),
        "depth": bool(depth_path and depth_path.exists()),
        "occupancy": bool(occupancy_path and occupancy_path.exists()),
        "collision": bool(collision_path and collision_path.exists()),
        "object_index": bool(object_index_path and object_index_path.exists()),
        "object_geometry": bool(object_geometry_path and object_geometry_path.exists()),
        "qualification_refs": bool(qualification_references),
    }
    missing_required = [key for key in ("visual_source", "arkit_poses", "arkit_intrinsics") if not checks[key]]
    missing_optional = [
        key for key in ("depth", "occupancy", "collision", "object_index", "object_geometry") if not checks[key]
    ]
    return {
        "checks": checks,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "qualification_state": str(spec.get("qualification_state") or ""),
        "downstream_evaluation_eligibility": spec.get("downstream_evaluation_eligibility"),
        "task_catalog_count": len(list(spec.get("task_catalog", []) or [])),
        "scenario_catalog_count": len(list(spec.get("scenario_catalog", []) or [])),
        "start_state_catalog_count": len(list(spec.get("start_state_catalog", []) or [])),
        "robot_profile_count": len(list(spec.get("robot_profiles", []) or [])),
    }


@dataclass(frozen=True)
class SiteWorldBundle:
    """Resolved site-world bundle consisting of registration, health, and spec artifacts."""

    registration: Dict[str, Any]
    health: Dict[str, Any]
    spec: Dict[str, Any]
    resolved: Dict[str, Any]
    grounding: Dict[str, Any]
    registration_path: Path
    health_path: Path
    spec_path: Path


def _has_non_empty_field(payload: Mapping[str, Any], key: str) -> bool:
    if key not in payload:
        return False
    value = payload.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def validate_site_world_bundle(bundle: SiteWorldBundle, *, production_mode: bool = False) -> list[str]:
    """Validate a loaded site-world bundle against shared cross-repo requirements."""
    errors: list[str] = []
    registration = bundle.registration
    health = bundle.health
    spec = bundle.spec

    if not spec:
        return ["missing_site_world_spec"] if production_mode else errors

    if production_mode:
        required_spec_fields = (
            "canonical_package_uri",
            "canonical_package_version",
            "qualification_state",
            "downstream_evaluation_eligibility",
            "grounding_status",
            "runtime_layer_policy",
            "runtime_eligibility",
            "canonical_output",
            "presentation_output",
            "provenance",
        )
        for key in required_spec_fields:
            if not _has_non_empty_field(spec, key):
                errors.append(f"missing_spec_field:{key}")

    errors.extend(validate_canonical_package_contract(spec))

    runtime_eligibility = spec.get("runtime_eligibility")
    if isinstance(runtime_eligibility, Mapping):
        errors.extend(validate_runtime_eligibility(runtime_eligibility))
    elif production_mode:
        errors.append("missing_spec_field:runtime_eligibility")

    provenance = spec.get("provenance")
    if isinstance(provenance, Mapping):
        errors.extend(validate_grounding_provenance(provenance))
        if bool(provenance.get("presentation_only")):
            errors.append("provenance:presentation_only_conflicts_with_canonical_bundle")
    elif production_mode:
        errors.append("missing_spec_field:provenance")

    for field, expected_authoritative in (("canonical_output", True), ("presentation_output", False)):
        payload = spec.get(field)
        if isinstance(payload, Mapping):
            errors.extend(
                validate_output_linkage(
                    payload,
                    context=field,
                    expected_authoritative=expected_authoritative,
                )
            )
        elif production_mode:
            errors.append(f"missing_spec_field:{field}")

    if production_mode and not isinstance(health, Mapping):
        errors.append("missing_site_world_health")
    if production_mode and "launchable" not in health:
        errors.append("missing_health_field:launchable")

    shared_grounding_statuses = {
        str(spec.get("grounding_status") or "").strip().lower(),
        str(health.get("grounding_status") or "").strip().lower(),
        str(registration.get("grounding_status") or "").strip().lower(),
        str((runtime_eligibility or {}).get("grounding_status") or "").strip().lower()
        if isinstance(runtime_eligibility, Mapping)
        else "",
    }
    shared_grounding_statuses.discard("")
    if any(value not in ALLOWED_GROUNDING_STATUSES for value in shared_grounding_statuses):
        errors.append("invalid_grounding_status")
    if len(shared_grounding_statuses) > 1:
        errors.append("grounding_status_mismatch")

    versions = {
        str(payload.get("canonical_package_version") or "").strip()
        for payload in (registration, health, spec)
        if isinstance(payload, Mapping) and str(payload.get("canonical_package_version") or "").strip()
    }
    if len(versions) > 1:
        errors.append("canonical_package_version_mismatch")

    if production_mode and isinstance(runtime_eligibility, Mapping):
        health_launchable = health.get("launchable")
        if not isinstance(health_launchable, bool):
            errors.append("invalid_health_field:launchable")
        elif health_launchable != bool(runtime_eligibility.get("launchable")):
            errors.append("health_launchable_mismatch")

    effective_grounding_status = str(spec.get("grounding_status") or "").strip().lower()
    if effective_grounding_status == "ungrounded":
        reason = (
            str(spec.get("ungrounded_reason") or "").strip()
            or str(health.get("ungrounded_reason") or "").strip()
            or str(registration.get("ungrounded_reason") or "").strip()
            or str((runtime_eligibility or {}).get("ungrounded_reason") or "").strip()
            if isinstance(runtime_eligibility, Mapping)
            else ""
        )
        if not reason:
            errors.append("ungrounded_reason_missing")

    for label, payload in (("registration", registration), ("health", health)):
        if isinstance(payload, Mapping) and payload.get("presentation_only") is True:
            errors.append(f"{label}:presentation_only_conflicts_with_canonical_bundle")
        if isinstance(payload, Mapping) and "authoritative_record" in payload and payload.get("authoritative_record") is False:
            errors.append(f"{label}:authoritative_record_expected_true")

    return errors


def load_site_world_bundle(registration_path: Path, *, require_spec: bool = False) -> SiteWorldBundle:
    """Load and validate a site-world registration and its adjacent artifacts."""
    registration_path = registration_path.resolve()
    if not registration_path.is_file():
        raise SiteWorldIntakeError(f"site-world registration not found: {registration_path}")
    registration = _validate_registration_payload(_read_json(registration_path))
    health_path, spec_path = adjacent_site_world_paths(registration_path)
    health = _validate_health_payload(_read_json(health_path), registration=registration) if health_path.is_file() else {}
    if require_spec and not spec_path.is_file():
        raise SiteWorldIntakeError(f"adjacent site-world spec not found: {spec_path}")
    spec = _validate_spec_payload(_read_json(spec_path), registration=registration) if spec_path.is_file() else {}
    resolved = merge_site_world_definition(registration=registration, spec=spec)
    return SiteWorldBundle(
        registration=registration,
        health=health,
        spec=spec,
        resolved=resolved,
        grounding=grounding_summary(spec) if spec else dict(_GROUNDING_EMPTY_SUMMARY),
        registration_path=registration_path,
        health_path=health_path,
        spec_path=spec_path,
    )


__all__ = [
    "DEFAULT_TRAJECTORY",
    "SITE_WORLD_SCHEMA_VERSION",
    "SiteWorldBundle",
    "SiteWorldIntakeError",
    "adjacent_site_world_paths",
    "grounding_summary",
    "load_site_world_bundle",
    "merge_site_world_definition",
    "normalize_trajectory_payload",
    "validate_site_world_bundle",
]
