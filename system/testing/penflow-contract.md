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
penflow validate-actual penflow/actual-ui-tree.json --schema --json
penflow compare-tree penflow/expected-ui-tree.json penflow/actual-ui-tree.json \
  --out penflow/compare-report.json \
  --markdown penflow/compare-report.md \
  --json
penflow review-report penflow/compare-report.json --out penflow/review-report.md
penflow fix-report penflow/compare-report.json --out penflow/fix-report.md
```

If the command status reports `runtime_comparison: BLOCKED`, stop before
running `penflow validate-actual`. A missing `actual-ui-tree.json` is not a
failure for non-UI runs that did not request runtime comparison; such runs can
return `runtime_comparison: ABSENT` with final verdict `PASS` when required
planning artifacts are present.

## Rules

- Do not write Penflow flows under `.specs/features/`.
- Do not generate runtime adapters in LiveSpec core.
- Preserve `semantic_id`, `test_id`, `binding`, `entity`, `validations`, and `side_effects` in UI implementation.
- Run Penflow before visual baseline approval; screenshot gates remain complementary visual regression gates.
