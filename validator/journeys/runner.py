# LiveSpec traceability anchors
# @spec(FR-024)
# @spec(FR-027)
# @spec(FR-029)

"""Compiled-only execution planner for User Journeys v2."""

# @spec FR-024, FR-027: compiled-only journey execution and stage run policies
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-024

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from .manifest import COMPILER_VERSION, CompiledManifest, read_compiled_manifest
from .models import JourneyIssue, JourneySeverity
from .paths import iter_journey_source_paths
from .schema import JourneySourceV2, RunPolicyValue, RunStage

# Native UI regressions can boot simulators/browsers; 10 minutes avoids short CI
# flake while still bounding hung runners.
RUNNER_TIMEOUT_SECONDS = 600
# simctl list should be quick; 30s bounds host CLI hangs without hiding startup lag.
SIMULATOR_COMMAND_TIMEOUT_SECONDS = 30
# bootstatus can cold-start CoreSimulator, so it gets a wider bounded wait.
SIMULATOR_BOOT_TIMEOUT_SECONDS = 120
XCODE_DESTINATION_ENV = "LIVESPEC_XCODE_DESTINATION"
XCODE_SCHEME_ENV = "LIVESPEC_XCODE_SCHEME"


@dataclass(frozen=True)
class _SimulatorDevice:
    """Simulator device metadata needed to select and boot XCUITest destinations."""

    name: str
    udid: str
    is_available: bool


class SimulatorDiscoveryError(Exception):
    """Typed failure while discovering simulator destinations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class JourneyExecutor(Protocol):
    """Callable contract for running compiled journey process commands."""

    def __call__(
        self,
        argv: list[str],
        *,
        cwd: str,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Run one compiled journey command and return process output."""
        ...


@dataclass(frozen=True)
class JourneyRunResult:
    """Result summary for a compiled-only journey run selection."""

    executed: list[str] = field(default_factory=list)
    manual: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)
    issues: list[JourneyIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Return the number of blocking run issues."""
        return sum(1 for issue in self.issues if issue.severity is JourneySeverity.ERROR)


def run_journeys(
    project_root: Path,
    *,
    journey: str | None = None,
    feature: str | None = None,
    stage: RunStage = RunStage.LOCAL,
    execute: bool = True,
    executor: JourneyExecutor | None = None,
) -> JourneyRunResult:
    """Select and run already compiled journeys without compiling."""
    resolved_executor = executor or _run_subprocess
    executed: list[str] = []
    manual: list[str] = []
    disabled: list[str] = []
    issues: list[JourneyIssue] = []
    for source_path in iter_journey_source_paths(project_root):
        source, raw_text = _read_source(source_path)
        if source is None or raw_text is None:
            continue
        if journey is not None and source.id != journey:
            continue
        covered_features = {cover.feature for cover in source.covers}
        if feature is not None and feature not in covered_features:
            continue
        policy = source.run_policy.get(stage, RunPolicyValue.IMPACTED)
        if policy is RunPolicyValue.DISABLED or source.status.value == "disabled":
            disabled.append(source.id)
            continue
        if policy is RunPolicyValue.MANUAL or source.status.value == "manual":
            manual.append(source.id)
            continue
        manifest = read_compiled_manifest(project_root, source.id)
        current_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        if manifest is None:
            issues.append(
                _issue("journey_compiled_missing", "compiled manifest is missing", source_path)
            )
            continue
        if manifest.source_hash != current_hash:
            issues.append(
                _issue(
                    "journey_compiled_stale",
                    "compiled manifest source hash is stale",
                    source_path,
                )
            )
            continue
        if manifest.compiler_version != COMPILER_VERSION:
            issues.append(
                _issue(
                    "journey_compiler_stale",
                    "compiled manifest compiler version is stale",
                    source_path,
                )
            )
            continue
        if execute:
            run_issue = _run_manifest_artifacts(
                project_root,
                source,
                manifest,
                resolved_executor,
            )
            if run_issue is not None:
                issues.append(run_issue)
                continue
        executed.append(source.id)
    return JourneyRunResult(executed=executed, manual=manual, disabled=disabled, issues=issues)


def _run_manifest_artifacts(
    project_root: Path,
    source: JourneySourceV2,
    manifest: CompiledManifest,
    executor: JourneyExecutor,
) -> JourneyIssue | None:
    """Run compiled native artifacts listed in a fresh manifest."""
    native_paths = manifest.native_output_paths
    if not native_paths:
        return _issue(
            "journey_compiled_missing",
            "compiled manifest has no native output paths",
            source_path(project_root, source.id),
        )
    for output_path in native_paths:
        artifact = project_root / output_path
        if not artifact.exists():
            return _issue(
                "journey_compiled_missing",
                f"compiled artifact missing: {output_path}",
                artifact,
            )
        try:
            argv = _runner_command(project_root, manifest.runner, artifact, executor)
        except SimulatorDiscoveryError as error:
            return _issue(error.code, error.message, artifact)
        if argv is None:
            return _issue(
                "journey_native_runner_unsupported",
                f"Unsupported native journey runner: {manifest.runner}",
                source_path(project_root, source.id),
            )
        if manifest.runner == "xcuitest":
            boot_issue = _boot_xcuitest_destination(project_root, artifact, argv, executor)
            if boot_issue is not None:
                return boot_issue
        issue = _run_command(project_root, source.id, artifact, argv, executor)
        if issue is not None:
            return issue
    return None


def _run_command(
    project_root: Path,
    journey_id: str,
    artifact: Path,
    argv: list[str],
    executor: JourneyExecutor,
) -> JourneyIssue | None:
    """Execute one native journey command and convert process failures to issues."""
    try:
        completed = executor(
            argv,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=RUNNER_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return _issue(
            "journey_native_runner_missing",
            f"Native runner command not found: {argv[0]}",
            artifact,
        )
    except subprocess.TimeoutExpired as error:
        return _issue(
            "journey_native_run_timeout",
            f"Journey {journey_id} timed out after {error.timeout}s",
            artifact,
        )
    if completed.returncode != 0:
        output = (completed.stderr or completed.stdout or "").strip()
        return _issue(
            "journey_native_run_failed",
            output or f"Native runner exited with {completed.returncode}",
            artifact,
        )
    return None


def _run_subprocess(
    argv: list[str],
    *,
    cwd: str,
    capture_output: bool,
    text: bool,
    timeout: int,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Run a native journey process through a pyright-friendly subprocess wrapper."""
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check,
    )


