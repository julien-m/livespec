# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-011)

"""Helpers for LiveSpec root ``penflow/`` UI contract workspaces.

The module inspects and bootstraps Penflow artifacts only. Runtime adapters
that emit ``actual-ui-tree.json`` stay outside LiveSpec core.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, cast

PENFLOW_DIRNAME = "penflow"
BRAINSTORM_PENFLOW_DIR = Path(".brainstorm") / "penflow"
CANONICAL_UI_PEN = Path(PENFLOW_DIRNAME) / "ui.pen"
IGNORED_PEN_SCAN_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "test-results",
}
REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "flow-ui-contract/",
    "ui.pen",
    "semantic-ui-tree.json",
    "expected-ui-tree.json",
    "code-ir.json",
)
REQUIRED_JSON_ARTIFACTS: tuple[str, ...] = (
    "semantic-ui-tree.json",
    "expected-ui-tree.json",
    "code-ir.json",
)
OPTIONAL_ARTIFACTS: tuple[str, ...] = (
    "actual-ui-tree.json",
    "compare-report.json",
    "compare-report.md",
    "review-report.md",
    "fix-report.md",
)
REQUIRED_MOCKUP_VALIDATION_FILES: tuple[str, ...] = (
    ".mockup-validation/audit-report.md",
    ".mockup-validation/visual-evidence/manifest.json",
    ".mockup-validation/visual-evidence/visual-report.md",
)

ContractState = Literal["absent", "incomplete", "ready"]
RuntimeComparisonState = Literal["ABSENT", "READY", "FAIL", "BLOCKED"]
PenflowTarget = Literal["web-desktop"]
JsonObject: TypeAlias = dict[str, object]

DESKTOP_MIN_WIDTH = 1024
DESKTOP_MIN_HEIGHT = 700
PLACEHOLDER_TEXT_RE = re.compile(
    r"^(?:[a-z][A-Za-z0-9_-]*\.[A-Za-z_][A-Za-z0-9_.-]*|\[[A-Z_ -]+]|<[^>]+>|REPLACE_ME|TBD)$"
)
FAKE_INTERACTION_LABELS = {
    "escape key",
    "esc key",
    "backdrop click",
    "click backdrop",
}


def _empty_str_list() -> list[str]:
    return []


@dataclass(frozen=True)
class PenflowContractStatus:
    """Status of a project's root Penflow UI contract workspace."""

    workspace: Path
    state: ContractState
    runtime_required: bool = False
    runtime_comparison: RuntimeComparisonState = "ABSENT"
    runtime_reason: str = "not_required"
    present: list[str] = field(default_factory=_empty_str_list)
    missing: list[str] = field(default_factory=_empty_str_list)
    optional_present: list[str] = field(default_factory=_empty_str_list)
    design_registry_required: bool = False
    design_registry_missing: list[str] = field(default_factory=_empty_str_list)
    mockup_validation_required: bool = False
    mockup_validation_missing: list[str] = field(default_factory=_empty_str_list)
    mockup_validation_status: str | None = None
    flow_count: int = 0
    screen_count: int = 0
    compare_status: str | None = None
    compare_issue_count: int | None = None
    parse_error: str | None = None

    def to_dict(self) -> JsonObject:
        """Return a JSON-serializable representation."""
        payload: JsonObject = {
            "workspace": str(self.workspace),
            "state": self.state,
            "runtime_required": self.runtime_required,
            "runtime_comparison": self.runtime_comparison,
            "runtime_reason": self.runtime_reason,
            "present": self.present,
            "missing": self.missing,
            "optional_present": self.optional_present,
            "design_registry_required": self.design_registry_required,
            "design_registry_missing": self.design_registry_missing,
            "mockup_validation_required": self.mockup_validation_required,
            "mockup_validation_missing": self.mockup_validation_missing,
            "flow_count": self.flow_count,
            "screen_count": self.screen_count,
        }
        if self.mockup_validation_status is not None:
            payload["mockup_validation_status"] = self.mockup_validation_status
        if self.compare_status is not None:
            payload["compare_status"] = self.compare_status
        if self.compare_issue_count is not None:
            payload["compare_issue_count"] = self.compare_issue_count
        if self.parse_error:
            payload["parse_error"] = self.parse_error
        return payload


@dataclass(frozen=True)
class PenflowBootstrapResult:
    """Result of copying a Brainstorm ``penflow/`` source to root ``penflow/``."""

    source: Path
    destination: Path
    copied: bool
    reason: str
    status: PenflowContractStatus

    def to_dict(self) -> JsonObject:
        """Return a JSON-serializable representation."""
        return {
            "source": str(self.source),
            "destination": str(self.destination),
            "copied": self.copied,
            "reason": self.reason,
            "status": self.status.to_dict(),
        }


