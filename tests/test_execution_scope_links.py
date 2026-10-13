"""Execution input scope never follows links out of the project (078 FR-011).

Regression for the Handy capture failure: ``livespec runtime dev`` links the
git-ignored ``.agent-sync.local`` entries to the LiveSpec checkout and agent
tooling (``.claude``, ``.agents``) links to those entries, so the capture
followed them outside the project and rejected the whole execution evidence.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.execution_evidence_support import FEATURE, run
from tests.execution_evidence_support import project as project
from validator.execution_evidence import verify_execution_receipt
from validator.execution_scope import source_manifest


def _outside(project: Path) -> Path:
    outside = project.parent / f"{project.name}-livespec/.agent-sync/rules/livespec"
    outside.mkdir(parents=True)
    (outside / "commands.md").write_text("# commands\n")
    return outside


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)


def _runtime_dev_links(project: Path, outside: Path) -> None:
    """Reproduce the link layout written by ``livespec runtime dev`` in a project."""
    local = project / ".agent-sync.local/rules"
    local.mkdir(parents=True)
    (local / "commands.md").symlink_to(outside / "commands.md")
    rules = project / ".claude/rules"
    rules.mkdir(parents=True)
    (rules / "commands.md").symlink_to("../../.agent-sync.local/rules/commands.md")
    skills = project / ".agents/skills"
    skills.mkdir(parents=True)
    (skills / "spec-fix").symlink_to(outside, target_is_directory=True)


# @spec FR-011: Capture scope stays inside the project
#   — .specs/features/078-requirement-evidence-integrity/spec.md#fr-011
def test_ignored_runtime_links_out_of_project_keep_capture_valid(project: Path) -> None:
    outside = _outside(project)
    _runtime_dev_links(project, outside)
    _git(project, "init", "-q")
    (project / ".gitignore").write_text(".agent-sync.local/\n")
    path = run(project)
    result = verify_execution_receipt(path, project, FEATURE)
    assert result.valid, result.gaps
    manifest = source_manifest(project, FEATURE)
    tooling = (".agent-sync.local", ".claude", ".agents")
    assert not any(name.startswith(tooling) for name in manifest)
    (outside / "commands.md").write_text("# changed outside the project\n")
    assert verify_execution_receipt(path, project, FEATURE).valid
    (project / "app.py").write_text("def add(a, b):\n    return 0\n")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_agent_tooling_directories_are_out_of_scope_without_git(project: Path) -> None:
    outside = _outside(project)
    _runtime_dev_links(project, outside)
    codex = project / ".codex/config.toml"
    codex.parent.mkdir()
    codex.write_text("model = 'a'\n")
    path = run(project)
    assert verify_execution_receipt(path, project, FEATURE).valid
    codex.write_text("model = 'b'\n")
    assert verify_execution_receipt(path, project, FEATURE).valid


def test_git_ignored_outputs_are_out_of_scope_and_tracked_inputs_stay_bound(
    project: Path,
) -> None:
    _git(project, "init", "-q")
    (project / ".gitignore").write_text("target/\n*.log\n")
    build = project / "target/debug/app.bin"
    build.parent.mkdir(parents=True)
    build.write_bytes(b"one")
    (project / "run.log").write_text("first")
    path = run(project)
    assert "target/debug/app.bin" not in source_manifest(project, FEATURE)
    build.write_bytes(b"two")
    (project / "run.log").write_text("second")
    assert verify_execution_receipt(path, project, FEATURE).valid
    (project / "pytest.ini").write_text("[pytest]\n")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_external_source_link_binds_its_text_without_reading_outside(project: Path) -> None:
    outside = _outside(project)
    shared = project / "shared.md"
    shared.symlink_to(outside / "commands.md")
    path = run(project)
    manifest = source_manifest(project, FEATURE)
    assert "shared.md@external-symlink" in manifest and "shared.md" not in manifest
    assert verify_execution_receipt(path, project, FEATURE).valid
    shared.unlink()
    shared.symlink_to(project / "app.py")
    assert not verify_execution_receipt(path, project, FEATURE).valid


def test_spec_reference_through_external_link_does_not_break_inventory(project: Path) -> None:
    outside = _outside(project)
    (project / "docs").mkdir()
    (project / "docs/rules.md").symlink_to(outside / "commands.md")
    spec = project / ".specs/features" / FEATURE / "spec.md"
    spec.write_text(spec.read_text() + "\nRead [rules](../../../docs/rules.md).\n")
    manifest = source_manifest(project, FEATURE)
    assert "docs/rules.md@external-symlink" in manifest


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_internal_link_to_excluded_tooling_is_still_rejected(project: Path, kind: str) -> None:
    tooling = project / ".claude/data"
    tooling.mkdir(parents=True)
    (tooling / "value.py").write_text("VALUE = 1\n")
    if kind == "file":
        (project / "value.py").symlink_to(tooling / "value.py")
    else:
        (project / "data").symlink_to(tooling, target_is_directory=True)
    with pytest.raises(ValueError, match="excluded inputs"):
        source_manifest(project, FEATURE)
