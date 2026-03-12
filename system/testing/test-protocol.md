# Test Protocol

> Centralized testing rules for LiveSpec — stack-agnostic, zero hardcoded commands.
> Referenced by `/spec.implement`, `/spec.plan`, and `/spec.check`.

---

## Section 1 — Test Discovery

Sequential procedure to resolve the project's test infrastructure. Run during `/spec.init` Phase B, `/spec.plan` Step 7.5, or on first `/spec.implement` if not yet resolved.

### 1. Detect language/runtime

| Marker file | Ecosystem |
|---|---|
| `package.json` | JavaScript / TypeScript |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `Makefile` with `test` target | Fallback universal |

If multiple ecosystems coexist, check `.specs/stacks/_default.md` for the primary language.

### 2. Detect test runner (by ecosystem)

#### JavaScript / TypeScript

| What | How to detect | Resolved command |
|---|---|---|
| Unit / Integration runner | `package.json` → `scripts.test`, `scripts["test:unit"]`, `scripts["test:e2e"]`; `devDependencies`: `vitest`, `jest`, `mocha` | e.g. `npm run test` or `npx vitest run` |
| E2E runner | `devDependencies`: `playwright`, `cypress`; config files: `playwright.config.*`, `cypress.config.*` | e.g. `npx playwright test` |
| Linter | `eslint.config.*` / `.eslintrc.*` → `npx eslint`; `biome.json` → `npx biome check` | e.g. `npx eslint src/` |
| Type checker | `tsconfig.json` → `npx tsc --noEmit` | e.g. `npx tsc --noEmit` |

#### Python

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `[tool.pytest]` in `pyproject.toml` or `pytest.ini` → `pytest`; else → `python -m unittest discover` | e.g. `pytest` |
| Linter | `[tool.ruff]` in `pyproject.toml` → `ruff check .`; `.flake8` → `flake8` | e.g. `ruff check .` |
| Type checker | `[tool.mypy]` in `pyproject.toml` → `mypy src/` | e.g. `mypy src/` |

#### Go

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `go.mod` exists | `go test ./...` |
| Linter | `.golangci.yml` exists | `golangci-lint run` |
| Type checker | N/A (built into compiler) | — |

### 3. Detect visual testing tool

#### Web apps with a GUI

If the project has a graphical interface (frontend, full-stack web app), visual testing requires Playwright CLI.

**Detection sequence (run once, during discovery):**

1. Run `playwright-cli --help`
2. If the command succeeds → Playwright CLI is installed, resolve visual commands via `playwright-cli`
3. If the command fails → **propose installation to the user:**

```
Visual testing requires Playwright CLI, which is not installed.

Install command:
  npm install -g @playwright/cli@latest

Then install browser engines:
  playwright-cli install --with-deps

Run these commands and re-run discovery.
```

4. If the user declines → mark visual tests as `Not available` in Resolved Test Commands, log: "Visual testing unavailable — Playwright CLI not installed"

This check is done **once** during discovery. The result is recorded in the Resolved Test Commands table. All subsequent phases (implement, check) use that recorded status — no re-detection.

#### Non-web projects or no GUI

- `cypress` in `devDependencies` → Cypress
- No visual tool applicable → visual baselines disabled, log: "Visual testing unavailable — no visual testing tool resolved"

### 4. Verify availability

For each resolved command, verify the binary exists (e.g. `npx vitest --version`, `pytest --version`).
Mark as `Verified` or `Not verified` accordingly.

### 5. Record results

Write the resolved commands into the **Resolved Test Commands** table in:
- `.specs/testing/strategy.md` (persistent, project-level)
- `plan.md` (feature-level, copied from strategy.md or re-resolved)

---

## Section 2 — When to Test

Stack-agnostic rules — applies to all ecosystems:

- **After each implementation step:** run tests targeting the layer just implemented
- **Transverse checks:** lint + type checker on touched files after each step
- **Before declaring a step Done:** the Step Gate in `implement.md` requires tests to pass
- **Before declaring the feature complete:** full suite (unit + integration + E2E if applicable)

All commands come from the **Resolved Test Commands** table. Never hardcode commands.

---

## Section 3 — Iteration Limits

| Test type | Max iterations | If limit reached |
|---|---|---|
| Unit tests | 3 | Stop, report with context, ask human |
| Integration tests | 3 | Stop, report with context, ask human |
| E2E tests | 5 | Stop, report with diffs, ask human |
| Visual tests | 5 | Stop, report diff images, ask human |
| Static analysis (lint/types) | 3 | Stop, show errors, ask human |

---

## Section 4 — On Test Failure

1. Read the error message carefully
2. Check if the spec/AC covers this case
3. Fix the issue and re-test
4. If iteration limit reached → use the error reporting format below

---

## Section 5 — Error Reporting Format

When max iterations are exceeded, report using this structure:

> **Max iterations reached for [test type]**
>
> **Feature:** NNN-feature-name
> **Step:** [current phase/step]
> **Test:** `[test file:line]`
>
> **Failing test:** `"[test description]"`
>
> **Error:**
> ```
> [exact error output]
> ```
>
> **What I tried:**
> 1. Iteration 1: [description]
> 2. Iteration 2: [description]
> 3. Iteration N: [description]
>
> **Likely cause:** [analysis]
>
> **Suggested fix:** [actionable suggestion]
>
> **Action needed:** Please review and fix, then run `/spec.implement [feature] --resume`

---

## Section 6 — Visual Baselines Protocol

Universal workflow — not tied to any specific tool.

### Capture

On first successful run, capture screenshots of key states:
- Empty state
- Loaded state with data
- Interactive states (hover, open, etc.)
- Error states

### Storage

Baselines are stored in `.specs/features/NNN-feature-name/baselines/`.

### Comparison

On each subsequent run, capture new screenshots and compare against stored baselines.

### Threshold

Diff > 2% → test FAILS.

### Update

When a change is intentional, update the baselines and commit them.

### Archival

Old baselines are moved to `baselines/archived/YYYY-MM-DD/` before replacement.

### Systematic capture

Every passing visual test saves its screenshot as the new reference baseline, enabling regression detection on the next run.

### Prerequisite check

The visual tool availability is resolved **once** during discovery (Section 1, step 3) and recorded in Resolved Test Commands.

- If status is `Verified` → proceed with visual tests
- If status is `Not available` → skip visual tests, no re-detection needed
- Log when skipped: "Visual baselines skipped — no visual testing tool resolved"

The exact capture/compare command comes from the **Resolved Test Commands** in `plan.md`.

---

## Section 7 — Final Validation

Before declaring implementation complete, execute in order:

1. Type checker (if applicable)
2. Linter
3. Full test suite (unit + integration)
4. E2E suite (if applicable)
5. Visual tests (if applicable and tool available)

All commands come from `plan.md` **Resolved Test Commands**. No hardcoded commands.

---

*LiveSpec Test Protocol v1.0*
