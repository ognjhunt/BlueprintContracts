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

ALLOWED_GROUNDING_LEVELS = frozenset({"observed", "reconstructed", "inferred", "generated"})
ALLOWED_GROUNDING_STATUSES = frozenset({"grounded", "ungrounded"})
ALLOWED_RUNTIME_READINESS_STATES = frozenset({"launchable", "blocked", "incomplete"})


def _safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _read_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _prefix_errors(prefix: str, errors: Sequence[str]) -> list[str]:
    return [f"{prefix}:{error}" for error in errors]


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


def validate_grounding_provenance(
    provenance: Mapping[str, Any] | None,
    *,
    context: str = "provenance",
) -> list[str]:
    """Validate shared provenance semantics used by canonical and presentation artifacts."""
    if not isinstance(provenance, Mapping):
        return [f"{context}:missing_mapping"]

    fields = grounding_fields_from_provenance(provenance)
    errors: list[str] = []
    grounding_level = str(fields.get("grounding_level") or "").strip().lower()
    evidence_sources = _string_list(fields.get("evidence_sources"))
    canonical_truth = bool(fields.get("canonical_truth"))
    presentation_only = bool(fields.get("presentation_only"))

    if grounding_level not in ALLOWED_GROUNDING_LEVELS:
        allowed = ",".join(sorted(ALLOWED_GROUNDING_LEVELS))
        errors.append(f"{context}:invalid_grounding_level:{grounding_level or 'missing'}:{allowed}")
    if canonical_truth and not grounding_level:
        errors.append(f"{context}:canonical_truth_requires_grounding_level")
    if canonical_truth and not evidence_sources:
        errors.append(f"{context}:canonical_truth_requires_evidence_sources")
    if presentation_only and canonical_truth:
        errors.append(f"{context}:presentation_only_conflicts_with_canonical_truth")
    if grounding_level in {"observed", "reconstructed"} and not evidence_sources:
        errors.append(f"{context}:evidence_sources_required_for_{grounding_level}")
    return errors


def validate_output_linkage(
    payload: Mapping[str, Any] | None,
    *,
    context: str = "output",
    expected_authoritative: Optional[bool] = None,
) -> list[str]:
    """Validate canonical/presentation linkage fields shared across artifacts."""
    if not isinstance(payload, Mapping):
        return [f"{context}:missing_mapping"]

    errors: list[str] = []
    canonical_artifact_uri = str(payload.get("canonical_artifact_uri") or "").strip()
    if not canonical_artifact_uri:
        errors.append(f"{context}:missing_canonical_artifact_uri")
    if "authoritative_record" not in payload or not isinstance(payload.get("authoritative_record"), bool):
        errors.append(f"{context}:missing_authoritative_record")
    else:
        authoritative_record = bool(payload.get("authoritative_record"))
        if expected_authoritative is True and not authoritative_record:
            errors.append(f"{context}:authoritative_record_expected_true")
        if expected_authoritative is False and authoritative_record:
            errors.append(f"{context}:authoritative_record_expected_false")
    derivation_mode = str(payload.get("derivation_mode") or "").strip()
    if not derivation_mode:
        errors.append(f"{context}:missing_derivation_mode")
    if "output_policy" in payload and payload.get("output_policy") is not None and not isinstance(
        payload.get("output_policy"), Mapping
    ):
        errors.append(f"{context}:invalid_output_policy")
    return errors


