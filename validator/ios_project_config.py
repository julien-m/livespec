# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-005)
# @spec(AC-010)

"""Project-level XCUITest settings read from ``livespec/ui-runners/ios.yaml``.

Precedence for ``test_scheme`` and ``launch_arguments`` is explicit argument
(CLI or ``surfaces.yaml`` ``runnerConfig``) > project config (selected scenario,
then top-level ``test_scheme``) > scheme autodetection by the runner.
"""

# @spec FR-001: Project ios.yaml configures the iOS runner
# — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-001
# @spec FR-005, AC-010: Per-scenario launch_arguments reach the XCUITest harness
# — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency without stubs.

PROJECT_CONFIG_RELATIVE = Path("livespec") / "ui-runners" / "ios.yaml"
_SCENARIO_KEYS = frozenset({"name", "test_scheme", "launch_arguments"})
_BOUNDARY_MARKERS = (".specs", ".git")


@dataclass(frozen=True)
class IosScenario:
    """One named XCUITest scenario from the project ``ios.yaml``."""

    name: str
    test_scheme: str | None = None
    launch_arguments: list[str] = field(default_factory=lambda: cast(list[str], []))


@dataclass(frozen=True)
class IosProjectConfig:
    """Parsed project-level iOS runner configuration."""

    path: Path
    test_scheme: str | None = None
    scenarios: tuple[IosScenario, ...] = ()

    def scenario(self, name: str | None) -> IosScenario | None:
        """Return the named scenario, else ``default``, else the first one.

        Raises:
            ValueError: A scenario name was requested but is not declared.
        """
        if name is not None:
            for scenario in self.scenarios:
                if scenario.name == name:
                    return scenario
            raise ValueError(f"{self.path}: scenario {name!r} is not declared")
        for scenario in self.scenarios:
            if scenario.name == "default":
                return scenario
        return self.scenarios[0] if self.scenarios else None


def find_project_ios_config(project_dir: Path) -> Path | None:
    """Locate ``livespec/ui-runners/ios.yaml`` from the runner dir up to the project root.

    The search stops at the first directory containing ``.specs`` or ``.git``.
    """
    for directory in (project_dir, *project_dir.parents):
        candidate = directory / PROJECT_CONFIG_RELATIVE
        if candidate.is_file():
            return candidate
        if any((directory / marker).exists() for marker in _BOUNDARY_MARKERS):
            return None
    return None


def _optional_str(value: object, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a non-empty string")
    return value


def _scenario(raw: object, path: Path, index: int) -> IosScenario:
    where = f"{path}: scenarios[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping")
    entry = cast(dict[str, Any], raw)
    unknown = sorted(set(entry) - _SCENARIO_KEYS)
    if unknown:
        raise ValueError(f"{where} has unsupported keys: {', '.join(unknown)}")
    name = _optional_str(entry.get("name"), f"{where}.name")
    if name is None:
        raise ValueError(f"{where}.name is required")
    arguments = entry.get("launch_arguments", [])
    if not isinstance(arguments, list) or not all(isinstance(a, str) for a in arguments):
        raise ValueError(f"{where}.launch_arguments must be a list of strings")
    return IosScenario(
        name=name,
        test_scheme=_optional_str(entry.get("test_scheme"), f"{where}.test_scheme"),
        launch_arguments=list(cast(list[str], arguments)),
    )


def load_project_ios_config(project_dir: Path) -> IosProjectConfig | None:
    """Parse the project ``ios.yaml``; other top-level manifest keys are ignored.

    Returns:
        The parsed config, or None when the project has no ``ios.yaml``.

    Raises:
        ValueError: The file is not YAML, or ``test_scheme``/``scenarios`` are malformed.
    """
    path = find_project_ios_config(project_dir)
    if path is None:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: unreadable iOS runner config: {exc}") from exc
    if data is None:
        return IosProjectConfig(path=path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: iOS runner config must be a mapping")
    mapping = cast(dict[str, Any], data)
    raw_scenarios = mapping.get("scenarios", [])
    if not isinstance(raw_scenarios, list):
        raise ValueError(f"{path}: scenarios must be a list")
    scenarios = tuple(
        _scenario(raw, path, index) for index, raw in enumerate(cast(list[object], raw_scenarios))
    )
    names = [scenario.name for scenario in scenarios]
    if len(names) != len(set(names)):
        raise ValueError(f"{path}: scenario names must be unique")
    return IosProjectConfig(
        path=path,
        test_scheme=_optional_str(mapping.get("test_scheme"), f"{path}: test_scheme"),
        scenarios=scenarios,
    )


def resolve_ios_run_settings(
    project_dir: Path,
    test_scheme: str | None,
    launch_arguments: list[str] | None,
    scenario: str | None = None,
) -> tuple[str | None, list[str] | None]:
    """Apply CLI > project config > autodetection precedence.

    Args:
        project_dir: Runner project directory (the ``ios.yaml`` search start).
        test_scheme: Explicit scheme from the CLI or ``runnerConfig``.
        launch_arguments: Explicit launch arguments, kept even when empty.
        scenario: Scenario name; None selects ``default`` or the first scenario.

    Returns:
        ``(test_scheme, launch_arguments)``; a None scheme lets the runner autodetect.

    Raises:
        ValueError: The project config is malformed or the scenario is unknown.
    """
    config = load_project_ios_config(project_dir)
    if config is None:
        if scenario is not None:
            raise ValueError(f"scenario {scenario!r} requested but no {PROJECT_CONFIG_RELATIVE}")
        return test_scheme, launch_arguments
    selected = config.scenario(scenario)
    if test_scheme is None:
        test_scheme = (selected.test_scheme if selected else None) or config.test_scheme
    if launch_arguments is None and selected is not None and selected.launch_arguments:
        launch_arguments = list(selected.launch_arguments)
    return test_scheme, launch_arguments


__all__ = [
    "IosProjectConfig",
    "IosScenario",
    "find_project_ios_config",
    "load_project_ios_config",
    "resolve_ios_run_settings",
]
