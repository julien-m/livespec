"""Release evidence of a feature plan: pending until a recorded proof names its step (090).

A release proof is a row of the ``## Release Evidence`` table of ``implementation.md``:
``| Step | Evidence | Proof |``. The row must give the step number and the step's own name,
so a proof never moves to another step when the plan is renumbered or rewritten, and its
proof cell must name something checkable (a path, a URL or an identifier with a digit) and
announce nothing (``pending``, ``deferred``, ``in progress``, ``❌``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

from .plan_evidence import (
    PlanStep,
    evidence_class_errors,
    heading,
    normalize_label,
    plain,
    plan_steps,
    title_text,
    unfenced,
)

# A table row: up to three spaces of indentation, then a pipe (four spaces is code).
_ROW = re.compile(r"^ {0,3}\|")
_LABEL = re.compile(r"(?:step *)?(\d{1,9}(?:\.\d{1,9})*)", re.IGNORECASE)
# A proof cell opening with one of these marks or words announces a proof instead of naming one.
_NOT_A_PROOF_MARKS = ("❌", "⏳", "⌛", "\U0001f6a7", "?", "☐", "[ ]", "<", "✗")
_NOT_A_PROOF_WORDS = re.compile(
    r"^(pending|tbd|tbc|todo|to do|not|no|none|missing|awaiting|waiting|will|later|blocked"
    r"|unknown|n/?a|wip|soon|x|false|planned|expected|placeholder)\b",
    re.IGNORECASE,
)
# Announcement words anywhere in the prose of the cell (paths and URLs are not prose).
_ANNOUNCEMENT = re.compile(
    r"\b(pending|tbd|tbc|tba|todo|to do|to be|yet|deferred|in progress|awaiting|waiting|later"
    r"|soon|coming|planned|placeholder|wip|missing|blocked)\b",
    re.IGNORECASE,
)
# Checkable tokens: a URL, a path (a separator and a 2+ character part, so not ``n/a``), a
# file name with an extension, or an identifier with a digit (build or receipt number).
_URL = re.compile(r"[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_PATH = re.compile(r"[/\\]\w{2}|\w{2}[/\\]|\w\.[a-z0-9]{1,8}$", re.IGNORECASE)
_TOKEN_EDGES = "()[]{}<>,;:'\"`*_"
_LEADING_PUNCTUATION = "-" + chr(0x2014) + chr(0x2013) + " ([{'\""
# Commands whose goal implements a feature; spec-ship requires the release evidence instead.
_IMPLEMENTING_COMMANDS = frozenset({"spec-implement", "spec-feature"})


class ReleaseItem(TypedDict):
    """One release-class plan step and the state of its proof."""

    feature: str
    step: str
    evidence: str
    status: Literal["pending", "satisfied", "mismatch"]
    proof: NotRequired[str]


def _key(text: str) -> str:
    return plain(text).lower().rstrip(" .:;")


def _checkable(token: str) -> bool:
    return bool(_URL.match(token) or _PATH.search(token) or any(c.isdigit() for c in token))


def is_proof(cell: str) -> bool:
    """Whether a proof cell names something checkable and announces nothing."""
    text = cell.strip()
    if not text or text.startswith(_NOT_A_PROOF_MARKS):
        return False
    words = plain(text).lstrip(_LEADING_PUNCTUATION)
    if not words or _NOT_A_PROOF_WORDS.match(words):
        return False
    tokens = [token.strip(_TOKEN_EDGES) for token in words.split()]
    prose = " ".join(t for t in tokens if not (_URL.match(t) or _PATH.search(t)))
    return any(_checkable(t) for t in tokens) and not _ANNOUNCEMENT.search(prose)


def recorded_release_rows(implementation: str) -> dict[str, tuple[str, str]]:
    """Step label to ``(named step, proof)``; the latest row of a step wins."""
    rows: dict[str, tuple[str, str]] = {}
    inside = False
    for line in unfenced(implementation):
        parsed = heading(line)
        if parsed:
            # Only the canonical level-2 section: a nested or top-level lookalike is no proof.
            inside = parsed[0] == 2 and _key(parsed[1]) == "release evidence"
            continue
        if not inside or not _ROW.match(line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        label = _LABEL.fullmatch(plain(cells[0]))
        if label and len(cells) >= 2:
            name, proof = (cells[1], cells[2]) if len(cells) >= 3 else ("", cells[1])
            rows[normalize_label(label.group(1))] = (name, proof)
    return rows


def _item(feature: str, step: PlanStep, row: tuple[str, str] | None) -> ReleaseItem:
    item = ReleaseItem(feature=feature, step=step.label, evidence=step.title, status="pending")
    if row is None or not is_proof(row[1]):
        return item
    if _key(row[0]) not in (_key(step.name), _key(step.title)):
        item["status"] = "mismatch"
    else:
        item["status"] = "satisfied"
    item["proof"] = title_text(row[1])
    return item


def _read(path: Path) -> str:
    # Undecodable bytes never crash a goal render; they cannot form a valid declaration.
    return path.read_text(encoding="utf-8", errors="replace")


# @spec FR-002: Release evidence pending until shipping
#   — .specs/features/090-minimal-plan-scope/spec.md#fr-002
def release_evidence(project_root: Path, feature: str) -> list[ReleaseItem]:
    """Release-class steps of the feature plan with the state of their recorded proof."""
    feature_dir = project_root / ".specs" / "features" / feature
    plan = feature_dir / "plan.md"
    if not plan.is_file():
        return []
    steps = [s for s in plan_steps(_read(plan))[0] if "release" in s.classes]
    implementation = feature_dir / "implementation.md"
    # implementation.md is read only for a plan that declares release evidence.
    readable = steps and implementation.is_file()
    rows = recorded_release_rows(_read(implementation)) if readable else {}
    return [_item(feature, step, rows.get(step.label)) for step in steps]


def release_evidence_errors(project_root: Path, feature: str) -> list[str]:
    """Plan evidence class errors, then proof rows that name another step than theirs."""
    plan = project_root / ".specs" / "features" / feature / "plan.md"
    if not plan.is_file():
        return []
    errors = evidence_class_errors(_read(plan))
    if errors:
        return errors
    return [
        f"Release Evidence row for step {item['step']} does not name the plan step "
        f"'{item['evidence']}'; write `| {item['step']} | <step name> | <proof> |`"
        for item in release_evidence(project_root, feature)
        if item["status"] == "mismatch"
    ]


def pending_release_evidence(project_root: Path, feature: str) -> list[ReleaseItem]:
    """Release items of the feature that no matching recorded proof satisfies yet."""
    return [i for i in release_evidence(project_root, feature) if i["status"] != "satisfied"]


# @spec FR-002: Release evidence pending, outside required tasks
#   — .specs/features/090-minimal-plan-scope/spec.md#fr-002
def release_goal_context(
    command: str, project_root: Path, feature: str | None
) -> dict[str, list[ReleaseItem] | str]:
    """Goal ``runtime_context`` entry listing pending release evidence, never a required task.

    The key is omitted when nothing is pending so existing contracts keep their bytes; an
    unreadable plan or map is reported instead of failing the goal render.
    """
    if command not in _IMPLEMENTING_COMMANDS or not feature:
        return {}
    try:
        pending = pending_release_evidence(project_root, feature)
    except OSError as exc:
        return {"release_evidence_unreadable": f"{type(exc).__name__}: {exc.strerror or exc}"}
    return {"pending_release_evidence": pending} if pending else {}
