"""Derive the AC-to-assertion mapping from `@spec AC-xxx` anchors in test sources.

An anchor block is a run of consecutive comment lines that names `@spec`, one or
more `AC-<n>` identifiers and the feature (`.specs/features/<feature>/` or
`<feature>:AC-<n>`). It binds the assertion it precedes, or the last assertion of
the test function it precedes. The derivation is deterministic: certification
derives it again and requires the same bindings, so no separate mapping review
is needed (feature 087).
"""

# @spec FR-001: Anchor-derived acceptance mapping
#   — .specs/features/087-anchor-derived-acceptance/spec.md#fr-001

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .acceptance_anchors_rust import rust_target
from .acceptance_requirements import AcceptanceRequirement, acceptance_inventory
from .execution_reports import junit_test_id
from .execution_scope import digest, read_regular

_AC = re.compile(r"\bAC-\d+\b")
_PY_COMMENT = re.compile(r"^\s*#")
_RS_COMMENT = re.compile(r"^\s*//")
_SKIPPED_DIRS = frozenset({"node_modules", "target", "venv", "__pycache__", "dist", "build"})
BLOCKING_CODES = frozenset(
    {
        "orphan_acceptance",
        "unknown_anchor",
        "anchor_target_unresolved",
        "anchor_test_without_assert",
        "anchor_test_parametrized",
        "anchor_source_unparsable",
    }
)


@dataclass(frozen=True)
class AnchorIssue:
    """One derivation finding; codes in BLOCKING_CODES refuse the mapping."""

    code: str
    detail: str

    @property
    def blocking(self) -> bool:
        return self.code in BLOCKING_CODES

    def to_json(self) -> dict[str, object]:
        return {"code": self.code, "detail": self.detail, "blocking": self.blocking}


@dataclass(frozen=True)
class DerivedBinding:
    """Plain binding data; `execution_mapping` turns it into an AcceptanceBinding."""

    requirement_id: str
    test_id: str
    expected: str
    assertion_path: str
    start_line: int
    end_line: int
    source_sha256: str
    justification: str


@dataclass
class Derivation:
    """Every binding and issue found for one feature."""

    feature: str
    bindings: list[DerivedBinding] = field(default_factory=list)
    issues: list[AnchorIssue] = field(default_factory=list)

    @property
    def blocking(self) -> list[AnchorIssue]:
        return [issue for issue in self.issues if issue.blocking]


@dataclass(frozen=True)
class _Anchor:
    path: str
    line: int  # Line of the block's first comment line.
    target: int  # First code line after the block (and decorators/attributes), or 0.
    ids: tuple[str, ...]
    label: str


def derive_acceptance(project_root: Path, feature: str) -> Derivation:
    """Scan test sources for the feature's anchors and bind each to one assertion."""
    root = project_root.resolve()
    spec_path = root / ".specs/features" / feature / "spec.md"
    spec = read_regular(spec_path, root).decode()
    inventory = {
        item.requirement_id: item for item in acceptance_inventory(root, feature, spec_text=spec)
    }
    result = Derivation(feature)
    for relative in _candidate_files(root):
        data = read_regular(root / relative, root)
        if b"@spec" not in data:
            continue
        text = data.decode(errors="replace")
        rust = relative.endswith(".rs")
        anchors = _anchors(relative, text, feature, rust)
        if not anchors:
            continue
        sha = digest(data)
        for anchor in anchors:
            _bind(result, inventory, anchor, text, sha, rust)
    bound = {binding.requirement_id for binding in result.bindings}
    for requirement_id, item in sorted(inventory.items()):
        if item.evidence_kind == "execution" and requirement_id not in bound:
            result.issues.append(
                AnchorIssue("orphan_acceptance", f"{requirement_id} has no @spec test anchor")
            )
    result.bindings.sort(key=lambda b: (b.requirement_id, b.assertion_path, b.start_line))
    return result


