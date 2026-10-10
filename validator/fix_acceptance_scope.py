"""Bind filtered fix execution to canonical acceptance declarations and their current source."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .acceptance_requirements import acceptance_inventory
from .normative_identity import normative_hash
from .penflow_requirement_source import extract_requirement_definitions

# Explicit internal adapters for compilation and typed proof consumption.
__all__ = ["_bind_fix_acceptance_scope", "_fix_selection_missing"]


class _FixSelection(BaseModel):
    """Immutable selector, execution IDs and normative source identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    selector_flags: tuple[str, ...]
    required_acs: tuple[str, ...]
    source_hash: str


def _selected_acceptance(root: Path, feature: str, flags: tuple[str, ...]) -> _FixSelection:
    """Resolve one explicit AC/FR selector, rejecting absent, unknown or mixed scopes."""
    if len(flags) != 1 or "=" not in flags[0]:
        raise ValueError("fix_selection_requires_one_ac_or_fr")
    option, selected = flags[0].split("=", 1)
    if option not in {"--ac", "--fr"}:
        raise ValueError("fix_unknown_selector")
    spec = root / ".specs/features" / feature / "spec.md"
    text = spec.read_bytes().decode("utf-8")
    inventory = {
        item.requirement_id: item for item in acceptance_inventory(root, feature, spec_text=text)
    }
    if option == "--ac":
        required: tuple[str, ...] = (f"{feature}:{selected}",)
    else:
        definitions = extract_requirement_definitions(spec, feature)
        matches = [
            item for item in definitions if item.local_id == selected and selected.startswith("FR-")
        ]
        if len(matches) != 1 or not matches[0].references:
            raise ValueError("fix_fr_acceptance_mapping_missing_or_ambiguous")
        required = tuple(sorted(ref.removeprefix("livespec:") for ref in matches[0].references))
    if any(key not in inventory for key in required):
        raise ValueError("fix_selected_acceptance_not_declared")
    if any(inventory[key].evidence_kind != "execution" for key in required):
        raise ValueError("fix_review_acceptance_requires_existing_full_feature_verification")
    source_hash = normative_hash(text, lifecycle_document=True)
    if source_hash != normative_hash(spec.read_bytes().decode("utf-8"), lifecycle_document=True):
        raise ValueError("fix_selection_source_changed_during_read")
    return _FixSelection(selector_flags=flags, required_acs=required, source_hash=source_hash)


def _bind_fix_acceptance_scope(
    tasks: list[dict[str, Any]], root: Path, feature: str | None, flags: list[str]
) -> None:
    """Freeze the selected requirements in existing JSON goal tasks; write no files."""
    # Goal tasks are heterogeneous JSON dictionaries at the existing compiler boundary.
    selected_flags = tuple(flag for flag in flags if flag.split("=", 1)[0] in {"--ac", "--fr"})
    execution = [task for task in tasks if task.get("evidence_kind") == "execution"]
    if not selected_flags or not execution:
        return
    if not feature:
        raise ValueError("fix_selection_feature_required")
    selection = _selected_acceptance(root, feature, selected_flags)
    for task in execution:
        task["required_acs"] = list(selection.required_acs)
        task.setdefault("expected_evidence", {})["fix_selection"] = selection.model_dump(
            mode="json"
        )


def _fix_selection_missing(task: Mapping[str, Any], root: Path, feature: str) -> list[str]:
    """Reject changed normative selection; tasks without this new binding stay unchanged."""
    expected = task.get("expected_evidence", {})
    raw = expected.get("fix_selection") if isinstance(expected, Mapping) else None
    if raw is None:
        return []
    selection = _FixSelection.model_validate(raw)
    current = _selected_acceptance(root, feature, selection.selector_flags)
    if current != selection or task.get("required_acs") != list(selection.required_acs):
        return ["fix_acceptance_selection_changed_recompile_required"]
    return []
