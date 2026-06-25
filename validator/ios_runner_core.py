"""XCUITest runner execution helpers."""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from typing import Any

from validator.ios_simulator_core import build_env
from validator.runner_xcuitest_impl import (
    _LICENSE_ERROR,
    _MACOS_SKIP_ERROR,
    _XCODE_MISSING_ERROR,
    SCREENSHOT_TIMEOUT_SECONDS,
    UICapabilityResult,
)

STDOUT_SNIPPET_LIMIT = 200


def _truncate_stdout(stdout: str) -> str:
    """Return a bounded stdout preview for metadata payloads."""
    return stdout[:STDOUT_SNIPPET_LIMIT]


def capture_screenshot(
    handler: Any,
    screen: str,
    destination: str | None,
    test_scheme: str | None,
    launch_arguments: list[str] | None,
    project: str | None,
    workspace: str | None,
    platform_name: str | None,
    only_testing: str | None,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
) -> UICapabilityResult:
    """Run xcodebuild test and extract screenshots from the result bundle."""
    output_path, blocked = _capture_blocker(handler, screen, output_path, feature_slug, run_id)
    if blocked is not None:
        return blocked
    return _capture_after_preflight(
        handler,
        destination,
        test_scheme,
        launch_arguments,
        project,
        workspace,
        platform_name,
        only_testing,
        output_path,
    )


def _capture_blocker(
    handler: Any,
    screen: str,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
) -> tuple[Path | None, UICapabilityResult | None]:
    """Return guarded output path plus any early capture blocker."""
    output_path, blocked = _resolve_capture_output(
        handler, screen, output_path, feature_slug, run_id
    )
    if blocked is not None:
        return output_path, blocked
    toolchain_blocker = _toolchain_blocker(handler)
    if toolchain_blocker is not None:
        return output_path, toolchain_blocker
    if output_path is None:
        return output_path, _missing_output_context_result()
    return output_path, None


def _capture_after_preflight(
    handler: Any,
    destination: str | None,
    test_scheme: str | None,
    launch_arguments: list[str] | None,
    project: str | None,
    workspace: str | None,
    platform_name: str | None,
    only_testing: str | None,
    output_path: Path | None,
) -> UICapabilityResult:
    """Resolve Xcode context and run capture after path/toolchain guards."""
    resolved = _resolve_project_scheme(handler, test_scheme, project, workspace, platform_name)
    if isinstance(resolved, UICapabilityResult):
        return resolved
    test_scheme, project, workspace = resolved
    destination = _resolve_destination(handler, destination, platform_name)
    assert output_path is not None
    return _run_capture(
        handler,
        destination,
        test_scheme,
        launch_arguments,
        project,
        workspace,
        only_testing,
        output_path,
    )


def _resolve_capture_output(
    handler: Any,
    screen: str,
    output_path: Path | None,
    feature_slug: str | None,
    run_id: str | None,
) -> tuple[Path | None, UICapabilityResult | None]:
    """Resolve and guard the capture output path."""
    from validator.ui_runner_protocol import (
        RuntimeOutputMisplacedError,
        assert_output_not_in_design_screens,
    )

    if output_path is None and feature_slug and run_id:
        output_path = (
            handler.project_dir / ".specs" / "features" / feature_slug / "run" / run_id / "ios"
        )
    if output_path is not None:
        try:
            assert_output_not_in_design_screens(output_path)
        except RuntimeOutputMisplacedError as exc:
            return output_path, UICapabilityResult(
                success=False, error=str(exc), metadata={"guard": "runtime_under_design_screens"}
            )
    return output_path, None


def _missing_output_context_result() -> UICapabilityResult:
    return UICapabilityResult(
        success=False,
        error=(
            "XCUITest runner refuses to write into .specs/design/screens/ by default "
            "(C6 strict). Provide output_path or feature_slug+run_id to derive "
            ".specs/features/<slug>/run/<run_id>/ios/."
        ),
        metadata={"guard": "missing_output_context", "target": "ios"},
    )


def _toolchain_blocker(handler: Any) -> UICapabilityResult | None:
    """Return capability blocker before running xcodebuild."""
    if not handler._check_macos():
        return UICapabilityResult(
            success=False, error=_MACOS_SKIP_ERROR, metadata={"skipped": True}
        )
    if handler._get_toolchain_path() is None:
        return UICapabilityResult(
            success=False,
            error=_XCODE_MISSING_ERROR,
            metadata={"command": "xcrun --find xcodebuild"},
        )
    if not handler._check_xcode_license():
        return UICapabilityResult(success=False, error=_LICENSE_ERROR)
    return None