def _candidate_files(root: Path) -> list[str]:
    """Test sources: Python `test_*.py`/`*_test.py` and every Rust file, outside dot dirs."""
    try:
        listed = subprocess.run(
            ["git", "--no-optional-locks", "ls-files", "-co", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        listed = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    selected = []
    for relative in sorted(set(listed)):
        parts = PurePosixPath(relative).parts
        if any(part.startswith(".") or part in _SKIPPED_DIRS for part in parts[:-1]):
            continue
        name = parts[-1]
        python_test = name.endswith(".py") and (
            name.startswith("test_") or name.endswith("_test.py")
        )
        if (python_test or name.endswith(".rs")) and (root / relative).is_file():
            selected.append(relative)
    return selected


def _entries(block: list[str]) -> list[str]:
    """Split a comment block into `@spec` entries with their continuation lines."""
    entries: list[str] = []
    for line in block:
        if "@spec" in line or not entries:
            entries.append(line)
        else:
            entries[-1] += "\n" + line
    return [entry for entry in entries if "@spec" in entry]


def _feature_ids(entry: str, feature: str) -> tuple[str, ...] | None:
    """AC ids an entry attributes to ``feature``; None when it names another feature."""
    qualified = re.findall(rf"(?<![\w-]){re.escape(feature)}:(AC-\d+)\b", entry)
    if qualified:
        return tuple(qualified)
    features = set(re.findall(r"\.specs/features/([^/\s#]+)/", entry))
    if features == {feature}:
        return tuple(_AC.findall(entry))
    return None


def _anchors(path: str, text: str, feature: str, rust: bool) -> list[_Anchor]:
    comment = _RS_COMMENT if rust else _PY_COMMENT
    lines = text.splitlines()
    anchors: list[_Anchor] = []
    index = 0
    while index < len(lines):
        if not comment.match(lines[index]):
            index += 1
            continue
        start = index
        while index < len(lines) and comment.match(lines[index]):
            index += 1
        ids: list[str] = []
        label = ""
        for entry in _entries(lines[start:index]):
            found = _feature_ids(entry, feature)
            if found:
                ids.extend(found)
                label = label or (
                    entry.split(":", 1)[1].splitlines()[0].strip() if ":" in entry else ""
                )
        if ids:
            target = index + 1 if index < len(lines) else 0
            anchors.append(_Anchor(path, start + 1, target, tuple(dict.fromkeys(ids)), label))
    return anchors


def _bind(
    result: Derivation,
    inventory: dict[str, AcceptanceRequirement],
    anchor: _Anchor,
    text: str,
    sha: str,
    rust: bool,
) -> None:
    where = f"{anchor.path}:{anchor.line}"
    targets = rust_target(anchor, text) if rust else _python_target(anchor, text)
    if isinstance(targets, AnchorIssue):
        result.issues.append(targets)
        return
    if targets is None:
        return  # A Rust anchor on production code, outside any test.
    test_id, start, end = targets
    for key in anchor.ids:
        requirement_id = f"{result.feature}:{key}"
        item = inventory.get(requirement_id)
        if item is None:
            result.issues.append(AnchorIssue("unknown_anchor", f"{where} names {key}"))
            continue
        if item.evidence_kind != "execution":
            result.issues.append(AnchorIssue("anchor_to_review_ac", f"{where} names {key}"))
            continue
        result.bindings.append(
            DerivedBinding(
                requirement_id=requirement_id,
                test_id=test_id,
                expected=f"{key}: {anchor.label}" if anchor.label else key,
                assertion_path=anchor.path,
                start_line=start,
                end_line=end,
                source_sha256=sha,
                justification=f"Derived from the @spec anchor at {where}",
            )
        )


def _python_target(anchor: _Anchor, text: str) -> tuple[str, int, int] | AnchorIssue:
    where = f"{anchor.path}:{anchor.line}"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return AnchorIssue("anchor_source_unparsable", f"{anchor.path}: {exc.msg}")
    for owner, function in _python_tests(tree):
        test_id = junit_test_id("::".join([anchor.path, *owner, function.name]))
        asserts = sorted(
            (node for node in ast.walk(function) if isinstance(node, ast.Assert)),
            key=lambda node: node.lineno,
        )
        header = min([item.lineno for item in function.decorator_list] + [function.lineno])
        parametrized = any(_is_parametrize(item) for item in function.decorator_list)
        inside = function.lineno < anchor.line <= (function.end_lineno or function.lineno)
        if header == anchor.target or inside:
            if parametrized:
                return AnchorIssue("anchor_test_parametrized", f"{where} {function.name}")
            if header == anchor.target and asserts:
                last = asserts[-1]
                return test_id, last.lineno, last.end_lineno or last.lineno
            if header == anchor.target:
                return AnchorIssue("anchor_test_without_assert", f"{where} {function.name}")
            for node in asserts:
                if node.lineno == anchor.target:
                    return test_id, node.lineno, node.end_lineno or node.lineno
            return AnchorIssue("anchor_target_unresolved", f"{where} precedes no assertion")
    return AnchorIssue("anchor_not_bound", f"{where} is outside any test function")


_PythonTest = ast.FunctionDef | ast.AsyncFunctionDef


def _python_tests(tree: ast.Module) -> list[tuple[tuple[str, ...], _PythonTest]]:
    found: list[tuple[tuple[str, ...], _PythonTest]] = []
    for node in tree.body:
        if isinstance(node, _PythonTest) and node.name.startswith("test"):
            found.append(((), node))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            found.extend(
                ((node.name,), item)
                for item in node.body
                if isinstance(item, _PythonTest) and item.name.startswith("test")
            )
    return found


def _is_parametrize(decorator: ast.expr) -> bool:
    return "parametrize" in ast.unparse(decorator)
