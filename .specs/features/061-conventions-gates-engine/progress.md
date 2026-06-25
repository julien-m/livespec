---
feature: 061-conventions-gates-engine
status: Done
created: 2026-06-12
updated: 2026-06-25
---

# Progress — Conventions Gates Engine

| Step | Status | Evidence |
|---|---|---|
| 1. Tests first for schema, verify, receipt | Done | `tests/test_conventions_*.py` red: missing modules |
| 2. Gates schema and generator | Done | `validator/conventions_gates.py`, `.specs/conventions-gates.yaml` |
| 3. Adapter registry | Done | `validator/conventions_lang/` |
| 4. Verify engine and report | Done | `validator/conventions_gate.py`, `validator/conventions_report.py` |
| 5. Receipt oracle | Done | `validator/conventions_receipt.py` |
| 6. CLI wiring | Done | `livespec conventions --help` lists verify/scaffold/gates |
| 7. Validation | Done | `python3 -m pytest tests/test_conventions_*.py -q` -> 9 passed, 0 skipped |
| 8. Generated workspace exclusions | Done | `python3 -m pytest tests/test_conventions_verify.py::test_verify_ignores_generated_dependency_workspaces tests/test_conventions_verify.py::test_verify_applies_exclusions_to_linter_output -q` -> 2 passed |