def get_penflow_contract_status(
    project_root: Path,
    *,
    require_actual: bool = False,
    require_design_registry: bool = False,
    require_mockup_validation: bool = False,
    feature_slug: str | None = None,
    target: PenflowTarget | None = None,
) -> PenflowContractStatus:
    """Inspect root ``penflow/`` and summarize contract readiness.

    Args:
        project_root: LiveSpec project root.
        require_actual: Whether a UI runtime comparison is expected.
        require_design_registry: Whether `.specs/design` must contain the
            Penflow/Pencil source, mockups, and baseline directories.
        require_mockup_validation: Whether Mockup Factory visual evidence and
            UX validation must exist before code or runtime approval.
        feature_slug: Optional feature slug used to validate feature-scoped
            design registry paths.
        target: Optional UI target. ``web-desktop`` blocks mobile-sized
            ``ui.pen`` roots so desktop web features cannot pass with mobile
            mockups.

    Returns:
        Workspace status. Missing workspaces report ``absent`` instead of
        failing so legacy non-UI projects remain valid. Missing
        ``actual-ui-tree.json`` is only blocking when runtime comparison is
        explicitly required.
    """
    workspace = project_root / PENFLOW_DIRNAME
    design_registry_missing = (
        _design_registry_missing(project_root, feature_slug=feature_slug)
        if require_design_registry
        else []
    )
    mockup_validation_missing, mockup_validation_status = (
        _mockup_validation_missing(project_root, feature_slug=feature_slug)
        if require_mockup_validation
        else ([], None)
    )
    if not workspace.exists():
        return PenflowContractStatus(
            workspace=workspace,
            state="absent",
            runtime_required=require_actual,
            runtime_comparison="ABSENT",
            runtime_reason="workspace_absent",
            missing=list(REQUIRED_ARTIFACTS),
            design_registry_required=require_design_registry,
            design_registry_missing=design_registry_missing,
            mockup_validation_required=require_mockup_validation,
            mockup_validation_missing=mockup_validation_missing,
            mockup_validation_status=mockup_validation_status,
        )

    present = [name for name in REQUIRED_ARTIFACTS if _required_path_exists(workspace, name)]
    missing = [name for name in REQUIRED_ARTIFACTS if name not in present]
    missing.extend(_invalid_required_artifacts(workspace, present))
    missing.extend(_ui_pen_quality_issues(workspace / "ui.pen", target=target))
    missing.extend(_duplicate_pen_files(project_root))
    missing.extend(design_registry_missing)
    missing.extend(mockup_validation_missing)
    missing = list(dict.fromkeys(missing))
    optional_present = [name for name in OPTIONAL_ARTIFACTS if (workspace / name).exists()]
    flow_count, screen_count, parse_error = _semantic_counts(workspace / "semantic-ui-tree.json")
    state: ContractState = "ready" if not missing else "incomplete"
    (
        runtime_comparison,
        runtime_reason,
        compare_status,
        compare_issue_count,
        compare_parse_error,
    ) = _runtime_comparison_state(
        workspace=workspace,
        contract_state=state,
        require_actual=require_actual,
    )
    if compare_parse_error:
        parse_error = compare_parse_error
    return PenflowContractStatus(
        workspace=workspace,
        state=state,
        runtime_required=require_actual,
        runtime_comparison=runtime_comparison,
        runtime_reason=runtime_reason,
        present=present,
        missing=missing,
        optional_present=optional_present,
        design_registry_required=require_design_registry,
        design_registry_missing=design_registry_missing,
        mockup_validation_required=require_mockup_validation,
        mockup_validation_missing=mockup_validation_missing,
        mockup_validation_status=mockup_validation_status,
        flow_count=flow_count,
        screen_count=screen_count,
        compare_status=compare_status,
        compare_issue_count=compare_issue_count,
        parse_error=parse_error,
    )


def bootstrap_penflow_workspace(
    project_root: Path,
    *,
    source_dir: Path | None = None,
) -> PenflowBootstrapResult:
    """Copy a Brainstorm ``penflow/`` directory to root ``penflow/`` if possible.

    The copy is intentionally non-destructive: an existing root workspace wins
    and is never overwritten.

    Args:
        project_root: LiveSpec project root.
        source_dir: Explicit Brainstorm ``penflow/`` directory. If omitted,
            LiveSpec falls back to the legacy in-project Brainstorm export.

    Returns:
        Copy result and post-copy workspace status.
    """
    source = source_dir if source_dir is not None else project_root / BRAINSTORM_PENFLOW_DIR
    destination = project_root / PENFLOW_DIRNAME
    if destination.exists():
        return PenflowBootstrapResult(
            source=source,
            destination=destination,
            copied=False,
            reason="workspace_exists",
            status=get_penflow_contract_status(project_root),
        )
    if not source.exists():
        return PenflowBootstrapResult(
            source=source,
            destination=destination,
            copied=False,
            reason="source_missing",
            status=get_penflow_contract_status(project_root),
        )

    shutil.copytree(source, destination)
    return PenflowBootstrapResult(
        source=source,
        destination=destination,
        copied=True,
        reason="copied",
        status=get_penflow_contract_status(project_root),
    )


