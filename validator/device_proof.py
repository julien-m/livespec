# LiveSpec traceability anchors: @spec(FR-004), @spec(FR-005), @spec(FR-006),
# @spec(FR-007), @spec(FR-008), @spec(FR-009), @spec(FR-010)

"""Agent Device proof/replay adapter core."""

# @spec FR-004: Agent Device calls bind UDID/session, FR-010: pinned package
# — .specs/features/074-agent-device-proof-adapter/spec.md#fr-004

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from validator.journeys.paths import journey_runs_dir

AGENT_DEVICE_PACKAGE_DEFAULT = "agent-device@0.18.3"
AGENT_DEVICE_PACKAGE_ENV = "LIVESPEC_AGENT_DEVICE_PACKAGE"
WATCHOS_GUIDANCE = "Use LiveSpec/XCTest and xcrun simctl io <watch_udid> screenshot."
OPEN_TIMEOUT_SECONDS = 300
CHECK_TIMEOUT_SECONDS = 60
LISTAPPS_TIMEOUT_SECONDS = 30
SUPPORTED_PLATFORMS = {"ios", "android", "web", "macos"}


@dataclass(frozen=True)
class DeviceCheck:
    name: str
    status: str
    code: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class DeviceProofReport:
    bundle: str
    udid: str
    session: str
    platform: str
    checks: list[DeviceCheck]
    screenshot: str | None = None


@dataclass(frozen=True)
class _Context:
    project_root: Path
    bundle: str
    platform: str
    udid: str
    session: str
    out_dir: Path
    checks: list[DeviceCheck]


class DeviceProofFailure(Exception):
    def __init__(self, report: DeviceProofReport, exit_code: int) -> None:
        super().__init__(report.checks[-1].code if report.checks else "device_proof_failed")
        self.report = report
        self.exit_code = exit_code


def run_device_proof(
    project_root: Path,
    *,
    bundle: str,
    platform: str,
    udid: str | None,
    journey: str | None,
    session: str,
    out_dir: Path | None,
) -> DeviceProofReport:
    """Run the bound Agent Device proof flow."""
    context = _resolve_context(project_root, bundle, platform, udid, journey, session, out_dir)
    package = os.environ.get(AGENT_DEVICE_PACKAGE_ENV, AGENT_DEVICE_PACKAGE_DEFAULT)
    _open_app(context, package)
    _verify_appstate(context, package)
    _write_snapshot_and_verify(context, package)
    screenshot_path = _capture_screenshot(context, package)
    return _report(context, str(screenshot_path))


def _resolve_context(
    project_root: Path,
    bundle: str,
    platform: str,
    udid: str | None,
    journey: str | None,
    session: str,
    out_dir: Path | None,
) -> _Context:
    checks: list[DeviceCheck] = []
    normalized_platform = _normalize_platform(bundle, udid, session, platform, checks)
    resolved_udid = udid or _udid_from_journey_receipt(
        project_root, journey, bundle, session, normalized_platform, checks
    )
    output_dir = out_dir or (project_root / ".specs" / ".device-proof")
    output_dir.mkdir(parents=True, exist_ok=True)
    context = _Context(
        project_root, bundle, normalized_platform, resolved_udid, session, output_dir, checks
    )
    if normalized_platform == "ios":
        _ensure_bundle_installed(context)
    return context


def _normalize_platform(
    bundle: str,
    udid: str | None,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
) -> str:
    normalized = platform.lower()
    if normalized == "watchos":
        _platform_fail(bundle, udid or "", session, normalized, checks, WATCHOS_GUIDANCE)
    if normalized not in SUPPORTED_PLATFORMS:
        _platform_fail(
            bundle, udid or "", session, normalized, checks, f"Unsupported platform: {platform}"
        )
    return normalized


def _udid_from_journey_receipt(
    project_root: Path,
    journey: str | None,
    bundle: str,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
) -> str:
    if journey is None:
        _receipt_fail(bundle, session, platform, checks, "device_udid_required")
    receipt_path = journey_runs_dir(project_root, journey) / "last-run.json"
    if not receipt_path.exists():
        _receipt_fail(
            bundle, session, platform, checks, "device_receipt_missing", str(receipt_path)
        )
    data = _read_receipt_json(receipt_path, bundle, session, platform, checks)
    if data.get("platform") == "watchos":
        _platform_fail(bundle, "", session, "watchos", checks, WATCHOS_GUIDANCE)
    receipt_udid = data.get("udid")
    if not isinstance(receipt_udid, str) or not receipt_udid:
        _receipt_fail(
            bundle, session, platform, checks, "device_receipt_no_udid", str(receipt_path)
        )
    return receipt_udid


def _read_receipt_json(
    receipt_path: Path,
    bundle: str,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
) -> dict[object, object]:
    try:
        raw_data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        _receipt_fail(
            bundle,
            session,
            platform,
            checks,
            "device_receipt_invalid",
            f"{receipt_path}: {error.msg}",
        )
    if not isinstance(raw_data, dict):
        _receipt_fail(
            bundle,
            session,
            platform,
            checks,
            "device_receipt_invalid",
            f"{receipt_path}: JSON root must be an object",
        )
    return raw_data


