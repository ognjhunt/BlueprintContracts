from __future__ import annotations

from blueprint_contracts.runtime_service_contract import (
    DEFAULT_RUNTIME_BACKEND_KIND,
    KNOWN_RUNTIME_BACKEND_KINDS,
    normalize_runtime_kind,
    parse_runtime_metadata,
    runtime_kind_label,
    runtime_kind_matches,
)


def test_native_world_model_is_the_default_runtime_kind() -> None:
    assert DEFAULT_RUNTIME_BACKEND_KIND == "native_world_model"
    assert "native_world_model" in KNOWN_RUNTIME_BACKEND_KINDS


def test_runtime_kind_label_covers_native_world_model() -> None:
    assert runtime_kind_label("native_world_model") == "Native world-model runtime"


def test_parse_runtime_metadata_preserves_native_runtime_kind() -> None:
    metadata = parse_runtime_metadata(
        {
            "runtime_kind": "native_world_model",
            "production_grade": True,
            "service": "cosmos-runtime",
            "runtime_base_url": "http://runtime.test/",
            "websocket_base_url": "ws://runtime.test/",
            "engine_identity": {"engine": "cosmos"},
            "model_identity": {"model_id": "cosmos-2.5"},
            "checkpoint_identity": {"checkpoint_id": "adapter-1"},
            "state_guarantees": {"authoritative_state": True},
            "capabilities": {"session_render": True},
            "readiness": {"model_ready": True, "checkpoint_ready": True},
        }
    )
    assert metadata.runtime_kind == "native_world_model"
    assert metadata.service == "cosmos-runtime"
    assert metadata.runtime_base_url == "http://runtime.test"
    assert metadata.websocket_base_url == "ws://runtime.test"


def test_runtime_kind_matches_supports_native_runtime_and_smoke_fallback() -> None:
    runtime = {"runtime_kind": "smoke_contract"}
    assert normalize_runtime_kind("unknown") == "native_world_model"
    assert runtime_kind_matches(
        {"runtime_kind": "native_world_model"},
        required_kind="native_world_model",
        allow_smoke_fallback=False,
    ) == (True, "ok")
    assert runtime_kind_matches(
        runtime,
        required_kind="native_world_model",
        allow_smoke_fallback=True,
    ) == (True, "smoke_fallback")
