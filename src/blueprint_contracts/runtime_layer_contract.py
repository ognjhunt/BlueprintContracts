"""Portable runtime-layer policy contracts shared across Blueprint repos.

The constants in this module are shared policy, not local implementation detail.
They define how Pipeline and Validation classify grounding confidence and how the
runtime-layer handoff should be interpreted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


# Observed geometry above this confidence is treated as locked shared truth.
PROTECTED_OBSERVED_THRESHOLD = 0.85
# Reconstructed geometry above this confidence is treated as locked shared truth.
PROTECTED_RECONSTRUCTED_THRESHOLD = 0.80
# Below this confidence, regions are editable regardless of grounding level.
EDITABLE_LOW_CONFIDENCE_THRESHOLD = 0.65
# Task-critical objects become locked once they reach this confidence.
TASK_CRITICAL_OVERRIDE_THRESHOLD = 0.70
# Locked task-critical regions are dilated by this many pixels in render policy.
TASK_CRITICAL_DILATION_PX = 3
# Presentation quality is marked degraded above this editable ratio.
DEGRADED_EDITABLE_RATIO_THRESHOLD = 0.40
# Locked-region violation retry budget shared by both repos.
LOCK_VIOLATION_RETRY_BUDGET = 1


def _safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def grounding_fields_from_provenance(provenance: Mapping[str, Any] | None) -> Dict[str, Any]:
    """Normalize provenance into the shared grounding fields expected by consumers."""
    provenance = dict(provenance or {})
    return {
        "grounding_level": str(provenance.get("grounding_level") or "").strip() or "generated",
        "confidence": _safe_float(provenance.get("confidence")),
        "evidence_sources": [
            str(item).strip()
            for item in provenance.get("evidence_sources", [])
            if str(item).strip()
        ]
        if isinstance(provenance.get("evidence_sources"), list)
        else [],
        "observation_coverage": (
            dict(provenance.get("observation_coverage") or {})
            if isinstance(provenance.get("observation_coverage"), Mapping)
            else {}
        ),
        "canonical_truth": bool(provenance.get("canonical_truth")),
        "presentation_only": bool(provenance.get("presentation_only")),
    }


def with_grounding_fields(
    payload: Mapping[str, Any],
    *,
    provenance: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a copy of ``payload`` with normalized shared grounding fields applied."""
    result = dict(payload)
    if provenance is None and isinstance(result.get("provenance"), Mapping):
        provenance = dict(result.get("provenance") or {})
    result.update(grounding_fields_from_provenance(provenance))
    if isinstance(extra, Mapping):
        result.update(dict(extra))
    return result


def task_critical_object_ids(task_entries: Sequence[Mapping[str, Any]]) -> set[str]:
    """Collect the shared set of task-critical object ids from task-anchor entries."""
    critical: set[str] = set()
    for task in task_entries:
        if not isinstance(task, Mapping):
            continue
        for key in ("target_object_ids", "articulation_required_ids"):
            values = task.get(key)
            if not isinstance(values, list):
                continue
            for item in values:
                text = str(item or "").strip()
                if text:
                    critical.add(text)
    return critical


def classify_region(
    *,
    grounding_level: Any,
    confidence: Any,
    task_critical: bool = False,
    provenance_present: bool = True,
) -> str:
    """Classify a region as ``locked``, ``uncertain``, or ``editable``."""
    if not provenance_present:
        return "editable"

    level = str(grounding_level or "").strip().lower()
    score = _safe_float(confidence)
    if not level or score is None:
        return "editable"
    if score < EDITABLE_LOW_CONFIDENCE_THRESHOLD:
        return "editable"
    if task_critical and score >= TASK_CRITICAL_OVERRIDE_THRESHOLD:
        return "locked"
    if level == "observed":
        return "locked" if score >= PROTECTED_OBSERVED_THRESHOLD else "editable"
    if level == "reconstructed":
        if score >= PROTECTED_RECONSTRUCTED_THRESHOLD:
            return "locked"
        if score >= EDITABLE_LOW_CONFIDENCE_THRESHOLD:
            return "uncertain"
        return "editable"
    if level in {"inferred", "generated"}:
        return "editable"
    return "editable"


