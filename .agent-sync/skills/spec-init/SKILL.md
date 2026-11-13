---
name: spec-init
description: Initialize LiveSpec from a project interview or observed code, preserving project data and reporting actual setup results.
---
<!-- @spec FR-001, FR-003: Bootstrap delivery — .specs/features/122-review-led-delivery/spec.md#fr-001 -->

# spec-init

Read [review led delivery](../../../system/review-led-delivery.md) first, resolving this link from the skill's physical directory through any installed symlink. It governs direct, nested, autonomous and resumed initialization. No goal render/prove/archive, semantic receipt, separate plan review or certification inventory is a prerequisite.

## Resolve scope before writes

- Resolve the target from `--dir`/`-D` (otherwise cwd) and the executing LiveSpec root from the physical skill, recorded project path or source layout. Verify its VERSION and required installer/sync scripts; keep the selected runtime, not a mutable `current` alias.
- Preserve `--from-code`/`-f`, `--auto`/`-a`, `--force`/`-F`, `--dry-run`/`-d` and the selected timeout. Autonomous from-code rejects unsupported `--deep`, `--stack` and incompatible flags before mutation.
- Preview is read-only: no installation, sync, hooks, backup creation, provider/host call or initialized/completed claim. A preview creates no goal or receipt either.
- Preserve existing features, hooks, runs, source, integration text and accepted decisions. Explicit `--force` never means unbacked overwrite: retain the unique local pre-image and its location. A different existing format requires migration first.

## Initialize

1. Read the relevant project conventions and [installation details](installation.md). For an interview/preset, establish vision, users, scope and stack with the user; preserve meaningful unknowns and functional choices. Import supplied brainstorm/design data without inventing ancestry or certification.
2. For autonomous observed-code setup, use the shipped backend before manual generation: `bash "$LIVESPEC_ROOT/scripts/init-from-code-autonomous.sh" "$TARGET_DIR" --timeout-seconds "$REMAINING_SECONDS"`, appending explicit `--force` or `--dry-run` when selected. The backend owns observed generation, backed-up recovery, integrations and bounded tool probes; it does not execute Markdown hooks. Use [the from-code procedure](installation.md#non-interactive-autonomous-from-code-mode) for its safeguards.
3. For interactive setup, use [the installation procedure](installation.md#phase-c--installation-automatic): project-specific constitution/profile/stack/ADRs/testing/roadmap, project-local assets and hooks. Apply only authorized setup hooks consistent with the shared policy; inherited certification steps cannot become prerequisites.
4. Verify the actual installation: required generated files and project links, effective source/runtime path, version, fresh-snapshot pin where applicable, retained backup/history and relevant tooling. `--verify-only` is a useful current check, not a semantic certificate. Preserve real exit codes and missing outputs; do not call an unsuccessful installation complete.
5. Preserve requested or configured project continuity. On a supported, authorized host, initialize or attach the project-bound process through the current runtime’s supported continuity path, without goals, certificates or implicit global installation. If continuity was not requested, no host call is needed; if unsupported, unauthorized or previously refused, retain the unmet need and report the affected action `NOT_RUN` rather than retrying it. Missing continuity does not block independent feature work. Read [the continuity procedure](installation.md#step-d7--mission-supervisor-and-prerequisites).
6. Return results to the parent owning the shared final review, or obtain that review under the shared policy. Correct material setup defects, retain nonblocking findings and unverified observations, and report actual outcomes and limitations. Commit or publish only within existing authorization.

Read [the former certification workflow](certification.md) only for an explicitly requested historical diagnostic. It retains its original inventory and verdicts, never the default bootstrap path.
