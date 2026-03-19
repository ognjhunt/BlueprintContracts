"""Shared capture-boundary enums and normalizers for Capture -> Pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


CAPTURE_DESCRIPTOR_SCHEMA_VERSION = "v1"
ALLOWED_CAPTURE_SOURCES = ("iphone", "glasses", "android")
ALLOWED_CAPTURE_MODALITIES = (
    "iphone_arkit_lidar",
    "iphone_video_only",
    "glasses_video_only",
    "glasses_plus_scaffolding",
    "android_video_only",
    "android_plus_scaffolding",
)
ALLOWED_EVIDENCE_TIERS = (
    "pre_screen_video",
    "qualified_metric_capture",
    "video_with_validated_scaffolding",
)
ALLOWED_CAPTURE_MODES = ("qualification_only", "site_world_candidate")
ALLOWED_REQUESTED_LANES = (
    "qualification",
    "scene_memory",
    "retrieval_index",
    "frame_alignment",
    "evaluation_prep",
    "synthesis_coverage_validation",
)


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_capture_source(raw_source: Any, capture_tier: Any = None) -> str:
    source = _text(raw_source)
    if source == "android_phone":
        return "android"
    if source in ALLOWED_CAPTURE_SOURCES:
        return source
    tier = _text(capture_tier)
    if "glasses" in tier:
        return "glasses"
    if "android" in tier:
        return "android"
    return "iphone"


def normalize_capture_tier(raw_capture_tier: Any, capture_source: Any = None) -> str:
    tier = str(raw_capture_tier or "").strip()
    lowered = tier.lower()
    if lowered == "tier2_android_phone":
        return "tier2_android"
    if tier:
        return tier
    source = normalize_capture_source(capture_source)
    if source == "glasses":
        return "tier2_glasses"
    if source == "android":
        return "tier2_android"
    return "tier1_iphone"


def normalize_requested_lanes(raw_requested_lanes: Any) -> List[str]:
    if raw_requested_lanes is None:
        return ["qualification"]
    if isinstance(raw_requested_lanes, str):
        values = [raw_requested_lanes]
    elif isinstance(raw_requested_lanes, (list, tuple, set)):
        values = [str(v) for v in raw_requested_lanes]
    else:
        values = [str(raw_requested_lanes)]

    normalized: List[str] = []
    for value in values:
        lowered = _text(value)
        if not lowered:
            continue
        if lowered == "all":
            for lane in ALLOWED_REQUESTED_LANES:
                if lane not in normalized:
                    normalized.append(lane)
            continue
        if lowered in ALLOWED_REQUESTED_LANES and lowered not in normalized:
            normalized.append(lowered)
            if lowered in {"retrieval_index", "frame_alignment", "evaluation_prep"} and "qualification" not in normalized:
                normalized.append("qualification")
    if (
        {"retrieval_index", "frame_alignment", "evaluation_prep"} & set(normalized)
        and "qualification" not in normalized
    ):
        normalized.append("qualification")
    ordered: List[str] = []
    for lane in ALLOWED_REQUESTED_LANES:
        if lane in normalized and lane not in ordered:
            ordered.append(lane)
    return ordered or ["qualification"]


def normalize_capture_modality(
    *,
    raw_modality: Any,
    capture_source: Any,
    has_metric_arkit_bundle: bool,
    scaffolding_used: Any = None,
    evidence_tier_hint: Any = None,
) -> str:
    explicit = _text(raw_modality)
    if explicit in ALLOWED_CAPTURE_MODALITIES:
        return explicit
    source = normalize_capture_source(capture_source)
    evidence_tier = _text(evidence_tier_hint)
    scaffolding = scaffolding_used if isinstance(scaffolding_used, (list, tuple, set)) else []
    if source == "iphone":
        if has_metric_arkit_bundle or evidence_tier == "qualified_metric_capture":
            return "iphone_arkit_lidar"
        return "iphone_video_only"
    if source == "glasses":
        return "glasses_plus_scaffolding" if scaffolding else "glasses_video_only"
    if source == "android":
        return "android_plus_scaffolding" if scaffolding else "android_video_only"
    return "iphone_video_only"


def normalize_route_anchors(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"schema_version": "v1", "route_anchors": []}
    raw = payload.get("route_anchors") or payload.get("routeAnchors")
    anchors: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            anchors.append(
                {
                    "anchor_id": str(item.get("anchor_id") or item.get("anchorId") or "").strip() or None,
                    "anchor_type": str(item.get("anchor_type") or item.get("anchorType") or "").strip() or None,
                    "label": str(item.get("label") or "").strip() or None,
                    "expected_observation": str(
                        item.get("expected_observation") or item.get("expectedObservation") or ""
                    ).strip()
                    or None,
                    "required_in_primary_pass": bool(
                        item.get("required_in_primary_pass")
                        if item.get("required_in_primary_pass") is not None
                        else item.get("requiredInPrimaryPass")
                    ),
                    "required_in_revisit_pass": bool(
                        item.get("required_in_revisit_pass")
                        if item.get("required_in_revisit_pass") is not None
                        else item.get("requiredInRevisitPass")
                    ),
                }
            )
    return {
        "schema_version": str(payload.get("schema_version") or payload.get("schemaVersion") or "v1"),
        "route_anchors": anchors,
    }


def normalize_checkpoint_events(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"schema_version": "v1", "checkpoint_events": []}
    raw = payload.get("checkpoint_events") or payload.get("checkpointEvents")
    events: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            events.append(
                {
                    "anchor_id": str(item.get("anchor_id") or item.get("anchorId") or "").strip() or None,
                    "pass_id": str(item.get("pass_id") or item.get("passId") or "").strip() or None,
                    "t_capture_sec": item.get("t_capture_sec")
                    if item.get("t_capture_sec") is not None
                    else item.get("tCaptureSec"),
                    "hold_duration_sec": item.get("hold_duration_sec")
                    if item.get("hold_duration_sec") is not None
                    else item.get("holdDurationSec"),
                    "completed": bool(item.get("completed")),
                }
            )
    return {
        "schema_version": str(payload.get("schema_version") or payload.get("schemaVersion") or "v1"),
        "checkpoint_events": events,
    }


__all__ = [
    "ALLOWED_CAPTURE_MODES",
    "ALLOWED_CAPTURE_MODALITIES",
    "ALLOWED_CAPTURE_SOURCES",
    "ALLOWED_EVIDENCE_TIERS",
    "ALLOWED_REQUESTED_LANES",
    "CAPTURE_DESCRIPTOR_SCHEMA_VERSION",
    "normalize_capture_modality",
    "normalize_capture_source",
    "normalize_capture_tier",
    "normalize_checkpoint_events",
    "normalize_requested_lanes",
    "normalize_route_anchors",
]
