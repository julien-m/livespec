# Visual Gate Coverage Audit — 2026-06-17

## Command

```bash
python -m pytest \
  tests/test_visual_gate.py \
  tests/test_visual_gate_receipts.py \
  tests/test_visual_implementation_gate.py \
  --cov=validator.visual_gate \
  --cov-branch \
  --cov-report=term-missing
```

## Result

- Tests: 49 passed.
- `validator/visual_gate.py`: 78.08% line/branch coverage.
- Baseline before targeted tests: 66% coverage.

## Remaining Branches

`term-missing` still reports uncovered defensive or integration-heavy branches around:

- unreadable or malformed spec/manifest files;
- Penflow index read failures and malformed `surfaces.yaml` variants;
- absolute/rooted design-alignment manifest source resolution variants;
- strict-links disabled path and auto-target derivation from existing registry/surfaces;
- malformed legacy manifests and escaping `mockup_path` rows;
- explicit aggregate verdict branches for Penflow/alignment BLOCKED/FAIL variants;
- manifest-mode promotion update of an existing manifest entry.

Each remaining branch is now identified by the coverage output instead of inferred from test-file existence.
