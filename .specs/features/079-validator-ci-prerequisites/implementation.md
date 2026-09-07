---
title: Validator CI Prerequisites Implementation
feature: 079-validator-ci-prerequisites
status: In Progress
---

<!-- @spec FR-001: Repair CI prerequisites — spec.md#fr-001 -->

# Implementation Mapping

Repairs are applied locally. This complete file scope is retained for native conventions checks. Runtime and remote evidence remain separate; same-SHA CI and full feature certification are pending.

## Requirement Mapping

| Requirement | Files | Status |
|---|---|---|
| FR-001 | Source/test paths below | Local lint and typing verified |
| FR-002 | Read [CI](../../../.github/workflows/ci.yml) | Pending |
| FR-003 | Read [CI](../../../.github/workflows/ci.yml) | Pending |
| FR-004 | Read [visual tests](../../../tests/test_visual_gate.py) | Pending |
| FR-005 | Read [CI](../../../.github/workflows/ci.yml) | Pending |

## Files Created/Modified

- Inspect [.agent-sync/skills/spec-specify/SKILL.md](../../../.agent-sync/skills/spec-specify/SKILL.md) for the scoped repair.
- Inspect [.github/workflows/ci.yml](../../../.github/workflows/ci.yml) for the scoped repair.
- Inspect [.specs/features/002-layer-3-cli-surface/plan.md](../../../.specs/features/002-layer-3-cli-surface/plan.md) for the scoped repair.
- Inspect [.specs/features/006-taxonomy-testing-infra/plan.md](../../../.specs/features/006-taxonomy-testing-infra/plan.md) for the scoped repair.
- Inspect [.specs/features/009-visual-state-baselines/plan.md](../../../.specs/features/009-visual-state-baselines/plan.md) for the scoped repair.
- Inspect [.specs/features/009-visual-state-baselines/spec.md](../../../.specs/features/009-visual-state-baselines/spec.md) for the scoped repair.
- Inspect [.specs/features/011-visual-migrate-integration/plan.md](../../../.specs/features/011-visual-migrate-integration/plan.md) for the scoped repair.
- Inspect [.specs/features/025-mutation-testing-on-demand/plan.md](../../../.specs/features/025-mutation-testing-on-demand/plan.md) for the scoped repair.
- Inspect [.specs/features/028-ui-runner-web/plan.md](../../../.specs/features/028-ui-runner-web/plan.md) for the scoped repair.
- Inspect [.specs/features/037-test-multi-runner-integration/plan.md](../../../.specs/features/037-test-multi-runner-integration/plan.md) for the scoped repair.
- Inspect [.specs/features/039-command-expectations-and-verify-output/plan.md](../../../.specs/features/039-command-expectations-and-verify-output/plan.md) for the scoped repair.
- Inspect [.specs/testing/strategy.md](../../../.specs/testing/strategy.md) for the scoped repair.
- Inspect [docs/superpowers/plans/2026-04-10-python-commit-hook-and-orchestration.md](../../../docs/superpowers/plans/2026-04-10-python-commit-hook-and-orchestration.md) for the scoped repair.
- Inspect [docs/superpowers/plans/2026-04-18-fix-visual-scaffolding-no-frontend.md](../../../docs/superpowers/plans/2026-04-18-fix-visual-scaffolding-no-frontend.md) for the scoped repair.
- Inspect [docs/superpowers/plans/2026-04-18-legacy-test-merge-plan.md](../../../docs/superpowers/plans/2026-04-18-legacy-test-merge-plan.md) for the scoped repair.
- Inspect [docs/superpowers/plans/2026-04-18-route-scan-full-coverage.md](../../../docs/superpowers/plans/2026-04-18-route-scan-full-coverage.md) for the scoped repair.
- Inspect [docs/superpowers/plans/2026-05-17-command-validation-hardening.md](../../../docs/superpowers/plans/2026-05-17-command-validation-hardening.md) for the scoped repair.
- Inspect [docs/superpowers/specs/2026-04-02-layer2-coherence-validation-design.md](../../../docs/superpowers/specs/2026-04-02-layer2-coherence-validation-design.md) for the scoped repair.
- Inspect [docs/superpowers/specs/2026-04-18-fix-visual-scaffolding-no-frontend-design.md](../../../docs/superpowers/specs/2026-04-18-fix-visual-scaffolding-no-frontend-design.md) for the scoped repair.
- Inspect [system/contracts/ACTIVATION_CONTRACT.md](../../../system/contracts/ACTIVATION_CONTRACT.md) for the scoped repair.
- Inspect [system/contracts/SUPERPOWERS_RETURN.md](../../../system/contracts/SUPERPOWERS_RETURN.md) for the scoped repair.
- Inspect [tests/goal_bootstrap_support.py](../../../tests/goal_bootstrap_support.py) for the scoped repair.
- Inspect [tests/test_conventions_ast_engine.py](../../../tests/test_conventions_ast_engine.py) for the scoped repair.
- Inspect [tests/test_conventions_diffguard.py](../../../tests/test_conventions_diffguard.py) for the scoped repair.
- Inspect [tests/test_conventions_lang_multilang.py](../../../tests/test_conventions_lang_multilang.py) for the scoped repair.
- Inspect [tests/test_conventions_taxonomy.py](../../../tests/test_conventions_taxonomy.py) for the scoped repair.
- Inspect [tests/test_conventions_verify_scope.py](../../../tests/test_conventions_verify_scope.py) for the scoped repair.
- Inspect [tests/test_device_cmd.py](../../../tests/test_device_cmd.py) for the scoped repair.
- Inspect [tests/test_goal_bootstrap_archive.py](../../../tests/test_goal_bootstrap_archive.py) for the scoped repair.
- Inspect [tests/test_goal_bootstrap_pairing.py](../../../tests/test_goal_bootstrap_pairing.py) for the scoped repair.
- Inspect [tests/test_goal_bootstrap_prove.py](../../../tests/test_goal_bootstrap_prove.py) for the scoped repair.
- Inspect [tests/test_goal_bootstrap_render.py](../../../tests/test_goal_bootstrap_render.py) for the scoped repair.
- Inspect [tests/test_goal_contracts.py](../../../tests/test_goal_contracts.py) for the scoped repair.
- Inspect [tests/test_hooks_cli.py](../../../tests/test_hooks_cli.py) for the scoped repair.
- Inspect [tests/test_journey_v2_runner.py](../../../tests/test_journey_v2_runner.py) for the scoped repair.
- Inspect [tests/test_penflow_contract_validation.py](../../../tests/test_penflow_contract_validation.py) for real positive/negative authority assertions and explicit missing-CLI diagnostics.
- Inspect [tests/test_penflow_approval_models.py](../../../tests/test_penflow_approval_models.py) for the scoped repair.
- Inspect [tests/test_run_artifact.py](../../../tests/test_run_artifact.py) for the scoped repair.
- Inspect [tests/test_visual_gate.py](../../../tests/test_visual_gate.py) for the scoped repair.
- Inspect [validator/conventions_gates.py](../../../validator/conventions_gates.py) for the scoped repair.
- Inspect [validator/doctor/models.py](../../../validator/doctor/models.py) for the scoped repair.

