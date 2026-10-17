"""Explicit task predicates over approved feature artifacts (078 FR-009)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def section(text: str, title: str) -> str | None:
    """Read one exact level-two heading outside fenced examples."""
    active = False
    fenced = False
    lines: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            if active:
                break
            active = line[3:].strip() == title
            continue
        if active:
            lines.append(line)
    return "\n".join(lines) if active else None


# @spec FR-009: Explicit execution applicability
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-009
def _declares_command(commands: str, token: str) -> bool:
    """Ignore explicit absent-command rows without hiding resolved or unknown declarations."""
    fenced = False
    for line in commands.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if fenced or not re.search(rf"\b{token}\b", line, re.IGNORECASE):
            continue
        if line.strip().startswith("|"):
            cells = [cell.strip().strip("`").strip() for cell in line.strip().strip("|").split("|")]
            # An absent command is authoritative. A real command still wins even
            # when its status is "Not run" or a separate row declares N/A.
            if len(cells) > 1 and cells[1].casefold() in {
                "n/a",
                "not applicable",
                "not run",
                "none",
                "—",
                "-",
            }:
                continue
        # Unknown declarations remain required so discovery fails closed.
        return True
    return False


def resolve_applicability(
    root: Path | None, feature: str | None, predicate: str
) -> dict[str, object]:
    """Missing prerequisites remain required; only an observed absent declaration is N/A."""
    if predicate not in {"behavioral-ac", "integration-command", "e2e-command"}:
        raise ValueError(f"unknown_evidence_applicability:{predicate}")
    if root is None or not feature:
        return {"predicate": predicate, "applicable": True, "reason": "context_unresolved"}
    if predicate == "e2e-command":
        from .visual_gate import detect_visual_feature

        if (
            detect_visual_feature(project_root=root, feature_slug=feature).classification
            != "NON_VISUAL"
        ):
            return {
                "predicate": predicate,
                "applicable": True,
                "reason": "visual_execution_required",
            }
    name = "spec.md" if predicate == "behavioral-ac" else "plan.md"
    path = root / ".specs/features" / feature / name
    if not path.is_file():
        return {"predicate": predicate, "applicable": True, "reason": "prerequisite_missing"}
    text = path.read_text(encoding="utf-8")
    if predicate == "behavioral-ac":
        applicable = section(text, "Behavioral AC") is not None
    else:
        commands = section(text, "Resolved Test Commands")
        if commands is None:
            return {"predicate": predicate, "applicable": True, "reason": "test_discovery_required"}
        token = "integration" if predicate == "integration-command" else "e2e"
        # This is an explicit declaration predicate, not task-purpose inference.
        applicable = _declares_command(commands, token)
    return {
        "predicate": predicate,
        "applicable": applicable,
        "source": path.relative_to(root).as_posix(),
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "reason": "declared" if applicable else "not_declared",
    }
