# LiveSpec traceability anchors
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-008)
# @spec(FR-009)
# @spec(FR-023)
# @spec(FR-028)
# @spec(FR-029)
# @spec(FR-030)
# @spec(FR-034)
# @spec(FR-036)

"""Ahead-of-time compiler facade for User Journeys v2."""

# @spec FR-023, FR-028, FR-029, FR-030, FR-036: compile, manifest, LLM capture
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-023

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import ValidationError

from .capabilities import validate_runner_capability
from .compiler_registry import get_compiler_backend
from .manifest import write_compiled_manifest
from .models import (
    CompiledJourneyArtifact,
    CompileResult,
    JourneyFile,
    JourneyIssue,
    JourneySeverity,
    JsonValue,
)
from .paths import relative_to_project, slug_to_pascal, slug_to_snake, visual_contracts_dir
from .schema import JourneySourceV2, JourneyTargetRef, VisualCheckMode
from .validator import validate_journeys

HASH_MARKER = "livespec-journey-source-hash:"
UI_TEST_JOURNEY_AUTH_ENV = "UI_TEST_JOURNEY_AUTH"
UI_TEST_JOURNEY_FIXTURES_ENV = "UI_TEST_JOURNEY_FIXTURES"
UI_TEST_JOURNEY_MOCKS_ENV = "UI_TEST_JOURNEY_MOCKS"
UI_TEST_JOURNEY_FEATURE_FLAGS_ENV = "UI_TEST_JOURNEY_FEATURE_FLAGS"


class _JourneySourceReadError(Exception):
    """Raised when a compiled journey source cannot be loaded into the typed model."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        super().__init__(f"Cannot read journey source {path}: {reason}")


@dataclass(frozen=True)
class _PendingManifest:
    """Compiled journey data waiting for an external project refresh."""

    journey: JourneyFile
    output_path: Path
    visual_contract_paths: list[Path]


def compile_journeys(
    project_root: Path,
    feature: str | None = None,
    *,
    journey: str | None = None,
    force: bool = False,
) -> CompileResult:
    """Compile executable v2 journeys into native artifacts and manifests."""
    validation = validate_journeys(project_root, feature)
    issues = list(validation.issues)
    artifacts: list[CompiledJourneyArtifact] = []
    if validation.error_count:
        return CompileResult(artifacts=artifacts, issues=issues)

    pending_xcuitest_manifests: list[_PendingManifest] = []
    for source in validation.journeys:
        if journey is not None and source.journey_id != journey:
            continue
        if not source.is_executable:
            continue
        capability_issue = validate_runner_capability(
            source.runner,
            source.journey_id,
            source.steps,
        )
        if capability_issue is not None:
            issues.append(_with_path(capability_issue, source.path))
            continue
        try:
            source_model = _read_source_model(source.path)
        except _JourneySourceReadError as error:
            issues.append(_source_read_issue(error))
            continue
        output_path = _native_artifact_path(project_root, source)
        content = _compile_native(project_root, source, source_model)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        visual_contract_paths = _write_visual_contracts(project_root, source_model)
        if source.runner == "xcuitest":
            pending_xcuitest_manifests.append(
                _PendingManifest(
                    journey=source,
                    output_path=output_path,
                    visual_contract_paths=visual_contract_paths,
                )
            )
            continue
        write_compiled_manifest(
            project_root,
            journey_id=source.journey_id,
            source_path=source.path,
            source_hash=source.source_hash,
            runner=source.runner,
            native_output_paths=[output_path],
            visual_contract_paths=visual_contract_paths,
        )
        artifacts.append(
            CompiledJourneyArtifact(
                source_path=source.path,
                output_path=output_path,
                source_hash=source.source_hash,
                runner=source.runner,
            )
        )
    if pending_xcuitest_manifests:
        xcodegen_issue = _run_xcodegen_if_needed(project_root)
        if xcodegen_issue is not None:
            issues.append(xcodegen_issue)
        else:
            for pending in pending_xcuitest_manifests:
                write_compiled_manifest(
                    project_root,
                    journey_id=pending.journey.journey_id,
                    source_path=pending.journey.path,
                    source_hash=pending.journey.source_hash,
                    runner=pending.journey.runner,
                    native_output_paths=[pending.output_path],
                    visual_contract_paths=pending.visual_contract_paths,
                )
                artifacts.append(
                    CompiledJourneyArtifact(
                        source_path=pending.journey.path,
                        output_path=pending.output_path,
                        source_hash=pending.journey.source_hash,
                        runner=pending.journey.runner,
                    )
                )
    return CompileResult(artifacts=artifacts, issues=issues)


def extract_source_hash(path: Path) -> str | None:
    """Read the embedded source hash from a compiled artifact."""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if HASH_MARKER in line:
            return line.split(HASH_MARKER, 1)[1].strip()
    return None


def _source_read_issue(error: _JourneySourceReadError) -> JourneyIssue:
    """Return a blocking compiler issue for an unreadable journey source."""
    return JourneyIssue(
        code="journey_source_unreadable",
        severity=JourneySeverity.ERROR,
        message=str(error),
        path=error.path,
    )


def _write_visual_contracts(project_root: Path, source: JourneySourceV2) -> list[Path]:
    """Write screenshot-only LLM visual contracts for compiled journey checks."""
    output_dir = visual_contracts_dir(project_root, source.id)
    paths: list[Path] = []
    for check in source.visual_checks:
        if check.mode not in {VisualCheckMode.LLM, VisualCheckMode.NATIVE_THEN_LLM}:
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{slug_to_snake(check.id)}.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "journey_id": source.id,
                    "check_id": check.id,
                    "mode": check.mode.value,
                    "assertion": check.assertion,
                    "target": check.target.model_dump(mode="json", exclude_none=True),
                    "instructions": check.prompt,
                    "blocking": check.blocking,
                    "privacy": source.privacy.model_dump(mode="json"),
                    "input": "native_screenshot_only",
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def _read_source_model(path: Path) -> JourneySourceV2:
    """Read the typed source model used for visual contract compilation."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise _JourneySourceReadError(path, str(error)) from error
    except yaml.YAMLError as error:
        raise _JourneySourceReadError(path, str(error)) from error
    if not isinstance(data, dict):
        raise _JourneySourceReadError(path, "source root must be a mapping")
    try:
        return JourneySourceV2.model_validate(data)
    except ValidationError as error:
        raise _JourneySourceReadError(path, str(error)) from error


