"""GitHub events run deterministic checks; real-model evaluation remains local opt-in."""

# @spec AC-013: Deterministic GitHub policy
# ../.specs/features/078-requirement-evidence-integrity/spec.md#ac-013
# @spec AC-006: No automatic provider dependency
# ../.specs/features/079-validator-ci-prerequisites/spec.md#ac-006

from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import JsonValue, TypeAdapter

from tests._json_fixture import JsonFixture

REPO = Path(__file__).resolve().parents[1]


def _workflow() -> JsonFixture:
    """Validate YAML data before inspecting the heterogeneous Actions declarations."""
    raw = yaml.load((REPO / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    # Actions mappings mix commands, inputs and arrays; JSON schema validates this fixture boundary.
    return cast(JsonFixture, TypeAdapter(dict[str, JsonValue]).validate_python(raw))


@pytest.mark.parametrize("event", ["pull_request", "workflow_dispatch", "release"])
def test_registered_events_keep_deterministic_jobs_without_model_inputs(event: str) -> None:
    workflow = _workflow()
    assert event in workflow["on"]
    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert workflow["on"]["release"]["types"] == ["published"]
    assert not workflow["on"]["workflow_dispatch"]
    assert set(workflow["jobs"]) == {"unit-tests", "integration-3a"}


@pytest.mark.parametrize(
    ("job_name", "expected_commands"),
    [
        (
            "unit-tests",
            [
                "ruff check .",
                "ruff format --check .",
                "pyright validator",
                "mypy .",
                "pytest tests/ --ignore=tests/integration -v --tb=short",
                "pytest tests/test_visual_gate.py tests/test_visual_gate_receipts.py "
                "tests/test_visual_implementation_gate.py --cov=validator.visual_gate "
                "--cov-branch --cov-report=term-missing --cov-fail-under=94",
            ],
        ),
        ("integration-3a", ["pytest tests/integration/ -m level_3a -v --tb=short"]),
    ],
)
def test_deterministic_jobs_preserve_all_check_commands(
    job_name: str, expected_commands: list[str]
) -> None:
    job = _workflow()["jobs"][job_name]
    assert "if" not in job and not job.get("needs")
    commands = [" ".join(step["run"].split()) for step in job["steps"] if "run" in step]
    actual = [
        text for text in commands if text.startswith(("ruff ", "pyright ", "mypy ", "pytest "))
    ]
    assert actual == expected_commands


def test_workflow_does_not_install_or_request_any_model_provider() -> None:
    workflow = _workflow()
    assert set(workflow["env"]) == {"NODE_VERSION", "PLAYWRIGHT_INSTALL_NODE_VERSION"}
    text = (REPO / ".github/workflows/ci.yml").read_text().lower()
    for forbidden in (
        "anthropic",
        "openai",
        "claude",
        "codex",
        "generation-selection",
        "generation-model",
    ):
        assert forbidden not in text
    commands = [
        step["run"] for job in workflow["jobs"].values() for step in job["steps"] if "run" in step
    ]
    global_installs = [
        command for command in commands if command.startswith("npm install --global")
    ]
    assert global_installs == ["npm install --global @ast-grep/cli@0.44.0"]