def validate_runtime_eligibility(
    payload: Mapping[str, Any] | None,
    *,
    context: str = "runtime_eligibility",
) -> list[str]:
    """Validate the machine-readable launchability contract."""
    if not isinstance(payload, Mapping):
        return [f"{context}:missing_mapping"]

    errors: list[str] = []
    launchable = payload.get("launchable")
    readiness_state = str(payload.get("readiness_state") or "").strip().lower()
    blockers = payload.get("blockers")
    warnings = payload.get("warnings")
    grounding_status = str(payload.get("grounding_status") or "").strip().lower()

    if not isinstance(launchable, bool):
        errors.append(f"{context}:missing_launchable")
    if readiness_state not in ALLOWED_RUNTIME_READINESS_STATES:
        allowed = ",".join(sorted(ALLOWED_RUNTIME_READINESS_STATES))
        errors.append(f"{context}:invalid_readiness_state:{readiness_state or 'missing'}:{allowed}")
    if not isinstance(blockers, list):
        errors.append(f"{context}:missing_blockers")
        blockers_list: list[str] = []
    else:
        blockers_list = _string_list(blockers)
    if not isinstance(warnings, list):
        errors.append(f"{context}:missing_warnings")
    if grounding_status not in ALLOWED_GROUNDING_STATUSES:
        allowed = ",".join(sorted(ALLOWED_GROUNDING_STATUSES))
        errors.append(f"{context}:invalid_grounding_status:{grounding_status or 'missing'}:{allowed}")

    if isinstance(launchable, bool):
        if launchable:
            if readiness_state != "launchable":
                errors.append(f"{context}:launchable_requires_launchable_state")
            if blockers_list:
                errors.append(f"{context}:launchable_requires_no_blockers")
        elif blockers_list:
            if readiness_state != "blocked":
                errors.append(f"{context}:blocked_runtime_requires_blocked_state")
        elif readiness_state != "incomplete":
            errors.append(f"{context}:incomplete_runtime_requires_incomplete_state")

    if grounding_status == "ungrounded":
        if not str(payload.get("ungrounded_reason") or "").strip():
            errors.append(f"{context}:ungrounded_requires_reason")
        if payload.get("launchable") is True:
            errors.append(f"{context}:ungrounded_cannot_be_launchable")

    launchable_backends = payload.get("launchable_backends")
    if launchable_backends is not None and not isinstance(launchable_backends, list):
        errors.append(f"{context}:invalid_launchable_backends")
    default_backend = str(payload.get("default_backend") or "").strip()
    if default_backend and isinstance(launchable_backends, list):
        available_backends = _string_list(launchable_backends)
        if available_backends and default_backend not in available_backends:
            errors.append(f"{context}:default_backend_not_launchable:{default_backend}")
    return errors


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
    runtime_eligibility = spec.get("runtime_eligibility")
    if runtime_eligibility is None:
        errors.append("missing_runtime_contract_field:runtime_eligibility")
    else:
        errors.extend(validate_runtime_eligibility(runtime_eligibility))
    canonical_output = spec.get("canonical_output")
    if canonical_output is None:
        errors.append("missing_runtime_contract_field:canonical_output")
    else:
        errors.extend(validate_output_linkage(canonical_output, context="canonical_output", expected_authoritative=True))
    presentation_output = spec.get("presentation_output")
    if presentation_output is None:
        errors.append("missing_runtime_contract_field:presentation_output")
    else:
        errors.extend(
            validate_output_linkage(
                presentation_output,
                context="presentation_output",
                expected_authoritative=False,
            )
        )
    provenance = spec.get("provenance")
    if provenance is None:
        errors.append("missing_runtime_contract_field:provenance")
    else:
        errors.extend(validate_grounding_provenance(provenance))
        if bool(grounding_fields_from_provenance(provenance).get("presentation_only")):
            errors.append("provenance:presentation_only_conflicts_with_canonical_spec")
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
    for name, path in _presentation_policy_paths(spec).items():
        if not path.is_file():
            errors.append(f"missing_runtime_layer_policy_file:{path.name}")
            continue
        payload = _read_json(path)
        if str(payload.get("schema_version") or "").strip() != "v1":
            errors.append(f"invalid_runtime_layer_policy_schema:{name}")
        if name == "protected_regions_manifest_path":
            protected_grounding_status = str(payload.get("grounding_status") or "").strip().lower()
            if protected_grounding_status not in ALLOWED_GROUNDING_STATUSES:
                errors.append(
                    f"protected_regions_manifest:invalid_grounding_status:{protected_grounding_status or 'missing'}"
                )
            if "region_count" in payload and int(payload.get("region_count") or 0) != len(
                [item for item in payload.get("regions", []) if isinstance(item, Mapping)]
            ):
                errors.append("protected_regions_manifest:region_count_mismatch")

    spec_grounding_status = str(spec.get("grounding_status") or "").strip().lower()
    runtime_grounding_status = (
        str(runtime_eligibility.get("grounding_status") or "").strip().lower()
        if isinstance(runtime_eligibility, Mapping)
        else ""
    )
    policy_grounding_status = str(policy.get("grounding_status") or "").strip().lower()
    for label, value in (
        ("spec", spec_grounding_status),
        ("runtime_layer_policy", policy_grounding_status),
        ("runtime_eligibility", runtime_grounding_status),
    ):
        if value and value not in ALLOWED_GROUNDING_STATUSES:
            errors.append(f"{label}:invalid_grounding_status:{value}")

    present_grounding_statuses = {
        value for value in (spec_grounding_status, runtime_grounding_status, policy_grounding_status) if value
    }
    if len(present_grounding_statuses) > 1:
        errors.append("grounding_status_mismatch")

    if isinstance(runtime_eligibility, Mapping) and runtime_grounding_status == "ungrounded":
        for candidate in (
            str(runtime_eligibility.get("ungrounded_reason") or "").strip(),
            str(policy.get("ungrounded_reason") or "").strip(),
            str(spec.get("ungrounded_reason") or "").strip(),
        ):
            if candidate:
                break
        else:
            errors.append("ungrounded_reason_missing")

    if isinstance(runtime_eligibility, Mapping):
        launchable = runtime_eligibility.get("launchable")
        if launchable is True and runtime_grounding_status == "ungrounded":
            errors.append("runtime_eligibility:ungrounded_cannot_be_launchable")
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
    "ALLOWED_GROUNDING_LEVELS",
    "ALLOWED_GROUNDING_STATUSES",
    "ALLOWED_RUNTIME_READINESS_STATES",
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
    "validate_grounding_provenance",
    "validate_output_linkage",
    "validate_runtime_eligibility",
    "validate_runtime_layer_spec",
    "with_grounding_fields",
]