def _ensure_bundle_installed(context: _Context) -> None:
    try:
        result = _run_subprocess(
            ["xcrun", "simctl", "listapps", context.udid],
            cwd=str(context.project_root),
            capture_output=True,
            text=True,
            timeout=LISTAPPS_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        _fail_context(context, "device_simctl_missing", "xcrun simctl not found", 1)
    if result.returncode != 0:
        _fail_context(context, "device_listapps_failed", _process_output(result), 1)
    if context.bundle not in result.stdout:
        _fail_context(
            context,
            "device_bundle_not_installed",
            f"{context.bundle} is not installed on {context.udid}",
            1,
        )
    context.checks.append(DeviceCheck("listapps", "pass"))


def _open_app(context: _Context, package: str) -> None:
    _run_agent_device(
        context,
        package,
        "open",
        [context.bundle, "--relaunch"],
        OPEN_TIMEOUT_SECONDS,
    )
    context.checks.append(DeviceCheck("open", "pass"))


def _verify_appstate(context: _Context, package: str) -> None:
    result = _run_agent_device(context, package, "appstate", [], CHECK_TIMEOUT_SECONDS)
    foreground = _parse_prefixed_value(result.stdout, ("Foreground app:", "Bundle:"))
    if foreground != context.bundle:
        _foreground_fail(context, "appstate", foreground)
    context.checks.append(DeviceCheck("appstate", "pass"))


def _write_snapshot_and_verify(context: _Context, package: str) -> None:
    result = _run_agent_device(context, package, "snapshot", [], CHECK_TIMEOUT_SECONDS)
    (context.out_dir / "snapshot.txt").write_text(result.stdout, encoding="utf-8")
    snapshot_bundle = _parse_prefixed_value(result.stdout, ("App:",))
    if snapshot_bundle != context.bundle:
        _foreground_fail(context, "snapshot", snapshot_bundle)
    context.checks.append(DeviceCheck("snapshot", "pass"))


def _capture_screenshot(context: _Context, package: str) -> Path:
    screenshot_path = context.out_dir / "screenshot.png"
    _run_agent_device(
        context,
        package,
        "screenshot",
        ["--out", str(screenshot_path)],
        CHECK_TIMEOUT_SECONDS,
    )
    if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
        context.checks.append(
            DeviceCheck("screenshot", "fail", "device_screenshot_empty", str(screenshot_path))
        )
        raise DeviceProofFailure(_report(context, str(screenshot_path)), 1)
    context.checks.append(DeviceCheck("screenshot", "pass"))
    return screenshot_path


def _run_agent_device(
    context: _Context,
    package: str,
    verb: str,
    args: list[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    argv = _agent_device_argv(context, package, verb, args)
    try:
        result = _run_subprocess(
            argv,
            cwd=str(context.project_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        _agent_command_fail(context, verb, f"command not found: {argv[0]}")
    except subprocess.TimeoutExpired as error:
        _agent_command_fail(context, verb, f"timed out after {error.timeout}s")
    if result.returncode != 0:
        _agent_command_fail(context, verb, _process_output(result) or f"exit {result.returncode}")
    return result


def _agent_device_argv(
    context: _Context,
    package: str,
    verb: str,
    args: list[str],
) -> list[str]:
    return [
        "npx",
        "-y",
        package,
        verb,
        *args,
        "--platform",
        context.platform,
        "--udid",
        context.udid,
        "--session",
        context.session,
    ]


def _run_subprocess(
    argv: list[str],
    *,
    cwd: str,
    capture_output: bool,
    text: bool,
    timeout: int,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check,
    )


def _foreground_fail(context: _Context, step: str, actual_bundle: str | None) -> NoReturn:
    detail = (
        f"{step} reported {actual_bundle or '<unknown>'}; expected {context.bundle}. "
        f"Verify the targeted UDID first, then simctl listapps {context.udid}."
    )
    context.checks.append(DeviceCheck(step, "fail", "device_foreground_mismatch", detail))
    raise DeviceProofFailure(_report(context, None), 1)


def _agent_command_fail(context: _Context, step: str, detail: str) -> NoReturn:
    context.checks.append(DeviceCheck(step, "fail", "device_agent_command_failed", detail))
    raise DeviceProofFailure(_report(context, None), 1)


def _platform_fail(
    bundle: str,
    udid: str,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
    detail: str,
) -> NoReturn:
    _fail(bundle, udid, session, platform, checks, "device_platform_unsupported", detail, 2)


def _receipt_fail(
    bundle: str,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
    code: str,
    detail: str = "Provide --udid or --journey.",
) -> NoReturn:
    _fail(bundle, "", session, platform, checks, code, detail, 2)


def _fail_context(context: _Context, code: str, detail: str, exit_code: int) -> NoReturn:
    _fail(
        context.bundle,
        context.udid,
        context.session,
        context.platform,
        context.checks,
        code,
        detail,
        exit_code,
    )


def _fail(
    bundle: str,
    udid: str,
    session: str,
    platform: str,
    checks: list[DeviceCheck],
    code: str,
    detail: str,
    exit_code: int,
) -> NoReturn:
    checks.append(DeviceCheck("preflight", "fail", code, detail))
    raise DeviceProofFailure(DeviceProofReport(bundle, udid, session, platform, checks), exit_code)


def _report(context: _Context, screenshot: str | None) -> DeviceProofReport:
    return DeviceProofReport(
        context.bundle, context.udid, context.session, context.platform, context.checks, screenshot
    )


def _parse_prefixed_value(output: str, prefixes: tuple[str, ...]) -> str | None:
    for line in output.splitlines():
        stripped = line.strip()
        for prefix in prefixes:
            if stripped.startswith(prefix):
                return stripped[len(prefix) :].strip() or None
    return None


def _process_output(result: subprocess.CompletedProcess[str]) -> str:
    parts = [stream.strip() for stream in (result.stderr, result.stdout) if stream.strip()]
    return "\n".join(parts)
