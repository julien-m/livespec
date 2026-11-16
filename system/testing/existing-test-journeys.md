# Reference existing tests from journeys

A reference journey links existing suite coverage to feature AC/FR without copying its test code, assertions, setup or fixtures. Read [the journey reference](user-journeys.md) for common coverage, policy, privacy and history rules; generated journeys continue to use their existing compilation workflow.

## Declare a reference

Create `.specs/journeys/<id>/journey.yaml` with `schema_version: 2` and the usual title/status/covers/policy/privacy fields. Add exactly one target using `playwright`, `vitest` or `pytest`, plus an `existing_test` mapping. Omit `steps` or use `steps: []`; do not add portable preconditions or visual contracts. The existing suite and its configuration own those behaviors.

```yaml
schema_version: 2
id: existing-onboarding
title: Existing onboarding suite
status: active
description: Link the original onboarding tests to their current requirements.
covers:
  - feature: 001-onboarding
    kind: ac
    ref: AC-001
    reason: The existing suite checks the declared onboarding behavior.
run_policy: { local: always, pre_push: smoke, ci: always }
targets:
  - surface: web
    runner: playwright
existing_test:
  path: tests/onboarding.spec.ts
  config: playwright.config.ts
  test_name: creates a first project
  evidence_level: browser suite with its existing mocked services
privacy: { llm_allowed: false, retention: none }
```

Replace the illustrative IDs, paths and selector with existing consumer files and real requirement references. `path` is required; `config` and `test_name` are optional. Both file paths are project-relative, must resolve to real files inside the selected project and cannot escape via symlinks. `evidence_level` is a required nonblank declaration of what this suite can prove. The selector is native runner syntax, not a shell expression.

A file reference runs its selected native tests; omit `test_name` to run the file according to that runner's discovery rules. A reference has one target; separate journeys may reference the same suite with distinct coverage links.

## Inspect and run

Use the CLI from the consumer project root:

```bash
livespec journey validate --journey existing-onboarding --json
livespec journey inspect existing-onboarding --json
livespec journey impact --changed-file tests/onboarding.spec.ts --json
livespec journey run --journey existing-onboarding --dry-run --json
livespec journey run --journey existing-onboarding --json
```

`list` and `inspect` expose the existing reference beside coverage. `impact` matches changes to the referenced test or configuration and retains current feature-linked impact analysis. A reference run does not require `compile`; compiling it produces no test file and leaves the original unchanged. Generated journeys still require current compiled manifests and retain their fixture/bootstrap checks.

The runner builds an argument vector without a shell and applies the existing bounded process timeout:

| Runner | Native invocation |
|---|---|
| Playwright | `npx --no-install playwright test <anchored-escaped-absolute-realpath> [--config <config>] [--grep <test_name>] --reporter=json` |
| Vitest | `node <installed-livespec-adapter>/vitest-reference.mjs <JSON-selection>` |
| pytest | `<current-python> -m pytest <path> [-c <config>] [-k <test_name>] --junitxml <owned-temp-file>` |

The consumer supplies the existing runner installation, services, browser binaries, credentials and suite-specific setup. Arguments remain separate values; no arbitrary shell command is accepted in YAML. Playwright uses an anchored escaped absolute resolved file path so a similarly named neighbour cannot match. Vitest CLI file filters use substring matching, so LiveSpec instead invokes its bundled Node adapter with a JSON selection containing `path`, optional `config` and optional `test_name`. It resolves only the consumer-local `vitest/node`, loads the real configuration with `createVitest`, collects specifications, filters their `moduleId` by exact realpath before executing, and closes the context in `finally`. The adapter selects the JSON reporter, disables watch mode and sets `passWithNoTests: false`; it does not install packages. Test selectors retain native runner syntax. JSON reporters and the invocation-owned temporary pytest JUnit report let LiveSpec verify that at least one selected test actually executed; an exit-zero result alone is insufficient. The temporary report is cleaned up by its owning invocation.

## Interpret the result

- `selection_status: no_selection` means the catalogue/filtered selection contains no journey. It does not mean a native suite passed.
- `selection_status: planned` means dry run prepared the selection without execution. `planned` lists journey IDs and `planned_commands` maps them to selected argument vectors. Preview executes no tests and writes no reports; the Vitest adapter selects its reporter internally if later executed; planned IDs are not included in executed counts.
- Equivalent reference commands execute once per invocation. `reused` maps each later journey ID to the first journey ID; reuse preserves the first command's actual outcome, including failure.
- Zero selected tests or an all-skipped suite produces `journey_no_tests_executed`, including a Vitest exit-zero/all-skipped result. Missing, malformed or invalid native reports produce `journey_test_results_invalid`. Neither result is successful test execution.
- Playwright results count both expected and flaky tests as executed when the native process succeeds. A native nonzero exit, including a consumer fail-on-flaky policy, remains failure.
- Manual and disabled policies retain their normal behavior. A missing file, unsupported runner or invalid combination fails validation before native execution.
- `evidence_level` remains declarative after success. A mock-based browser test does not become device proof; coverage links do not retrospectively change historical verdicts.

## Adopt in an existing product safely

Start with the product's existing suite and runner configuration. Link a current AC, FR or historical requirement only when that suite actually exercises it, and describe the limits in `evidence_level`. Keep the original fixture/bootstrap path; adding a journey is not a reason to duplicate setup or regenerate tests.

Confirm the consumer's selected LiveSpec runtime supports references before using the new YAML. For Atlas, preserve its newer private runtime lineage (`23-6897`) and existing product session. Prepare only the reference YAML pointing to the actual existing suite; a runtime change requires a safe checkpoint with that session and explicit scope. This guide does not install, repin or downgrade Atlas, change global skills, rewrite historical evidence or establish product acceptance.

## Validation scope

Real pytest, Node Playwright fixtures without a browser, and Vitest integrations exercise original configuration/fixture reuse, exact file selection and native outcome handling. Vitest 4.0.18 was observed; compatibility with other versions is not established and requires the same public API. Read [the official advanced test API guide](https://vitest.dev/guide/advanced/tests) for that API lifecycle; its current examples may target a newer signature. Real Vitest all-skipped execution exposed an exit-zero case, which native report validation rejects. The reviewer also exposed neighbouring-file execution from CLI substring filtering; the exact specification filter addresses it. Read [the current feature progress](../../.specs/features/123-existing-test-journeys/progress.md) for check outcomes rather than treating this guide as a frozen test-count report. Browser rendering, images, product services and provider integrations were not observed. Independent final review remains in progress; consumer adoption is separate.
