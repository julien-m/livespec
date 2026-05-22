# Penflow Contract Gate

Penflow is the primary UI behavior contract when a project has root `penflow/`.
In reports, screenshots remain visual regression gates; they never replace Penflow flow correctness.

## Workspace

Root layout:

```text
penflow/
├── flow-ui-contract/
├── semantic-ui-tree.json
├── expected-ui-tree.json
├── code-ir.json
├── actual-ui-tree.json
├── compare-report.json
├── compare-report.md
├── review-report.md
└── fix-report.md
```

Required for contract-ready planning/implementation:

- `penflow/semantic-ui-tree.json`
- `penflow/expected-ui-tree.json`
- `penflow/code-ir.json`

Required for runtime comparison:

- `penflow/actual-ui-tree.json` emitted by an external adapter

## Global LiveSpec Design Registry

Penflow-backed UI features must also populate the project-level design registry.
Feature-local artifacts are proof copies; `.specs/design/` is the shared visual source of truth.

Required registry layout:

```text
.specs/design/
├── ui.pen
├── screens/
│   ├── index.md
│   └── <feature_slug>/
│       └── <screen>.png
├── baselines/
│   └── <feature_slug>/
│       └── <runtime-screen>.png
└── changelog.md
```

If `.specs/design/ui.pen` or mockup PNGs under `.specs/design/screens/<feature_slug>/`
are missing for a Penflow-backed UI feature, the visual gate is `BLOCKED`. Do not
auto-approve runtime screenshots without mockups.

## Mockup Factory Validation

Penflow-backed UI features must run Mockup Factory after the Penflow forward
chain and design registry sync, before code starts. Required proof:

```text
.mockup-validation/
├── audit-report.md
├── <feature_slug>/
│   ├── checklist.md
│   ├── manifest.json
│   └── drift-report.json
└── visual-evidence/
    ├── manifest.json   (status: PASS)
    ├── visual-report.md
    └── *.png
```

The canonical visual evidence manifest path is
`.mockup-validation/visual-evidence/manifest.json`.

`PASSED_WITH_WARNINGS`, `ESCALATED`, `BLOCKED`, and `BLOCKED_VISUAL_NOT_RUN`
block `/spec-feature` and `/spec-test` for web desktop UI features. The mockup
must pass modern desktop, no-placeholder, no-overflow, and visual evidence gates
before implementation or runtime baseline approval.

## Verdict

Every UI contract run reports exactly one final line:

```text
Penflow Contract Verdict: PASS | FAIL | BLOCKED | ABSENT
```

When `--json` is used, the same value is emitted as the top-level `verdict`
field so stdout stays parseable JSON.

| Verdict | Meaning | Build behavior |
|---|---|---|
| `PASS` | Expected and actual trees match. | Continue to screenshot regression gates. |
| `FAIL` | Penflow compare found structural drift. | Block UI flow correctness. |
| `BLOCKED` | Required Penflow artifacts, `actual-ui-tree.json`, or CLI validation are unavailable for a UI flow that requires runtime comparison. | Block until artifacts/tooling exist. |
| `ABSENT` | No root `penflow/` workspace exists. | Non-UI or legacy projects may continue with fallback paths. |

## Command Sequence

```bash
livespec penflow-contract status --project . --require-actual --json
livespec penflow-contract status --project . --require-actual --require-design-registry --require-mockup-validation --feature <feature_slug> --json
penflow validate-actual penflow/actual-ui-tree.json --schema --json
penflow compare-tree penflow/expected-ui-tree.json penflow/actual-ui-tree.json \
  --out penflow/compare-report.json \
  --markdown penflow/compare-report.md \
  --json
penflow review-report penflow/compare-report.json --out penflow/review-report.md
penflow fix-report penflow/compare-report.json --out penflow/fix-report.md
```

If the command status reports `runtime_comparison: BLOCKED`, stop before
running `penflow validate-actual`. If `penflow/compare-report.json` exists,
status must return `FAIL` unless the raw report has `status: PASS` and zero
`issues`. A missing `actual-ui-tree.json` is not a failure for non-UI runs that
did not request runtime comparison; such runs can return
`runtime_comparison: ABSENT` with final verdict `PASS` when required planning
artifacts are present.

## Rules

- Do not treat Penflow flows under `.specs/features/` as the project registry; feature-local copies are audit evidence only.
- Do not leave Penflow/Pencil artifacts only under feature-local directories; sync `.specs/design/ui.pen`, `.specs/design/screens/<feature_slug>/`, `.specs/design/baselines/<feature_slug>/`, `.specs/design/screens/index.md`, and `.specs/design/changelog.md`.
- Do not generate runtime adapters in LiveSpec core.
- Preserve `semantic_id`, `test_id`, `binding`, `entity`, `validations`, and `side_effects` in UI implementation.
- Run Penflow before visual baseline approval; screenshot gates remain complementary visual regression gates.
