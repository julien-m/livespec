"""Helpers for LiveSpec root ``penflow/`` UI contract workspaces.

The module inspects and bootstraps Penflow artifacts only. Runtime adapters
that emit ``actual-ui-tree.json`` stay outside LiveSpec core.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, cast

PENFLOW_DIRNAME = "penflow"
BRAINSTORM_PENFLOW_DIR = Path(".brainstorm") / "penflow"
REQUIRED_ARTIFACTS: tuple[str, ...] = (
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

ContractState = Literal["absent", "incomplete", "ready"]
RuntimeComparisonState = Literal["ABSENT", "READY", "BLOCKED"]
JsonObject: TypeAlias = dict[str, object]


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
    flow_count: int = 0
    screen_count: int = 0
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
            "flow_count": self.flow_count,
            "screen_count": self.screen_count,
        }
        if self.parse_error:
            payload["parse_error"] = self.parse_error
        return payload


@dataclass(frozen=True)
class PenflowBootstrapResult:
    """Result of copying ``.brainstorm/penflow/`` to root ``penflow/``."""

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
) -> PenflowContractStatus:
    """Inspect root ``penflow/`` and summarize contract readiness.

    Args:
        project_root: LiveSpec project root.
        require_actual: Whether a UI runtime comparison is expected.

    Returns:
        Workspace status. Missing workspaces report ``absent`` instead of
        failing so legacy non-UI projects remain valid. Missing
        ``actual-ui-tree.json`` is only blocking when runtime comparison is
        explicitly required.
    """
    workspace = project_root / PENFLOW_DIRNAME
    if not workspace.exists():
        return PenflowContractStatus(
            workspace=workspace,
            state="absent",
            runtime_required=require_actual,
            runtime_comparison="ABSENT",
            runtime_reason="workspace_absent",
            missing=list(REQUIRED_ARTIFACTS),
        )

    present = [name for name in REQUIRED_ARTIFACTS if (workspace / name).exists()]
    missing = [name for name in REQUIRED_ARTIFACTS if name not in present]
    missing.extend(_invalid_required_artifacts(workspace, present))
    optional_present = [name for name in OPTIONAL_ARTIFACTS if (workspace / name).exists()]
    flow_count, screen_count, parse_error = _semantic_counts(workspace / "semantic-ui-tree.json")
    state: ContractState = "ready" if not missing else "incomplete"
    runtime_comparison, runtime_reason = _runtime_comparison_state(
        workspace=workspace,
        contract_state=state,
        require_actual=require_actual,
    )
    return PenflowContractStatus(
        workspace=workspace,
        state=state,
        runtime_required=require_actual,
        runtime_comparison=runtime_comparison,
        runtime_reason=runtime_reason,
        present=present,
        missing=missing,
        optional_present=optional_present,
        flow_count=flow_count,
        screen_count=screen_count,
        parse_error=parse_error,
    )


def bootstrap_penflow_workspace(project_root: Path) -> PenflowBootstrapResult:
    """Copy ``.brainstorm/penflow/`` to root ``penflow/`` if possible.

    The copy is intentionally non-destructive: an existing root workspace wins
    and is never overwritten.

    Args:
        project_root: LiveSpec project root.

    Returns:
        Copy result and post-copy workspace status.
    """
    source = project_root / BRAINSTORM_PENFLOW_DIR
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
        path = workspace / name
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append(name)
            continue
        if not isinstance(raw, dict):
            invalid.append(name)
    return invalid


def _runtime_comparison_state(
    *,
    workspace: Path,
    contract_state: ContractState,
    require_actual: bool,
) -> tuple[RuntimeComparisonState, str]:
    if contract_state == "absent":
        return "ABSENT", "workspace_absent"
    if contract_state == "incomplete":
        return "BLOCKED", "required_contract_artifacts_missing"
    if (workspace / "actual-ui-tree.json").exists():
        return "READY", "actual_tree_present"
    if require_actual:
        return "BLOCKED", "actual_tree_missing"
    return "ABSENT", "actual_tree_not_required"


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
    "OPTIONAL_ARTIFACTS",
    "PENFLOW_DIRNAME",
    "REQUIRED_ARTIFACTS",
    "JsonObject",
    "PenflowBootstrapResult",
    "PenflowContractStatus",
    "RuntimeComparisonState",
    "bootstrap_penflow_workspace",
    "get_penflow_contract_status",
]
