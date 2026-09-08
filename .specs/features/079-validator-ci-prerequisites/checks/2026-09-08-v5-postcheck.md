# V5 post-check — convention corpus fixture isolation

**Result:** PASS for the bounded V5 fixture-isolation patch. Feature 079 remains **In Progress** because exact-SHA GitHub CI and actual private checkout are separate pending evidence.

## Immutable review inputs

- HEAD and PR 35 head: `bb76ca0ea75531e9b4322db9f0a03eb739cce3f9`.
- Tree: `0673ec2fde93c3ad5251369dfb28910826ba25dd`; index and tracked worktree were clean before this check.
- Packet: `/Users/julienm/projects/codex-automation/github-ci-guardian/reports/task-45c889a2/packet-v5.json`, SHA-256 `c768b46cea9a2e303b4b67889f91407ac4a0ed45a9148d5055fb45ec97ad0cd3`.
- Native goal: `969adca81552bb01731fe63dd23d5e58e158880b65df731e2c7e953646d5a447`; contract `/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/livespec-goals/goal-spec-check-969adca8.contract.json`; state `/var/folders/l_/t1s_zytx2fqb0dkzz40d3v7m0000gn/T/livespec-goals/goal-spec-check-969adca8.state.json`.
- Scope diff: 13 files, 352 insertions and 243 deletions from parent `6dd27b73db2225d1f9a5328346ac29f10e2fb9b7`.

## Tree and spec quality

- Required `.specs/` system files and three ADRs exist. Feature directory names are valid; feature `012` is the only sequence warning. No orphan files were found.
- README inventory matches all 81 feature directories. Existing repository debt remains: features 038 and 045 lack `changelog.md`.
- `livespec validate .specs/features/079-validator-ci-prerequisites --format json` passes: five documents score 100 with zero errors or warnings.
- The spec contains five FRs, six ACs, three success criteria, six Gherkin scenarios and one Mermaid flow. All FRs map to ACs and no clarification marker remains.
- The plan contains sequence and state diagrams, a populated constitution check and coverage of FR-001 through FR-005. An ER diagram is not applicable to this change.
- Surface drift is not applicable: no `surfaces.yaml` and no configured or discovered web application surface.

## Patch inspection

- `tests/conventions_corpus_fixture.py` declares exactly 12 synthetic public source paths. Its explicit temporary manifest, CSV and `ai_resources_path` isolate tests from `HOME` and from the full private corpus.
- The six manifest-dependent modules use the temporary corpus while retaining meaningful ARS rule inventory, SQL/CSS/Tailwind families and capabilities, generated/deferred metadata failures, source decisions, hashes and anchors. The generated-catalog test overwrites `HOME` with an empty directory and asserts the exact declared inventory and count.
- Mechanical extraction to `tests/_conventions_source_decisions_serialization.py` preserves the exact 16 collected node IDs: baseline-only `[]`, current-only `[]`.
- `.github/workflows/ci.yml` has no diff. Static inspection finds no Anthropic key, model or generation job. The existing sparse private checkout remains pinned and names only `javascript.md`, `rust.md` and `swift-kotlin.md`, with credentials persistence disabled and cleanup retained.
- The check read only those three private documents through the prepared parity directory. It did not access or publish the full private corpus.

## Requirement coverage

| Requirement | Status | Evidence and boundary |
|---|---|---|
| FR-001 | ✅ Verified | Ruff, format, Pyright and Mypy worker logs pass; negative typing/format assertions remain. |
| FR-002 | ✅ Verified locally | Pinned three-document corpus and `ast-grep 0.44.0`; native receipt certifies AC-002 only. |
| FR-003 | ✅ Verified locally | Current full native capture passes and independent V5 targeted suite passes. Remote CI is outside this result. |
| FR-004 | ✅ Verified | Reread worker visual evidence: 121 tests and 94.41% branch coverage. |
| FR-005 | ⚠️ Partial | Deterministic workflow policy is unchanged and statically valid; exact-SHA GitHub execution remains unobserved. |

