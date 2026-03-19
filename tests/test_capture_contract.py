from __future__ import annotations

from blueprint_contracts.capture_contract import (
    normalize_capture_modality,
    normalize_capture_source,
    normalize_capture_tier,
    normalize_checkpoint_events,
    normalize_requested_lanes,
    normalize_route_anchors,
)


def test_normalize_capture_source_and_tier_support_android_compat_alias() -> None:
    assert normalize_capture_source("android_phone") == "android"
    assert normalize_capture_tier("tier2_android_phone") == "tier2_android"


def test_normalize_capture_modality_preserves_iphone_video_only_truth() -> None:
    assert (
        normalize_capture_modality(
            raw_modality="iphone_video_only",
            capture_source="iphone",
            has_metric_arkit_bundle=False,
        )
        == "iphone_video_only"
    )
    assert (
        normalize_capture_modality(
            raw_modality=None,
            capture_source="iphone",
            has_metric_arkit_bundle=False,
        )
        == "iphone_video_only"
    )
    assert (
        normalize_capture_modality(
            raw_modality=None,
            capture_source="iphone",
            has_metric_arkit_bundle=True,
        )
        == "iphone_arkit_lidar"
    )


def test_normalize_requested_lanes_expands_all_and_evaluation_prep() -> None:
    assert normalize_requested_lanes(None) == ["qualification"]
    assert normalize_requested_lanes("evaluation_prep") == ["qualification", "evaluation_prep"]
    assert normalize_requested_lanes("all") == [
        "qualification",
        "scene_memory",
        "retrieval_index",
        "frame_alignment",
        "evaluation_prep",
        "synthesis_coverage_validation",
    ]


def test_normalize_route_and_checkpoint_sidecars() -> None:
    route_payload = normalize_route_anchors(
        {
            "schemaVersion": "v1",
            "routeAnchors": [
                {
                    "anchorId": "anchor_entry",
                    "anchorType": "entry",
                    "requiredInPrimaryPass": True,
                    "requiredInRevisitPass": False,
                }
            ],
        }
    )
    checkpoint_payload = normalize_checkpoint_events(
        {
            "schemaVersion": "v1",
            "checkpointEvents": [
                {
                    "anchorId": "anchor_entry",
                    "passId": "pass-1",
                    "tCaptureSec": 1.0,
                    "holdDurationSec": 0.8,
                    "completed": True,
                }
            ],
        }
    )
    assert route_payload["route_anchors"][0]["anchor_id"] == "anchor_entry"
    assert checkpoint_payload["checkpoint_events"][0]["pass_id"] == "pass-1"
