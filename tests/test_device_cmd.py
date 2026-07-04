"""Tests for the Agent Device proof adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


def _setup_project(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    (tmp_path / ".specs").mkdir()
    monkeypatch.chdir(tmp_path)


def _success_fake(calls: list[list[str]]) -> object:
    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        if argv[3] == "appstate":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout="Foreground app: com.example.app\n",
                stderr="",
            )
        if argv[3] == "snapshot":
            return subprocess.CompletedProcess(argv, 0, stdout="App: com.example.app\n", stderr="")
        if argv[3] == "screenshot":
            out_path = Path(argv[argv.index("--out") + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"png")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    return fake_run


def _invoke(*args: str) -> object:
    return runner.invoke(app, ["device", "proof", "com.example.app", *args])


def test_device_proof_binds_udid_on_every_agent_device_call(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-004: every Agent Device command uses --udid and --session, never --device."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "validator.device_proof._run_subprocess",
        _success_fake(calls),
    )

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17", "--session", "live")

    assert result.exit_code == 0, result.output
    agent_calls = [argv for argv in calls if argv[:3] == ["npx", "-y", "agent-device@0.18.3"]]
    assert len(agent_calls) == 4
    for argv in agent_calls:
        assert argv[argv.index("--udid") + 1] == "IPHONE-17"
        assert argv[argv.index("--session") + 1] == "live"
        assert "--device" not in argv


def test_device_proof_honors_agent_device_package_override(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-010: env override replaces the pinned default package when requested."""
    _setup_project(tmp_path, monkeypatch)
    monkeypatch.setenv("LIVESPEC_AGENT_DEVICE_PACKAGE", "agent-device@0.18.4")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "validator.device_proof._run_subprocess",
        _success_fake(calls),
    )

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 0, result.output
    agent_calls = [argv for argv in calls if argv[:1] == ["npx"]]
    assert agent_calls
    assert all(argv[2] == "agent-device@0.18.4" for argv in agent_calls)


def test_device_proof_fails_fast_on_settings_foreground(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-007: Settings foreground mismatch fails before snapshot or screenshot."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        if argv[3] == "appstate":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout="Foreground app: com.apple.Preferences\n",
                stderr="",
            )
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_foreground_mismatch" in result.output
    assert all(argv[3] != "snapshot" for argv in calls if argv[:1] == ["npx"])
    assert all(argv[3] != "screenshot" for argv in calls if argv[:1] == ["npx"])


def test_device_proof_fails_on_snapshot_bundle_mismatch(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-007: snapshot App mismatch fails with the same stable code."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        if argv[3] == "appstate":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout="Foreground app: com.example.app\n",
                stderr="",
            )
        if argv[3] == "snapshot":
            return subprocess.CompletedProcess(argv, 0, stdout="App: com.other.app\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_foreground_mismatch" in result.output


def test_device_proof_rejects_watchos_platform_with_simctl_guidance(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-009: watchOS is rejected before any Agent Device process starts."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "validator.device_proof._run_subprocess",
        _success_fake(calls),
    )

    result = _invoke("--platform", "watchos", "--udid", "WATCH-1")

    assert result.exit_code == 2
    assert "device_platform_unsupported" in result.output
    assert "simctl io" in result.output
    assert not calls


def test_device_proof_requires_installed_bundle(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-006: iOS proof refuses to open a bundle absent from the target UDID."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="com.other.app\n", stderr="")

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_bundle_not_installed" in result.output
    assert all(argv[:1] != ["npx"] for argv in calls)


def test_device_proof_consumes_udid_from_journey_receipt(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-005: --journey resolves the UDID from last-run.json."""
    _setup_project(tmp_path, monkeypatch)
    receipt_dir = tmp_path / ".specs" / "journeys" / "checkout" / "runs"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "last-run.json").write_text(
        json.dumps({"udid": "IPHONE-17", "platform": "ios"}),
        encoding="utf-8",
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "validator.device_proof._run_subprocess",
        _success_fake(calls),
    )

    result = _invoke("--platform", "ios", "--journey", "checkout")

    assert result.exit_code == 0, result.output
    agent_calls = [argv for argv in calls if argv[:1] == ["npx"]]
    assert all(argv[argv.index("--udid") + 1] == "IPHONE-17" for argv in agent_calls)


def test_device_proof_reports_missing_or_udidless_receipt(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-005: missing or incomplete journey receipts produce stable usage errors."""
    _setup_project(tmp_path, monkeypatch)

    missing = _invoke("--platform", "ios", "--journey", "missing")
    assert missing.exit_code == 2
    assert "device_receipt_missing" in missing.output

    receipt_dir = tmp_path / ".specs" / "journeys" / "checkout" / "runs"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "last-run.json").write_text(json.dumps({"platform": "ios"}), encoding="utf-8")

    no_udid = _invoke("--platform", "ios", "--journey", "checkout")
    assert no_udid.exit_code == 2
    assert "device_receipt_no_udid" in no_udid.output


def test_device_proof_reports_malformed_receipt(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-005: malformed receipts fail with a stable code instead of traceback."""
    _setup_project(tmp_path, monkeypatch)
    receipt_dir = tmp_path / ".specs" / "journeys" / "checkout" / "runs"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "last-run.json").write_text("{not json", encoding="utf-8")

    result = _invoke("--platform", "ios", "--journey", "checkout")

    assert result.exit_code == 2
    assert "device_receipt_invalid" in result.output


def test_device_proof_fails_on_empty_screenshot(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-008: empty screenshots fail the proof."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        if argv[3] == "appstate":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout="Foreground app: com.example.app\n",
                stderr="",
            )
        if argv[3] == "snapshot":
            return subprocess.CompletedProcess(argv, 0, stdout="App: com.example.app\n", stderr="")
        if argv[3] == "screenshot":
            Path(argv[argv.index("--out") + 1]).write_bytes(b"")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_screenshot_empty" in result.output


def test_device_proof_reports_agent_device_command_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-004: Agent Device process failures become stable proof checks."""
    _setup_project(tmp_path, monkeypatch)

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="agent failed")

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_agent_command_failed" in result.output
    assert "agent failed" in result.output


def test_device_proof_reports_agent_device_timeout(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-004: Agent Device timeouts become stable proof checks."""
    _setup_project(tmp_path, monkeypatch)

    def fake_run(
        argv: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["xcrun", "simctl", "listapps"]:
            return subprocess.CompletedProcess(argv, 0, stdout="com.example.app\n", stderr="")
        raise subprocess.TimeoutExpired(argv, timeout=60)

    monkeypatch.setattr("validator.device_proof._run_subprocess", fake_run)

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17")

    assert result.exit_code == 1
    assert "device_agent_command_failed" in result.output
    assert "timed out" in result.output


def test_device_proof_json_output_reports_checks(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """FR-004: JSON output includes target identity, checks, and screenshot path."""
    _setup_project(tmp_path, monkeypatch)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        "validator.device_proof._run_subprocess",
        _success_fake(calls),
    )

    result = _invoke("--platform", "ios", "--udid", "IPHONE-17", "--json")

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["bundle"] == "com.example.app"
    assert payload["udid"] == "IPHONE-17"
    assert payload["session"] == "livespec-proof"
    assert payload["screenshot"].endswith("screenshot.png")
    assert all(check["status"] == "pass" for check in payload["checks"])
