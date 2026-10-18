"""Closed absence grammar preserves required opaque execution declarations."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import pytest

from tests.test_suite_command_discovery import FEATURE, _archive_errors, _goal, _project
from validator.evidence_applicability import (
    _command_rows,
    resolve_applicability,
    section,
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
    accepted = ["N/A", "Not applicable", "Not run", "None", "\u2014", "-", absence, "N/A — no UI"]
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


def test_corpus_no_ui_absence_is_exact_and_never_hides_command_suffixes(tmp_path: Path) -> None:
    """Both approved plans use the eighth exact marker; all appended execution stays required."""
    root = Path(__file__).resolve().parents[1]
    plans = ["039.1-goal-archive-run-artifacts", "060-journey-fixture-bootstrap-contract"]
    for name in plans:
        text = (root / ".specs/features" / name / "plan.md").read_text()
        rows = _command_rows(section(text, "Resolved Test Commands") or "")
        # @spec AC-007: Real approved plan rows use the exact supported absence marker.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
        assert ("Visual tests", "N/A — no UI") in rows
    unit = [sys.executable, "-m", "pytest", "tests/test_one.py"]
    feature = _project(tmp_path, [("Unit tests", shlex.join(unit)), ("Integration / E2E", "TOKEN")])
    plan = feature / "plan.md"
    original = plan.read_text()
    plan.write_text(original.replace("TOKEN", "N/A — no UI"))
    assert suite_binding(tmp_path, FEATURE, "all")["commands"] == [["pytest", ".", *unit[3:]]]
    assert not resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]
    for suffix in [" pnpm test", ": yarn test", " because ./e2e.sh", " (./e2e.sh)", " && pytest x"]:
        declaration = "N/A — no UI" + suffix
        plan.write_text(original.replace("TOKEN", declaration))
        binding = suite_binding(tmp_path, FEATURE, "all")
        if suffix.startswith(" ("):
            assert binding.get("error") and "commands" not in binding
        else:
            assert ["opaque", ".", *shlex.split(declaration)] in binding["commands"]
        assert resolve_applicability(tmp_path, FEATURE, "integration-command")["applicable"]
        assert resolve_applicability(tmp_path, FEATURE, "e2e-command")["applicable"]


def test_fenced_corpus_commands_preserve_selection_and_exclude_only_direct_quality() -> None:
    """Untyped031 and bash081 bind every actual test invocation without argv suite inference."""
    root = Path(__file__).resolve().parents[1]
    for feature, count in [("031-ui-runner-android", 3), ("081-lightweight-outcome-goals", 2)]:
        binding = suite_binding(root, feature, "all")
        # @spec AC-007: Approved fenced test invocations remain exact required selections.
        # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
        assert len(binding["commands"]) == count
        assert all(command[0] in {"pytest", "opaque"} for command in binding["commands"])
        text = (root / ".specs/features" / feature / "plan.md").read_text()
        original = [
            shlex.split(line)
            for line in (section(text, "Resolved Test Commands") or "").splitlines()
            if line.startswith(("python -m pytest", "pytest "))
        ]
        for frozen, argv in zip(binding["commands"], original, strict=True):
            retained = argv
            if frozen[0] == "pytest":
                retained = argv[3:] if argv[1:3] == ["-m", "pytest"] else argv[1:]
            assert frozen[2:] == retained
        assert any(
            "tests/integration/" in command
            or "tests/integration/test_surfaces_maestro.py" in command
            for command in binding["commands"]
        )
    rows = _command_rows(
        "~~~bash\n# setup note\nruff check . && ruff format --check .\n"
        "custom-driver --ignore=tests/integration\n~~~\n| Integration | N/A |\n"
    )
    assert rows == [
        ("Static quality", "ruff check . && ruff format --check ."),
        ("Declared command", "custom-driver --ignore=tests/integration"),
        ("Integration", "N/A"),
    ]
    for command in [
        "ruff check . && custom-driver",
        "env CI=1 mypy .",
        "ruff check .; ./unknown",
        "ruff check . | unknown",
        "mypy . & unknown",
    ]:
        assert _command_rows("```\n" + command + "\n```")[0] == ("Declared command", command)


@pytest.mark.integration
def test_real_fenced_goal_proves_unit_and_all_but_never_unknown_invocations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real pytest proves the complete fenced selection, never an unknown driver."""
    for unknown in [False, True]:
        root = tmp_path / str(unknown)
        unit = [sys.executable, "-m", "pytest", "tests/test_one.py", "-q"]
        feature = _project(root, [])
        (feature / "plan.md").write_text(
            "## Resolved Test Commands\n\n```bash\n"
            + shlex.join(unit)
            + "\nruff check . && ruff format --check .\nmypy .\n"
            + ("custom-driver --ignore=tests/integration\n" if unknown else "")
            + "```\n"
        )
        contract, state = _goal(root, monkeypatch)
        result = capture_execution(
            unit,
            project_root=root,
            feature=FEATURE,
            adapter="junit",
            env=dict(os.environ),
            timeout=5,
        )
        receipt = Path(result.receipt_path)
        assert verify_execution_observation(receipt, root, FEATURE, "passed").valid
        for task in contract["tasks"]:
            binding = task.get("expected_evidence", {}).get("suite_binding", {})
            if binding.get("suite") not in {"unit", "all"}:
                continue
            proof = prove_goal_task(
                contract,
                state,
                task["id"],
                {"execution_receipt_path": str(receipt)},
                project_root=root,
            )
            # @spec AC-007: Canonical unit and aggregate require every actual fenced invocation.
            # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-007
            assert proof["accepted"] is (not unknown)
            if unknown:
                # @spec AC-010: Unknown fenced drivers stay required and unsupported, never absent.
                # — .specs/features/078-requirement-evidence-integrity/spec.md#ac-010
                assert (
                    "suite_assertion_adapter_unsupported:custom-driver" in proof["missing_evidence"]
                )
