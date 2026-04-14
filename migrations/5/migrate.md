---
version: 5
description: "Add baseline provenance manifests for existing baselines (Visual Testing Governance)"
date: 2026-04-14
---

<!-- @spec FR-008: migration v5 manifest — .specs/features/004-visual-testing-governance/spec.md#fr-008 -->

# Migration v5: Visual Testing Governance

Generates `baseline.manifest.yml` stubs for existing baseline PNGs that pre-date governance tracking.

Without this migration, baselines captured before v5 have no provenance record. The stub manifest makes the gap explicit (`approved_by: "pre-v5 (untracked)"`) rather than silently missing.

After migration completes:
1. Review the generated stubs in each feature's `baselines/` directory
2. Run `spec.test --reset-baselines` on each feature to replace stubs with real provenance
3. Human approval will be required — stubs are not considered verified

## Idempotency Check

Before running any action:

```
IF .livespec-version file contains "5" or greater:
  REPORT: "Already at v5 — no changes needed"
  EXIT (no further actions)
```

## Actions

### GENERATE_STUB

Scan all feature directories for baselines without a manifest:

```
FOR each directory matching .specs/features/*/baselines/:
  IF baseline.manifest.yml does NOT exist in that directory:
    AND at least one *.png file exists:
      COLLECT list of PNG filenames (without .png extension) → these are the screen names
      WRITE baseline.manifest.yml to that directory with stub content (see template below)
      LOG: "Generated stub manifest for <feature-name> (<N> screens)"
  ELSE:
    LOG: "Skipping <feature-name> — manifest already exists"
```

**Stub manifest template:**

```yaml
schema_version: "1"
feature: "<feature-directory-name>"
generated_at: "<current-ISO-8601-timestamp>"
screens:
  - screen: "<screen-name>"
    capture_date: null
    approved_by: "pre-v5 (untracked)"
    browser_version: "unknown"
    os: "unknown"
    mockup_version: "none"
    docker_image: "none"
  # ... one entry per PNG file found in baselines/
```

**Notes on stub values:**
- `capture_date: null` — unknown; the PNG predates provenance tracking
- `approved_by: "pre-v5 (untracked)"` — explicitly marks the ambiguity (see schema approved-by values)
- `browser_version: "unknown"` — tells spec.check to skip browser version staleness check for this screen
- `mockup_version: "none"` — tells spec.check to skip mockup hash check for this screen

**Edge case: no baselines found anywhere:**

```
IF no feature has a baselines/ directory with PNG files:
  REPORT: "No baselines found — nothing to migrate."
  EXIT
```

### SET_VERSION 5

```
WRITE "5" to .livespec-version
LOG: "Updated .livespec-version to 5"
```

## Migration Report

After all actions complete, display:

```
Migration v5 complete.

Stub manifests generated:
  - .specs/features/003-visual-testing-fidelity/baselines/baseline.manifest.yml (2 screens)
  - .specs/features/001-user-auth/baselines/baseline.manifest.yml (4 screens)

Files not modified:
  - .specs/features/004-visual-testing-governance/baselines/ — manifest already exists
  - .specs/features/002-layer-3-cli-surface/ — no baselines found

Next steps:
  1. Review the generated stub manifests
  2. Run spec.test --reset-baselines on each feature to capture real provenance
  3. Approve the new baselines with the human approval gate

Note: Stub baselines are treated as NO-MANIFEST by spec.check staleness detection
until replaced by real captures.
```

If no files were generated:

```
Migration v5 complete — no changes needed.
All baselines already have provenance manifests (or no baselines exist).
```

## Staleness Behavior After Migration

Stub manifests use `"unknown"` for `browser_version` and `"none"` for `mockup_version`.

`spec.check` staleness gate behavior with stubs:
- `browser_version: "unknown"` → browser check skipped for this screen (not marked STALE-BROWSER)
- `mockup_version: "none"` → mockup hash check skipped (not marked STALE-MOCKUP)
- `approved_by: "pre-v5 (untracked)"` → WARNING displayed in `--show-provenance` output

This means stubs produce a WARNING in `--show-provenance` but do NOT trigger STALE classification — allowing existing tests to continue running after migration without forcing an immediate reset.

## Edge Cases

- **`baseline.manifest.yml` already exists:** Skip (idempotent per-feature). Never overwrite existing manifests.
- **`baselines/` directory is empty (no PNGs):** Skip — nothing to stub.
- **PNG filename with spaces:** Encode the screen name exactly as-is (space → space). The manifest schema allows any string for `screen`.
- **Multiple PNGs with same name in different case:** Generate one entry per unique lowercase name, log a warning about case collision.
