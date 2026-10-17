"""Real single-invocation cwd identity, confinement and root compatibility (096)."""

from __future__ import annotations

import json
import shlex
import shutil
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.execution_vitest_fixture import FEATURE, VitestProject
from tests.execution_vitest_fixture import vitest_dependencies as vitest_dependencies
from tests.execution_vitest_fixture import vitest_project as vitest_project
from validator.cli import app
from validator.execution_evidence import verify_execution_observation


def _nested_package(project: VitestProject, name: str) -> Path:
    """Use a separate real local installation and cwd-sensitive matcher."""
    package = project.root / name
    package.mkdir()
    for file in ("package.json", "package-lock.json", "vitest.config.ts"):
        shutil.copy2(project.root / file, package / file)
    shutil.copytree(project.root / "node_modules", package / "node_modules")
    (package / "cwd.test.ts").write_text(
        "import { test, expect } from 'vitest';\n"
        "test('actual cwd', () => { expect(process.cwd()).toBe("
        f"{json.dumps(str(package))}); }});\n"
    )
    return package


@pytest.mark.integration
@pytest.mark.parametrize("name", ["dashboard", "slides"])
def test_cli_observes_actual_nested_cwd_and_rejects_directory_drift(
    vitest_project: VitestProject, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """The real invocation owns cwd; a root receipt cannot stand in for it."""
    # @spec AC-003, AC-004: Actual confined cwd and immutable receipt identity
    # — .specs/features/096-node-vitest-execution/spec.md#ac-003
    package = _nested_package(vitest_project, name)
    executable = str(vitest_project.node)
    if name == "dashboard":
        (package / "bin").mkdir()
        (package / "bin/node").symlink_to(vitest_project.node)
        (vitest_project.root / "bin").mkdir()
        (vitest_project.root / "bin/node").symlink_to(sys.executable)
        executable = "./bin/node"
    command = [executable, "node_modules/vitest/vitest.mjs", "run"]
    monkeypatch.chdir(vitest_project.root)
    result = CliRunner().invoke(
        app,
        [
            "test",
            "--feature",
            FEATURE,
            "--execution-command",
            shlex.join(command),
            "--execution-observation",
            "passed",
            "--execution-cwd",
            name,
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    receipt = Path(payload["execution_receipt_path"])
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["project_root"] == str(vitest_project.root)
    assert capture["execution_cwd"] == name
    assert capture["runner_provenance"]["execution_cwd"] == str(package)
    assert payload["certified_acs"] == []
    assert verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed").valid
    # Renaming and recreating the same path leaves bytes unchanged but invalidates cwd identity.
    package.rename(vitest_project.root / (name + "-old"))
    package.mkdir()
    assert not verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed").valid


def test_cwd_confinement_and_unused_cli_modifier(tmp_path: Path) -> None:
    """Reject external directories, escaped links and an option without execution."""
    from validator.cli_commands.operation_options import check_execution_options
    from validator.execution_working_directory import resolve_execution_cwd, resolve_runner_cwd

    root = tmp_path / "governed"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    for requested in (tmp_path, root / "escape"):
        with pytest.raises(ValueError, match="confined") as rejected:
            resolve_execution_cwd(root, requested)
        assert "confined" in str(rejected.value)
    (root / "nested").mkdir()
    with pytest.raises(ValueError, match="only for direct Vitest") as unsupported:
        resolve_runner_cwd(root, Path("nested"), ["python", "-m", "pytest"])
    assert "only for direct Vitest" in str(unsupported.value)
    with pytest.raises(ValueError, match="requires --execution-command") as unused:
        check_execution_options(
            feature=None,
            command=None,
            mapping=None,
            prepare=False,
            ingest=None,
            adapter="junit",
            mutation=False,
            no_coverage=False,
            debug=False,
            execution_cwd=Path("."),
        )
    assert "requires --execution-command" in str(unused.value)


@pytest.mark.integration
def test_historical_root_capture_retains_root_meaning(vitest_project: VitestProject) -> None:
    """The schema-1 representation without cwd fields remains a root invocation."""
    from validator.execution_evidence import _read_capture
    from validator.execution_scope import digest
    from validator.execution_working_directory import capture_execution_cwd

    vitest_project.write("test('root', () => { expect(1).toBe(1); });")
    receipt = vitest_project.capture()
    capture = json.loads((receipt.parent / "capture.json").read_text())
    assert capture["execution_cwd"] == "."
    capture.pop("execution_cwd")
    capture.pop("execution_cwd_identity")
    for key in ("execution_cwd", "cwd_device", "cwd_inode"):
        capture["runner_provenance"].pop(key)
    payload = json.dumps(capture).encode()
    vitest_project.replace_artifact(receipt, "capture.json", payload)
    reference = json.loads(receipt.read_text())
    reference["capture_sha256"] = digest(payload)
    vitest_project.replace_artifact(receipt, "receipt.json", json.dumps(reference).encode())
    historical, _ = _read_capture(receipt, vitest_project.root, FEATURE)
    assert capture_execution_cwd(historical) == vitest_project.root
    assert verify_execution_observation(receipt, vitest_project.root, FEATURE, "passed").valid


def test_timeout_capture_keeps_attempted_nested_cwd(tmp_path: Path) -> None:
    """A nonqualifying preparation timeout must not invent a root invocation."""
    from validator.execution_evidence import _read_capture
    from validator.execution_timeout_capture import timeout_capture

    root = tmp_path / "project"
    nested = root / "dashboard"
    nested.mkdir(parents=True)
    result = timeout_capture(
        ["node", "vitest.mjs", "run"], root, FEATURE, "junit", {}, execution_cwd=Path("dashboard")
    )
    capture, _ = _read_capture(Path(result.receipt_path), root, FEATURE)
    assert capture.execution_cwd == "dashboard"
    assert capture.exit_code == 124
    assert not verify_execution_observation(
        Path(result.receipt_path), root, FEATURE, "passed"
    ).valid
