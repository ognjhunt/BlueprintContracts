"""Blueprint shared contract package.

Supported imports are module-based:

- ``blueprint_contracts.handoff_contract``
- ``blueprint_contracts.site_world_contract``
- ``blueprint_contracts.runtime_layer_contract``
- ``blueprint_contracts.runtime_service_contract``
- ``blueprint_contracts.canonical_package``
"""

from __future__ import annotations

from importlib import metadata as _metadata

try:
    __version__ = _metadata.version("blueprint-contracts")
except _metadata.PackageNotFoundError:  # pragma: no cover - local source tree without installed metadata
    __version__ = "0.1.0"

__all__ = ["__version__"]
