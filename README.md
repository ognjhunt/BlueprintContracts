# BlueprintContracts

`BlueprintContracts` is the single lightweight source of truth for shared handoff, site-world, runtime-layer policy, and canonical package contracts used by Pipeline and Validation.

## What This Repo Is For

This package owns portable contract logic for artifacts that cross repo boundaries between:

- `/Users/nijelhunt_1/workspace/BlueprintCapturePipeline`
- `/Users/nijelhunt_1/workspace/BlueprintValidation`

It is intentionally stdlib-only, low-cost to import, and narrow in scope. The supported public API is module-based:

- `blueprint_contracts.handoff_contract`
- `blueprint_contracts.capture_contract`
- `blueprint_contracts.site_world_contract`
- `blueprint_contracts.runtime_layer_contract`
- `blueprint_contracts.canonical_package`

`blueprint_contracts.__init__` is metadata-only and should not be treated as a compatibility bucket.

## What Belongs Here

- Portable contract validation for qualified opportunity handoffs
- Portable enums and normalizers for the capture-side boundary between producer repos and Pipeline
- Structural validation and normalization for site-world registration/spec/health artifacts
- Shared runtime-layer policy constants and helper builders that must not diverge across repos
- Canonical package version computation and verification
- Shared public exports needed by both consumer repos

## What Must Not Go Here

- Runtime execution logic
- HTTP service logic
- Session orchestration
- Rollout export logic
- Evaluation or scoring logic
- Webapp workflow/business logic
- Repo-specific helper utilities
- Heavy runtime dependencies such as OpenCV, NumPy, Torch, TensorFlow, or FastAPI

## Public API and Ownership

Each module defines its supported exports via `__all__`. Anything prefixed with `_` is internal-only and may change without notice.

- `handoff_contract`: validates and normalizes the qualified opportunity payload boundary
- `capture_contract`: defines shared capture source/modality/tier enums plus sidecar normalizers
- `site_world_contract`: loads adjacent site-world artifacts and summarizes local grounding completeness
- `runtime_layer_contract`: defines shared thresholds/policies for protected region handling
- `canonical_package`: computes and verifies the deterministic canonical package version

Module-level imports are the supported consumer pattern:

```python
from blueprint_contracts.handoff_contract import validate_qualified_opportunity_handoff
from blueprint_contracts.site_world_contract import load_site_world_bundle
from blueprint_contracts.runtime_layer_contract import classify_region
from blueprint_contracts.canonical_package import compute_canonical_package_version
```

## Consumer Install and Pinning

Consumers currently pin this repo by Git reference. Keep doing that until a published package workflow is introduced.

Current verified consumer refs:

- `BlueprintCapturePipeline`: `blueprint-contracts @ git+https://github.com/ognjhunt/BlueprintContracts.git@2933580`
- `BlueprintValidation`: `blueprint-contracts @ git+https://github.com/ognjhunt/BlueprintContracts.git@2933580`

Example dependency pin:

```toml
blueprint-contracts = { git = "https://github.com/<org>/BlueprintContracts.git", rev = "<tag-or-commit>" }
```

Preferred upgrade flow:

1. Cut and push a release tag in this repo.
2. Review `CHANGELOG.md` and the maintenance guide for compatibility notes.
3. Update the pinned tag or commit in each consumer repo.
4. Run each consumer repo's compatibility and integration tests.

The current in-workspace consumers already import from module paths. No package-root imports were found in:

- `/Users/nijelhunt_1/workspace/BlueprintCapturePipeline`
- `/Users/nijelhunt_1/workspace/BlueprintValidation`

## Local Verification

```bash
uv sync --dev
uv run pytest
uv build
```

The test suite includes guardrails for:

- public API shape
- banned heavy dependencies inside `src/blueprint_contracts`
- threshold/policy drift
- deterministic canonical package hashing

## Docs

- [`docs/handoff_contract.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/docs/handoff_contract.md)
- [`docs/site_world_contract.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/docs/site_world_contract.md)
- [`docs/runtime_layer_contract.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/docs/runtime_layer_contract.md)
- [`docs/canonical_package.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/docs/canonical_package.md)
- [`docs/maintenance.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/docs/maintenance.md)
- [`CHANGELOG.md`](/Users/nijelhunt_1/workspace/BlueprintContracts/CHANGELOG.md)
