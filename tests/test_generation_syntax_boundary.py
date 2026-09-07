"""Generated-source syntax validation cannot execute test, import or startup hooks."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_command_preview_obligations import ROOT, _goal
from validator.goal_contracts import render_goal_contract_file

SKILL = ROOT / ".agent-sync/skills/spec-test/SKILL.md"


def _syntax_command(extension: str, generated: Path) -> list[str]:
    section = SKILL.read_text().split("### 3.5 — Compilation Gate", 1)[1].split("### 3.6", 1)[0]
    commands = re.findall(r"```bash\n([^`]+)\n```", section)
    command = next((line for line in commands if f"<generated-file.{extension}>" in line), None)
    assert command, f"Missing verified non-executing {extension} syntax command"
    compiler = ROOT / "node_modules/typescript/lib/typescript.js"
    argv = shlex.split(command)
    return [
        sys.executable
        if token == "python"
        else str(compiler)
        if token == "<typescript-compiler.js>"
        else str(generated)
        if token == f"<generated-file.{extension}>"
        else token
        for token in argv
    ]


def _adversarial_source(extension: str) -> str:
    if extension == "py":
        return (
            "from pathlib import Path\nimport runtime_hook\n"
            'for name in ("baseline", "report", "app"):\n'
            '    Path(name).write_text("executed")\n'
            "def test_generated():\n    assert True\n"
        )
    return (
        'const fs = require("node:fs"); require("./runtime_hook.cjs");\n'
        'for (const name of ["baseline", "report", "app"]) fs.writeFileSync(name, "executed");\n'
    )


@pytest.mark.parametrize("extension", ["py", "js", "ts"])
@pytest.mark.parametrize("valid", [True, False])
def test_documented_parser_rejects_syntax_errors_without_executing_source_or_hooks(
    tmp_path: Path, extension: str, valid: bool
) -> None:
    generated = tmp_path / f"generated.{extension}"
    generated.write_text(_adversarial_source(extension) + ("" if valid else "\ninvalid = ("))
    (tmp_path / "runtime_hook.py").write_text('raise RuntimeError("must not import")\n')
    (tmp_path / "runtime_hook.cjs").write_text('throw Error("must not import");\n')
    (tmp_path / "sitecustomize.py").write_text('raise RuntimeError("must not start")\n')
    preload = tmp_path / "preload.cjs"
    preload.write_text('require("node:fs").writeFileSync("preloaded", "executed");\n')
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    env = {**os.environ, "PYTHONPATH": str(tmp_path), "NODE_OPTIONS": f"--require={preload}"}

    result = subprocess.run(
        _syntax_command(extension, generated),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert (result.returncode == 0) is valid, result.stderr
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_adversarial_fixture_has_real_effects_when_executed(tmp_path: Path) -> None:
    generated = tmp_path / "generated.js"
    generated.write_text(_adversarial_source("js"))
    (tmp_path / "runtime_hook.cjs").write_text(
        'require("node:fs").writeFileSync("hook", "executed");'
    )
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run([node, str(generated)], cwd=tmp_path, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert all(
        (tmp_path / name).read_text() == "executed"
        for name in ("baseline", "report", "app", "hook")
    )


@pytest.mark.parametrize(
    "flags,generates", [("", True), ("--dry-run", False), ("--regenerate-missing --confirm", True)]
)
def test_generated_file_tasks_only_validate_syntax_until_runtime_phases(
    tmp_path: Path, flags: str, generates: bool
) -> None:
    tasks = json.loads(render_goal_contract_file(_goal(tmp_path, "spec-test", flags, True)))[
        "tasks"
    ]
    checks = [task for task in tasks if task["description"].startswith("Per generated")]
    assert bool(checks) is generates
    assert all(
        "syntax-only" in task["description"] and "run in isolation" not in task["description"]
        for task in checks
    )
    assert all(task["evidence_kind"] == "documentary" for task in checks)
    if not flags:
        assert any(task["evidence_kind"] == "execution" for task in tasks)
    if "--regenerate-missing" in flags:
        assert not any(task["evidence_kind"] == "execution" for task in tasks)


def test_penflow_captures_are_confined_to_run_before_baseline_promotion(tmp_path: Path) -> None:
    tasks = json.loads(render_goal_contract_file(_goal(tmp_path, "spec-test", "", True)))["tasks"]
    capture = next(task for task in tasks if task["description"].startswith("4.5.P Web runtime:"))
    assert ".specs/features/<feature>/run/<run-id>/<target>/" in capture["description"]
    assert (
        "capture screenshots to .specs/features/<feature>/baselines/" not in capture["description"]
    )
    assert any("livespec visual-gate promote" in task["description"] for task in tasks)
