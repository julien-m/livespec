## 2026-10-12 — [Refactor]: Replace private-helper coverage tests with a public serialization test

- **Type:** Refactor
- **Spec modified:** No
- **Code modified:** tests/test_visual_gate.py, tests/_visual_gate_02.py, tests/_visual_gate_04.py
- **AC impacted:** None
- **Author:** claude-code (test-suite cleanup, lot 5)
- **Details:** Removed the `_as_list`/`_as_mapping` tests and `_manifest_status_to_dict(None)`. `test_non_visual_report_serializes_without_manifest_status` now covers the same branch through `validate_gate(...).to_dict()`. The CI visual-gate coverage is unchanged at 94.41% (threshold 94%).

## 2026-06-08 — [Spec Update]: Normalize changelog format

- **Type:** Spec Update
- **Spec modified:** No
- **Code modified:** None
- **AC impacted:** None
- **Author:** spec.doctor

---

# Changelog - Feature 046 - Visual Implementation Gate

## 2026-06-17 — [Test]: Add mypy-clean visual gate typing

- **Type:** Test
- **Spec modified:** No
- **Code modified:** [validator/visual_gate.py](../../../validator/visual_gate.py), [validator/cli_commands/visual_gate_cmd.py](../../../validator/cli_commands/visual_gate_cmd.py), [tests/test_visual_gate.py](../../../tests/test_visual_gate.py), [tests/test_visual_gate_receipts.py](../../../tests/test_visual_gate_receipts.py), [pyproject.toml](../../../pyproject.toml), [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
- **AC impacted:** AC-005, AC-006
- **Author:** codex

## 2026-06-17 — [Test]: Measure and expand visual_gate branch coverage

- **Type:** Test
- **Spec modified:** No
- **Code modified:** [tests/test_visual_gate.py](../../../tests/test_visual_gate.py), [tests/test_visual_gate_receipts.py](../../../tests/test_visual_gate_receipts.py), [pyproject.toml](../../../pyproject.toml), [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
- **AC impacted:** AC-005, AC-006
- **Author:** codex

## 2026-05-17 — Feature: Mandatory visual implementation gate

- **Type:** Feature
- **Spec modified:** Yes (feature created and marked Implemented)
- **Code modified:** `commands/spec-implement.md`, `commands/spec-test.md`, `commands/spec-implement.expectations.md`, `commands/spec-test.expectations.md`, `tests/test_visual_implementation_gate.py`
- **AC impacted:** AC-001, AC-002, AC-003, AC-004, AC-005, AC-006
- **Author:** codex
