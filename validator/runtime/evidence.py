"""Conventions test evidence a snapshot ships, read from the installed commit (083 FR-001).

The code running ``livespec runtime install`` may be older than the commit it installs,
so its own ``SNAPSHOT_TEST_EVIDENCE`` can miss evidence the target needs. The target
tree therefore supplies its rules too: the ``SNAPSHOT_TEST_EVIDENCE`` literal of its
``validator/runtime/models.py`` and the fixtures and tests its bundled AST catalogs cite.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import yaml

POLICY_PATH = "validator/runtime/models.py"
CATALOG_DIR = "validator/conventions_ast/rule_catalog/"
_POLICY_NAME = "SNAPSHOT_TEST_EVIDENCE"


def is_catalog(path: str) -> bool:
    """Return whether a tree path is a bundled AST rule catalog."""
    return (
        path.startswith(CATALOG_DIR)
        and path.endswith(".yaml")
        and "/" not in path[len(CATALOG_DIR) :]
    )


def declared_policy(models_source: str) -> tuple[str, ...]:
    """Return the ``SNAPSHOT_TEST_EVIDENCE`` literal of a ``models.py`` source, or ``()``.

    The source is parsed, never executed; a missing or non-literal value yields ``()``.
    """
    try:
        tree = ast.parse(models_source)
    except SyntaxError:
        return ()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == _POLICY_NAME for t in targets):
            continue
        try:
            literal: object = ast.literal_eval(value)
        except (ValueError, TypeError):
            return ()
        if not isinstance(literal, (tuple, list)):
            return ()
        # literal_eval returns untyped containers; only string entries are kept.
        items = cast(tuple[object, ...], tuple(literal))
        return tuple(item for item in items if isinstance(item, str))
    return ()


def cited_paths(catalog_text: str) -> set[str]:
    """Return the fixture and test paths one AST catalog cites (malformed parts skipped)."""
    try:
        raw = yaml.safe_load(catalog_text)
    except yaml.YAMLError:
        return set()
    rules = raw.get("rules") if isinstance(raw, dict) else None
    cited: set[str] = set()
    # PyYAML returns object-shaped data; every level is narrowed before use.
    for rule in cast(list[object], rules) if isinstance(rules, list) else []:
        if not isinstance(rule, dict):
            continue
        data = cast(dict[str, object], rule)
        fixtures = data.get("fixtures")
        if isinstance(fixtures, dict):
            values = cast(dict[str, object], fixtures)
            cited.update(v for v in (values.get("pass"), values.get("fail")) if isinstance(v, str))
        evidence = data.get("deterministic_test_evidence")
        for item in cast(list[object], evidence) if isinstance(evidence, list) else []:
            test = cast(dict[str, object], item).get("test") if isinstance(item, dict) else None
            if isinstance(test, str):
                cited.add(test)
    return cited


# @spec FR-001: Evidence rules of the installed commit
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
def target_evidence(policy_source: str | None, catalog_sources: Iterable[str]) -> tuple[str, ...]:
    """Return the evidence entries the installed commit declares or cites."""
    declared = declared_policy(policy_source) if policy_source is not None else ()
    cited = {path for text in catalog_sources for path in cited_paths(text)}
    return (*declared, *sorted(cited))


def missing_evidence(root: Path) -> list[str]:
    """Return the evidence entries the tree under ``root`` declares or cites but lacks.

    A ``SNAPSHOT_TEST_EVIDENCE`` entry ending in ``/`` must be a directory there; every
    other declared entry and every path an AST catalog cites must be a file.
    """
    policy = root / POLICY_PATH
    declared = declared_policy(policy.read_text("utf-8")) if policy.is_file() else ()
    catalog_dir = root / CATALOG_DIR
    catalogs = sorted(catalog_dir.glob("*.yaml")) if catalog_dir.is_dir() else []
    cited = {path for catalog in catalogs for path in cited_paths(catalog.read_text("utf-8"))}
    missing = {
        entry
        for entry in declared
        if not ((root / entry).is_dir() if entry.endswith("/") else (root / entry).is_file())
    }
    return sorted(missing | {path for path in cited if not (root / path).is_file()})
