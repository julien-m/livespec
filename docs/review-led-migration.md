<!-- @spec FR-004: Safe adoption — .specs/features/122-review-led-delivery/spec.md#fr-004 -->
# Migrate to review led delivery

## Scope

Standard skills now use implementation, useful checks and one independent final review. Failed scripts remain visible inputs to that review instead of automatic phase stops. This policy does not change historical CLI verdicts or retrospectively certify an active goal.

## Before changing a consumer

1. Stop new worker dispatch at a safe checkpoint; let current file writes finish.
2. Record the current runtime pin, SDK interpreter, provider links and owned agent prompts. Back up the feature documents, accepted decisions and active mission state without deleting originals.
3. Check that the candidate includes the consumer's existing runtime fixes. Never downgrade a consumer merely to obtain shorter skills. If its private runtime is ahead of public main, port the reviewed delivery-policy delta onto that runtime separately and retain both source commit identities.

## Adopt

1. Build and install an immutable runtime with its matching wheel/interpreter using the supported runtime installer. Verify actual CLI startup and project projection on an isolated project first.
2. Upgrade the project pin through the supported runtime selection command. Re-read the actual selected runtime and resolved skill files; updating the global default does not update existing pins.
3. Resolve shared instructions from the runtime's `system/review-led-delivery.md`. Project copies read `.specs/.livespec-path`; skill symlinks resolve from their real source directory.
4. Preserve customized agent settings. Use a fresh generic native reviewer if an old mutable agent prompt still injects certification gates; do not overwrite customization silently.
5. Inspect existing Git hooks. The supported installer replaces an exact original LiveSpec hook with the advisory template. For a composite/custom hook it preserves the original content and appends the advisory reminder; inspect and migrate only the old LiveSpec-owned block manually, preserving other tools and their checks. The original certification hook remains an explicit diagnostic template. Do not bypass an unrelated custom hook.
6. Preserve old mission and goal history. Record explicitly that remaining work follows review-led delivery; do not fabricate archive/proof success for the former contract. Do not let an obsolete goal stop independent product work.
7. Reload the coordinator and worker instructions at the checkpoint. Resume from the actual implemented feature, accepted decisions and remaining product findings, without restarting completed work.

## Verify the migration

- A failed administrative script reaches final review with its true result.
- A real product defect is corrected; missing essential observations remain unverified.
- One independent final reviewer inspects code, file placement, conventions and actual checks.
- A normal feature reaches delivery without invoking the old certificate chain.

## Rollback

Select the saved previous runtime through the supported runtime command and restore only the saved provider links or prompts changed by adoption. Keep newer product changes and both histories. Report which policy now applies; do not mix old machine certification with review-led completion.

## Bootstrap follow-up

Initialization and format migration now use the same review-led policy; read [initialization](../.agent-sync/skills/spec-init/SKILL.md) and [migration](../.agent-sync/skills/spec-migrate/SKILL.md) for the operational safeguards. Adopt these instruction changes through the selected runtime at a safe checkpoint. This change adds no format migration, continuity service or application installation. Preserve an active consumer pin and its private fixes; public format21 is not a replacement for an existing private format23 runtime.
