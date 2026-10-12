"""Unit-suite imports resolve from declared dependencies.

A fresh environment built from ``uv sync --extra dev`` must run the unit suite
without relying on packages that only arrive transitively through another
extra (``click`` via the integration SDK, ``jsonschema`` likewise).
"""

# @spec FR-003: Declared unit-test deps
# — .specs/features/079-validator-ci-prerequisites/spec.md#fr-003

from __future__ import annotations

import ast
import re
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LOCAL = {"validator", "tests", "conftest", "helpers"}


def _declared(*extras: str) -> set[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements = [*project["dependencies"]]
    for extra in extras:
        requirements.extend(project["optional-dependencies"][extra])
    return {_normalize(re.split(r"[<>=!~\[; ]", item, maxsplit=1)[0]) for item in requirements}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _optional_imports(tree: ast.Module) -> set[int]:
    """Imports guarded by ``except ImportError`` are explicit optional boundaries."""
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(
            isinstance(handler.type, ast.Name)
            and handler.type.id in {"ImportError", "ModuleNotFoundError"}
            for handler in node.handlers
        ):
            guarded.update(id(child) for stmt in node.body for child in ast.walk(stmt))
    return guarded


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    optional = _optional_imports(tree)
    names: set[str] = set()
    for node in ast.walk(tree):
        if id(node) in optional:
            continue
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "importorskip"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            # importorskip would otherwise hide a missing dev dependency as a skip.
            names.add(node.args[0].value.split(".")[0])
    return names


def _local_modules() -> set[str]:
    tests = ROOT / "tests"
    return (
        _LOCAL
        | {path.stem for path in tests.rglob("*.py")}
        | {path.name for path in tests.rglob("*") if path.is_dir()}
    )


def test_unit_suite_third_party_imports_are_declared_for_dev_installs() -> None:
    declared = _declared("dev")
    distributions = packages_distributions()
    local = _local_modules()
    undeclared: dict[str, set[str]] = {}
    for path in sorted((ROOT / "tests").rglob("*.py")):
        relative = path.relative_to(ROOT)
        if relative.parts[1] in {"integration", "fixtures"}:
            continue
        for module in _imported_modules(path):
            if module in sys.stdlib_module_names or module in local or module == "__future__":
                continue
            providers = {_normalize(dist) for dist in distributions.get(module, [module])}
            if not providers & declared:
                undeclared.setdefault(module, set()).add(relative.as_posix())

    assert not undeclared, f"Unit-test imports missing from runtime/dev dependencies: {undeclared}"
