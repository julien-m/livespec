"""Feature 083 boundary and documentation tests (AC-012, AC-018, SC-001, SC-002, SC-004)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.runtime_support import (
    PYTHON,
    WORKTREE,
    git,
    install,
    link_into,
    make_project,
    make_source,
    restore_write_bits,
    run_shim,
    tree_hashes,
    write,
)
from validator.runtime.home import RuntimeHome
from validator.runtime.project import pin_project

BOUNDARY = WORKTREE / "system/tool-project-boundary.md"
REFERENCING_FILES = (
    "system/spec-system.md",
    ".specs/spec-system.md",
    ".agent-sync/skills/spec-feature/SKILL.md",
    ".agent-sync/skills/spec-fix/SKILL.md",
    ".agent-sync/skills/spec-implement/SKILL.md",
    ".agent-sync/skills/spec-ship/SKILL.md",
)
LIFECYCLE_SKILLS = ("spec-feature", "spec-fix", "spec-implement", "spec-ship")
# Markdown link whose target ends with tool-project-boundary.md, e.g. "](../system/x.md)".
_LINK_RE = re.compile(r"\]\(([^)]*tool-project-boundary\.md)\)")
# Documented migration block between HTML markers, without its ```bash fence.
_BLOCK_RE = re.compile(
    r"<!-- runtime-migration:start -->\n```bash\n(.*?)```\n<!-- runtime-migration:end -->", re.S
)
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Docs Test",
    "GIT_AUTHOR_EMAIL": "docs@example.invalid",
    "GIT_COMMITTER_NAME": "Docs Test",
    "GIT_COMMITTER_EMAIL": "docs@example.invalid",
}


def _isolated_environment(base: Path) -> dict[str, str]:
    """Environment rooted under ``base``: HOME, TMPDIR and git config never reach real ones."""
    for directory in ("user-home", "tmpdir"):
        (base / directory).mkdir(parents=True, exist_ok=True)
    write(base / "gitconfig", "")
    return {
        "HOME": str(base / "user-home"),
        "TMPDIR": str(base / "tmpdir"),
        "GIT_CONFIG_GLOBAL": str(base / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        # Bytecode caches would otherwise land in the protected fixture checkout.
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(base / "pycache"),
    }


def _working_tree_hashes(root: Path) -> dict[str, str]:
    """Full content hash of a fixture tree, git internals excluded."""
    return tree_hashes(root, excluded_prefixes=(".git/",))


def _reference_lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if "tool-project-boundary.md" in line]


def _migration_block(path: Path) -> str:
    match = _BLOCK_RE.search(path.read_text())
    assert match is not None, path
    return match.group(1)


def test_boundary_rule_states_the_four_rules() -> None:
    """AC-012: never touch a LiveSpec root, report + block, no repo lifecycle, resume on upgrade."""
    text = BOUNDARY.read_text()
    for phrase in (
        "every lock mode",
        "inside any LiveSpec root, whether snapshot or checkout",
        "livespec runtime defect",
        "`Blocked`",
        "never depends on a LiveSpec repository lifecycle",
        "ships in LiveSpec separately",
        "livespec runtime upgrade --to <fixed runtime>",
    ):
        assert phrase in text, phrase


def _entry_point_facts(relative: str) -> tuple[int, bool, bool]:
    """Return (reference line count, link resolves to the boundary, names .livespec-path)."""
    path = WORKTREE / relative
    lines = _reference_lines(path)
    match = _LINK_RE.search(lines[0]) if lines else None
    target = (path.resolve().parent / match.group(1)).resolve() if match else None
    resolves = target == BOUNDARY.resolve()
    names_path = bool(lines) and ".specs/.livespec-path" in lines[0]
    return len(lines), resolves, names_path


def test_each_entry_point_references_the_boundary_once() -> None:
    """AC-012: each of the six files has one relative line that resolves and names the path."""
    facts = {relative: _entry_point_facts(relative) for relative in REFERENCING_FILES}
    assert facts == {relative: (1, True, True) for relative in REFERENCING_FILES}


@pytest.fixture(scope="module")
def pinned_consumer(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Path, Path]]:
    """Pin a consumer whose lifecycle skill links point into a real-code snapshot."""
    base = tmp_path_factory.mktemp("boundary").resolve()
    with pytest.MonkeyPatch.context() as patch:
        for key, value in _isolated_environment(base).items():
            patch.setenv(key, value)
        patch.delenv("LIVESPEC_HOME", raising=False)
        checkout = make_source(base / "checkout", real_code=True)
        home = RuntimeHome(base / "home")
        runtime_id = install(home, checkout).runtime_id
        project = make_project(base / "consumer")
        for skill in LIFECYCLE_SKILLS:
            link_into(project, f"skills/{skill}", checkout / ".agent-sync/skills" / skill)
        pin_project(project, runtime_id, home)
        yield project, home.snapshot(runtime_id)
    restore_write_bits(base)


def _linked_reference_target(project: Path, skill: str) -> tuple[bool, Path | None]:
    """Resolve a linked SKILL.md reference from the SKILL.md physical location."""
    physical = (project / ".agent-sync.local/skills" / skill / "SKILL.md").resolve()
    lines = _reference_lines(physical)
    match = _LINK_RE.search(lines[0]) if lines else None
    target = (physical.parent / match.group(1)).resolve() if match else None
    return physical.is_file(), target


def test_linked_skill_references_resolve_inside_snapshot(
    pinned_consumer: tuple[Path, Path],
) -> None:
    """AC-012: from a pinned consumer each lifecycle skill reference reaches the snapshot file."""
    project, snapshot = pinned_consumer
    boundary = snapshot / "system/tool-project-boundary.md"
    targets = {skill: _linked_reference_target(project, skill) for skill in LIFECYCLE_SKILLS}
    assert targets == {skill: (True, boundary) for skill in LIFECYCLE_SKILLS} and boundary.is_file()


def test_docs_cover_every_runtime_command() -> None:
    """AC-018: six commands, PATH ordering, fresh machine and one identical migration block."""
    readme = (WORKTREE / "README.md").read_text()
    installation = readme.split("## Installation", 1)[1].split("\n## ", 1)[0]
    reference = (WORKTREE / "docs/cli-reference.md").read_text()
    for text in (installation, reference):
        for command in ("install", "pin", "upgrade", "dev", "status", "defect"):
            assert f"livespec runtime {command}" in text, command
        assert "$HOME/.livespec/bin:$PATH" in text and "/opt/homebrew/bin/livespec" in text
        assert "link-local.sh" in text and "--runtime <" in text
    assert _migration_block(WORKTREE / "README.md") == _migration_block(
        WORKTREE / "docs/cli-reference.md"
    )


def _handy_fixture(user_home: Path) -> tuple[Path, Path]:
    origin = make_source(user_home.parent / "origin", real_code=True)
    checkout = user_home / "projects/livespec"
    checkout.parent.mkdir(parents=True)
    git(user_home, "clone", "-q", str(origin), str(checkout))
    handy = make_project(user_home / "projects/handy")
    write(handy / ".gitignore", ".specs/.livespec-path\n.agent-sync.local/\n")
    write(handy / ".specs/.livespec-path", f"{checkout}\n")
    for skill in ("spec-check", "spec-implement", "spec-feature"):
        link_into(handy, f"skills/{skill}", checkout / ".agent-sync/skills" / skill)
    link_into(handy, "rules/commands.md", checkout / ".agent-sync/rules/livespec/commands.md")
    git(handy, "init", "-q", "-b", "main")
    git(handy, "add", "-A")
    git(handy, "commit", "-q", "-m", "handy")
    return checkout, handy


def _checkout_venv(checkout: Path) -> None:
    """Stand in for the checkout's ``uv sync`` venv: ``.venv/bin/python`` runs this venv.

    An ``exec`` wrapper, not a symlink: a symlinked interpreter outside its venv directory
    loses the venv's site-packages (typer, pydantic) and would hide a broken command.
    """
    python = checkout / ".venv/bin/python"
    write(python, f'#!/bin/sh\nexec "{PYTHON}" "$@"\n')
    python.chmod(0o755)


def _git_only_bin(base: Path) -> Path:
    """A PATH directory exposing the caller's git and nothing else."""
    git_path = shutil.which("git")
    assert git_path is not None, "git is required by the documented migration"
    write(base / "git-only-bin/git", f'#!/bin/sh\nexec "{git_path}" "$@"\n', mode=0o755)
    return base / "git-only-bin"


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def _written_paths(home: RuntimeHome, handy: Path) -> list[Path]:
    """Every location the migration selected: shim, current, .livespec-path and links."""
    recorded = Path((handy / ".specs/.livespec-path").read_text().strip())
    links = [link for link in (handy / ".agent-sync.local").rglob("*") if link.is_symlink()]
    return [home.shim, home.current.resolve(), recorded, *(link.resolve() for link in links)]