def _invalid_required_artifacts(workspace: Path, present: list[str]) -> list[str]:
    invalid: list[str] = []
    for name in present:
        if name not in REQUIRED_JSON_ARTIFACTS:
            continue
        path = workspace / name
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append(name)
            continue
        if not isinstance(raw, dict):
            invalid.append(name)
    return invalid


def _required_path_exists(workspace: Path, name: str) -> bool:
    path = workspace / name.rstrip("/")
    if name.endswith("/"):
        return path.is_dir()
    return path.is_file()


def _design_registry_missing(project_root: Path, *, feature_slug: str | None) -> list[str]:
    missing: list[str] = []
    design_root = project_root / ".specs" / "design"
    required_files = (
        design_root / "screens" / "index.md",
        design_root / "changelog.md",
    )
    for path in required_files:
        if not path.is_file():
            missing.append(str(path.relative_to(project_root)))

    if feature_slug is None:
        screens_root = design_root / "screens"
        if not screens_root.is_dir():
            missing.append(".specs/design/screens/")
        elif not any(screens_root.rglob("*.png")):
            missing.append(".specs/design/screens/**/*.png")
        return missing

    feature_screens = design_root / "screens" / feature_slug
    feature_baselines = design_root / "baselines" / feature_slug
    if not feature_screens.is_dir():
        missing.append(f".specs/design/screens/{feature_slug}/")
    elif not any(feature_screens.glob("*.png")):
        missing.append(f".specs/design/screens/{feature_slug}/*.png")
    if not feature_baselines.is_dir():
        missing.append(f".specs/design/baselines/{feature_slug}/")
    return missing


def _duplicate_pen_files(project_root: Path) -> list[str]:
    duplicates: list[str] = []
    for path in project_root.rglob("*.pen"):
        try:
            relative = path.relative_to(project_root)
        except ValueError:
            continue
        if any(part in IGNORED_PEN_SCAN_DIRS for part in relative.parts):
            continue
        if relative == CANONICAL_UI_PEN:
            continue
        duplicates.append(f"duplicate_pen:{relative.as_posix()}")
    return duplicates


def _mockup_validation_missing(
    project_root: Path,
    *,
    feature_slug: str | None,
) -> tuple[list[str], str | None]:
    missing: list[str] = []
    for name in REQUIRED_MOCKUP_VALIDATION_FILES:
        if not (project_root / name).is_file():
            missing.append(name)

    if feature_slug is not None:
        feature_group = project_root / ".mockup-validation" / feature_slug
        for name in ("checklist.md", "manifest.json", "drift-report.json"):
            path = feature_group / name
            if not path.is_file():
                missing.append(str(path.relative_to(project_root)))

    manifest_path = project_root / ".mockup-validation" / "visual-evidence" / "manifest.json"
    status = _mockup_validation_status(manifest_path)
    if status != "PASS":
        missing.append(".mockup-validation/visual-evidence/manifest.json:status")
    if not any((project_root / ".mockup-validation" / "visual-evidence").glob("*.png")):
        missing.append(".mockup-validation/visual-evidence/*.png")
    return list(dict.fromkeys(missing)), status


