---
schema_version: "1"
created: 2026-04-14
---

<!-- @spec FR-007: baseline manifest schema definition — .specs/features/004-visual-testing-governance/spec.md#fr-007 -->

# Schema: baseline.manifest.yml

Provenance manifest written by `spec-test` after every baseline approval (human or auto).
Stored at `baselines/baseline.manifest.yml` alongside the PNG baselines.

---

## Purpose

Without provenance metadata, a baseline is just a PNG with no context. This manifest records:
- **Who** approved it (human username or "auto (spec-ship)")
- **When** it was captured
- **Which browser** rendered it (Playwright + browser tag)
- **Which OS** it ran on
- **Which mockup version** it was compared against (SHA-256 hash)
- **Which Docker image** was used (or "none" for local captures)

---

## Schema Definition

```yaml
schema_version: "1"                    # String, required. Increment when fields change.
feature: "NNN-feature-name"            # String, required. Feature directory name.
generated_at: "2026-04-14T10:30:00Z"  # ISO 8601 UTC, required. When the manifest was written.
screens:                               # List, required. One entry per captured baseline.
  - screen: "logo"                     # String, required. Matches PNG filename (without .png).
    capture_date: "2026-04-14T10:28:00Z"  # ISO 8601 UTC, required.
    approved_by: "julienm"             # String, required. See Approved-by values below.
    browser_version: "chromium/1.44"   # String, required. Format: "<browser>/<version>".
    os: "Linux 6.1"                    # String, required. OS name + version.
    mockup_path: ".specs/design/screens/003-visual-testing-fidelity/logo.png" # String, optional. Required when `screen` is not the mockup filename.
    mockup_version: "sha256:abc123..."  # String, required. SHA-256 of mockup PNG at capture. "none" if no mockup.
    docker_image: "mcr.microsoft.com/playwright:v1.44.0-jammy"  # String, required. "none" if local capture.
```

---

## Field Definitions

| Field | Level | Type | Required | Description |
|-------|-------|------|----------|-------------|
| `schema_version` | Top | String | Yes | Schema version — always `"1"` for now |
| `feature` | Top | String | Yes | Feature directory name (e.g., `"003-visual-testing-fidelity"`) |
| `generated_at` | Top | ISO 8601 UTC | Yes | Timestamp when the manifest file was written |
| `screens` | Top | List | Yes | One entry per captured PNG baseline |
| `screen` | Screen | String | Yes | Screen identifier — matches PNG filename without `.png` |
| `capture_date` | Screen | ISO 8601 UTC | Yes | Timestamp when Playwright captured this specific PNG |
| `approved_by` | Screen | String | Yes | Who approved this baseline |
| `browser_version` | Screen | String | Yes | Playwright browser tag — format `"<browser>/<version>"` |
| `os` | Screen | String | Yes | OS where Playwright ran — from `platform.system()` + version |
| `mockup_path` | Screen | String | No | Canonical mockup PNG path, relative to project root. Required when `screen` names a runtime state rather than the mockup filename. |
| `mockup_version` | Screen | String | Yes | `sha256:<hex>` hash of the mockup PNG at capture time. `"none"` if no mockup exists for this screen. |
| `docker_image` | Screen | String | Yes | Full Docker image reference used for capture. `"none"` if Playwright ran outside Docker. |

---

## Approved-by Values

| Value | Meaning |
|-------|---------|
| `"<git-username>"` | Human approval — `git config user.name` at approval time |
| `"auto (spec-ship)"` | Auto-approved by `spec-ship` pipeline (all diffs ≤ 5%) |
| `"auto (spec-feature)"` | Auto-approved by `spec-feature` pipeline |
| `"pre-v5 (untracked)"` | Migration v5 stub — baseline existed before provenance was introduced |

---

## mockup_version Format

```
sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

- SHA-256 of the mockup PNG binary content at the moment of capture
- Used by `spec-check` / `visual-gate validate` to detect when a mockup has changed since the baseline was captured
- Resolved from `mockup_path` when present; otherwise from `.specs/design/screens/<feature>/<screen>.png`
- `"none"` only for migrated non-visual stubs; visual features must provide a resolvable mockup PNG

---

## browser_version Format

```
chromium/1.44
firefox/1.44
webkit/1.44
```

- First component: browser name (lowercase)
- Second component: Playwright version tag
- Derived from `playwright --version` output: `Version 1.44.0` → tag `1.44`
- Used by `spec-check` to detect when Playwright has been upgraded since capture

---

## Example: Full Manifest

```yaml
schema_version: "1"
feature: "003-visual-testing-fidelity"
generated_at: "2026-04-14T10:30:00Z"
screens:
  - screen: "logo"
    capture_date: "2026-04-14T10:28:00Z"
    approved_by: "julienm"
    browser_version: "chromium/1.44"
    os: "Linux 6.1"
    mockup_path: ".specs/design/screens/003-visual-testing-fidelity/logo.png"
    mockup_version: "sha256:e3b0c44298fc1c149afbf4c8996fb924abc123def456"
    docker_image: "mcr.microsoft.com/playwright:v1.44.0-jammy"
  - screen: "dashboard"
    capture_date: "2026-04-14T10:29:00Z"
    approved_by: "julienm"
    browser_version: "chromium/1.44"
    os: "Linux 6.1"
    mockup_path: ".specs/design/screens/003-visual-testing-fidelity/dashboard.png"
    mockup_version: "sha256:abc987def654..."
    docker_image: "mcr.microsoft.com/playwright:v1.44.0-jammy"
```

---

## Example: Migration v5 Stub

```yaml
schema_version: "1"
feature: "001-user-auth"
generated_at: "2026-04-15T08:00:00Z"
screens:
  - screen: "login"
    capture_date: null
    approved_by: "pre-v5 (untracked)"
    browser_version: "unknown"
    os: "unknown"
    mockup_version: "none"
    docker_image: "none"
```

---

## Validation Rules

1. `schema_version` must be `"1"` (current only version)
2. `feature` must match the directory name in `features/`
3. `generated_at` and `capture_date` must be valid ISO 8601 strings (or `null` for stubs)
4. `approved_by` must be a non-empty string
5. `browser_version` must match pattern `<browser>/<version>` or be `"unknown"`
6. If `mockup_path` is present, it must resolve under the project root
7. If `mockup_path` is absent, `.specs/design/screens/<feature>/<screen>.png` must exist for visual features
8. `mockup_version` must start with `"sha256:"` or be `"none"`
9. For visual features, `mockup_version` must equal the SHA-256 of the resolved mockup PNG
10. Each `screen` value must be unique within a manifest (no duplicate entries)

---

## Error Handling

If `baseline.manifest.yml` exists but is **unparseable YAML**: treat as missing manifest.
- Emit WARNING: "baseline.manifest.yml is corrupted — treating as missing. Re-run spec-test --reset-baselines."
- Do NOT crash `spec-check`.

If `baseline.manifest.yml` has **missing required fields**: treat as a stub (pre-v5 format).
- Fields default to `"unknown"` for version checks, `"none"` for hash checks.

---

*LiveSpec Schema v1 — generated 2026-04-14*
