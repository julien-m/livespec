# Progress — Conventions Blocking Pipeline

| Step | Status | Evidence |
|---|---|---|
| Spec first | Done | Created [`spec.md`](spec.md) before production code edits |
| Receipt wiring tests | Done | Added and watched failing tests in [`tests/test_run_receipts.py`](../../../tests/test_run_receipts.py) |
| Pipeline outcome tests | Done | Added failing tests in [`tests/test_run_artifact.py`](../../../tests/test_run_artifact.py) and [`tests/test_verify_output.py`](../../../tests/test_verify_output.py) |
| Goal proof tests | Done | Added failing tests in [`tests/test_goal_contracts.py`](../../../tests/test_goal_contracts.py) |
| R7 and supervisor lock tests | Done | Added failing tests in [`tests/test_coherence_rules.py`](../../../tests/test_coherence_rules.py) and [`tests/test_conventions_diffguard.py`](../../../tests/test_conventions_diffguard.py) |
| Command docs tests | Done | Added failing tests in [`tests/test_conventions_pipeline_docs.py`](../../../tests/test_conventions_pipeline_docs.py) |
| Implementation | Done | Targeted feature tests pass: 22 passed |
| Full verification | Done | `pytest tests/ -x -q`: 2079 passed, 40 skipped; `ruff check .`; `ruff format --check .`; `pyright` |