def test_documented_migration_runs_on_consumer_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-018/SC-002/SC-004: documented commands end pinned and clean, all writes in the fixture."""
    isolated = _isolated_environment(tmp_path)
    for key, value in isolated.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("LIVESPEC_HOME", raising=False)
    user_home = Path(isolated["HOME"]).resolve()
    checkout, handy = _handy_fixture(user_home)
    _checkout_venv(checkout)
    protected = (user_home.parent / "origin", checkout)
    before = [_working_tree_hashes(root) for root in protected]
    # Run as a user with no activated venv and no interpreter that happens to carry
    # LiveSpec's dependencies: only git (via a wrapper) and the base system directories.
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"LIVESPEC_HOME", "VIRTUAL_ENV"}
    }
    env.update(_GIT_IDENTITY, PATH=f"{_git_only_bin(tmp_path)}:/usr/bin:/bin")
    script = write(tmp_path / "migration.sh", _migration_block(WORKTREE / "docs/cli-reference.md"))
    try:
        completed = subprocess.run(
            ["bash", "-euo", "pipefail", str(script)],
            cwd=user_home,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert str(user_home / ".livespec/bin/livespec") in completed.stdout.splitlines()
        home = RuntimeHome(user_home / ".livespec")
        status = run_shim(home, handy, "runtime", "status", "--json", env=env)
        payload = json.loads(status.stdout)
        assert status.returncode == 0 and payload["mode"] == "pinned"
        assert [item for item in payload["findings"] if item["severity"] != "INFO"] == []
        assert git(handy, "ls-files", ".specs/livespec.lock").strip() == ".specs/livespec.lock"
        assert [path for path in _written_paths(home, handy) if not _inside(path, tmp_path)] == []
        assert [_working_tree_hashes(root) for root in protected] == before
    finally:
        restore_write_bits(tmp_path)
