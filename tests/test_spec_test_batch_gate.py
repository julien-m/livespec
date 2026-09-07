"""A real batch readiness check cannot borrow the previous feature's successful review."""

import json
from pathlib import Path

from typer.testing import CliRunner

from tests.review_support import reviewed_project
from validator.cli import app


def test_ready_then_stale_feature_stops_before_second_feature_test_write(tmp_path: Path) -> None:
    ready = reviewed_project(tmp_path, "001-ready")
    blocked = reviewed_project(tmp_path, "002-blocked")
    spec = blocked / "spec.md"
    spec.write_text(spec.read_text() + "\n## FR-999\nA newly required behavior.\n")
    observed: list[dict[str, object]] = []
    runner = CliRunner()
    for feature in (ready, blocked):
        command = [
            "validate",
            str(feature),
            "--progression",
            "implement",
            "--model",
            "reviewer/v1",
            "--review-max-chars",
            "60000",
        ]
        result = runner.invoke(app, command)
        observed.append(
            {
                "feature": feature.name,
                "command": command,
                "exit_code": result.exit_code,
                "raw_output": result.output,
            }
        )
        if result.exit_code != 0:
            break
        tests = feature / "tests"
        tests.mkdir()
        (tests / "generated_test.py").write_text("def test_behavior():\n    assert True\n")
    journal = tmp_path / "generation-readiness.json"
    journal.write_text(json.dumps(observed))
    assert [row["feature"] for row in observed] == [ready.name, blocked.name]
    assert [row["exit_code"] for row in observed] == [0, 1]
    assert "Progression: READY" in str(observed[0]["raw_output"])
    assert "BLOCKED" in str(observed[1]["raw_output"])
    assert (ready / "tests/generated_test.py").is_file()
    assert not (blocked / "tests").exists()
    assert json.loads(journal.read_text()) == observed