def _resolve_project_scheme(
    handler: Any,
    test_scheme: str | None,
    project: str | None,
    workspace: str | None,
    platform_name: str | None,
) -> tuple[str, str | None, str | None] | UICapabilityResult:
    """Resolve xcode project/workspace and scheme defaults."""
    if test_scheme is not None and (project is not None or workspace is not None):
        return test_scheme, project, workspace
    xcodeproj = handler._find_xcodeproj()
    if xcodeproj is not None:
        project, workspace = _project_workspace_from_path(
            handler.project_dir, xcodeproj, project, workspace
        )
        test_scheme = test_scheme or handler._autodetect_scheme(xcodeproj, platform=platform_name)
    if test_scheme is None:
        return UICapabilityResult(
            success=False,
            error="xcodebuild requires a -scheme.",
            metadata={"project_dir": str(handler.project_dir)},
        )
    return test_scheme, project, workspace


def _project_workspace_from_path(
    project_dir: Path, xcodeproj: Path, project: str | None, workspace: str | None
) -> tuple[str | None, str | None]:
    """Fill project/workspace args from an auto-detected Xcode path."""
    if project is not None or workspace is not None:
        return project, workspace
    rel = xcodeproj.relative_to(project_dir) if xcodeproj.is_relative_to(project_dir) else xcodeproj
    return (None, str(rel)) if xcodeproj.suffix == ".xcworkspace" else (str(rel), None)


def _resolve_destination(handler: Any, destination: str | None, platform_name: str | None) -> str:
    """Resolve an xcodebuild destination with legacy fallback."""
    if destination is not None:
        return destination
    detected = handler._autodetect_destination(platform=platform_name or "ios")
    if detected is not None:
        return detected
    if (platform_name or "").lower() == "watchos":
        return "platform=watchOS Simulator,name=Apple Watch"
    return "platform=iOS Simulator,name=iPhone 16"


def _run_capture(
    handler: Any,
    destination: str,
    test_scheme: str,
    launch_arguments: list[str] | None,
    project: str | None,
    workspace: str | None,
    only_testing: str | None,
    output_path: Path,
) -> UICapabilityResult:
    """Run or reuse xcodebuild output, then parse screenshots."""
    from validator.ios_hash_core import capture_paths, compute_swift_hash

    paths = capture_paths(handler.project_dir, only_testing)
    swift_hash = compute_swift_hash(handler.project_dir, only_testing)
    cached = _cached_capture(paths, swift_hash, handler, destination, output_path)
    if cached is not None:
        return cached
    paths["bundle"].parent.mkdir(parents=True, exist_ok=True)
    _remove_existing_bundle(paths["bundle"])
    command = handler._build_xcodebuild_command(
        destination, test_scheme, paths["bundle"], project, workspace, only_testing
    )
    result = _run_xcodebuild(
        command, handler.project_dir, build_env(launch_arguments), paths["bundle"]
    )
    if isinstance(result, UICapabilityResult):
        return result
    return _capture_result(handler, destination, output_path, paths, swift_hash, command, result)


def _cached_capture(
    paths: dict[str, Path],
    swift_hash: str | None,
    handler: Any,
    destination: str,
    output_path: Path,
) -> UICapabilityResult | None:
    """Return cached extraction result when Swift sources are unchanged."""
    if swift_hash is None or not paths["bundle"].exists() or not paths["hash"].exists():
        return None
    if paths["hash"].read_text(encoding="utf-8").strip() != swift_hash:
        return None
    destination_id = handler._friendly_destination_id(destination)
    output_dir = output_path if output_path.suffix == "" else output_path.parent
    exported = handler._parse_xcresult(paths["bundle"], output_dir, destination_id)
    return UICapabilityResult(
        success=True,
        output_path=exported[0] if exported else None,
        metadata={
            "command": "<cached — swift hash unchanged>",
            "exit_code": 0,
            "exported_paths": [str(path) for path in exported],
            "stdout_snippet": "",
            "xcresult_path": str(paths["bundle"]),
            "cached": True,
        },
    )


def _remove_existing_bundle(xcresult_path: Path) -> None:
    """Remove a previous xcresult bundle before xcodebuild writes a new one."""
    if xcresult_path.exists():
        import shutil

        shutil.rmtree(xcresult_path)