def _runner_command(
    project_root: Path,
    runner: str,
    artifact: Path,
    executor: JourneyExecutor,
) -> list[str] | None:
    """Return the native command for one compiled journey artifact."""
    relative = artifact.relative_to(project_root).as_posix()
    if runner == "playwright":
        return ["npx", "playwright", "test", relative]
    if runner == "maestro":
        return ["maestro", "test", relative]
    if runner == "xcuitest":
        return _xcuitest_command(project_root, artifact, executor)
    if runner == "pytest":
        return ["pytest", relative]
    if runner == "cargo":
        return ["cargo", "test"]
    return None


def _xcuitest_command(
    project_root: Path,
    artifact: Path,
    executor: JourneyExecutor,
) -> list[str] | None:
    """Build an xcodebuild command for a generated XCUITest journey class."""
    test_target = _xcuitest_target_name(artifact)
    class_name = artifact.stem
    platform = _xcuitest_platform(test_target, class_name)
    destination = _xcode_destination(project_root, platform, executor)
    scheme = _xcode_scheme(project_root, test_target)
    if destination is None or scheme is None:
        return None
    command = ["xcodebuild", "test"]
    project_flag = _xcode_project_flag(project_root)
    if project_flag:
        command.extend(project_flag)
    command.extend(
        [
            "-scheme",
            scheme,
            "-destination",
            destination,
            f"-only-testing:{test_target}/{class_name}",
        ]
    )
    return command


def _xcode_destination(
    project_root: Path,
    platform: str,
    executor: JourneyExecutor,
) -> str | None:
    """Resolve an Xcode destination from explicit env or available simulators."""
    configured = _env_value(XCODE_DESTINATION_ENV, "")
    if configured is None:
        return None
    if configured:
        return configured
    device = _first_available_simulator(project_root, platform, executor)
    simulator_platform = "watchOS Simulator" if platform == "watchos" else "iOS Simulator"
    return f"platform={simulator_platform},id={device.udid}"


