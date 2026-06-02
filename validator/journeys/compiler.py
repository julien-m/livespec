"""Ahead-of-time compilers from journey YAML to native test artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .models import (
    CompiledJourneyArtifact,
    CompileResult,
    JourneyFile,
    JourneyIssue,
    JourneySeverity,
    JsonValue,
)
from .paths import compiled_artifact_path, relative_to_project
from .validator import validate_journeys

# @spec FR-009: Source hash marker
# — .specs/features/056-executable-user-journeys/spec.md#fr-009
HASH_MARKER = "livespec-journey-source-hash:"


def compile_journeys(project_root: Path, feature: str | None = None) -> CompileResult:
    """Compile executable journeys into native test artifacts.

    Args:
        project_root: Project root containing `.specs/`.
        feature: Optional feature slug.

    Returns:
        Generated artifacts plus validation/compilation issues.
    """
    validation = validate_journeys(project_root, feature)
    issues = list(validation.issues)
    artifacts: list[CompiledJourneyArtifact] = []
    if validation.error_count:
        return CompileResult(artifacts=artifacts, issues=issues)

    for journey in validation.journeys:
        if not journey.is_executable:
            continue
        artifact_path = compiled_artifact_path(
            project_root,
            journey.feature,
            journey.journey_id,
            journey.target_surface,
        )
        if journey.target_surface == "web":
            content = _compile_playwright(project_root, journey)
            runner = "playwright"
        elif journey.target_surface in {"ios", "watchos"}:
            content = _compile_xcuitest(project_root, journey)
            runner = "xcuitest"
        elif journey.target_surface in {"android", "maestro"}:
            content = _compile_maestro(project_root, journey)
            runner = "maestro"
        else:
            issues.append(
                JourneyIssue(
                    code="journey_target_unsupported",
                    severity=JourneySeverity.ERROR,
                    message=f"unsupported target surface {journey.target_surface!r}",
                    path=journey.path,
                )
            )
            continue
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        artifacts.append(
            CompiledJourneyArtifact(
                source_path=journey.path,
                output_path=artifact_path,
                source_hash=journey.source_hash,
                runner=runner,
            )
        )
    return CompileResult(artifacts=artifacts, issues=issues)


def extract_source_hash(path: Path) -> str | None:
    """Read the embedded source hash from a compiled artifact."""
    if not path.exists():
        return None
    marker = HASH_MARKER
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if marker not in line:
            continue
        return line.split(marker, 1)[1].strip()
    return None


def _compile_playwright(project_root: Path, journey: JourneyFile) -> str:
    """Compile one web journey to a Playwright test file."""
    # @spec FR-006: Playwright journey compiler
    # — .specs/features/056-executable-user-journeys/spec.md#fr-006
    source = relative_to_project(project_root, journey.path)
    lines = [
        f"// {HASH_MARKER} {journey.source_hash}",
        f"// livespec-journey-source: {source}",
        "import { test, expect } from '@playwright/test';",
        "",
        f"test({journey.title!r}, async ({{ page }}) => {{",
    ]
    for step in journey.steps:
        lines.extend(f"  {line}" for line in _playwright_step(step))
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def _playwright_step(step: dict[str, JsonValue]) -> list[str]:
    """Render one journey step into Playwright TypeScript."""
    action, payload = next(iter(step.items()))
    if action == "open":
        return [f"await page.goto({_literal(str(payload))});"]
    if action == "click" and isinstance(payload, dict):
        role = _literal(str(payload.get("role", "button")))
        name = _literal(str(payload.get("name", "")))
        return [f"await page.getByRole({role}, {{ name: {name} }}).click();"]
    if action == "fill" and isinstance(payload, dict):
        label = _literal(str(payload.get("label", "")))
        value = _literal(str(payload.get("value", "")))
        return [f"await page.getByLabel({label}).fill({value});"]
    if action == "select" and isinstance(payload, dict):
        label = _literal(str(payload.get("label", "")))
        value = _literal(str(payload.get("value", "")))
        return [f"await page.getByLabel({label}).selectOption({value});"]
    if action == "wait" and isinstance(payload, dict):
        seconds = _int_value(payload.get("seconds"), default=1)
        until = payload.get("until")
        if isinstance(until, dict) and isinstance(until.get("text"), str):
            timeout = seconds * 1000
            return [
                f'await page.waitForSelector("text={until["text"]}", {{ timeout: {timeout} }});'
            ]
        return [f"await page.waitForTimeout({seconds * 1000});"]
    if action == "assert" and isinstance(payload, dict):
        text = _literal(str(payload.get("text", "")))
        return [f"await expect(page.getByText({text})).toBeVisible();"]
    if action == "assert_not" and isinstance(payload, dict):
        text = _literal(str(payload.get("text", "")))
        return [f"await expect(page.getByText({text})).not.toBeVisible();"]
    if action == "screenshot":
        return ["await page.screenshot();"]
    if action == "back":
        return ["await page.goBack();"]
    if action == "press" and isinstance(payload, dict):
        return [f"await page.keyboard.press({_literal(str(payload.get('key', 'Enter')))});"]
    return [f"// Unsupported compile step retained for review: {action}"]


def _compile_xcuitest(project_root: Path, journey: JourneyFile) -> str:
    """Compile one Apple-platform journey to Swift/XCUITest."""
    # @spec FR-007: XCUITest journey compiler
    # — .specs/features/056-executable-user-journeys/spec.md#fr-007
    source = relative_to_project(project_root, journey.path)
    class_name = compiled_artifact_path(
        project_root,
        journey.feature,
        journey.journey_id,
        journey.target_surface,
    ).stem
    lines = [
        f"// {HASH_MARKER} {journey.source_hash}",
        f"// livespec-journey-source: {source}",
        "import XCTest",
        "",
        f"final class {class_name}: XCTestCase {{",
        "    func testJourney() throws {",
        "        let app = XCUIApplication()",
        "        app.launch()",
    ]
    for step in journey.steps:
        lines.extend(f"        {line}" for line in _xcuitest_step(step))
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def _xcuitest_step(step: dict[str, JsonValue]) -> list[str]:
    """Render one journey step into Swift/XCUITest."""
    action, payload = next(iter(step.items()))
    if action == "open":
        return [f'app.launchArguments.append("livespec-open={payload}")']
    if action == "click" and isinstance(payload, dict):
        return [f"app.buttons[{_swift_literal(str(payload.get('name', '')))}].tap()"]
    if action == "fill" and isinstance(payload, dict):
        label = _swift_literal(str(payload.get("label", "")))
        value = _swift_literal(str(payload.get("value", "")))
        return [
            f"app.textFields[{label}].tap()",
            f"app.textFields[{label}].typeText({value})",
        ]
    if action == "wait" and isinstance(payload, dict):
        seconds = _int_value(payload.get("seconds"), default=1)
        until = payload.get("until")
        if isinstance(until, dict) and isinstance(until.get("text"), str):
            text = _swift_literal(str(until["text"]))
            return [f"XCTAssertTrue(app.staticTexts[{text}].waitForExistence(timeout: {seconds}))"]
        return [f"sleep({seconds})"]
    if action == "assert" and isinstance(payload, dict):
        text = _swift_literal(str(payload.get("text", "")))
        return [f"XCTAssertTrue(app.staticTexts[{text}].exists)"]
    if action == "assert_not" and isinstance(payload, dict):
        text = _swift_literal(str(payload.get("text", "")))
        return [f"XCTAssertFalse(app.staticTexts[{text}].exists)"]
    if action == "back":
        return ['app.buttons["Back"].tap()']
    if action == "press" and isinstance(payload, dict):
        return [f"// Press {payload.get('key', 'Enter')} requires project-specific mapping"]
    return [f"// Unsupported compile step retained for review: {action}"]


def _compile_maestro(project_root: Path, journey: JourneyFile) -> str:
    """Compile one Android/Maestro journey to a Maestro YAML flow."""
    # @spec FR-008: Maestro journey compiler
    # — .specs/features/056-executable-user-journeys/spec.md#fr-008
    source = relative_to_project(project_root, journey.path)
    flow: list[dict[str, object]] = [
        {"comment": f"{HASH_MARKER} {journey.source_hash}"},
        {"comment": f"livespec-journey-source: {source}"},
    ]
    for step in journey.steps:
        flow.extend(_maestro_step(step))
    return yaml.safe_dump(flow, sort_keys=False)


def _maestro_step(step: dict[str, JsonValue]) -> list[dict[str, object]]:
    """Render one journey step into Maestro YAML commands."""
    action, payload = next(iter(step.items()))
    if action == "open":
        return [{"launchApp": {"clearState": False}}, {"openLink": str(payload)}]
    if action == "click" and isinstance(payload, dict):
        return [{"tapOn": str(payload.get("name", ""))}]
    if action == "fill" and isinstance(payload, dict):
        return [
            {"tapOn": str(payload.get("label", ""))},
            {"inputText": str(payload.get("value", ""))},
        ]
    if action == "wait" and isinstance(payload, dict):
        seconds = _int_value(payload.get("seconds"), default=1)
        until = payload.get("until")
        if isinstance(until, dict) and isinstance(until.get("text"), str):
            return [{"extendedWaitUntil": {"visible": until["text"], "timeout": seconds * 1000}}]
        return [{"waitForAnimationToEnd": {"timeout": seconds * 1000}}]
    if action == "assert" and isinstance(payload, dict):
        return [{"assertVisible": str(payload.get("text", ""))}]
    if action == "assert_not" and isinstance(payload, dict):
        return [{"assertNotVisible": str(payload.get("text", ""))}]
    if action == "back":
        return [{"back": True}]
    if action == "press" and isinstance(payload, dict):
        return [{"pressKey": str(payload.get("key", "Enter"))}]
    return [{"comment": f"Unsupported compile step retained for review: {action}"}]


def _literal(value: str) -> str:
    """Return a JavaScript string literal."""
    return repr(value)


def _int_value(value: JsonValue, *, default: int) -> int:
    """Return an integer for scalar YAML values, or a deterministic fallback."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _swift_literal(value: str) -> str:
    """Return a Swift string literal with basic escaping."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
