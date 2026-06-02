---
name: spec-doctor
description: LiveSpec project health command /spec-doctor
---

# /spec-doctor

> **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md) before starting — runtime goal contract (§5), canonical ERROR/BLOCKED format (§2), finalization gate.

## Purpose

`/spec-doctor` and `$spec-doctor` explain and execute the project health audit. The executable CLI is `livespec doctor`; `livespec validate --coherence` remains the lower-level spec validator that doctor orchestrates.

## Usage

```bash
livespec doctor
livespec doctor --format json
livespec doctor --strict
livespec doctor --fix-plan
livespec doctor --apply-cleanup
```

## Steps

### Step 1 — Resolve Project Root

**Prerequisite:** None.

**Required inputs:**
- `.specs/`

**Action:** Run `livespec doctor --format compact`.

**Execution evidence:** Exit code and stdout summary.

**Success criteria:**
- Output starts with `LiveSpec doctor:`.
- Output distinguishes doctor from `livespec validate --coherence`.

**Failure handling:**
- If `.specs/` is missing, emit `BLOCKED at step 1 - prerequisite_unmet - .specs directory missing`.

### Step 2 — Interpret Report

**Prerequisite:** Step 1 produced a doctor report.

**Required inputs:**
- Doctor stdout or JSON report.

**Action:** Classify findings by severity and category.

**Execution evidence:** Finding count and top-level status.

**Success criteria:**
- `OK` means no findings.
- `WARN` means actionable warnings.
- `FAIL` means at least one error or strict warning promotion.

**Failure handling:**
- If JSON parsing fails, emit `ERROR step=2 type=verification_failed retry_count=0 timed_out=false message="doctor report invalid"`.

## Checks

Doctor validates:
- Coherence: includes `livespec validate --coherence` results.
- Implementation maps: stale FR/AC files and missing mapped tests.
- Runners: mapped tests not included by configured runner metadata.
- Hooks: missing LiveSpec commit/push enforcement.
- Lifecycle: deprecated specs without supersession metadata.
- Visual evidence: orphaned baselines or receipts.
- Cleanup: `--fix-plan` is read-only; `--apply-cleanup` refuses destructive evidence deletion.

## Internal Command Invocations

- [suggestion] `/spec-fix <feature>` — displayed when doctor findings point to fixable implementation drift; not executed by this command.
- [suggestion] `/spec-check <feature>` — displayed when a focused spec-code verification is needed; not executed by this command.
