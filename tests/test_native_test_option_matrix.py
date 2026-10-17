"""Native test operations require one complete request before any driver or capture work."""

import json
import shlex
import sys
from itertools import combinations
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.execution_evidence import verify_execution_receipt

OPERATIONS = (
    ("--derive-mapping",),
    ("--prepare-mapping-review",),
    ("--ingest-mapping-review", "raw.json"),
    ("--execution-command", "pytest"),
)
INVALID_REQUESTS = (
    ("--acceptance-mapping", "mapping.json"),
    *OPERATIONS,
    *((*a, *b, "--acceptance-mapping", "mapping.json") for a, b in combinations(OPERATIONS, 2)),
    (
        "--prepare-mapping-review",
        "--ingest-mapping-review",
        "raw.json",
        "--execution-command",
        "pytest",
        "--acceptance-mapping",
        "mapping.json",
    ),
    ("--execution-command", "", "--acceptance-mapping", "mapping.json"),
    ("--report-adapter", "custom"),
)


@pytest.mark.parametrize("arguments", INVALID_REQUESTS)
def test_native_incomplete_or_ambiguous_request_never_runs_either_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...]
) -> None:
    """Native incomplete or ambiguous request never runs either path."""
    calls: list[str] = []

    def resolve() -> Path:
        """Resolve."""
        calls.append("project")
        raise AssertionError("Invalid request reached runtime")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(app, ["test", "--feature", "001-feature", *arguments])
    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert calls == []
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("modifier", ("--mutation", "--no-coverage", "--debug"))
def test_native_request_rejects_unconsumed_driver_modifiers(
    monkeypatch: pytest.MonkeyPatch, operation: tuple[str, ...], modifier: str
) -> None:
    """Native request rejects unconsumed driver modifiers."""
    calls: list[str] = []

    def resolve() -> Path:
        """Resolve."""
        calls.append("project")
        raise AssertionError("Invalid request reached runtime")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(
        app,
        [
            "test",
            "--feature",
            "001-feature",
            "--acceptance-mapping",
            "mapping.json",
            *operation,
            modifier,
        ],
    )
    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert calls == []


@pytest.mark.parametrize("operation", OPERATIONS)
def test_native_feature_is_required_before_project_resolution(
    monkeypatch: pytest.MonkeyPatch, operation: tuple[str, ...]
) -> None:
    """Native feature is required before project resolution."""
    calls: list[str] = []

    def resolve() -> Path:
        """Resolve."""
        calls.append("project")
        raise AssertionError("Incomplete request reached runtime")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(app, ["test", "--acceptance-mapping", "mapping.json", *operation])
    assert result.exit_code == 1
    assert "require --feature and --acceptance-mapping" in result.output
    assert calls == []


@pytest.mark.parametrize("operation", OPERATIONS[:2])
def test_review_cannot_ignore_nondefault_execution_adapter(
    monkeypatch: pytest.MonkeyPatch, operation: tuple[str, ...]
) -> None:
    """Review cannot ignore nondefault execution adapter."""
    calls: list[str] = []

    def resolve() -> Path:
        """Resolve."""
        calls.append("project")
        raise AssertionError("Conflicting request reached runtime")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(
        app,
        [
            "test",
            "--feature",
            "001-feature",
            "--acceptance-mapping",
            "mapping.json",
            *operation,
            "--report-adapter",
            "custom",
        ],
    )
    assert result.exit_code == 1
    assert "--report-adapter requires --execution-command" in result.output
    assert calls == []


@pytest.mark.parametrize(
    "arguments",
    [
        ("--execution-observation", "passed"),
        ("--execution-observation", "passed", "--execution-command", ""),
        *[
            ("--execution-observation", "passed", "--execution-command", "pytest", *extra)
            for extra in (
                ("--acceptance-mapping", "missing.json"),
                ("--derive-mapping",),
                ("--prepare-mapping-review",),
                ("--ingest-mapping-review", "missing.json"),
                ("--mutation",),
                ("--no-coverage",),
                ("--debug",),
            )
        ],
    ],
)
def test_observation_contradictions_reject_before_project_resolution(
    monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...]
) -> None:
    """Observation contradictions reject before project resolution."""

    def resolve() -> Path:
        """Resolve."""
        raise AssertionError("Contradictory observation reached project resolution")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(app, ["test", "--feature", "001-feature", *arguments])
    assert result.exit_code == 1
    assert result.output.startswith("Error:")


def test_observation_requires_feature_before_project_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observation requires feature before project resolution."""

    def resolve() -> Path:
        """Resolve."""
        raise AssertionError("Incomplete observation reached project resolution")

    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", resolve)
    result = CliRunner().invoke(
        app, ["test", "--execution-command", "pytest", "--execution-observation", "passed"]
    )
    assert result.exit_code == 1
    assert "requires --feature and --execution-command" in result.output


@pytest.mark.integration
@pytest.mark.parametrize("outcome", ["passed", "red"])
def test_cli_observation_verifies_real_assertions_without_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    """Cli observation verifies real assertions without mapping."""
    feature, arguments = _observation_arguments(tmp_path, outcome)
    monkeypatch.setattr("validator.cli_commands.test_cmd.require_specs_root", lambda: tmp_path)
    result = CliRunner().invoke(app, [*arguments, "--execution-observation", outcome])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["valid"]
    assert payload["certified_acs"] == []
    assert payload["acceptance_result_count"] == 0
    receipt = Path(payload["execution_receipt_path"])
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["acceptance_mapping"] is None
    assert not verify_execution_receipt(receipt, tmp_path, feature).valid
    mismatch = "red" if outcome == "passed" else "passed"
    result = CliRunner().invoke(app, [*arguments, "--execution-observation", mismatch])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert not payload["valid"]
    assert payload["certified_acs"] == []


def _observation_arguments(tmp_path: Path, outcome: str) -> tuple[str, list[str]]:
    """Build the real assertion fixture and CLI argv for the requested observation."""
    feature = "001-observation"
    directory = tmp_path / ".specs/features" / feature
    directory.mkdir(parents=True)
    (directory / "spec.md").write_text("# Observation\nAC-001: Real assertion executes.\n")
    (tmp_path / "test_observation.py").write_text(
        f"def test_observation():\n    assert {outcome == 'passed'}\n"
    )
    command = f"{shlex.quote(sys.executable)} -m pytest test_observation.py -q"
    arguments = ["test", "--feature", feature, "--execution-command", command]
    return feature, arguments
