# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Copy the exact production workflow outside a generated candidate before evaluation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from tests.integration.helpers.witness_generation import TrialResult
    from tests.integration.helpers.witness_process import ProcessCapture

DIRECTORIES = (
    "validator",
    ".agent-sync",
    "system",
    "livespec",
    "migrations",
    "scripts",
    "templates",
    "stacks",
    "hooks",
    "tests/fixtures/conventions_ast",
)


def snapshot_workflow(source: Path, destination: Path) -> dict[str, str]:
    """Freeze current code/skills/config, refusing a concurrent source change while copying."""
    before = workflow_identity(source)
    for name in DIRECTORIES:
        path = source / name
        if path.is_dir():
            shutil.copytree(path, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("VERSION", "pyproject.toml", ".specs/spec-system.md", *_catalog_inputs(source)):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, path)
    if before != workflow_identity(source) or before != workflow_identity(destination):
        raise ValueError("production_workflow_changed_during_snapshot")
    return before


def workflow_identity(root: Path) -> dict[str, str]:
    """Hash copied workflow sources including additions and deletions."""
    files = [
        root / name
        for name in ("VERSION", "pyproject.toml", ".specs/spec-system.md", *_catalog_inputs(root))
    ]
    for directory in DIRECTORIES:
        files.extend(
            path
            for path in (root / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
    }


def _catalog_inputs(root: Path) -> list[str]:
    """Bind every bundled catalog's fixture and deterministic test dependencies."""
    inputs: set[str] = set()
    catalogs = root / "validator/conventions_ast/rule_catalog"
    for catalog in sorted(catalogs.glob("*.yaml")):
        data = yaml.safe_load(catalog.read_text())
        for rule in data["rules"]:
            inputs.update(rule["fixtures"].values())
            for evidence in rule["deterministic_test_evidence"]:
                inputs.update(evidence[key] for key in ("test", "pass_fixture", "fail_fixture"))
    for name in inputs:
        path = root / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink():
            raise ValueError(f"unsafe_workflow_catalog_input:{name}")
        path.resolve().relative_to(root.resolve())
        if not path.is_file():
            raise ValueError(f"missing_workflow_catalog_input:{name}")
    return sorted(inputs)


def snapshot_environment(snapshot: Path) -> dict[str, str]:
    """Route every livespec invocation to frozen code, retaining the runtime's normal auth."""
    bin_dir = snapshot / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "livespec"
    executable.write_text(
        f"#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(snapshot)!r})\n"
        "from validator.cli import app\napp()\n"
    )
    executable.chmod(0o755)
    return {
        **os.environ,
        "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONPATH": str(snapshot),
    }


def candidate_policy_identity(candidate: Path) -> dict[str, str]:
    """Bind the actual copied skill/tool policies the native agent reads."""
    files = [candidate / name for name in ("AGENTS.md", "contract.md", ".specs/spec-system.md")]
    for directory in (".agents/skills", ".agent-sync/skills", "system"):
        files.extend(path for path in (candidate / directory).rglob("*") if path.is_file())
    return {str(path.relative_to(candidate)): _policy_digest(path) for path in sorted(files)}


def _policy_digest(path: Path) -> str:
    if path.is_symlink():
        return "invalid_symlink"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "missing_or_unreadable"


def candidate_identity(candidate: Path) -> dict[str, str]:
    """Bind exact candidate bytes evaluated, including file additions/deletions."""
    return {
        str(path.relative_to(candidate)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(candidate.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def capture_candidate_sources(candidate: Path) -> dict[str, str]:
    """Retain the actual evaluated entrypoints, so a later oracle can recheck identical bytes."""
    return {
        name: (candidate / name).read_text()
        for name in ("purge.py", "app.ts", "index.html")
        if (candidate / name).is_file()
        and not (candidate / name).is_symlink()
        and (candidate / name).stat().st_size <= 1_000_000
    }


def _observed_metadata(result: TrialResult, capture: ProcessCapture) -> None:
    for line in capture.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        model = event.get("model")
        if isinstance(model, str):
            result.model = model
        model_usage = event.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            result.model = ",".join(sorted(str(name) for name in model_usage))
        cost = event.get("total_cost_usd")
        if isinstance(cost, (float, int)) and not isinstance(cost, bool) and cost >= 0:
            result.measured_cost_usd = (result.measured_cost_usd or 0) + cost