def _first_available_simulator(
    project_root: Path,
    platform: str,
    executor: JourneyExecutor,
) -> _SimulatorDevice:
    """Select the newest available iOS/watchOS simulator compatible with the journey."""
    runtimes = _list_simulators(project_root, executor)
    runtime_marker = "watchOS" if platform == "watchos" else "iOS"
    runtime_keys = sorted(
        (key for key in runtimes if runtime_marker in key),
        key=lambda key: (_runtime_version_tuple(key, runtime_marker), key),
        reverse=True,
    )
    # Newest runtimes win so old available devices do not mask current simulators.
    for runtime_key in runtime_keys:
        for device in runtimes[runtime_key]:
            if not device.is_available:
                continue
            is_watch = "watch" in device.name.lower()
            if platform == "watchos" and is_watch:
                return device
            if platform == "ios" and not is_watch:
                return device
    raise SimulatorDiscoveryError(
        "journey_simulator_unavailable",
        f"No available {runtime_marker} simulator found for XCUITest journey",
    )


def _list_simulators(
    project_root: Path,
    executor: JourneyExecutor,
) -> dict[str, list[_SimulatorDevice]]:
    """Return normalized `simctl list devices` output grouped by runtime."""
    try:
        # xcrun exposes host state; check=False lets LiveSpec map failures
        # to stable issue codes.
        completed = executor(
            ["xcrun", "simctl", "list", "devices", "available", "--json"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=SIMULATOR_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as error:
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_missing",
            "xcrun simctl not found while discovering available simulators",
        ) from error
    except subprocess.TimeoutExpired as error:
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_timeout",
            f"simctl list devices timed out after {error.timeout}s",
        ) from error
    if completed.returncode != 0:
        message = (
            completed.stderr
            or completed.stdout
            or f"simctl list devices exited {completed.returncode}"
        ).strip()
        raise SimulatorDiscoveryError("journey_simulator_discovery_failed", message)
    try:
        parsed: object = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            f"simctl list devices returned invalid JSON: {error.msg}",
        ) from error
    if not isinstance(parsed, dict):
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            "simctl list devices JSON root must be an object",
        )
    devices = parsed.get("devices")
    if not isinstance(devices, dict):
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            "simctl list devices JSON missing object field: devices",
        )
    normalized: dict[str, list[_SimulatorDevice]] = {}
    for runtime_key, raw_devices in devices.items():
        if not isinstance(runtime_key, str):
            raise SimulatorDiscoveryError(
                "journey_simulator_discovery_invalid_json",
                "simctl devices field runtime keys must be strings",
            )
        if not isinstance(raw_devices, list):
            raise SimulatorDiscoveryError(
                "journey_simulator_discovery_invalid_json",
                "simctl runtime device entry must be a list",
            )
        normalized_devices = [_normalize_simulator_device(raw) for raw in raw_devices]
        normalized[runtime_key] = normalized_devices
    return normalized


def _normalize_simulator_device(raw: object) -> _SimulatorDevice:
    """Convert one `simctl` device object into the fields the runner needs."""
    if not isinstance(raw, dict):
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            "simctl device entry must be an object",
        )
    name = raw.get("name")
    udid = raw.get("udid")
    # Older simctl payloads omit isAvailable for usable devices.
    is_available = raw.get("isAvailable", True)
    if not isinstance(is_available, bool):
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            "simctl device field isAvailable must be a boolean when present",
        )
    if not isinstance(name, str) or not isinstance(udid, str):
        raise SimulatorDiscoveryError(
            "journey_simulator_discovery_invalid_json",
            "simctl device fields name and udid must be strings",
        )
    return _SimulatorDevice(
        name=name,
        udid=udid,
        is_available=is_available,
    )


def _runtime_version_tuple(runtime_key: str, runtime_marker: str) -> tuple[int, ...]:
    """Return numeric runtime version parts so iOS-26-4 sorts after iOS-9-3."""
    marker_index = runtime_key.find(runtime_marker)
    if marker_index == -1:
        return ()
    suffix = runtime_key[marker_index + len(runtime_marker) :].lstrip(".-_ ")
    version_parts: list[int] = []
    for part in suffix.replace(".", "-").split("-"):
        if part.isdigit():
            version_parts.append(int(part))
            continue
        if version_parts:
            break
    return tuple(version_parts)


