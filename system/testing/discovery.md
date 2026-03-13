# Test Discovery

> Sequential procedure to resolve the project's test infrastructure.
> Run during `/spec.init` Phase B, `/spec.plan` Step 7.5, or on first `/spec.implement` if not yet resolved.

---

## 1. Detect language/runtime

| Marker file | Ecosystem |
|---|---|
| `package.json` | JavaScript / TypeScript |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `Package.swift`, `*.xcodeproj` | Swift (iOS / macOS) |
| `build.gradle.kts`, `build.gradle` | Kotlin (Android) |
| `Makefile` with `test` target | Fallback universal |

If multiple ecosystems coexist, check `.specs/stacks/_default.md` for the primary language.

## 2. Detect test runner (by ecosystem)

### JavaScript / TypeScript

| What | How to detect | Resolved command |
|---|---|---|
| Unit / Integration runner | `package.json` → `scripts.test`, `scripts["test:unit"]`, `scripts["test:e2e"]`; `devDependencies`: `vitest`, `jest`, `mocha` | e.g. `npm run test` or `npx vitest run` |
| E2E runner | `devDependencies`: `playwright`, `cypress`; config files: `playwright.config.*`, `cypress.config.*` | e.g. `npx playwright test` |
| Linter | `eslint.config.*` / `.eslintrc.*` → `npx eslint`; `biome.json` → `npx biome check` | e.g. `npx eslint src/` |
| Type checker | `tsconfig.json` → `npx tsc --noEmit` | e.g. `npx tsc --noEmit` |

### Python

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `[tool.pytest]` in `pyproject.toml` or `pytest.ini` → `pytest`; else → `python -m unittest discover` | e.g. `pytest` |
| Linter | `[tool.ruff]` in `pyproject.toml` → `ruff check .`; `.flake8` → `flake8` | e.g. `ruff check .` |
| Type checker | `[tool.mypy]` in `pyproject.toml` → `mypy src/` | e.g. `mypy src/` |

### Go

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `go.mod` exists | `go test ./...` |
| Linter | `.golangci.yml` exists | `golangci-lint run` |
| Type checker | N/A (built into compiler) | — |

### Rust

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `Cargo.toml` exists | `cargo test` |
| Linter | `clippy` (included with rustup) | `cargo clippy -- -D warnings` |
| Formatter | `rustfmt` (included with rustup) | `cargo fmt --check` |
| Type checker | N/A (built into compiler) | — |

### Swift (iOS / macOS)

| What | How to detect | Resolved command |
|---|---|---|
| Test runner | `Package.swift` → Swift Package Manager; `*.xcodeproj` → Xcode | `swift test` or `xcodebuild test -scheme [scheme] -destination 'platform=iOS Simulator,name=iPhone 16'` |
| Linter | `.swiftlint.yml` exists | `swiftlint` |
| Formatter | `.swift-format` config or `swiftformat` in deps | `swift-format lint -r Sources/` |
| Type checker | N/A (built into compiler) | — |

### Kotlin (Android)

| What | How to detect | Resolved command |
|---|---|---|
| Unit test runner | `build.gradle.kts` or `build.gradle` with `testImplementation` | `./gradlew test` |
| Instrumented tests | `androidTestImplementation` in build.gradle | `./gradlew connectedAndroidTest` |
| Linter | `detekt` in gradle plugins or `detekt.yml` | `./gradlew detekt` |
| Formatter | `ktlint` in deps or plugins | `./gradlew ktlintCheck` |
| Type checker | N/A (built into Kotlin compiler) | — |

## 3. Detect visual testing tool

### Web apps with a GUI

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

### Non-web projects or no GUI

- `cypress` in `devDependencies` → Cypress
- No visual tool applicable → visual baselines disabled, log: "Visual testing unavailable — no visual testing tool resolved"

### Mobile apps (iOS / Android)

- **iOS**: screenshot tests via `swift-snapshot-testing` (check `Package.swift` dependencies) or Xcode UI Tests
- **Android**: screenshot tests via `paparazzi` (check `paparazzi` in build.gradle plugins) or Espresso screenshots
- If no mobile screenshot tool detected → visual baselines disabled for mobile

## 4. Verify availability

For each resolved command, verify the binary exists (e.g. `npx vitest --version`, `pytest --version`).
Mark as `Verified` or `Not verified` accordingly.

## 5. Record results

Write the resolved commands into the **Resolved Test Commands** table in:
- `.specs/testing/strategy.md` (persistent, project-level)
- `plan.md` (feature-level, copied from strategy.md or re-resolved)

---

*LiveSpec Test Protocol — Discovery v1.1*
