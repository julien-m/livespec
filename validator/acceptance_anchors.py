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

from .acceptance_requirements import AcceptanceRequirement, acceptance_inventory
from .execution_reports import junit_test_id
from .execution_rust_source import rust_assertions, rust_functions
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
            ["git", "ls-files", "-co", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
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
        block = "\n".join(lines[start:index])
        if "@spec" not in block or not _AC.search(block):
            continue
        if f".specs/features/{feature}/" not in block and f"{feature}:AC-" not in block:
            continue  # Unqualified or another feature's anchor.
        target = index
        prefix = "#[" if rust else "@"
        while target < len(lines) and lines[target].lstrip().startswith(prefix):
            target += 1
        ids = tuple(dict.fromkeys(_AC.findall(block)))
        label = block.split(":", 1)[1].splitlines()[0].strip() if ":" in block else ""
        anchors.append(
            _Anchor(path, start + 1, target + 1 if target < len(lines) else 0, ids, label)
        )
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
    targets = _rust_target(anchor, text) if rust else _python_target(anchor, text)
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
    tree = ast.parse(text)
    for owner, function in _python_tests(tree):
        test_id = junit_test_id("::".join([anchor.path, *owner, function.name]))
        asserts = sorted(
            (node for node in ast.walk(function) if isinstance(node, ast.Assert)),
            key=lambda node: node.lineno,
        )
        if function.lineno == anchor.target:
            if any(_is_parametrize(item) for item in function.decorator_list):
                return AnchorIssue("anchor_test_parametrized", f"{where} {function.name}")
            if not asserts:
                return AnchorIssue("anchor_test_without_assert", f"{where} {function.name}")
            last = asserts[-1]
            return test_id, last.lineno, last.end_lineno or last.lineno
        inside = function.lineno < anchor.line <= (function.end_lineno or function.lineno)
        for node in asserts:
            if inside and node.lineno == anchor.target:
                if any(_is_parametrize(item) for item in function.decorator_list):
                    return AnchorIssue("anchor_test_parametrized", f"{where} {function.name}")
                return test_id, node.lineno, node.end_lineno or node.lineno
    return AnchorIssue("anchor_target_unresolved", f"{where} precedes no test or assertion")


def _python_tests(tree: ast.Module) -> list[tuple[tuple[str, ...], ast.FunctionDef]]:
    found: list[tuple[tuple[str, ...], ast.FunctionDef]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
            found.append(((), node))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            found.extend(
                ((node.name,), item)
                for item in node.body
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test")
            )
    return found


def _is_parametrize(decorator: ast.expr) -> bool:
    return "parametrize" in ast.unparse(decorator)


def _rust_target(anchor: _Anchor, text: str) -> tuple[str, int, int] | AnchorIssue | None:
    where = f"{anchor.path}:{anchor.line}"
    lines = text.splitlines()
    attributes = "\n".join(lines[anchor.line - 1 : max(anchor.target - 1, 0)])
    assertions = rust_assertions(text)
    integration = "tests" in PurePosixPath(anchor.path).parts[:-1]
    for function in rust_functions(text):
        test_id = "::".join([*_rust_module(anchor.path), *function.modules, function.name])
        owned = [
            item
            for item in assertions
            if item.function == function.name and function.line <= item.line <= function.end_line
        ]
        if function.line == anchor.target:
            if not re.search(r"#\[[\w:]*test\b", attributes):
                break  # An anchor on a production function: not a test binding.
            if not owned:
                return AnchorIssue("anchor_test_without_assert", f"{where} {function.name}")
            last = owned[-1]
            return test_id, last.line, last.end_line
        for item in owned:
            if item.line == anchor.target:
                return test_id, item.line, item.end_line
    if integration:
        return AnchorIssue("anchor_target_unresolved", f"{where} precedes no test or assertion")
    return None


def _rust_module(path: str) -> list[str]:
    """Module path of a crate source file; integration test files are crate roots."""
    parts = list(PurePosixPath(path).with_suffix("").parts)
    for root_dir in ("src", "tests"):
        if root_dir in parts:
            index = len(parts) - 1 - parts[::-1].index(root_dir)
            module = parts[index + 1 :]
            if root_dir == "tests":
                return []
            if module in (["lib"], ["main"]):
                return []
            return module[:-1] if module and module[-1] == "mod" else module
    return parts[-1:]