def _mockup_validation_status(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    status = cast(dict[str, object], raw).get("status")
    return status.upper() if isinstance(status, str) else None


def _ui_pen_quality_issues(path: Path, *, target: PenflowTarget | None) -> list[str]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["ui.pen"]
    if not isinstance(raw, dict):
        return ["ui.pen"]
    payload = cast(dict[str, object], raw)
    surfaces = _ui_pen_surfaces(payload)
    if not surfaces:
        return ["ui.pen:missing_screen"]

    issues: list[str] = []
    if target == "web-desktop":
        issues.extend(_desktop_frame_issues(surfaces))
    for node in _walk_pen_nodes(surfaces):
        issues.extend(_node_text_quality_issues(node))
    return list(dict.fromkeys(issues))


def _ui_pen_surfaces(payload: dict[str, object]) -> list[object]:
    children = payload.get("children")
    if isinstance(children, list) and children:
        return cast(list[object], children)
    screens = payload.get("screens")
    if isinstance(screens, list) and screens:
        return cast(list[object], screens)
    return []


def _desktop_frame_issues(children: list[object]) -> list[str]:
    first_frame: dict[str, object] | None = None
    for item in children:
        if not isinstance(item, dict):
            continue
        candidate = cast(dict[str, object], item)
        if candidate.get("type") == "frame" or candidate.get("width") is not None:
            first_frame = candidate
            break
    if first_frame is None:
        return ["ui.pen:missing_screen"]
    issues: list[str] = []
    width = first_frame.get("width")
    height = first_frame.get("height")
    if not isinstance(width, int | float) or width < DESKTOP_MIN_WIDTH:
        issues.append("ui.pen:desktop_frame_width")
    if not isinstance(height, int | float) or height < DESKTOP_MIN_HEIGHT:
        issues.append("ui.pen:desktop_frame_height")
    return issues


def _walk_pen_nodes(nodes: list[object]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        payload = cast(dict[str, object], node)
        found.append(payload)
        for child_key in ("children", "regions"):
            children = payload.get(child_key)
            if isinstance(children, list):
                found.extend(_walk_pen_nodes(cast(list[object], children)))
    return found


def _node_text_quality_issues(node: dict[str, object]) -> list[str]:
    issues: list[str] = []
    for text_field in ("content", "text", "label"):
        value = node.get(text_field)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if PLACEHOLDER_TEXT_RE.match(normalized):
            issues.append("ui.pen:placeholder_text")
        if normalized.lower() in FAKE_INTERACTION_LABELS:
            issues.append("ui.pen:fake_interaction_control")
    return issues


def _runtime_comparison_state(
    *,
    workspace: Path,
    contract_state: ContractState,
    require_actual: bool,
) -> tuple[RuntimeComparisonState, str, str | None, int | None, str | None]:
    if contract_state == "absent":
        return "ABSENT", "workspace_absent", None, None, None
    if contract_state == "incomplete":
        return "BLOCKED", "required_contract_artifacts_missing", None, None, None
    if (workspace / "actual-ui-tree.json").exists():
        compare_report = workspace / "compare-report.json"
        if compare_report.exists():
            compare_status, issue_count, parse_error = _compare_report_status(compare_report)
            if parse_error is not None:
                return "BLOCKED", "compare_report_invalid", compare_status, issue_count, parse_error
            if compare_status != "PASS":
                return "FAIL", "compare_report_failed", compare_status, issue_count, None
            if issue_count and issue_count > 0:
                return "FAIL", "compare_report_has_issues", compare_status, issue_count, None
            return "READY", "compare_report_passed", compare_status, issue_count, None
        return "READY", "actual_tree_present", None, None, None
    if require_actual:
        return "BLOCKED", "actual_tree_missing", None, None, None
    return "ABSENT", "actual_tree_not_required", None, None, None


def _compare_report_status(path: Path) -> tuple[str | None, int | None, str | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, None, str(exc)
    if not isinstance(raw, dict):
        return None, None, "compare report root must be an object"
    payload = cast(dict[str, object], raw)
    status_raw = payload.get("status")
    status = status_raw.upper() if isinstance(status_raw, str) else None
    issues_raw = payload.get("issues")
    if isinstance(issues_raw, list):
        issue_count = len(cast(list[object], issues_raw))
    else:
        issue_count = _summary_issue_count(payload.get("summary"))
    return status, issue_count, None


def _summary_issue_count(summary: object) -> int | None:
    if not isinstance(summary, dict):
        return None
    payload = cast(dict[str, object], summary)
    value = payload.get("issues")
    return value if isinstance(value, int) else None


def _semantic_counts(path: Path) -> tuple[int, int, str | None]:
    if not path.exists():
        return 0, 0, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 0, 0, str(exc)
    if not isinstance(raw, dict):
        return 0, 0, "semantic tree root must be an object"
    # json.loads returns Any; the root shape check above narrows runtime behavior.
    payload = cast(dict[str, object], raw)
    flows = payload.get("flows")
    screens = payload.get("screens")
    # List element types do not affect counts, so object casts keep validation shape-only.
    flow_count = len(cast(list[object], flows)) if isinstance(flows, list) else 0
    screen_count = len(cast(list[object], screens)) if isinstance(screens, list) else 0
    return flow_count, screen_count, None


# Export only the Penflow contract helpers used by the CLI and tests.
__all__ = [
    "CANONICAL_UI_PEN",
    "OPTIONAL_ARTIFACTS",
    "PENFLOW_DIRNAME",
    "REQUIRED_ARTIFACTS",
    "JsonObject",
    "PenflowBootstrapResult",
    "PenflowContractStatus",
    "PenflowTarget",
    "RuntimeComparisonState",
    "bootstrap_penflow_workspace",
    "get_penflow_contract_status",
]
