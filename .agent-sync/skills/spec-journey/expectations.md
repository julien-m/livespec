---
command: spec-journey
contract_version: "1.0"
last_reviewed: 2026-06-07
---

# Expectations — $spec-journey

## 1. Purpose

Create, edit, bootstrap, impact-check, list, inspect, compile, and run global User Journeys v2.

## 2. Preconditions

- `.specs/` exists.
- Journey creation/editing has enough project evidence to infer or confirm qualified refs.

## 3. Observable Signals

**stdout must_contain:**
- "journey"
- "OK"

**stdout must_not_contain:**
- "Traceback"

**stderr:**
- "_(none expected on happy path)_"

## 4. Filesystem Effects

**create:**
- `.specs/journeys/<journey-id>/journey.yaml`
- `.specs/journeys/<journey-id>/changelog.md`
- `.specs/journeys/<journey-id>/decisions/*.md`
- `.specs/journeys/<journey-id>/compiled/manifest.json`

**update:**
- `.specs/features/<feature>/journeys.md`

**optional:**
- `.specs/journeys/<journey-id>/compiled/visual-contracts/*.json`
- `.specs/journeys/<journey-id>/runs/`

**forbidden:**
- `src/`

## 5. Git Effects

**expected dirty paths:**
- `.specs/journeys/`
- `.specs/features/*/journeys.md`

**forbidden changes:**
- _(none)_

**commit expectations:**
- _(none)_

## 6. Produced Artifacts

- v2 journey YAML source.
- decision and changelog evidence.
- compiled manifest and native artifact paths.

## 7. Exit Codes

| Code | Meaning | Operator action |
|------|---------|-----------------|
| 0 | success | nothing |
| 1 | validation or stale compiled artifact failed | inspect output and fix journey |
| 2 | blocked precondition | restore missing `.specs/` or evidence |

## 8. Outcome Matrix

- **success:** journey validates, compiles on create/edit, and run uses compiled artifacts.
- **drift:** impacted old journey requires `$spec-journey edit <journey-id>`.
- **blocked:** missing refs, privacy denial, stale manifest, or unsupported runner capability.
- **error:** command itself crashed.

## 9. Runtime Profile

- Typical range: 5-300 seconds.
- Factors: bootstrap scan size, native compile target, runner availability.

## 10. Post-run Checks

- [ ] `livespec journey validate` exits 0.
- [ ] `livespec journey compile` ran only for create/edit.
- [ ] `livespec journey run` did not compile and did not rewrite generated artifacts.

## 11. Troubleshooting

- **Symptom:** `journey_compiled_stale`
  **Cause:** `journey.yaml` changed after the last compile.
  **Fix:** run `$spec-journey edit <journey-id>` or `livespec journey compile --journey <journey-id>`.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "journey"
  may:
    - contains: "compiled"
    - contains: "manifest"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### 13.1 Live Console Output

```
$ $spec-journey create
> Journey candidate: onboarding-first-project
> journey validate OK
```

### 13.2 Files Produced

```
.specs/journeys/onboarding-first-project/journey.yaml
.specs/journeys/onboarding-first-project/changelog.md
.specs/journeys/onboarding-first-project/compiled/manifest.json
```

### 13.3 Aligned / Drift / Missing

```
aligned: qualified feature refs and backlinks exist
drift: stale compiled manifest blocks run
missing: decision/changelog required for old journey edits
```

### 13.4 Runtime Profile

```
create: validates, compiles, and smoke-runs once
run: compiled-only and deterministic
impact: scans changed files against old journeys
```

### 13.5 Edge Cases

```
implemented feature: allowed without $spec-refine
LLM visual check: requires privacy.llm_allowed
pytest/cargo UI journey: blocked as unsupported
```

### 13.6 Post-run Actions

```
inspect manifest when run fails stale
edit journey with classification for intentional product changes
rerun validate and run after compile
```