def _run_xcodebuild(
    command: list[str], project_dir: Path, env: dict[str, str] | None, xcresult_path: Path
) -> subprocess.CompletedProcess[str] | UICapabilityResult:
    """Run xcodebuild with retry for the known UI-query timeout."""
    marker = "Failed to get matching snapshots: Timed out while evaluating UI query"
    result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, 4):
        if xcresult_path.exists() and attempt > 1:
            _remove_existing_bundle(xcresult_path)
        attempt_result = _run_xcodebuild_once(command, project_dir, env)
        if isinstance(attempt_result, UICapabilityResult):
            return attempt_result
        result = attempt_result
        if marker not in ((result.stdout or "") + (result.stderr or "")):
            return result
    assert result is not None
    return result


def _run_xcodebuild_once(
    command: list[str], project_dir: Path, env: dict[str, str] | None
) -> subprocess.CompletedProcess[str] | UICapabilityResult:
    """Run one xcodebuild attempt."""
    try:
        return subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=SCREENSHOT_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return UICapabilityResult(
            success=False,
            error=f"xcodebuild test timed out after {error.timeout}s",
            metadata={"timeout": error.timeout, "command": " ".join(command)},
        )
    except OSError as error:
        return UICapabilityResult(
            success=False,
            error=f"Failed to execute xcodebuild: {error}",
            metadata={"command": " ".join(command)},
        )


def _capture_result(
    handler: Any,
    destination: str,
    output_path: Path,
    paths: dict[str, Path],
    swift_hash: str | None,
    command: list[str],
    result: subprocess.CompletedProcess[str],
) -> UICapabilityResult:
    """Map xcodebuild capture output to UICapabilityResult."""
    license_error = _license_result(result, command)
    if license_error is not None:
        return license_error
    if not paths["bundle"].exists():
        return _missing_bundle_result(command, result)
    output_dir = output_path if output_path.suffix == "" else output_path.parent
    exported = handler._parse_xcresult(
        paths["bundle"], output_dir, handler._friendly_destination_id(destination)
    )
    _write_swift_hash(paths["hash"], swift_hash, result.returncode, exported)
    return _capture_result_payload(command, result, exported, paths["bundle"])


def _missing_bundle_result(
    command: list[str], result: subprocess.CompletedProcess[str]
) -> UICapabilityResult:
    """Return a failed result for missing xcresult bundles."""
    return UICapabilityResult(
        metadata={
            "command": " ".join(command),
            "exit_code": result.returncode,
            "stdout_snippet": _truncate_stdout(result.stdout),
        },
        success=False,
        error="No .xcresult bundle produced by xcodebuild test",
    )


def _write_swift_hash(
    hash_path: Path, swift_hash: str | None, returncode: int, exported: list[Path]
) -> None:
    """Persist the Swift hash after a successful or useful capture."""
    if swift_hash is not None and (returncode == 0 or bool(exported)):
        with contextlib.suppress(OSError):
            hash_path.write_text(swift_hash, encoding="utf-8")


def _capture_result_payload(
    command: list[str],
    result: subprocess.CompletedProcess[str],
    exported: list[Path],
    bundle_path: Path,
) -> UICapabilityResult:
    """Return the structured XCUITest capture payload."""
    return UICapabilityResult(
        success=result.returncode == 0 or bool(exported),
        output_path=exported[0] if exported else None,
        error=result.stderr or None if not exported and result.returncode != 0 else None,
        metadata={
            "command": " ".join(command),
            "exit_code": result.returncode,
            "exported_paths": [str(path) for path in exported],
            "stdout_snippet": _truncate_stdout(result.stdout),
            "xcresult_path": str(bundle_path),
        },
    )


def _license_result(
    result: subprocess.CompletedProcess[str], command: list[str]
) -> UICapabilityResult | None:
    """Return the license blocker when xcodebuild output reports it."""
    combined = (result.stdout + result.stderr).lower()
    if "license" in combined and "not been accepted" in combined:
        return UICapabilityResult(
            success=False, error=_LICENSE_ERROR, metadata={"command": " ".join(command)}
        )
    return None


def run_flow(
    handler: Any,
    destination: str | None,
    test_scheme: str | None,
    launch_arguments: list[str] | None,
    platform_name: str | None,
) -> UICapabilityResult:
    """Run the full XCUITest suite and report pass/fail."""
    from validator.ios_flow_core import run_flow as run_xcuitest_flow

    return run_xcuitest_flow(handler, destination, test_scheme, launch_arguments, platform_name)
