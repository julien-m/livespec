# V5 Post-check — Feature 076 Spec Init Goal Bootstrap

## Verdict

**PASS — bounded V5 archive-descriptor correction.** The reviewed patch keeps the invocation-owned temporary descriptor live through publication and cleanup, closes it exactly once on success and all six injected failure stages, preserves the historical foreign-replacement assertions, and introduces no observed code-convention gap.

This verdict certifies only the V5 change slice and the acceptance scope proven by the current native receipt. It does not certify the full Feature 076, Feature 079, a merge to `main`, or post-merge CI.

## Immutable review identity

| Evidence | Observed value |
|---|---|
| HEAD | `f9340080ee8c61dcdbf946e10d3d7a30972e7110` |
| Tree | `6e467c5e87c0dd1fbb305a3407011140fcfbdeba` |
| Remote branch | `origin/codex/ci-guardian/2026-09-07-task-45c889a2` at the same HEAD |
| Pull request | PR 35, open draft, merge state `CLEAN`, head at the same HEAD |
| Guardian packet | `/Users/julienm/projects/codex-automation/github-ci-guardian/reports/task-45c889a2/packet-v5.json`, SHA-256 `c768b46cea9a2e303b4b67889f91407ac4a0ed45a9148d5055fb45ec97ad0cd3` |
| Goal | `df17604e48bc3fb6b505624f81416da734a60745b6b3364e6c582059216994a8` (`spec-check`, `gpt-6-astra`) |

## Tree validation

| Check | Status | Evidence |
|---|---|---|
| Required system files | PASS | 7/7 present; 3 ADRs |
| Feature naming | PASS | 81/81 directories match the canonical pattern |
| Feature 076 completeness | PASS | `spec.md`, `plan.md`, `implementation.md`, `progress.md`, `pipeline.md`, and `changelog.md` present |
| Orphans | PASS | No direct orphan under `.specs/features/` |
| README sync | PASS | 81 feature IDs on disk and 81 in the registry; no mismatch |
| Surfaces | NOT CONFIGURED | `.specs/surfaces.yaml` absent; no app/package web marker found |
| Feature structural validation | PASS | 6 files, 0 errors, 0 warnings; every file scores 100 |
| Repository structural validation | OUTSIDE PATCH SCOPE | 438 files; 8 errors in 5 files under Features 074/078, plus missing changelogs in Features 038/045 found by the completeness scan |

The repository-level findings predate and do not touch the reviewed Feature 076 commit. They remain separate follow-up work.

## Spec quality

| Gate | Status | Evidence |
|---|---|---|
| Stories and behavioral diagrams | PASS | 3 stories, 3 Gherkin blocks, 3 Mermaid blocks |
| Acceptance criteria | PASS | 10 canonical `AC-NNN` headings; diff review found formatting normalization without a requirement-wording change |
| Functional and success criteria | PASS | 12 FR, each with AC mapping; 5 SC |
| Plan coverage | PASS | Feature validator score 100; V5 plan explicitly maps FR-005, AC-006, and AC-008 to the descriptor lifecycle and race tests |
| Clarification markers | PASS | No unresolved marker in current feature artifacts |

## Patch verification

| Contract | Status | Evidence |
|---|---|---|
| Ownership transfer | PASS | `OwnedTemporary(descriptor, identity)` returns both the open FD and pinned inode identity |
| Stream ownership | PASS | `os.fdopen(..., closefd=False)` prevents stream exit from closing the invocation-owned FD |
| Publication lifetime | PASS | Publication receives `temporary.identity` while the descriptor remains open |
| Cleanup lifetime | PASS | Residue cleanup runs before the outer descriptor close |
| Single final close | PASS | Nested `finally` closes the temporary once, then closes directory/lock descriptors on success and every handled failure |
| Wrapper compatibility | PASS | Race/publication wrappers now return `OwnedTemporary`; behavior and foreign-replacement assertions remain unchanged |
| Convention compliance | PASS | Python typing, names, public ownership documentation, order rationale, error propagation, and real-filesystem tests comply with the loaded `code` bundle |

## Functional requirements

