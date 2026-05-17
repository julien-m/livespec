# Schema: design-alignment.manifest.json

<!-- @spec FR-002: Design alignment manifest schema — .specs/features/047-design-alignment-gate/spec.md#fr-002 -->

Written by `livespec design-alignment compare` and consumed by `/spec.test --visual`.

## Location

```text
.specs/features/NNN-feature/design-alignment/design-alignment.manifest.json
```

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `screen` | string | yes | Screen identifier from `spec.md ## Screens`. |
| `verdict` | enum | yes | `PASS`, `FAIL`, or `BLOCKED`. |
| `design_source` | string | yes | Path to `.specs/design/ui.pen` or normalized design contract. |
| `runtime_source` | string | yes | Path to runtime contract captured from browser/simulator. |
| `design_hash` | string/null | yes | SHA-256 of the design source when readable. |
| `runtime_hash` | string/null | yes | SHA-256 of runtime source when readable. |
| `support.design` | object/null | yes | Normalized design support contract. |
| `support.runtime` | object/null | yes | Normalized runtime support contract. |
| `issues` | array | yes | Actionable support or node/property mismatches. |

## Example

```json
{
  "screen": "dashboard",
  "verdict": "PASS",
  "design_source": ".specs/design/ui.pen",
  "runtime_source": ".specs/features/047/design-alignment/dashboard.runtime.json",
  "design_hash": "abc123",
  "runtime_hash": "def456",
  "support": {
    "design": {"width": 393, "height": 852, "dpr": 3},
    "runtime": {"width": 393, "height": 852, "dpr": 3}
  },
  "issues": []
}
```
