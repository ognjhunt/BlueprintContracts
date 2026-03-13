# Changelog

All notable changes to `blueprint-contracts` should be documented in this file.

The format is intentionally simple:

- `Unreleased` for pending work
- one section per released version

## Unreleased

- Clarified in docs and maintenance guidance that `runtime_eligibility.readiness_state` is the required machine-readable launchability field.
- Documented that consumer repos must not emit `runtime_eligibility.status` in place of `readiness_state`.

## 0.1.0 - 2026-03-13

- Established `BlueprintContracts` as the shared contract package for Pipeline and Validation.
- Tightened the public API to supported module-level exports with a minimal package root.
- Added contract documentation, maintenance guidance, changelog discipline, and lightweight CI.
- Expanded regression and guardrail tests for handoff, site-world, runtime-layer, and canonical package behavior.