def _boot_xcuitest_destination(
    project_root: Path,
    artifact: Path,
    argv: list[str],
    executor: JourneyExecutor,
) -> JourneyIssue | None:
    """Boot an explicit UDID destination before running XCUITest."""
    udid = _destination_udid(argv)
    if udid is None:
        return None
    try:
        # Booting an already-running simulator is acceptable; the stderr text is normalized below.
        boot = executor(
            ["xcrun", "simctl", "boot", udid],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=SIMULATOR_COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return _issue("journey_simulator_runner_missing", "xcrun simctl not found", artifact)
    except subprocess.TimeoutExpired as error:
        return _issue(
            "journey_simulator_boot_timeout",
            f"Simulator {udid} boot timed out after {error.timeout}s",
            artifact,
        )
    boot_error = (boot.stderr or boot.stdout or "").lower()
    if (
        boot.returncode != 0
        and "already booted" not in boot_error
        and "state: booted" not in boot_error
    ):
        message = (boot.stderr or boot.stdout or f"simctl boot exited {boot.returncode}").strip()
        return _issue("journey_simulator_boot_failed", message, artifact)
    try:
        ready = executor(
            ["xcrun", "simctl", "bootstatus", udid, "-b"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=SIMULATOR_BOOT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return _issue("journey_simulator_runner_missing", "xcrun simctl not found", artifact)
    except subprocess.TimeoutExpired as error:
        return _issue(
            "journey_simulator_boot_timeout",
            f"Simulator {udid} bootstatus timed out after {error.timeout}s",
            artifact,
        )
    if ready.returncode != 0:
        message = (
            ready.stderr or ready.stdout or f"simctl bootstatus exited {ready.returncode}"
        ).strip()
        return _issue("journey_simulator_boot_failed", message, artifact)
    return None


def _destination_udid(argv: list[str]) -> str | None:
    """Extract `id=<UDID>` from an xcodebuild command destination."""
    try:
        destination = argv[argv.index("-destination") + 1]
    except (ValueError, IndexError):
        return None
    for part in destination.split(","):
        key, separator, value = part.strip().partition("=")
        if separator and key == "id" and value:
            return value
    return None


def _xcuitest_platform(test_target: str, class_name: str) -> str:
    """Infer simulator platform from the generated XCUITest target and class names."""
    combined = f"{test_target} {class_name}".lower()
    return "watchos" if "watch" in combined else "ios"


def _xcuitest_target_name(artifact: Path) -> str:
    """Infer the XCUITest target directory from a generated Swift artifact path."""
    if artifact.parent.name == "Journeys":
        return artifact.parent.parent.name
    return artifact.parent.name


def _xcode_project_flag(project_root: Path) -> list[str]:
    """Return the first available workspace/project flag for xcodebuild."""
    workspaces = sorted(project_root.glob("*.xcworkspace"))
    if workspaces:
        return ["-workspace", workspaces[0].name]
    projects = sorted(project_root.glob("*.xcodeproj"))
    if projects:
        return ["-project", projects[0].name]
    return []


def _xcode_scheme(project_root: Path, test_target: str) -> str | None:
    """Infer the XCUITest scheme, honoring `LIVESPEC_XCODE_SCHEME` first."""
    configured = _env_value(XCODE_SCHEME_ENV, "")
    if configured is None:
        return None
    if configured:
        return configured
    suffixes = ("UITests", "UI Tests")
    for suffix in suffixes:
        if test_target.endswith(suffix):
            return test_target[: -len(suffix)] or test_target
    schemes = sorted(project_root.glob("*.xcodeproj/xcshareddata/xcschemes/*.xcscheme"))
    if schemes:
        return schemes[0].stem
    return test_target


def _env_value(name: str, default: str) -> str | None:
    """Return a stripped env value, rejecting values set to whitespace only."""
    value = os.environ.get(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or None


def source_path(project_root: Path, journey_id: str) -> Path:
    """Return a source path for manifest-level errors without importing path helpers late."""
    return project_root / ".specs" / "journeys" / journey_id / "journey.yaml"


def _read_source(path: Path) -> tuple[JourneySourceV2 | None, str | None]:
    """Read a v2 journey source for run selection."""
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw_text)
        if not isinstance(data, dict):
            return None, raw_text
        return JourneySourceV2.model_validate(data), raw_text
    except (OSError, yaml.YAMLError, ValidationError):
        return None, None


def _issue(code: str, message: str, path: Path) -> JourneyIssue:
    """Create a blocking run issue."""
    return JourneyIssue(code=code, severity=JourneySeverity.ERROR, message=message, path=path)


__all__ = ["JourneyRunResult", "run_journeys"]
