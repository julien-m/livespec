---
created: 2026-09-04
feature: 076-spec-init-goal-bootstrap
title: "Implementation Map: Spec Init Goal Bootstrap"
type: implementation
updated: 2026-09-08
---

# Implementation Map: Spec Init Goal Bootstrap (076)

**Status:** V5 implementation checkpoint — the descriptor ownership correction passes targeted local checks; native execution proof and the independent post-check remain pending. The prior Feature PASS below is historical evidence and does not establish Linux parity.

## V5 temporary ownership correction — 2026-09-08

- Inspect [the archive writer](../../../validator/goal_archive_file.py) for `OwnedTemporary(descriptor, identity)` and the write-failure `finally` close. Inspect [the coordinator](../../../validator/goal_archive_fd.py) for the descriptor retained through publication and cleanup before one final close.
- Run [the lifecycle matrix](../../../tests/test_goal_archive_file.py) to prove success, write/fsync, pre-publication, link, post-publication and cleanup failures. Inspect [the race assertions](../../../tests/test_goal_bootstrap_archive_races.py) and [publication assertions](../../../tests/test_goal_bootstrap_archive_publication.py): only temporary-writer return annotations changed; foreign replacements remain protected.
- FR-005 / AC-006 / AC-008: local targeted evidence is 21 passed; Ruff, format, Pyright and mypy pass. This checkpoint does not certify all acceptance criteria or Linux CI. The full native capture and independent post-check are still required.
- Read [the independent pre-check](checks/2026-09-08-v5-precheck.md) for the observed Linux inode-reuse failure. The correction preserves cooperative locking, exclusive publication, the non-cooperating syscall-race boundary, and all historical receipts.

## Requirement Mapping

| Requirement | Implementation | Anchor | Automated proof |
|---|---|---|---|
| FR-001 | [goal_bootstrap.py](../../../validator/goal_bootstrap.py), [goal_cmd.py](../../../validator/cli_commands/goal_cmd.py) | `@spec FR-001` | [test_goal_bootstrap_render.py](../../../tests/test_goal_bootstrap_render.py), [test_goal_bootstrap_non_init.py](../../../tests/test_goal_bootstrap_non_init.py) |
| FR-002 | [goal_bootstrap.py](../../../validator/goal_bootstrap.py) | `@spec FR-002` | [test_goal_bootstrap_render.py](../../../tests/test_goal_bootstrap_render.py) |
| FR-003 | goal_contracts.py compatibility façade, anchored at compile and serialization | `@spec FR-003` | [test_goal_bootstrap_render.py](../../../tests/test_goal_bootstrap_render.py) |
| FR-004 | [goal_cli_inputs.py](../../../validator/goal_cli_inputs.py), [goal_pairing.py](../../../validator/goal_pairing.py), [goal_evidence_paths.py](../../../validator/goal_evidence_paths.py), plus the anchored goal_contracts.py proof façade | `@spec FR-004` | [test_goal_bootstrap_pairing.py](../../../tests/test_goal_bootstrap_pairing.py), [test_goal_bootstrap_prove.py](../../../tests/test_goal_bootstrap_prove.py) |
| FR-005 | [goal_pairing.py](../../../validator/goal_pairing.py), [goal_archive_paths.py](../../../validator/goal_archive_paths.py), [goal_archive_fd.py](../../../validator/goal_archive_fd.py), [goal_archive_file.py](../../../validator/goal_archive_file.py), [run_artifacts.py](../../../validator/run_artifacts.py) | `@spec FR-005` | [test_goal_bootstrap_pairing.py](../../../tests/test_goal_bootstrap_pairing.py), [test_goal_bootstrap_archive.py](../../../tests/test_goal_bootstrap_archive.py), [test_goal_bootstrap_archive_races.py](../../../tests/test_goal_bootstrap_archive_races.py), [test_goal_bootstrap_archive_publication.py](../../../tests/test_goal_bootstrap_archive_publication.py) |
| FR-006 | [goal_bootstrap.py](../../../validator/goal_bootstrap.py), [goal_cli_inputs.py](../../../validator/goal_cli_inputs.py) | `@spec FR-001`, `@spec FR-004` | [test_goal_bootstrap_non_init.py](../../../tests/test_goal_bootstrap_non_init.py), existing goal/run regressions |
| FR-007 | [goal_cmd.py](../../../validator/cli_commands/goal_cmd.py), [goal_cli_actions.py](../../../validator/goal_cli_actions.py), [goal_cli_output.py](../../../validator/goal_cli_output.py) | `@spec FR-001`, `@spec FR-004`, `@spec FR-005` | all seven feature test modules |
| FR-008 | Feature-owned test modules and [progress.md](progress.md) | test collection | 185 feature tests and 179 goal/run/version regressions |
| FR-009 | [goal_bootstrap.py](../../../validator/goal_bootstrap.py), anchored goal_contracts.py serialization façade | `@spec FR-003`, `@spec FR-009` | `test_explicit_target_controls_root_and_conventions` |
| FR-010 | [goal_pairing.py](../../../validator/goal_pairing.py), anchored goal_contracts.py proof façade, [goal_run_builder.py](../../../validator/goal_run_builder.py), [run_artifacts.py](../../../validator/run_artifacts.py) | `@spec FR-010` | proof transition and archive outcome tests |
| FR-011 | [goal_evidence_paths.py](../../../validator/goal_evidence_paths.py), [goal_archive_paths.py](../../../validator/goal_archive_paths.py) | `@spec FR-011` | evidence escape and `.runs` symlink matrices |
| FR-012 | [goal_cli_inputs.py](../../../validator/goal_cli_inputs.py), [goal_pairing.py](../../../validator/goal_pairing.py) | `@spec FR-012` | omitted/empty/malformed/mismatched pair tests |

