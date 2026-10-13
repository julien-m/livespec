"""Migration v23 repairs projects initialized before the bootstrap self-consistency fix."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from tests.test_init_bootstrap_closure import IGNORED, bootstrap
from tests.test_init_recovery import ROOT, environment, execute, tree
from validator.migration_planner import build_migration_plan

MIGRATION = ROOT / "migrations/23/migrate.md"
LEGACY_BLOCK = """<!-- livespec:start -->
## LiveSpec

Read [the specification system](.specs/spec-system.md) before any spec command or code modification.
Use `$spec-init` (Codex) or `/spec-init` (Claude) for initialization.
<!-- livespec:end -->"""


def _rewrite(project: Path, relative: str, text: str) -> None:
    """Write legacy bytes and keep the bootstrap profile identity they had when generated."""
    (project / relative).write_text(text)
    manifest_path = project / ".specs/bootstrap-profile.json"
    manifest = json.loads(manifest_path.read_text())
    if relative in manifest["documents"]:
        manifest["documents"][relative] = hashlib.sha256(text.encode()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def legacy_project(tmp_path: Path) -> Path:
    """Reproduce the artifacts of a version 21 autonomous bootstrap."""
    project, _ = bootstrap(tmp_path)
    changelog = (project / ".specs/changelog.md").read_text()
    _rewrite(
        project,
        ".specs/changelog.md",
        changelog.replace("— [Setup]: LiveSpec initialized", "— LiveSpec initialized")
        + "\n## 2026-10-12 — Custom history kept as written\n",
    )
    preflight = (project / ".specs/preflight.md").read_text()
    preflight = re.sub(r"## Tokens\n\n[^\n]*\n\n", "", preflight)
    preflight = preflight.replace(
        "<!-- preflight:custom:start -->\n", "<!-- preflight:custom:start -->\nmy check\n"
    )
    _rewrite(project, ".specs/preflight.md", preflight)
    stack = (project / ".specs/stacks/_default.md").read_text()
    _rewrite(project, ".specs/stacks/_default.md", stack.replace("title: Default Stack\n", ""))
    for document in ("CLAUDE.md", "AGENTS.md"):
        text = (project / document).read_text()
        legacy = re.sub(
            r"<!-- livespec:start -->.*?<!-- livespec:end -->", LEGACY_BLOCK, text, flags=re.S
        )
        _rewrite(project, document, "# Team notes\n\n" + legacy)
    ignore = (project / ".gitignore").read_text().splitlines()
    kept = [line for line in ignore if line not in ("test-results/", "playwright-report/")]
    _rewrite(project, ".gitignore", "\n".join(kept) + "\n")
    for relative in (".specs/design/screens/index.md", ".specs/design/changelog.md"):
        (project / relative).unlink()
    (project / ".specs/livespec-version").write_text("21\n")
    return project


def migrate(project: Path) -> subprocess.CompletedProcess[str]:
    """Apply migration v23 through the real migration runner."""
    return subprocess.run(
        ["bash", str(ROOT / "scripts/migrate.sh"), str(MIGRATION), str(project), str(ROOT)],
        text=True,
        capture_output=True,
        timeout=60,
    )


def test_ac009_migration_repairs_legacy_bootstrap(tmp_path: Path) -> None:
    project = legacy_project(tmp_path)
    before = (project / ".specs/changelog.md").read_text()
    result = migrate(project)
    assert result.returncode == 0, result.stdout + result.stderr
    validated = subprocess.run(
        [sys.executable, "-m", "validator.cli", "validate", str(project / ".specs")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert validated.returncode == 0, validated.stdout
    changelog = (project / ".specs/changelog.md").read_text()
    assert changelog == before.replace("— LiveSpec initialized", "— [Setup]: LiveSpec initialized")
    assert (
        "<!-- preflight:custom:start -->\nmy check\n"
        in (project / ".specs/preflight.md").read_text()
    )
    assert (project / ".specs/design/screens/index.md").is_file()
    ignored = (project / ".gitignore").read_text().splitlines()
    assert [pattern for pattern in IGNORED if pattern not in ignored] == []
    for document in ("CLAUDE.md", "AGENTS.md"):
        text = (project / document).read_text()
        assert text.startswith("# Team notes\n")
        assert "Commands: `/spec-check`" in text and "Use `$spec-init`" not in text
    assert (project / ".specs/livespec-version").read_text().strip() == "23"
    again = tmp_path / "again"
    again.mkdir()
    verified = execute(project, environment(again), "--verify-only")
    assert verified.returncode == 0, verified.stderr


def test_ac009_second_run_changes_nothing_and_custom_blocks_survive(tmp_path: Path) -> None:
    project = legacy_project(tmp_path)
    custom = (
        "<!-- livespec:start -->\n## LiveSpec\n\nCommands: `/spec-x` · custom\n"
        "<!-- livespec:end -->\n"
    )
    (project / "CLAUDE.md").write_text(custom)
    assert migrate(project).returncode == 0
    assert (project / "CLAUDE.md").read_text() == custom
    snapshot = tree(project)
    second = migrate(project)
    assert second.returncode == 0, second.stderr
    assert tree(project) == snapshot


def test_ac009_version_23_applies_pending_v22_then_v23(tmp_path: Path) -> None:
    project = tmp_path / "app"
    (project / ".specs").mkdir(parents=True)
    (project / ".specs/livespec-version").write_text("21\n")
    plan = build_migration_plan(project, ROOT)
    assert plan.target_version == 23
    assert plan.apply == [22, 23]
    assert plan.skipped == []