| Acceptance criterion | Status | Evidence and boundary |
|---|---|---|
| AC-001 | ✅ Verified locally | Worker static checks pass on the reviewed SHA. |
| AC-002 | ✅ Verified | Native execution receipt is valid with `gaps=[]` and certifies exactly `079-validator-ci-prerequisites:AC-002`. |
| AC-003 | ✅ Verified for current local capture | `3727 passed, 26 skipped`; this is not a global, feature-076 or GitHub CI certification. |
| AC-004 | ✅ Verified from worker evidence | 121 visual tests pass at 94.41% branch coverage. |
| AC-005 | ❌ Missing/Pending | No successful exact-SHA GitHub CI receipt was supplied or observed. |
| AC-006 | ⚠️ Partial | Sparse private checkout and cleanup are present; actual private GitHub access is not proved by local inspection. |

## Test and receipt evidence

- Independent targeted retry: the six changed manifest-dependent modules pass `45 passed in 9.65s` under Python 3.12, with `AIRESOURCES` containing exactly the three expected files and `ast-grep 0.44.0` on `PATH`.
- Corpus SHA-256 values: JavaScript `9ea7336d3b80963a0740aff3e09526e21e79e40809160d75f2bf2e0241e301bd`; Rust `868f663dde00b42671fa478c470ca00b61b1cc11e200c54fe01a12bf89b34d88`; Swift/Kotlin `5a65f11d4f54bac0bfdbd50092cd7b3663b353a2e6d7a26fe8b3f6d47387b74a`.
- Worker logs reread: Ruff `All checks passed`; format `1395 files already formatted`; Pyright `0 errors, 0 warnings`; Mypy `629 source files`; targeted `45 passed`; native capture `3727 passed, 26 skipped`.
- Native receipt `.specs/.execution/83783d1c682146f3826525d50b225737/receipt.json` binds capture SHA-256 `c359e47d849b2d36aac8b28608cfe55cf8e46ba96d0d2de10c1d82ce730d74b3`. Independent verifier output is `valid=True`, `gaps=[]`, 3753 executed tests and the single certified AC listed above.

## Convention Compliance

- Domains checked: `code`; sources read: `general.md`, `python.md`, `javascript.md`, `cli.md`, `stack-commands.md` from the manifest-selected `$AIRESOURCES/code-conventions/` paths.
- The mapped test/support diff follows explicit-path, deterministic-fixture, typing and assertion guidance. Worker convention receipt `20260908T083929Z` is `PASS` with zero blockers.
- Convention gaps: none in the V5 patch. The receipt retains 406 repository-wide advisory violations and five unsupported rules; this check does not hide or promote them to patch failures.

## Gaps and actions

1. Run the unchanged GitHub workflows on exact SHA `bb76ca0...`, then retain the successful required-check receipts to satisfy AC-005.
2. Verify the pinned private checkout actually succeeds in each relevant GitHub job, including `persist-credentials: false` and unconditional cleanup, to close AC-006.
3. Treat feature 076 independently; this report carries no certification for it.

## Observed discrepancies

- Packet V5 still names removed `tests/test_goal_archive_file.py`; invoking that literal path exits 4 before collection. The bounded V5 scope is the six changed convention modules, which independently collect and pass 45 tests.
- A first local run under system Python 3.14 without `AIRESOURCES` produced four AST-catalog failures. A parity retry initially produced setup errors because its historical `TMPDIR` no longer existed. After proving the three exact corpus files, their hashes, `ast-grep 0.44.0`, and a writable runtime temp directory, the materially corrected retry passed 45/45.

## Goal receipt

- Final native state: `complete`, 39/39 tasks, pending 0; mutable state SHA-256 `a2738ac22b601b6b2b28b692d339331ddf7605bffeeb5956b6f9c072bc660577`.
- Contract file SHA-256: `dd88f5748c79248a1aec4b42af7fa00b127f04aa0208215760de7026e03e9b0b` (semantic goal hash remains `969adca81552bb01731fe63dd23d5e58e158880b65df731e2c7e953646d5a447`).
- Successful governed archive: `.specs/.runs/spec-check-2026-09-08T09-21-06.446321-969adca8-policy2.json`, outcome `success`, SHA-256 `c4059814f02f1a5945d96e05e93dea133ef97082b97f932062298f4fdfbbba62`.
- The preceding archive attempt `.specs/.runs/spec-check-2026-09-08T09-20-27.306160-969adca8-policy2.json` correctly recorded `drift` because the transcript omitted the literal `gap report` and `Penflow Contract Verdict` contract markers. The transcript was amended with the existing report path and the truthful non-visual `NOT_APPLICABLE` verdict before the successful archive; the drift artifact is preserved.