## Acceptance Criteria Mapping

| AC | Proof | Status |
|---|---|---|
| AC-001 | [`tests/test_goal_bootstrap_render.py`](../../../tests/test_goal_bootstrap_render.py): fresh cwd and explicit target render; no `.specs` creation | Covered — PASS |
| AC-002 | [`tests/test_goal_bootstrap_render.py`](../../../tests/test_goal_bootstrap_render.py): relative/absolute aliases, ignored/post-`--` tokens, identical/conflicting duplicates, canonical target root, target-only conventions, and stable hash | Covered — PASS |
| AC-003 | [`tests/test_goal_bootstrap_render.py`](../../../tests/test_goal_bootstrap_render.py): malformed, missing, nonexistent, unresolvable, non-directory, unreadable, and loop targets fail with exit 2 and no writes | Covered — PASS |
| AC-004 | [`tests/test_goal_bootstrap_pairing.py`](../../../tests/test_goal_bootstrap_pairing.py): required fields, types, mirrors, hashes, task identity, feature, and statuses | Covered — PASS |
| AC-005 | [`tests/test_goal_bootstrap_prove.py`](../../../tests/test_goal_bootstrap_prove.py): eight transitions, external evidence, and real-path confinement | Covered — PASS |
| AC-006 | [`tests/test_goal_bootstrap_archive.py`](../../../tests/test_goal_bootstrap_archive.py), [`tests/test_goal_bootstrap_archive_races.py`](../../../tests/test_goal_bootstrap_archive_races.py), and [`tests/test_goal_bootstrap_archive_publication.py`](../../../tests/test_goal_bootstrap_archive_publication.py): contained archive, descriptor lifetime, symlink/target identity, cooperative-writer ownership checks, exclusive publication, cleanup, residue, and outcome identity | Covered — PASS |
| AC-007 | [`tests/test_goal_bootstrap_archive.py`](../../../tests/test_goal_bootstrap_archive.py), [`tests/test_goal_bootstrap_non_init.py`](../../../tests/test_goal_bootstrap_non_init.py): missing `.specs` and strict non-init operations | Covered — PASS |
| AC-008 | Seven bootstrap test modules, including [`test_goal_bootstrap_archive_races.py`](../../../tests/test_goal_bootstrap_archive_races.py) and [`test_goal_bootstrap_archive_publication.py`](../../../tests/test_goal_bootstrap_archive_publication.py), plus the existing goal-contract, archive-CLI, run-artifact, and version-guard regressions recorded in the Test report | Covered — PASS |
| AC-009 | Prove/archive/non-init modules: external control files allowed while project evidence and run destinations remain confined | Covered — PASS |
| AC-010 | [`tests/test_goal_bootstrap_pairing.py`](../../../tests/test_goal_bootstrap_pairing.py): explicit pair failures and legacy/mixed claims | Covered — PASS |

## Historical verification — 2026-09-04

| Gate | Result |
|---|---|
| Feature suite | 185 passed |
| Goal/run/version regressions | 179 passed, 3 upstream deprecation warnings |
| Ruff check | PASS for repository and feature scope |
| Ruff format | PASS for feature scope; six unchanged HEAD files remain outside feature formatting |
| Pyright | 0 errors, 0 warnings, 0 information |
| No-LLM suite | 2444 passed, 4 skipped, 1 unrelated external-catalog count failure |

Read the fresh Test-phase evidence in [`checks/2026-09-04-test.md`](checks/2026-09-04-test.md).

The no-LLM failure is outside this feature: the unchanged feature-073 assertion expects 196 convention sources while the live external `ai-ressources` corpus reports 197. No feature-073 or conventions-AST file was changed.
