"""Compiled-only execution planner for User Journeys v2."""

# @spec FR-024, FR-027: compiled-only journey execution and stage run policies
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-024

from __future__ import annotations

import hashlib
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
DEFAULT_XCODE_DESTINATION = "platform=iOS Simulator,name=iPhone 16"


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
        argv = _runner_command(project_root, manifest.runner, artifact)
        if argv is None:
            return _issue(
                "journey_native_runner_unsupported",
                f"Unsupported native journey runner: {manifest.runner}",
                source_path(project_root, source.id),
            )
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


def _runner_command(project_root: Path, runner: str, artifact: Path) -> list[str] | None:
    """Return the native command for one compiled journey artifact."""
    relative = artifact.relative_to(project_root).as_posix()
    if runner == "playwright":
        return ["npx", "playwright", "test", relative]
    if runner == "maestro":
        return ["maestro", "test", relative]
    if runner == "xcuitest":
        return _xcuitest_command(project_root, artifact)
    if runner == "pytest":
        return ["pytest", relative]
    if runner == "cargo":
        return ["cargo", "test"]
    return None


def _xcuitest_command(project_root: Path, artifact: Path) -> list[str] | None:
    """Build an xcodebuild command for a generated XCUITest journey class."""
    test_target = _xcuitest_target_name(artifact)
    class_name = artifact.stem
    destination = _env_value("LIVESPEC_XCODE_DESTINATION", DEFAULT_XCODE_DESTINATION)
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
    """Infer the scheme used to run a generated XCUITest target."""
    configured = _env_value("LIVESPEC_XCODE_SCHEME", "")
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
