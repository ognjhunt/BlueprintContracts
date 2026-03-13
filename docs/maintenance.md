# Maintenance Guide

## Repo Boundary

Add code here only when all of the following are true:

- the logic defines or validates an artifact crossing between Pipeline and Validation
- divergence across repos would be a bug
- the logic can stay lightweight and portable

Do not add runtime execution, service, CV/ML, or repo-specific convenience code.

## Public API Discipline

- Public API is module-based and defined by each module's `__all__`
- Package-root exports are not a compatibility surface
- New public exports require a consumer need in both repos or a strong contract reason
- Internal helpers must stay prefixed with `_`

## Safe Evolution Rules

- Patch releases (`0.1.x`) are for backwards-compatible fixes, docs, tests, and guardrails
- Minor releases (`0.x+1.0`) may add fields or behaviors, but must include explicit upgrade notes
- Breaking removals or changed semantics require a minor release and clear consumer coordination
- Prefer additive changes to payloads over shape redesigns
- Keep normalization explicit and deterministic

## Release Process

1. Update code, docs, tests, and `CHANGELOG.md`
2. Run:

   ```bash
   uv sync --dev
   uv run pytest
   uv build
   ```

3. Commit the release state
4. Create and push the tag:

   ```bash
   git tag v0.1.0
   git push origin main --tags
   ```

5. Update each consumer repo to the new pinned tag or commit
6. Run the consumer repos' compatibility and integration checks before merging those pin bumps

## Consumer Upgrade Guidance

- Read the changelog section for the target release
- Update the pinned Git ref
- Run at least the shared-contract compatibility tests in Pipeline and Validation
- If the release changes payload semantics or adds required fields, land the consumer updates in coordinated PRs

Current workspace status at the time of this hardening pass:

- `BlueprintCapturePipeline` pins `blueprint-contracts` to commit `2933580`
- `BlueprintValidation` pins `blueprint-contracts` to commit `2933580`
- both repos already import shared symbols from module paths rather than package-root exports

## Guardrails

- Keep dependencies empty in `pyproject.toml` unless there is a clear, portable contract need
- Do not import banned heavy modules under `src/blueprint_contracts`
- Keep threshold constants and policy builders covered by tests
- Keep failure messages actionable because these contracts fail across repo boundaries
