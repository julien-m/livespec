"""Feature 077 closure gates at finalization and its idempotent boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

import validator.finalize as finalize_module
from tests.test_finalize import _implement_request, _make_specs_tree, _registry_snapshot
from validator.cli import app
from validator.finalize import FinalizeError, apply_finalization, verify_finalization


# @spec AC-007: current proof before lifecycle success
# — .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-007
def test_apply_forwards_manifest_before_idempotent_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure, raising=False)
    manifest = tmp_path / "runner-build.json"
    request = _implement_request()
    apply_finalization(tmp_path, request, build_manifest=manifest)
    assert (
        apply_finalization(tmp_path, request, build_manifest=manifest).outcome
        == "already_finalized"
    )
    assert closure.call_count == 2
    closure.assert_called_with(tmp_path, request.feature_slug, build_manifest=manifest)


def test_preparation_does_not_require_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure, raising=False)
    apply_finalization(tmp_path, replace(_implement_request(), status=None))
    closure.assert_not_called()


def test_current_implemented_cannot_bypass_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure, raising=False)
    apply_finalization(tmp_path, _implement_request())
    closure.reset_mock()
    apply_finalization(tmp_path, replace(_implement_request(), status=None))
    closure.assert_called_once()


def test_stale_replay_blocks_without_registry_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator.penflow_closure import PenflowClosureError

    specs = _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure)
    apply_finalization(tmp_path, _implement_request())
    before = _registry_snapshot(specs)
    closure.side_effect = PenflowClosureError("current report rejected")
    with pytest.raises(FinalizeError, match="current report rejected") as error:
        apply_finalization(tmp_path, _implement_request())
    assert _registry_snapshot(specs) == before
    assert error.value.receipt_path is not None
    assert json.loads(error.value.receipt_path.read_text())["verdict"] == "BLOCKED"


def test_verify_revalidates_current_implemented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator.penflow_closure import PenflowClosureError

    _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    closure.side_effect = PenflowClosureError("stale build")
    result = verify_finalization(tmp_path, request.feature_slug, run_id="verify-stale")
    assert result.verdict == "FAIL"
    assert any(item.rule_id == "penflow.closure" for item in result.violations)


@pytest.mark.parametrize("operation", ["apply", "verify"])
def test_cli_forwards_runner_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure, raising=False)
    monkeypatch.chdir(tmp_path)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    closure.reset_mock()
    manifest = tmp_path / "independent-build.json"
    args = [
        "finalize",
        operation,
        "--feature",
        request.feature_slug,
        "--build-manifest",
        str(manifest),
    ]
    if operation == "apply":
        entry = tmp_path / "entry.md"
        entry.write_text("Feature: verify closure")
        args += [
            "--command",
            "spec-implement",
            "--entry-file",
            str(entry),
            "--status",
            "Implemented",
        ]
    CliRunner().invoke(app, args, catch_exceptions=False)
    closure.assert_called_once_with(tmp_path, request.feature_slug, build_manifest=manifest)


def test_real_visual_closure_blocks_before_implemented_write(tmp_path: Path) -> None:
    specs = _make_specs_tree(tmp_path)
    spec = specs / "features" / _implement_request().feature_slug / "spec.md"
    spec.write_text(spec.read_text().replace("status: Planned", "status: Planned\nvisual: true"))
    before = _registry_snapshot(specs)
    with pytest.raises(FinalizeError, match="visual_authority_conflict"):
        apply_finalization(tmp_path, _implement_request())
    after = _registry_snapshot(specs)
    # Certification runs under the real project lock; only its empty lockfile is new.
    assert after.pop(str(specs / ".LOCK")) == b""
    assert after == before


def test_cli_missing_visual_proof_emits_blocked_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    specs = _make_specs_tree(tmp_path)
    spec = specs / "features" / _implement_request().feature_slug / "spec.md"
    spec.write_text(spec.read_text().replace("status: Planned", "status: Planned\nvisual: true"))
    entry = tmp_path / "entry.md"
    entry.write_text("Feature: implementation closure")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "finalize",
            "apply",
            "--feature",
            _implement_request().feature_slug,
            "--command",
            "spec-implement",
            "--entry-file",
            str(entry),
            "--status",
            "Implemented",
            "--json",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 9
    assert json.loads(result.stdout)["outcome"] == "BLOCKED"
    assert "verification_failed" in result.stderr


@pytest.mark.parametrize("reopened_status", ["In Progress", "Draft"])
def test_stale_implemented_can_reopen_but_cannot_reclose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reopened_status: str
) -> None:
    from validator.parser import parse_file
    from validator.penflow_closure import PenflowClosureError

    specs = _make_specs_tree(tmp_path)
    closure = Mock()
    monkeypatch.setattr(finalize_module, "require_penflow_closure", closure)
    request = _implement_request()
    apply_finalization(tmp_path, request)
    closure.reset_mock()
    closure.side_effect = PenflowClosureError("stale build")
    apply_finalization(tmp_path, replace(request, status=reopened_status, command="spec-fix"))
    closure.assert_not_called()
    assert (
        parse_file(specs / "features" / request.feature_slug / "spec.md").metadata["status"]
        == reopened_status
    )
    with pytest.raises(FinalizeError, match="stale build"):
        apply_finalization(tmp_path, request)


def test_valid_reclosure_updates_live_status_despite_old_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from validator.parser import parse_file

    specs = _make_specs_tree(tmp_path)
    monkeypatch.setattr(finalize_module, "require_penflow_closure", Mock())
    request = _implement_request()
    apply_finalization(tmp_path, request)
    apply_finalization(tmp_path, replace(request, status="Draft", command="spec-fix"))
    result = apply_finalization(tmp_path, request)
    assert result.outcome == "applied"
    assert set(result.written) == {"spec_status", "readme"}
    assert (
        parse_file(specs / "features" / request.feature_slug / "spec.md").metadata["status"]
        == "Implemented"
    )
    assert "Implemented" in (specs / "README.md").read_text()