def _native_artifact_path(project_root: Path, journey: JourneyFile) -> Path:
    """Return native artifact destination for a compiled v2 journey."""
    stem = slug_to_snake(journey.journey_id)
    if journey.runner == "playwright":
        return project_root / "tests" / "e2e" / "journeys" / f"{stem}.spec.ts"
    if journey.runner == "xcuitest":
        filename = f"{slug_to_pascal(journey.journey_id)}Journey.swift"
        return project_root / "STRAPTUITests" / "Journeys" / filename
    if journey.runner == "maestro":
        return project_root / ".specs" / "maestro" / "journeys" / f"{stem}.yaml"
    filename = f"{stem}.{journey.runner}.txt"
    return project_root / ".specs" / "journeys" / journey.journey_id / "compiled" / filename


def _compile_native(project_root: Path, journey: JourneyFile, source: JourneySourceV2) -> str:
    """Dispatch to the runner-specific compiler."""
    backend = get_compiler_backend(journey.runner)
    if backend is not None and backend.artifact_kind == "playwright":
        return _compile_playwright(project_root, journey, source)
    if backend is not None and backend.artifact_kind == "xcuitest":
        return _compile_xcuitest(project_root, journey, source)
    return _compile_maestro(project_root, journey)


def _header(project_root: Path, journey: JourneyFile, comment: str) -> list[str]:
    """Return standard source markers embedded in every native artifact."""
    source = relative_to_project(project_root, journey.path)
    return [
        f"{comment} livespec-journey-id: {journey.journey_id}",
        f"{comment} {HASH_MARKER} {journey.source_hash}",
        f"{comment} livespec-journey-source: {source}",
    ]


def _compile_playwright(
    project_root: Path,
    journey: JourneyFile,
    source: JourneySourceV2,
) -> str:
    """Compile one web journey to a Playwright test file."""
    lines = [
        *_header(project_root, journey, "//"),
        "import { test, expect } from '@playwright/test';",
        "",
        f"test({journey.title!r}, async ({{ page }}) => {{",
    ]
    for step in journey.steps:
        lines.extend(f"  {line}" for line in _playwright_step(step))
    lines.extend(f"  {line}" for line in _playwright_visual_steps(source))
    lines.extend(["});", ""])
    return "\n".join(lines)


