# `canonical_package`

## Purpose

This module computes and verifies the deterministic canonical package version shared across Pipeline and Validation.

## Supported Public API

- `CANONICAL_PACKAGE_HASH_INPUTS`
- `normalized_json_bytes`
- `compute_canonical_package_version`
- `verify_canonical_package_version`

## Hash Inputs

Hash order is fixed:

1. scene memory manifest
2. conditioning bundle
3. object geometry manifest
4. task anchor manifest
5. site-world spec without `canonical_package_version`
6. protected regions manifest
7. canonical render policy
8. presentation variance policy

`normalized_json_bytes()` uses sorted keys and compact separators so semantically equivalent dictionaries hash identically even if key order differs.

## Why `canonical_package_version` Is Excluded

The spec's `canonical_package_version` field is excluded from the hashed copy of the spec so the computed digest does not depend on its own output. This prevents self-referential version churn and makes verification deterministic.

## Verification Behavior

`verify_canonical_package_version()` returns:

- `None` when the version matches or the spec does not declare an expected version
- `canonical_package_verification_inputs_missing` when required local JSON inputs are unavailable
- `canonical_package_version_mismatch:<observed>` when the recomputed version differs from the spec