- Inspect [tests/_conventions_verify_scope_01.py](../../../tests/_conventions_verify_scope_01.py) for preserved cases or fixture boundaries.
- Inspect [tests/_conventions_verify_scope_02.py](../../../tests/_conventions_verify_scope_02.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_01.py](../../../tests/_goal_contracts_01.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_02.py](../../../tests/_goal_contracts_02.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_03.py](../../../tests/_goal_contracts_03.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_04.py](../../../tests/_goal_contracts_04.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_05.py](../../../tests/_goal_contracts_05.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_06.py](../../../tests/_goal_contracts_06.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_07.py](../../../tests/_goal_contracts_07.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_08.py](../../../tests/_goal_contracts_08.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_09.py](../../../tests/_goal_contracts_09.py) for preserved cases or fixture boundaries.
- Inspect [tests/_goal_contracts_10.py](../../../tests/_goal_contracts_10.py) for preserved cases or fixture boundaries.
- Inspect [tests/_journey_v2_runner_01.py](../../../tests/_journey_v2_runner_01.py) for preserved cases or fixture boundaries.
- Inspect [tests/_journey_v2_runner_02.py](../../../tests/_journey_v2_runner_02.py) for preserved cases or fixture boundaries.
- Inspect [tests/_journey_v2_runner_03.py](../../../tests/_journey_v2_runner_03.py) for preserved cases or fixture boundaries.
- Inspect [tests/_journey_v2_runner_04.py](../../../tests/_journey_v2_runner_04.py) for preserved cases or fixture boundaries.
- Inspect [tests/_json_fixture.py](../../../tests/_json_fixture.py) for preserved cases or fixture boundaries.
- Inspect [tests/_run_artifact_01.py](../../../tests/_run_artifact_01.py) for preserved cases or fixture boundaries.
- Inspect [tests/_run_artifact_02.py](../../../tests/_run_artifact_02.py) for preserved cases or fixture boundaries.
- Inspect [tests/_visual_gate_01.py](../../../tests/_visual_gate_01.py) for preserved cases or fixture boundaries.
- Inspect [tests/_visual_gate_02.py](../../../tests/_visual_gate_02.py) for preserved cases or fixture boundaries.
- Inspect [tests/_visual_gate_03.py](../../../tests/_visual_gate_03.py) for preserved cases or fixture boundaries.
- Inspect [tests/_visual_gate_04.py](../../../tests/_visual_gate_04.py) for preserved cases or fixture boundaries.

- Inspect [.specs/README.md](../../../.specs/README.md) for scoped repair documentation.
- Inspect [.specs/changelog.md](../../../.specs/changelog.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/changelog.md](../../../.specs/features/079-validator-ci-prerequisites/changelog.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/implementation.md](../../../.specs/features/079-validator-ci-prerequisites/implementation.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/plan.md](../../../.specs/features/079-validator-ci-prerequisites/plan.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/progress.md](../../../.specs/features/079-validator-ci-prerequisites/progress.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/spec.md](../../../.specs/features/079-validator-ci-prerequisites/spec.md) for scoped repair documentation.
- Inspect [.specs/features/079-validator-ci-prerequisites/checks/2026-09-07.md](../../../.specs/features/079-validator-ci-prerequisites/checks/2026-09-07.md) for scoped repair documentation.

## Acceptance Criteria Mapping

| AC | Check | Status |
|---|---|---|
| AC-001 | Full Ruff and typing gates | Local PASS; zero lint, formatting, pyright and mypy errors |
| AC-002 | Real Penflow subprocess suites | Direct suites PASS with verified pinned CLI; reviewed native mapping remains separate |
| AC-003 | Full unit and level_3a suites | 3726 unit passed; 89 integration passed; existing skips preserved |
| AC-004 | Visual coverage and symlink cases | 121 passed, 94.41 percent |
| AC-005 | Same-SHA stable GitHub workflow | Pending |
