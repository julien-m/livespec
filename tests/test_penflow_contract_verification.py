"""C51 consumer protocol tests; transport doubles do not certify producer behavior."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.penflow_approval_fixtures import approved_feature
from validator.cli import app
from validator.penflow_contract import get_penflow_contract_status
from validator.penflow_verification import VerificationProfile, verify_penflow_report


def _workspace(root: Path) -> Path:
    workspace = root / "penflow"
    (workspace / "flow-ui-contract").mkdir(parents=True)
    for name, value in {
        "ui.pen": {"children": [{"type": "frame", "width": 1440, "height": 900}]},
        "semantic-ui-tree.json": {"flows": [], "screens": []},
        "expected-ui-tree.json": {"screens": []},
        "code-ir.json": {"flows": []},
        "run-report.json": {"protocol_test_placeholder": True},
    }.items():
        (workspace / name).write_text(json.dumps(value))
    return workspace


def _response(root: Path | None = None, profile: str = "design") -> dict[str, object]:
    return {
        "kind": "penflow-verification-validation",
        "version": 1,
        "status": "PASS",
        "required_profile": profile,
        "profile": profile,
        "issues": [],
        "report_sha256": hashlib.sha256((root / "penflow/run-report.json").read_bytes()).hexdigest()
        if root
        else "",
        "scope": {
            "project_root": str(root.resolve()),
            "workspace": str((root / "penflow").resolve()),
        }
        if root
        else {},
        "build_manifest": {
            "path": str((root / "runner-build.json").resolve()),
            "sha256": hashlib.sha256((root / "runner-build.json").read_bytes()).hexdigest(),
        }
        if root and profile == "implementation"
        else None,
    }


def _transport(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    returncode: int = 0,
) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr("validator.penflow_verification.shutil.which", lambda _: "/tools/penflow")

    def run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(arguments, returncode, json.dumps(payload), "")

    monkeypatch.setattr("validator.penflow_verification.subprocess.run", run)
    return calls


@pytest.mark.parametrize("profile", list(VerificationProfile))
def test_certification_delegates_exact_profile_project_and_independent_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile: VerificationProfile,
) -> None:
    workspace = _workspace(tmp_path)
    approved_feature(tmp_path)
    build = tmp_path / "runner-build.json"
    build.write_text("{}")
    calls = _transport(monkeypatch, _response(tmp_path, profile.value))
    status = get_penflow_contract_status(
        tmp_path,
        required_profile=profile,
        feature_slug="001-test",
        build_manifest=build if profile is VerificationProfile.IMPLEMENTATION else None,
    )
    assert status.certified
    assert calls[0][:3] == [
        "/tools/penflow",
        "validate-report",
        str((workspace / "run-report.json").resolve()),
    ]
    assert calls[0][calls[0].index("--project") + 1] == str(tmp_path.resolve())
    assert calls[0][calls[0].index("--required-profile") + 1] == profile.value
    assert "--schema" in calls[0] and "--json" in calls[0]
    assert ("--build-manifest" in calls[0]) == (profile is VerificationProfile.IMPLEMENTATION)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("kind", "penflow-verification-report"),
        ("version", True),
        ("version", "1"),
        ("version", 2),
        ("required_profile", "implementation"),
        ("profile", "implementation"),
        ("profile", None),
        ("status", "READY"),
        ("status", "FAIL"),
        ("issues", None),
        ("issues", {}),
        ("issues", [{"code": "missing"}]),
    ],
)
def test_invalid_or_noncertifying_envelope_never_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: object,
) -> None:
    workspace = _workspace(tmp_path)
    response = _response(tmp_path)
    response[key] = value
    _transport(monkeypatch, response)
    result = verify_penflow_report(tmp_path, workspace, VerificationProfile.DESIGN, None)
    assert result.status != "PASS"


@pytest.mark.parametrize("key", list(_response()))
def test_missing_envelope_field_never_certifies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
) -> None:
    workspace = _workspace(tmp_path)
    response = _response(tmp_path)
    del response[key]
    _transport(monkeypatch, response)
    assert (
        verify_penflow_report(tmp_path, workspace, VerificationProfile.DESIGN, None).status
        != "PASS"
    )


def test_nonzero_process_cannot_certify_pass_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    _transport(monkeypatch, _response(tmp_path), returncode=1)
    assert (
        verify_penflow_report(tmp_path, workspace, VerificationProfile.DESIGN, None).status
        == "BLOCKED"
    )


@pytest.mark.parametrize("failure", ["missing", "timeout", "launch", "invalid_json", "encoding"])
def test_transport_failures_are_noncertifying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setattr(
        "validator.penflow_verification.shutil.which",
        lambda _: None if failure == "missing" else "/tools/penflow",
    )

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if failure == "timeout":
            raise subprocess.TimeoutExpired("penflow", 30)
        if failure == "launch":
            raise OSError("unavailable")
        if failure == "encoding":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return subprocess.CompletedProcess(["penflow"], 0, "not json", "")

    monkeypatch.setattr("validator.penflow_verification.subprocess.run", run)
    assert (
        verify_penflow_report(tmp_path, workspace, VerificationProfile.DESIGN, None).status
        == "BLOCKED"
    )


@pytest.mark.parametrize("profile", list(VerificationProfile))
def test_absent_workspace_blocks_explicit_certification(
    tmp_path: Path, profile: VerificationProfile
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "penflow-contract",
            "status",
            "--project",
            str(tmp_path),
            "--required-profile",
            profile.value,
            "--json",
        ],
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["verdict"] == "BLOCKED" and payload["certified"] is False


def test_require_actual_cannot_be_downgraded(tmp_path: Path) -> None:
    _workspace(tmp_path)
    status = get_penflow_contract_status(
        tmp_path,
        require_actual=True,
        required_profile=VerificationProfile.DESIGN,
    )
    assert not status.certified
    assert status.verification is not None
    assert status.verification.reason == "conflicting_verification_profiles"


def test_implementation_manifest_is_not_taken_from_report(tmp_path: Path) -> None:
    _workspace(tmp_path)
    status = get_penflow_contract_status(tmp_path, require_actual=True)
    assert not status.certified
    assert status.verification is not None
    assert status.verification.reason == "independent_build_manifest_required"


def test_inspection_does_not_invoke_certification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _workspace(tmp_path)
    calls = _transport(monkeypatch, _response(tmp_path))
    result = CliRunner().invoke(
        app, ["penflow-contract", "status", "--project", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["verdict"] == "READY"
    assert json.loads(result.stdout)["certified"] is False
    assert calls == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("report_sha256", "0" * 64),
        ("scope", {"project_root": "/other", "workspace": "/other/penflow"}),
        ("scope", None),
        ("build_manifest", {"path": "/other/build.json", "sha256": "0" * 64}),
    ],
)
def test_foreign_validation_identity_never_certifies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: object,
) -> None:
    workspace = _workspace(tmp_path)
    response = _response(tmp_path)
    response[key] = value
    _transport(monkeypatch, response)
    assert (
        verify_penflow_report(tmp_path, workspace, VerificationProfile.DESIGN, None).status
        == "BLOCKED"
    )


@pytest.mark.parametrize("changed_input", ["report", "build", "symlink"])
def test_input_mutation_during_revalidation_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_input: str,
) -> None:
    workspace = _workspace(tmp_path)
    build = tmp_path / "runner-build.json"
    build.write_text("{}")
    report = workspace / "run-report.json"
    response = _response(tmp_path, "implementation")
    monkeypatch.setattr("validator.penflow_verification.shutil.which", lambda _: "/tools/penflow")

    def run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if changed_input == "symlink":
            replacement = workspace / "other-report.json"
            replacement.write_bytes(report.read_bytes())
            report.unlink()
            report.symlink_to(replacement)
        else:
            (report if changed_input == "report" else build).write_text('{"changed":true}')
        return subprocess.CompletedProcess(arguments, 0, json.dumps(response), "")

    monkeypatch.setattr("validator.penflow_verification.subprocess.run", run)
    result = verify_penflow_report(tmp_path, workspace, VerificationProfile.IMPLEMENTATION, build)
    assert result.status == "BLOCKED" and result.reason == "verification_inputs_changed"


def test_explicit_cli_certificate_has_pass_and_certified_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _workspace(tmp_path)
    approved_feature(tmp_path)
    _transport(monkeypatch, _response(tmp_path))
    result = CliRunner().invoke(
        app,
        [
            "penflow-contract",
            "status",
            "--project",
            str(tmp_path),
            "--required-profile",
            "design",
            "--feature",
            "001-test",
            "--json",
        ],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["verdict"] == "PASS"
    assert json.loads(result.stdout)["certified"] is True


@pytest.mark.parametrize("feature_slug", [None, "001-test"])
def test_explicit_certification_requires_independently_approved_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, feature_slug: str | None
) -> None:
    _workspace(tmp_path)
    calls = _transport(monkeypatch, _response(tmp_path))
    status = get_penflow_contract_status(
        tmp_path, required_profile=VerificationProfile.DESIGN, feature_slug=feature_slug
    )
    assert not status.certified
    assert status.verification is not None
    assert status.verification.status == "BLOCKED"
    assert status.verification.reason.startswith("approved_requirements_invalid:")
    assert calls == []
