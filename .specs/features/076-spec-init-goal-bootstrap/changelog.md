# Changelog: Spec Init Goal Bootstrap (076)

## 2026-09-08 — Check: V5 descriptor ownership correction independently verified

- Read [the V5 post-check](checks/2026-09-08-v5-postcheck.md): `OwnedTemporary` keeps the temporary FD live through publication and cleanup, then closes it exactly once on success and six injected failure stages.
- Fresh parity evidence is 21/21 targeted tests; the native policy-2 receipt is valid with 3734 passed, 26 skipped, no gaps, and certification bounded to AC-006.
- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None by this check
- **Coverage:** Bounded V5 patch PASS; full Feature 076, Feature 079, merge, and `main` remain outside this verdict
- **Author:** Codex

## 2026-09-08 — Check: Linux temporary ownership gap confirmed

- Read [the V5 independent check](checks/2026-09-08-v5-precheck.md): the temporary writer closes its descriptor before publication, so Linux unlink/recreate can reuse `(st_dev, st_ino)` and impersonate owned residue.
- FR-005 and AC-006/AC-008 remain partial until an `OwnedTemporary(descriptor, identity)` stays open through publication and cleanup, closes in `finally`, and the causal race/lifecycle tests pass.
- Author: Codex.

## 2026-09-04 — [Implement]: Initial bootstrap implementation completed

- Added canonical fresh-root rendering, fail-closed proof, contained archive, and strict non-init compatibility.

<!-- finalize:spec-implement:2026-09-04:a98e152e -->

## 2026-09-04 — [Plan Update]: Map bootstrap success criteria to execution gates

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None (plan.md updated)
- **AC impacted:** None (pre-implementation)
- **Author:** Codex

## 2026-09-04 — [Plan]: Technical plan generated

- Defined six implementation steps, three behavioral diagrams, and SC-to-gate mappings.

<!-- finalize:spec-plan:2026-09-04:89422724 -->

## 2026-09-04 — [Plan]: Approved plan finalized

- Finalized the approved six-step implementation and quality-gate sequence.

<!-- finalize:spec-plan:2026-09-04:28e16cfb -->

## 2026-09-04 — [Spec Update]: Close independent review blockers

- Made `.specs/.runs` creation and real-path confinement explicit.
- Defined atomic pairing/status rows, external evidence boundaries, and proof transitions.
- **AC impacted:** AC-004, AC-005, AC-008, AC-009, AC-010

## 2026-09-04 — [Spec]: Feature specification created

- Defined three stories, ten acceptance criteria, and twelve functional requirements.

<!-- finalize:spec-specify:2026-09-04:14b0e052 -->

## 2026-09-04 — [Implement]: Spec Init Goal Bootstrap implemented after independent review

- Added exact-command fresh-root selection and canonical root hashing.
- Added complete schema pairing, confined evidence, and dirfd-confined archival.
- Added 158 feature cases and preserved 172 goal/run/version regressions.

<!-- finalize:spec-implement:2026-09-04:9e1ef40b -->

### 2026-09-04 — Test: AC coverage validated

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** `tests/test_goal_bootstrap_pairing.py`, `tests/test_goal_bootstrap_prove.py`, `tests/test_goal_bootstrap_render.py`
- **Coverage:** 10/10 AC covered (100%), 11 generated, all 11 passing
- **Report:** `checks/2026-09-04-test.md`
- **Repository signal:** One external catalog-count regression and six non-feature format files remain separated from the Feature 076 PASS verdict.
- **Author:** Codex

<!-- finalize:spec-test:2026-09-04:24b126d1 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed the `.specs` pre-mkdir swap with pinned directory descriptors and descriptor-relative atomic writes.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 170 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:5d267080 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through atomic rename.
- Added explicit temporary ownership and post-mkdir reopen cleanup without deleting concurrent files.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 175 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:ac9f0e2b -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through atomic rename.
- Added explicit temporary ownership and post-mkdir reopen cleanup without deleting concurrent files.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 177 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:b5339c37 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through atomic rename.
- Added explicit temporary ownership and post-mkdir reopen cleanup without deleting concurrent files.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 180 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:9637faa2 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added created-directory identity binding, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 182 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:128dece7 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added a pinned `.specs` advisory lock, safe `.runs` residue policy, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort artifact cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 183 feature tests, 172 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:c7b5977d -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added a pinned `.specs` advisory lock, safe `.runs` residue policy, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort artifact cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Passed 185 feature tests, 177 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:9398704c -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added a pinned `.specs` advisory lock, safe `.runs` residue policy, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort artifact cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Restored historical non-init unknown-task compatibility and documented the cooperative publication boundary.
- Passed 185 feature tests, 177 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:43831902 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added a pinned `.specs` advisory lock, safe `.runs` residue policy, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort artifact cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Restored historical non-init unknown-task compatibility and documented the cooperative publication boundary.
- Passed 185 feature tests, 179 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:1faecba9 -->

### 2026-09-04 — Test: Final audit remediation verified

- Closed pre-mkdir, real-directory, and contained-symlink swaps with one descriptor scope retained through final publication.
- Added a pinned `.specs` advisory lock, safe `.runs` residue policy, invocation-unique temporary ownership, exclusive final publication, and identity-aware best-effort artifact cleanup.
- Replaced new dynamic business shapes with closed JSON types and bounded support modules.
- Restored historical non-init unknown-task compatibility and documented the cooperative publication boundary.
- Passed 185 feature tests, 179 regressions, Ruff, feature format, Pyright, and 6/6 feature validation artifacts.
- Kept the Feature PASS verdict separate from the repository's external catalog-count and six non-feature format follow-ups.

<!-- finalize:spec-test:2026-09-04:79b41969 -->

### 2026-09-08 — ## 2026-09-08 — Fix: V5 archive temporary ownership verified

- **Type:** Bug Fix
- **Spec modified:** Acceptance-heading formatting only; requirement wording unchanged.
- **Code modified:** Inspect [the temporary writer](../../../validator/goal_archive_file.py), [the archive coordinator](../../../validator/goal_archive_fd.py), and [the lifecycle tests](../../../tests/test_goal_archive_file.py); existing race/publication assertions remain intact.
- **Gaps closed:** Selected FR-005 descriptor lifetime defect; native acceptance proof limited to AC-006. AC-008 has passing regression evidence without a separate native certificate.
- **Verification:** Read [the independent post-check](checks/2026-09-08-v5-postcheck.md): 21 targeted tests, static checks and conventions pass; native unit evidence is 3734 passed and 26 skipped. Closure preserves or refreshes this proof on the final governed document identity.
- **Remaining:** No selected V5 source correction; full-feature certification, final CI stability and main delivery remain separate gates.
- **Author:** spec-fix

<!-- finalize:spec-fix:2026-09-08:2d0a611e -->