def _compile_xcuitest(
    project_root: Path,
    journey: JourneyFile,
    source: JourneySourceV2,
) -> str:
    """Compile one Apple-platform journey to Swift/XCUITest."""
    method_name = f"test{slug_to_pascal(journey.journey_id)}Journey"
    lines = [
        *_header(project_root, journey, "//"),
        "import Foundation",
        "import XCTest",
        "",
        f"final class {slug_to_pascal(journey.journey_id)}Journey: XCTestCase {{",
        f"    func {method_name}() throws {{",
        "        let app = XCUIApplication()",
    ]
    lines.extend(f"        {line}" for line in _xcuitest_launch_environment(source))
    lines.append("        app.launch()")
    for step in journey.steps:
        lines.extend(f"        {line}" for line in _xcuitest_step(step))
    lines.extend(["    }", "", *_xcuitest_helpers(journey.steps), "}", ""])
    return "\n".join(lines)


def _xcuitest_launch_environment(source: JourneySourceV2) -> list[str]:
    """Render journey preconditions as launch environment before app launch."""
    preconditions = source.preconditions
    lines: list[str] = []
    if preconditions.auth:
        lines.append(
            f'app.launchEnvironment["{UI_TEST_JOURNEY_AUTH_ENV}"] = '
            f"{_swift_literal(preconditions.auth)}"
        )
    if preconditions.fixtures:
        lines.append(
            f'app.launchEnvironment["{UI_TEST_JOURNEY_FIXTURES_ENV}"] = '
            f"{_swift_literal(_json_list(preconditions.fixtures))}"
        )
    if preconditions.mocks:
        lines.append(
            f'app.launchEnvironment["{UI_TEST_JOURNEY_MOCKS_ENV}"] = '
            f"{_swift_literal(_json_list(preconditions.mocks))}"
        )
    if preconditions.feature_flags:
        lines.append(
            f'app.launchEnvironment["{UI_TEST_JOURNEY_FEATURE_FLAGS_ENV}"] = '
            f"{_swift_literal(_json_list(preconditions.feature_flags))}"
        )
    return lines


def _compile_maestro(project_root: Path, journey: JourneyFile) -> str:
    """Compile one Android/Maestro journey to a Maestro YAML flow."""
    flow: list[dict[str, object]] = [
        {"comment": line.removeprefix("# ")} for line in _header(project_root, journey, "#")
    ]
    for step in journey.steps:
        flow.extend(_maestro_step(step))
    return yaml.safe_dump(flow, sort_keys=False)


