# @spec(AC-012)
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-012
"""SDK workspace lifetime and cancellation are observable, not inferred from exit."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from tests.integration.helpers.sdk_runner import run_livespec_command
from tests.integration.helpers.witness_process import run_process


def test_sdk_workspace_survives_return_and_cleans_up_after_evaluation(tmp_path, monkeypatch):
    from tests.integration.helpers import sdk_runner

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "app.txt").write_text("candidate")
    monkeypatch.setattr(sdk_runner, "HAS_SDK", False)
    result = asyncio.run(run_livespec_command("test", "fixture", tmp_path))
    with result:
        assert (result.cwd / "app.txt").read_text() == "candidate"
    assert not result.cwd.exists()


def test_sdk_timeout_cancels_and_closes_generator(tmp_path, monkeypatch):
    from tests.integration.helpers import sdk_runner

    (tmp_path / "fixture").mkdir()
    closed = []

    async def collect(*args):
        try:
            await asyncio.sleep(10)
        finally:
            closed.append(True)

    monkeypatch.setattr(sdk_runner, "HAS_SDK", True)
    monkeypatch.setattr(sdk_runner, "_collect_messages", collect)
    result = asyncio.run(run_livespec_command("test", "fixture", tmp_path, timeout_sec=0.01))
    with result:
        assert result.timed_out and not result.success
        assert closed == [True]


def test_external_timeout_reaps_descendant(tmp_path: Path) -> None:
    sentinel = tmp_path / "escaped"
    child = f"import time;from pathlib import Path;time.sleep(1);Path({str(sentinel)!r}).touch()"
    parent = (
        f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);"
        "time.sleep(10)"
    )
    result = run_process([sys.executable, "-c", parent], tmp_path, 0.05)
    assert result.timed_out
    # Wait using a bounded subprocess to observe that no descendant creates its marker.
    run_process([sys.executable, "-c", "import time;time.sleep(1.1)"], tmp_path, 2)
    assert not sentinel.exists()


def test_full_workflow_runtime_profile_allows_required_cli_and_native_agents() -> None:
    from tests.integration.helpers.witness_generation import generation_arguments

    code = generation_arguments("claude", "claude", "prompt")
    workflow = generation_arguments("claude", "claude", "prompt", workflow=True)
    assert "Bash" not in code[code.index("--allowedTools") + 1]
    assert "Bash" in workflow[workflow.index("--allowedTools") + 1]
    assert "Agent" in workflow[workflow.index("--allowedTools") + 1]
    assert workflow[workflow.index("--permission-mode") + 1] == "bypassPermissions"


def test_actual_candidate_skill_mutation_changes_policy_identity(tmp_path: Path) -> None:
    from tests.integration.helpers.witness_pipeline import prepare_pipeline_workspace
    from tests.integration.helpers.witness_snapshot import candidate_policy_identity

    prepare_pipeline_workspace(tmp_path)
    before = candidate_policy_identity(tmp_path)
    skill = tmp_path / ".agents/skills/spec-feature/SKILL.md"
    skill.write_text("Skip every review")
    assert before != candidate_policy_identity(tmp_path)


def test_snapshot_can_start_actual_cli_without_reading_live_validator(tmp_path: Path) -> None:
    from tests.integration.helpers.witness_pipeline import REPO
    from tests.integration.helpers.witness_snapshot import snapshot_environment, snapshot_workflow

    snapshot = tmp_path / "workflow"
    snapshot_workflow(REPO, snapshot)
    environment = snapshot_environment(snapshot)
    captured = run_process(
        [str(snapshot / "bin/livespec"), "goal", "--help"], tmp_path, 10, env=environment
    )
    assert captured.exit_code == 0, captured.stderr
    assert "render" in captured.stdout


def test_codex_full_workflow_keeps_parent_registration_for_native_children() -> None:
    from tests.integration.helpers.witness_generation import generation_arguments

    assert "--ephemeral" not in generation_arguments("codex", "codex", "prompt", workflow=True)
    assert "--ephemeral" in generation_arguments("codex", "codex", "prompt")


def test_removed_or_symlink_policy_is_invalid_without_reading_external_bytes(
    tmp_path: Path,
) -> None:
    from tests.integration.helpers.witness_pipeline import prepare_pipeline_workspace
    from tests.integration.helpers.witness_snapshot import candidate_policy_identity

    prepare_pipeline_workspace(tmp_path)
    before = candidate_policy_identity(tmp_path)
    (tmp_path / "AGENTS.md").unlink()
    assert candidate_policy_identity(tmp_path) != before
    (tmp_path / "AGENTS.md").symlink_to(tmp_path.parent / "absent")
    assert candidate_policy_identity(tmp_path)["AGENTS.md"] == "invalid_symlink"


def test_detached_descendant_marks_control_incomplete_without_signalling_foreign_process(tmp_path):
    import subprocess

    sentinel = tmp_path / "detached-write"
    child = f"import time;from pathlib import Path;time.sleep(1);Path({str(sentinel)!r}).touch()"
    parent = (
        f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}],"
        "start_new_session=True);time.sleep(10)"
    )
    foreign = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(10)"])
    try:
        result = run_process([sys.executable, "-c", parent], tmp_path, 0.3)
        assert result.timed_out and not result.control_complete
        assert foreign.poll() is None
        run_process([sys.executable, "-c", "import time;time.sleep(1.1)"], tmp_path, 2)
        assert sentinel.exists()  # Detached worker was deliberately not signalled by stale PID.
        assert foreign.poll() is None
    finally:
        foreign.kill()
        foreign.wait()


def test_incomplete_workspace_preserves_original_candidate_until_explicit_cleanup(tmp_path):
    import shutil

    from tests.integration.helpers.witness_workspace import WitnessWorkspace

    with WitnessWorkspace(prefix="livespec_retention_test_") as workspace:
        workspace.preserve = True
        candidate = workspace.root / "candidate.txt"
        candidate.write_text("original generated bytes")
    try:
        assert candidate.read_text() == "original generated bytes"
    finally:
        shutil.rmtree(workspace.root)


def test_snapshot_binds_catalog_inputs_and_passes_actual_conventions(tmp_path):
    from tests.integration.helpers.witness_pipeline import REPO, prepare_pipeline_workspace
    from tests.integration.helpers.witness_snapshot import (
        snapshot_environment,
        snapshot_workflow,
        workflow_identity,
    )

    snapshot, candidate = tmp_path / "workflow", tmp_path / "candidate"
    identity = snapshot_workflow(REPO, snapshot)
    prepare_pipeline_workspace(candidate, snapshot)
    environment = snapshot_environment(snapshot)
    refreshed = run_process(
        [
            str(snapshot / "bin/livespec"),
            "conventions",
            "refresh",
            "--repo",
            str(candidate),
            "--full",
        ],
        candidate,
        60,
        env=environment,
    )
    assert refreshed.exit_code == 0, refreshed.stderr
    initialized = run_process(
        [str(snapshot / "bin/livespec"), "conventions", "gates", "init"],
        candidate,
        60,
        env=environment,
    )
    assert initialized.exit_code == 0, initialized.stderr
    captured = run_process(
        [str(snapshot / "bin/livespec"), "conventions", "verify", "--json", "--feature", "repo"],
        candidate,
        60,
        env=environment,
    )
    assert captured.exit_code == 0, captured.stdout + captured.stderr
    assert json.loads(captured.stdout)["verdict"] == "PASS"
    dependency = snapshot / "tests/test_conventions_ast_multilang.py"
    assert str(dependency.relative_to(snapshot)) in identity
    dependency.write_text(dependency.read_text() + "\n# Changed after freezing\n")
    assert workflow_identity(snapshot) != identity
    dependency.unlink()
    with pytest.raises(ValueError, match="missing_workflow_catalog_input"):
        workflow_identity(snapshot)