| FR | Status | Bounded post-check evidence |
|---|---|---|
| FR-001 | Not re-certified | Unchanged implementation map retained |
| FR-002 | Not re-certified | Unchanged implementation map retained |
| FR-003 | Not re-certified | Unchanged implementation map retained |
| FR-004 | Not re-certified | Unchanged implementation map retained |
| FR-005 | Verified for V5 slice | Owned descriptor remains live through atomic publication and cleanup |
| FR-006 | Not re-certified | Unchanged implementation map retained |
| FR-007 | Not re-certified | Unchanged implementation map retained |
| FR-008 | Fresh regression signal | 21 targeted tests pass; current acceptance receipt does not certify this FR independently |
| FR-009 | Not re-certified | Unchanged implementation map retained |
| FR-010 | Not re-certified | Unchanged implementation map retained |
| FR-011 | Not re-certified | Unchanged implementation map retained |
| FR-012 | Not re-certified | Unchanged implementation map retained |

## Acceptance criteria

| AC | Status | Evidence boundary |
|---|---|---|
| AC-001 | Not re-certified | Existing mapping only |
| AC-002 | Not re-certified | Existing mapping only |
| AC-003 | Not re-certified | Existing mapping only |
| AC-004 | Not re-certified | Existing mapping only |
| AC-005 | Not re-certified | Existing mapping only |
| AC-006 | Verified and certified | 98 reviewed bindings across 21 tests; native policy-2 receipt certifies this AC only |
| AC-007 | Not re-certified | Existing mapping only |
| AC-008 | Fresh regression signal | 21 targeted tests pass; absent from the current certified-AC set |
| AC-009 | Not re-certified | Existing mapping only |
| AC-010 | Not re-certified | Existing mapping only |

## Independent execution evidence

| Evidence | Result |
|---|---|
| Fresh targeted parity run | 21 passed in 0.45 s using the Python 3.12 Guardian venv, a dedicated existing mode-700 `TMPDIR`, and the three-document parity corpus root |
| Mapping review | SHA-256 `9490790d8f1110815d073c0c5ba54989e7bfce7033080897054caa42100c405b`; complete/ready, 36 reviewed sections, 98 bindings, 21 unique tests, no finding/ambiguity/extra scope, AC-006 only |
| Native execution receipt | SHA-256 `4e2c1237365be763c6093ef91ba0adf7d81a3eeb9b9c8dd7116527157e032aab`; fresh verification `valid=true`, `gaps=[]`, 3734 passed, 26 skipped, certified AC set exactly `076-spec-init-goal-bootstrap:AC-006` |
| Static checks | Worker evidence records Ruff check, Ruff format, Pyright, and mypy PASS; remote PR checks observed SUCCESS on the exact reviewed head |
| Remote checks | Unit Tests, Integration 3A, CodeQL, and five visual matrix jobs observed `SUCCESS` on PR 35 |

## Convention Compliance

| Domain | Files | Status | Evidence |
|---|---|---|---|
| `code` | `validator/goal_archive_file.py`, `validator/goal_archive_fd.py` | PASS | Typed ownership object, documented side effects, explicit close ownership, justified order-dependent cleanup |
| `code` | `tests/test_goal_archive_file.py`, race/publication wrappers | PASS | Descriptive pytest cases, real descriptor probes, close-count and `EBADF` assertions, preserved foreign replacement checks |

Loaded sources: `$AIRESOURCES/code-conventions/general.md`, `python.md`, `javascript.md`, `cli.md`, and `stack-commands.md`.

## Findings and suggested fixes

No finding requires a V5 patch change. No `implementation.md` update is requested because its V5 checkpoint already states the bounded evidence and pending independent post-check accurately.

The unrelated repository structural findings in Features 038, 045, 074, and 078 should be handled in their own authorized scope. They do not alter this bounded PASS.

## Limits

- Native acceptance certification is AC-006 only, despite the broader passing suite.
- The run does not certify the full Feature 076 or Feature 079.
- PR 35 is still an open draft; no merge or `main` ancestry is claimed.
- Remote checks were observed green on the exact head; this report does not establish a later stability window or post-merge result.
