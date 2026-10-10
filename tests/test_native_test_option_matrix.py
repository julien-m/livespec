"""Native test operations require one complete request before any driver or capture work."""

from itertools import combinations
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

OPERATIONS = (
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
    calls: list[str] = []

    def resolve() -> Path:
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
    calls: list[str] = []

    def resolve() -> Path:
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
    calls: list[str] = []

    def resolve() -> Path:
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
    calls: list[str] = []

    def resolve() -> Path:
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
