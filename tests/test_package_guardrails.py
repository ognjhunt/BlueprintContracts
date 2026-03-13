from __future__ import annotations

import ast
import importlib
from types import ModuleType
from pathlib import Path

import blueprint_contracts


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src" / "blueprint_contracts"


def test_package_root_surface_is_minimal() -> None:
    non_module_public = {
        name
        for name, value in blueprint_contracts.__dict__.items()
        if name not in {"annotations", "__version__"}
        and not name.startswith("_")
        and not isinstance(value, ModuleType)
    }
    assert non_module_public == set()
    assert isinstance(blueprint_contracts.__version__, str)
    assert blueprint_contracts.__all__ == ["__version__"]


def test_module_public_apis_are_explicit() -> None:
    handoff_contract = importlib.import_module("blueprint_contracts.handoff_contract")
    site_world_contract = importlib.import_module("blueprint_contracts.site_world_contract")
    runtime_layer_contract = importlib.import_module("blueprint_contracts.runtime_layer_contract")
    canonical_package = importlib.import_module("blueprint_contracts.canonical_package")

    assert handoff_contract.__all__ == [
        "ALLOWED_QUALIFICATION_STATES",
        "LEGACY_THIN_COMPATIBILITY_MODE",
        "LEGACY_THIN_HANDOFF_MODE",
        "QUALIFIED_OPPORTUNITY_SCHEMA_VERSION",
        "QualifiedOpportunityValidationError",
        "RICH_HANDOFF_MODE",
        "load_and_validate_qualified_opportunity_handoff",
        "validate_qualified_opportunity_handoff",
    ]
    assert site_world_contract.__all__ == [
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
    assert runtime_layer_contract.__all__ == [
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
    assert canonical_package.__all__ == [
        "CANONICAL_PACKAGE_HASH_INPUTS",
        "compute_canonical_package_version",
        "normalized_json_bytes",
        "validate_canonical_package_contract",
        "verify_canonical_package_version",
        "verify_canonical_package_version_details",
    ]


def test_no_banned_heavy_dependencies_are_imported() -> None:
    banned = {"cv2", "numpy", "torch", "tensorflow", "fastapi", "sklearn", "PIL"}
    for path in SRC_ROOT.rglob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned, f"{path} imports banned dependency {alias.name}"
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned, f"{path} imports banned dependency {node.module}"