def _run_xcodegen_if_needed(project_root: Path) -> JourneyIssue | None:
    """Regenerate XcodeGen projects after writing generated XCUITest Swift files."""
    project_file = _xcodegen_project_path(project_root)
    if project_file is None:
        return None
    if shutil.which("xcodegen") is None:
        return JourneyIssue(
            code="journey_xcodegen_missing",
            severity=JourneySeverity.ERROR,
            message="XcodeGen project detected but `xcodegen` is not on PATH.",
            path=project_file,
        )
    try:
        # XcodeGen reads project.yml/project.yaml from cwd, exits non-zero for invalid
        # specs, and 120s covers large project regeneration without hanging CI forever.
        result = subprocess.run(
            ["xcodegen", "generate"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return JourneyIssue(
            code="journey_xcodegen_failed",
            severity=JourneySeverity.ERROR,
            message=f"xcodegen generate timed out after {error.timeout}s",
            path=project_file,
        )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        return JourneyIssue(
            code="journey_xcodegen_failed",
            severity=JourneySeverity.ERROR,
            message=output or f"xcodegen generate exited with {result.returncode}",
            path=project_file,
        )
    return None


def _xcodegen_project_path(project_root: Path) -> Path | None:
    """Return the XcodeGen project spec path when one is present."""
    for filename in ("project.yml", "project.yaml"):
        path = project_root / filename
        if path.exists():
            return path
    return None


def _playwright_step(step: dict[str, JsonValue]) -> list[str]:
    """Render one journey step into Playwright TypeScript."""
    action, payload = next(iter(step.items()))
    if action == "open":
        return [f"await page.goto({_literal(str(payload))});"]
    if action == "click" and isinstance(payload, dict):
        target = _target_text(payload)
        return [f"await page.getByText({_literal(target)}).click();"]
    if action == "assert" and isinstance(payload, dict):
        return [f"await expect(page.getByText({_literal(_target_text(payload))})).toBeVisible();"]
    if action == "assert_not" and isinstance(payload, dict):
        return [
            f"await expect(page.getByText({_literal(_target_text(payload))})).not.toBeVisible();"
        ]
    if action == "fill" and isinstance(payload, dict):
        target = _playwright_locator(_target_from_payload(payload))
        value = str(payload.get("value", ""))
        return [f"await {target}.fill({_literal(value)});"]
    if action == "screenshot":
        return ["await page.screenshot();"]
    if action == "back":
        return ["await page.goBack();"]
    if action == "press" and isinstance(payload, dict):
        return [f"await page.keyboard.press({_literal(str(payload.get('key', 'Enter')))});"]
    raise ValueError(f"unsupported playwright action after capability validation: {action}")


def _playwright_visual_steps(source: JourneySourceV2) -> list[str]:
    """Render supported native visual checks into Playwright assertions."""
    lines: list[str] = []
    for check in source.visual_checks:
        if check.mode not in {VisualCheckMode.NATIVE, VisualCheckMode.NATIVE_THEN_LLM}:
            continue
        variable = slug_to_snake(check.id)
        locator = _playwright_locator(check.target)
        lines.append(f"// native visual check: {check.id}")
        lines.append(f"const {variable} = {locator};")
        lines.append(f"const {variable}Box = await {variable}.boundingBox();")
        lines.append(f"expect({variable}Box).not.toBeNull();")
        if check.assertion == "min_margin":
            lines.extend(_playwright_min_margin_assertions(variable, check.min_px or 0))
        elif check.assertion == "text_fits":
            lines.extend(_playwright_text_fits_assertions(variable))
        else:
            lines.append(
                f"throw new Error('native_visual_assertion_unsupported: {check.assertion}');"
            )
    return lines


def _playwright_min_margin_assertions(variable: str, min_px: int) -> list[str]:
    """Return Playwright viewport margin assertions for one element box."""
    return [
        f"expect({variable}Box!.x).toBeGreaterThanOrEqual({min_px});",
        f"expect({variable}Box!.y).toBeGreaterThanOrEqual({min_px});",
        f"const {variable}Viewport = page.viewportSize();",
        f"expect({variable}Viewport).not.toBeNull();",
        "expect("
        f"{variable}Viewport!.width - ({variable}Box!.x + {variable}Box!.width)"
        f").toBeGreaterThanOrEqual({min_px});",
        "expect("
        f"{variable}Viewport!.height - ({variable}Box!.y + {variable}Box!.height)"
        f").toBeGreaterThanOrEqual({min_px});",
    ]


def _playwright_text_fits_assertions(variable: str) -> list[str]:
    """Return Playwright viewport-fit assertions for one element box."""
    return [
        f"const {variable}Viewport = page.viewportSize();",
        f"expect({variable}Viewport).not.toBeNull();",
        f"expect({variable}Box!.x).toBeGreaterThanOrEqual(0);",
        f"expect({variable}Box!.y).toBeGreaterThanOrEqual(0);",
        f"expect({variable}Box!.x + {variable}Box!.width).toBeLessThanOrEqual("
        f"{variable}Viewport!.width);",
        f"expect({variable}Box!.y + {variable}Box!.height).toBeLessThanOrEqual("
        f"{variable}Viewport!.height);",
    ]


def _playwright_locator(target: JourneyTargetRef) -> str:
    """Return a Playwright locator expression for a stable target."""
    if target.test_id:
        return f"page.getByTestId({_literal(target.test_id)})"
    if target.semantic_id:
        selector = f'[data-semantic-id="{target.semantic_id}"]'
        return f"page.locator({_literal(selector)})"
    if target.role and target.name:
        return f"page.getByRole({_literal(target.role)}, {{ name: {_literal(target.name)} }})"
    if target.accessibility_label:
        return f"page.getByLabel({_literal(target.accessibility_label)})"
    if target.text:
        return f"page.getByText({_literal(target.text)})"
    if target.label:
        return f"page.getByText({_literal(target.label)})"
    if target.route:
        selector = f'a[href="{target.route}"]'
        return f"page.locator({_literal(selector)})"
    return "page.locator('body')"


def _xcuitest_step(step: dict[str, JsonValue]) -> list[str]:
    """Render one journey step into Swift/XCUITest."""
    action, payload = next(iter(step.items()))
    if action == "open" and isinstance(payload, str):
        return [f"openJourneyURL({_swift_literal(payload)}, in: app)"]
    if action == "click" and isinstance(payload, dict):
        return [f"{_xcuitest_target(payload)}.tap()"]
    if action == "assert" and isinstance(payload, dict):
        return [f"XCTAssertTrue({_xcuitest_target(payload)}.exists)"]
    if action == "assert_not" and isinstance(payload, dict):
        return [f"XCTAssertFalse({_xcuitest_target(payload)}.exists)"]
    if action == "fill" and isinstance(payload, dict):
        value = _swift_literal(str(payload.get("value", "")))
        target = _xcuitest_target(payload)
        return [f"{target}.tap()", f"{target}.typeText({value})"]
    if action == "screenshot":
        return _xcuitest_screenshot()
    if action == "back":
        return ['app.buttons["Back"].tap()']
    raise ValueError(f"unsupported xcuitest action after capability validation: {action}")


def _xcuitest_screenshot() -> list[str]:
    """Return Swift that records screenshots as XCUITest attachments."""
    return [
        "let screenshot = app.screenshot()",
        "let attachment = XCTAttachment(screenshot: screenshot)",
        'attachment.name = "journey-screenshot"',
        "attachment.lifetime = .keepAlways",
        "add(attachment)",
    ]


def _xcuitest_helpers(steps: list[dict[str, JsonValue]]) -> list[str]:
    """Return Swift helpers required by rendered XCUITest steps."""
    if not any(next(iter(step.items()))[0] == "open" for step in steps):
        return []
    return [
        "    private func openJourneyURL(_ urlString: String, in app: XCUIApplication) {",
        "        guard let url = URL(string: urlString) else {",
        '            XCTFail("invalid journey URL: \\(urlString)")',
        "            return",
        "        }",
        "        app.open(url)",
        "    }",
    ]


def _xcuitest_target(payload: dict[str, JsonValue]) -> str:
    """Return a broad XCUITest element lookup for stable journey identifiers."""
    identifier = _target_identifier(payload)
    return f"app.descendants(matching: .any)[{_swift_literal(identifier)}]"


def _maestro_step(step: dict[str, JsonValue]) -> list[dict[str, object]]:
    """Render one journey step into Maestro YAML commands."""
    action, payload = next(iter(step.items()))
    if action == "open":
        return [{"launchApp": {"clearState": False}}, {"openLink": str(payload)}]
    if action == "click" and isinstance(payload, dict):
        return [{"tapOn": _target_text(payload)}]
    if action == "assert" and isinstance(payload, dict):
        return [{"assertVisible": _target_text(payload)}]
    if action == "assert_not" and isinstance(payload, dict):
        return [{"assertNotVisible": _target_text(payload)}]
    if action == "fill" and isinstance(payload, dict):
        return [{"tapOn": _target_text(payload)}, {"inputText": str(payload.get("value", ""))}]
    if action == "back":
        return [{"back": True}]
    if action == "press" and isinstance(payload, dict):
        return [{"pressKey": str(payload.get("key", "Enter"))}]
    raise ValueError(f"unsupported maestro action after capability validation: {action}")


def _target_text(payload: dict[str, JsonValue]) -> str:
    """Choose a readable target for generated runner code."""
    for key in ("name", "text", "label", "semantic_id", "test_id", "route"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _target_identifier(payload: dict[str, JsonValue]) -> str:
    """Choose a stable identifier before falling back to product text."""
    for key in ("test_id", "semantic_id", "accessibility_label", "name", "text", "label", "route"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _target_from_payload(payload: dict[str, JsonValue]) -> JourneyTargetRef:
    """Rebuild a typed target from a legacy compiler payload."""
    return JourneyTargetRef.model_validate(
        {key: value for key, value in payload.items() if key != "value"}
    )


def _literal(value: str) -> str:
    """Return a JavaScript string literal."""
    return repr(value)


def _swift_literal(value: str) -> str:
    """Return a Swift string literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _json_list(values: list[str]) -> str:
    """Return compact JSON for launch environment list values."""
    return json.dumps(values, separators=(",", ":"))


def _with_path(issue: JourneyIssue, path: Path) -> JourneyIssue:
    """Return a copy of a capability issue attached to the source path."""
    return JourneyIssue(
        code=issue.code,
        severity=issue.severity,
        message=issue.message,
        path=path,
    )