def build_protected_regions_manifest(
    *,
    scene_id: str,
    capture_id: str,
    object_geometry_manifest: Mapping[str, Any],
    task_anchor_manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build the shared protected-regions manifest consumed across repos."""
    tasks = (
        task_anchor_manifest.get("tasks")
        if isinstance(task_anchor_manifest.get("tasks"), list)
        else []
    )
    critical_ids = task_critical_object_ids([task for task in tasks if isinstance(task, Mapping)])
    objects = (
        object_geometry_manifest.get("objects")
        if isinstance(object_geometry_manifest.get("objects"), list)
        else []
    )
    object_geometry_status = str(object_geometry_manifest.get("status") or "").strip().lower()
    empty_index_cause = str(object_geometry_manifest.get("empty_index_cause") or "").strip() or None
    regions = []
    for item in objects:
        if not isinstance(item, Mapping):
            continue
        object_id = str(item.get("object_id") or "").strip()
        provenance = item.get("provenance") if isinstance(item.get("provenance"), Mapping) else {}
        fields = grounding_fields_from_provenance(provenance)
        task_critical = bool(item.get("task_critical")) or object_id in critical_ids
        classification = classify_region(
            grounding_level=fields["grounding_level"],
            confidence=fields["confidence"],
            task_critical=task_critical,
            provenance_present=bool(provenance),
        )
        regions.append(
            {
                "region_id": f"object:{object_id or 'unknown'}",
                "region_type": "object",
                "object_id": object_id or None,
                "label": str(item.get("label") or "").strip() or None,
                "classification": classification,
                "task_critical": task_critical,
                "confidence_thresholds": {
                    "protected_observed": PROTECTED_OBSERVED_THRESHOLD,
                    "protected_reconstructed": PROTECTED_RECONSTRUCTED_THRESHOLD,
                    "editable_low_confidence": EDITABLE_LOW_CONFIDENCE_THRESHOLD,
                    "task_critical_override": TASK_CRITICAL_OVERRIDE_THRESHOLD,
                },
                "geometry_refs": {
                    "placement_bbox": dict(item.get("placement_bbox") or {})
                    if isinstance(item.get("placement_bbox"), Mapping)
                    else {},
                    "mesh_glb_path": str(item.get("mesh_glb_path") or "").strip() or None,
                    "collision_hulls": [
                        str(hull.get("path") or "").strip()
                        for hull in item.get("collision_hulls", [])
                        if isinstance(hull, Mapping) and str(hull.get("path") or "").strip()
                    ],
                },
                "mask_refs": [
                    {
                        "view_id": str(mask.get("view_id") or "").strip(),
                        "mask_path": str(mask.get("mask_path") or "").strip(),
                        "image_path": str(mask.get("image_path") or "").strip(),
                    }
                    for mask in item.get("visual_replacement_masks", [])
                    if isinstance(mask, Mapping) and str(mask.get("mask_path") or "").strip()
                ],
                "coverage_refs": {
                    "selected_views": [
                        {
                            "view_id": str(view.get("view_id") or "").strip(),
                            "image_path": str(view.get("image_path") or "").strip(),
                            "mask_path": str(view.get("mask_path") or "").strip(),
                            "source_mode": str(view.get("source_mode") or "").strip(),
                        }
                        for view in item.get("selected_views", [])
                        if isinstance(view, Mapping)
                    ],
                },
                **fields,
            }
        )
    grounding_status = "grounded"
    ungrounded_reason: Optional[str] = None
    if object_geometry_status in {"empty_object_index", "missing_object_index"}:
        grounding_status = "ungrounded"
        ungrounded_reason = object_geometry_status
    elif not regions:
        grounding_status = "ungrounded"
        ungrounded_reason = "no_grounded_regions"
    return {
        "schema_version": "v1",
        "scene_id": scene_id,
        "capture_id": capture_id,
        "grounding_status": grounding_status,
        "ungrounded_reason": ungrounded_reason,
        "empty_index_cause": empty_index_cause,
        "region_count": len(regions),
        "thresholds": {
            "protected_observed": PROTECTED_OBSERVED_THRESHOLD,
            "protected_reconstructed": PROTECTED_RECONSTRUCTED_THRESHOLD,
            "editable_low_confidence": EDITABLE_LOW_CONFIDENCE_THRESHOLD,
            "task_critical_override": TASK_CRITICAL_OVERRIDE_THRESHOLD,
            "task_critical_dilation_px": TASK_CRITICAL_DILATION_PX,
            "unknown_is_editable": True,
            "ungrounded_default_mode": "canonical_only",
            "unsafe_editable_override_flag": "unsafe_allow_blocked_site_world",
        },
        "regions": regions,
    }


def build_canonical_render_policy() -> Dict[str, Any]:
    """Build the shared canonical render policy contract."""
    return {
        "schema_version": "v1",
        "compositing_mode": "runtime_layer_grounded",
        "lock_rules": {
            "hard_rule": "presentation runtime must never modify locked regions",
            "unknown_is_editable": True,
            "task_critical_dilation_px": TASK_CRITICAL_DILATION_PX,
        },
        "uncertain_region_policy": {
            "mode": "canonical_preferred",
            "edit_allowed_only_when": "geometry_consistent_with_canonical_depth_or_silhouette",
        },
        "fallback_behavior": {
            "on_locked_region_violation": "canonical_only",
            "retry_budget": LOCK_VIOLATION_RETRY_BUDGET,
            "rejection_mode": "retry_then_fallback",
        },
        "presentation_quality": {
            "degraded_when_editable_ratio_gt": DEGRADED_EDITABLE_RATIO_THRESHOLD,
            "degraded_label": "editable_ratio_gt_0.40",
        },
    }


def build_presentation_variance_policy() -> Dict[str, Any]:
    """Build the shared presentation variance policy contract."""
    return {
        "schema_version": "v1",
        "allowed_variable_inputs": [
            "trajectory",
            "camera_path",
            "prompt",
            "presentation_model",
            "style_settings",
        ],
        "allowed_editable_region_classes": [
            "inferred",
            "generated",
            "missing_geometry",
            "low_confidence_reprojection_failure",
            "uncaptured_backsides",
            "uncaptured_interiors",
            "low_confidence_hole_fill",
        ],
        "forbidden_changes": [
            "protected_object_placement",
            "protected_object_identity",
            "protected_object_articulation_state",
            "task_anchor_relocation",
        ],
    }


def _presentation_policy_paths(spec: Mapping[str, Any]) -> Dict[str, Path]:
    policy = dict(spec.get("runtime_layer_policy") or {}) if isinstance(spec.get("runtime_layer_policy"), Mapping) else {}
    out: Dict[str, Path] = {}
    for key in (
        "protected_regions_manifest_path",
        "canonical_render_policy_path",
        "presentation_variance_policy_path",
    ):
        value = str(policy.get(key) or "").strip()
        if value:
            out[key] = Path(value).resolve()
    return out


def validate_runtime_layer_spec(spec: Mapping[str, Any]) -> list[str]:
    """Validate that a site-world spec references the required runtime-layer artifacts."""
    errors: list[str] = []
    if not str(spec.get("canonical_package_version") or "").strip():
        errors.append("missing_canonical_package_version")
    policy = dict(spec.get("runtime_layer_policy") or {}) if isinstance(spec.get("runtime_layer_policy"), Mapping) else {}
    for key in (
        "protected_regions_manifest_uri",
        "canonical_render_policy_uri",
        "presentation_variance_policy_uri",
        "protected_regions_manifest_path",
        "canonical_render_policy_path",
        "presentation_variance_policy_path",
    ):
        if not str(policy.get(key) or "").strip():
            errors.append(f"missing_runtime_layer_policy:{key}")
    for path in _presentation_policy_paths(spec).values():
        if not path.is_file():
            errors.append(f"missing_runtime_layer_policy_file:{path.name}")
    return errors


def load_runtime_layer_bundle(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """Load the local runtime-layer policy bundle referenced by a site-world spec."""
    paths = _presentation_policy_paths(spec)
    return {
        "protected_regions_manifest": _read_json(paths["protected_regions_manifest_path"]),
        "canonical_render_policy": _read_json(paths["canonical_render_policy_path"]),
        "presentation_variance_policy": _read_json(paths["presentation_variance_policy_path"]),
        "paths": {key: str(value) for key, value in paths.items()},
    }


__all__ = [
    "DEGRADED_EDITABLE_RATIO_THRESHOLD",
    "EDITABLE_LOW_CONFIDENCE_THRESHOLD",
    "LOCK_VIOLATION_RETRY_BUDGET",
    "PROTECTED_OBSERVED_THRESHOLD",
    "PROTECTED_RECONSTRUCTED_THRESHOLD",
    "TASK_CRITICAL_DILATION_PX",
    "TASK_CRITICAL_OVERRIDE_THRESHOLD",
    "build_canonical_render_policy",
    "build_presentation_variance_policy",
    "build_protected_regions_manifest",
    "classify_region",
    "grounding_fields_from_provenance",
    "load_runtime_layer_bundle",
    "task_critical_object_ids",
    "validate_runtime_layer_spec",
    "with_grounding_fields",
]
