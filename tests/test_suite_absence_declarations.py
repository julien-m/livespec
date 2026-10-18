"""Closed absence grammar preserves required opaque execution declarations."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import pytest

from tests.test_suite_command_discovery import FEATURE, _archive_errors, _goal, _project
from validator.evidence_applicability import (
    resolve_applicability,
    suite_binding,
    suite_evidence_missing,
)
from validator.execution_capture import capture_execution
from validator.execution_evidence import verify_execution_observation
from validator.goal_contracts import prove_goal_task


def test_qualified_absence_prose_never_hides_embedded_commands(tmp_path: Path) -> None:
    """The actual corpus absence sentence is explicit, while shell execution stays required."""
    argv = [sys.executable, "-m", "pytest", "tests/test_one.py"]
    absence = "Not applicable to bootstrap fixtures"
    feature = _project(
        tmp_path,
        [
            ("Unit tests", shlex.join(argv)),
            ("Visual/application runtime", absence),
            ("Integration / E2E", absence),
        ],
    )
    plan = feature / "plan.md"
    original = plan.read_text()
    accepted = ["N/A", "Not applicable", "Not run", "None", "\u2014", "-", absence]
    for marker in accepted:
        plan.write_text(original.replace(absence, marker))
        # @spec AC-007: Only closed positive absence forms remove declared commands.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
        assert suite_binding(tmp_path, FEATURE, "all")["commands"] == [["pytest", ".", *argv[3:]]]
        assert not resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
        assert not resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]
    plan.write_text(original)
    plan.write_text(plan.read_text().replace(absence, "N/A && pytest tests/test_one.py"))
    binding = suite_binding(tmp_path, FEATURE, "all")
    assert ["opaque", ".", "N/A", "&&", "pytest", "tests/test_one.py"] in binding["commands"]
    assert resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
    assert resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]
    assert "suite_assertion_adapter_unsupported:N/A" in suite_evidence_missing(
        binding, None, tmp_path, FEATURE, {}
    )


def test_absence_qualifiers_preserve_every_opaque_command_identity(tmp_path: Path) -> None:
    """A closed grammar rejects all suffix families without enumerating runner names."""
    commands = [
        "pnpm test",
        "yarn test",
        "./scripts/e2e.sh",
        "/opt/project/bin/e2e",
        "env CI=1 ./scripts/e2e",
        "npx playwright test",
        "uv run pytest",
        "sh -c true",
    ]
    forms = [
        "Not run: {}",
        "Not applicable: {}",
        "N/A ({})",
        "Not run because {}",
        "Not applicable to {}",
        "Not applicable for {}",
        "N/A && {}",
        "N/A ; {}",
        "N/A | {}",
        "Not applicable to bootstrap fixtures {}",
        "Not applicable to bootstrap fixtures ({})",
        "Not applicable to bootstrap fixtures: {}",
    ]
    argv = [sys.executable, "-m", "pytest", "tests/test_one.py"]
    feature = _project(
        tmp_path, [("Unit tests", shlex.join(argv)), ("Integration / E2E", "OPAQUE")]
    )
    plan = feature / "plan.md"
    original = plan.read_text()
    for form in forms:
        for command in commands:
            declaration = form.format(command)
            plan.write_text(original.replace("OPAQUE", declaration.replace("|", "\\|")))
            opaque = ["opaque", ".", *shlex.split(declaration)]
            # @spec AC-007: Every ambiguous suffix remains a frozen required command.
            # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
            aggregate = suite_binding(tmp_path, FEATURE, "all")
            e2e = suite_binding(tmp_path, FEATURE, "e2e")
            if form.endswith("({})"):
                # Existing trailing-parenthesis cwd grammar leaves these declarations unresolved.
                assert aggregate.get("error") and "commands" not in aggregate
                assert e2e.get("error") and "commands" not in e2e
            else:
                assert opaque in aggregate["commands"]
                assert e2e["commands"] == [opaque]
            assert resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
            assert resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]


@pytest.mark.integration
def test_qualified_commands_cannot_be_proved_by_a_real_unit_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine passed unit cannot replace the previously hidden E2E commands or aggregate."""
    unit = [sys.executable, "-m", "pytest", "tests/test_one.py", "-q"]
    _project(
        tmp_path,
        [
            ("Unit tests", shlex.join(unit)),
            ("E2E", "Not run: pnpm test"),
            ("E2E", "Not applicable: ./scripts/e2e.sh"),
            ("Integration", "Not applicable"),
        ],
    )
    contract, state = _goal(tmp_path, monkeypatch)
    result = capture_execution(
        unit,
        project_root=tmp_path,
        feature=FEATURE,
        adapter="junit",
        env=dict(os.environ),
        timeout=5,
    )
    receipt = Path(result.receipt_path)
    assert verify_execution_observation(receipt, tmp_path, FEATURE, "passed").valid
    tasks = {
        t["expected_evidence"]["suite_binding"]["suite"]: t
        for t in contract["tasks"]
        if "suite_binding" in t.get("expected_evidence", {})
    }
    evidence = {"execution_receipt_path": str(receipt)}
    # @spec AC-007: The real unit observation still proves only its actual frozen command.
    # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
    assert prove_goal_task(contract, state, tasks["unit"]["id"], evidence, project_root=tmp_path)[
        "accepted"
    ]
    for suite in ("e2e", "all"):
        proof = prove_goal_task(
            contract, state, tasks[suite]["id"], evidence, project_root=tmp_path
        )
        # @spec AC-009: Previously hidden commands cannot disappear from E2E or aggregate proof.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-009
        assert not proof["accepted"]
        # @spec AC-010: Unknown opaque declarations still report insufficient adapter proof.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-010
        assert "suite_assertion_adapter_unsupported" in " ".join(proof["missing_evidence"])
    assert "suite_assertion_adapter_unsupported" in " ".join(
        _archive_errors(contract, tasks["e2e"], tmp_path, receipt)
    )
