"""View a 081 outcome contract's inventory as ordered task-like rows for inventory tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def checklist_tasks(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return every active inventory row, using the required task when one proves it.

    Args:
        contract: Saved contract (``checklist``) or canonical payload
            (``execution_tasks`` + ``definition_of_done``).

    Returns:
        Rows in inventory order; indicative rows carry ``evidence_kind: documentary``.
    """
    if "checklist" in contract:
        rows = list(contract["checklist"])
    else:
        rows = [*contract["execution_tasks"], *contract["definition_of_done"]]
    required: dict[str, dict[str, Any]] = {}
    for task in contract["tasks"]:
        description = str(task["description"]).split(" [feature: ", 1)[0]
        required.setdefault(description, task)
    view: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows, 1):
        task = required.get(row)
        if task is not None:
            view.append({**task, "description": row, "ordinal": ordinal})
        else:
            view.append(
                {
                    "id": None,
                    "description": row,
                    "ordinal": ordinal,
                    "evidence_kind": "documentary",
                    "indicative": True,
                }
            )
    return view
