# Migration technical reference

Read [review led delivery](../../../system/review-led-delivery.md) first. These are operational safeguards, not goal/receipt prerequisites. The extended original procedure remains in [the historical diagnostic](certification.md).

## Execution flow

1. Resolve the existing project, `.specs/livespec-version` (default1 when absent), recorded `.specs/.livespec-path` and executing skill's physical source. Verify VERSION and scripts. Preview may inspect a missing/stale path but never writes its replacement.
2. On a pinned project, use the authorized selected snapshot after runtime upgrade; do not replace consumer-specific fixes, switch to `current`, downgrade a newer project or silently adopt another policy.
3. Run `livespec migrate plan --project <project> --livespec <source> --json`. Respect `apply` order, `skipped` reasons and `invalid_restore_points`; the planner reads `supersedes`, `replaces_when_unapplied` and `invalidates_restore_points` metadata.
4. Inspect each planned `migrations/N/migrate.md`; execute only the authorized ordered actions with the same source's executor:

```bash
bash <source>/scripts/migrate.sh <source>/migrations/N/migrate.md <project> <source>
```

- `--dry-run` is the skill's read-only planning mode: display DSL actions, paths and warnings without executing them. No sync, version/path writes, hooks, restore point, scaffolding or inverse.
- `--force` requests explicit historical reapplication; it does not discard backups or falsify the current version. The current `migrate plan` CLI has no `--force` option and plans pending versions only. Inspect the requested replay and compatibility against the real version/pre-images before using shipped idempotent actions; when a safe replay cannot be established, report that concrete limit rather than inventing planner support or blindly replaying destructive actions.
- If versions match, report no format migration needed; optional visual follow-up is separate. If the project is newer, report the incompatibility and leave it intact.
- A missing/invalid planned migration or nonzero script exit leaves dependent actions unapplied. Preserve the error and current version; do not announce the target version or force a pin past the failure. Continue independent diagnosis/review without restarting certification.
- On retry, preserve the first complete restore point and inspect the failed action. Never reset metadata, delete history or manually bump the format to hide a failure. `SET_VERSION` belongs last, after successful migration actions.

## Restore points

- Read each planned migration's shipped procedure for its exact owned scope and backup behavior. Report the restore-point location when provided; preserve the first complete pre-image on retry.
- Preserve bytes, kinds, modes, symlink targets, custom policy and immutable historical records. Never assume that a newer private release or its inverse is shipped by this source.

## Post-migration observations

- Inspect actual project version, effective runtime/path/pin, managed links and project-local agent outputs. Use the current project sync implementation when the migration requests it; preserve custom files and never modify global skills.
- A generated path that does not resolve is an incomplete integration finding, not successful setup. Preserve actual exit codes, partial writes, unknown observations and material risks for review.
- Preserve any requested/configured project continuity and its existing association. On a supported, authorized host, include the safe project-bound attachment/startup needed by that request through the current review-led interface, without nested goals or implicit global installation. Otherwise retain the unmet need and actual unavailable/refused/NOT_RUN observation; migration does not authorize retries of a known host/socket refusal or block independent feature work on missing continuity.

## Optional visual follow-up

Only perform this scope when requested; format migration or matching versions do not authorize it automatically.

- Inspect `.specs/surfaces.yaml`; use [the surface resolver](../../../scripts/lib/surface-resolver.js) for selected Playwright surfaces. Report unsupported runners rather than inventing one.
- Read [visual migration scaffolding](../../../scripts/migrate-visual-tests.js) before `node <source>/scripts/migrate-visual-tests.js --generate`. Preserve its real `VISUAL_SCAFFOLD_RESULT` and counts. Missing Node/script or a failed helper is an unavailable/failed visual observation, not proof that scaffolding occurred.
- Reconciliation concerns newly generated scaffolds: inspect visual/nonvisual scope, duplicate coverage, syntax, empty stubs, route existence and heading coherence. Preserve real assertions and user code; do not delete existing tests, backups or logs to make migration appear clean. Do not stage/commit changes without existing Git authorization.
- For requested E2E generation, read [the generator](../../../scripts/generate-e2e-tests.js), actual feature Gherkin, routes, components, selectors and existing fixtures. Generate only supported scenarios with real assertions; a missing route/selector remains unverified, never an invented working test.
- Check generated files with available syntax/typing/runtime tools; retain outcomes and missing observations. No visual, Penflow or semantic certificate gates migration completion.

## Rollback

Only on an explicit rollback request, inspect the selected newer source's actual inverse procedures and restore points. Apply supported inverses in reverse migration order before re-pinning a previous runtime. If an inverse is absent or restore data is missing or altered, retain that limit and do not improvise destructive restoration, delete metadata or claim a rollback succeeded. Preserve bytes, modes, link targets and data outside the recorded scope.

## Report

Report the plan, versions, skipped metadata, actual actions/exits, effective runtime, retained restore points and any requested optional work as executed/failed/NOT_RUN. Only claim completion of the operations actually achieved. Return results to the parent owning final review or use the shared independent final reviewer; no separate plan review or certification inventory is required.
