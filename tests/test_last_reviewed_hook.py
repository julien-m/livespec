"""Integration tests for the pre-commit `last_reviewed` hook.

# @spec FR-009, AC-008 — .specs/features/039-command-expectations-and-verify-output/spec.md
# @spec EC-001 — whitespace-only edits still trigger the hook.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[1]
    / "hooks"
    / "livespec-last-reviewed.py"
)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    # Git is the contract under test here; capture_output/check let the test
    # assert hook and repository behavior without mutating global process state.
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "test")
    _git(repo, "commit", "--allow-empty", "-m", "init", "-q")


def _run_hook(repo: Path) -> subprocess.CompletedProcess[str]:
    # The hook is executed as a subprocess so tests can assert its real exit code
    # and stderr contract exactly as pre-commit would observe them.
    return subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def _make_expectations(repo: Path, name: str, last_reviewed: str) -> None:
    if not name.startswith("spec-"):
        name = f"spec-{name}"
    (repo / ".agent-sync" / "skills" / name).mkdir(parents=True, exist_ok=True)
    (repo / f".agent-sync/skills/{name}/expectations.md").write_text(
        (
            f"---\ncommand: {name}\ncontract_version: \"1.0\"\n"
            f"last_reviewed: {last_reviewed}\n---\n\n# x\n"
        ),
        encoding="utf-8",
    )


def test_pre_commit_hook_allows_fresh_last_reviewed(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".agent-sync" / "skills" / "spec-plan").mkdir(parents=True)
    (repo / ".agent-sync/skills/spec-plan/SKILL.md").write_text("hello", encoding="utf-8")
    _make_expectations(repo, "plan", date.today().isoformat())
    _git(
        repo,
        "add",
        ".agent-sync/skills/spec-plan/SKILL.md",
        ".agent-sync/skills/spec-plan/expectations.md",
    )

    result = _run_hook(repo)
    assert result.returncode == 0, result.stderr


def test_pre_commit_hook_blocks_stale_last_reviewed(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".agent-sync" / "skills" / "spec-plan").mkdir(parents=True)
    (repo / ".agent-sync/skills/spec-plan/SKILL.md").write_text("hello", encoding="utf-8")
    _make_expectations(repo, "plan", "2020-01-01")
    _git(
        repo,
        "add",
        ".agent-sync/skills/spec-plan/SKILL.md",
        ".agent-sync/skills/spec-plan/expectations.md",
    )

    result = _run_hook(repo)
    assert result.returncode != 0
    assert "Relis `.agent-sync/skills/spec-plan/expectations.md`" in result.stderr
    assert "bump `last_reviewed`" in result.stderr
    assert "recommit." in result.stderr


def test_pre_commit_hook_blocks_when_expectations_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".agent-sync" / "skills" / "spec-newcmd").mkdir(parents=True)
    (repo / ".agent-sync/skills/spec-newcmd/SKILL.md").write_text("hello", encoding="utf-8")
    _git(repo, "add", ".agent-sync/skills/spec-newcmd/SKILL.md")

    result = _run_hook(repo)
    assert result.returncode != 0
    assert ".agent-sync/skills/spec-newcmd/expectations.md is missing" in result.stderr


def test_pre_commit_hook_ignores_unrelated_changes(tmp_path: Path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "src").mkdir()
    (repo / "src/foo.py").write_text("x = 1", encoding="utf-8")
    _git(repo, "add", "src/foo.py")

    result = _run_hook(repo)
    assert result.returncode == 0


def test_pre_commit_hook_ignores_expectations_md_changes_only(tmp_path: Path):
    """Editing expectations.md itself does not require bumping anything."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _make_expectations(repo, "plan", "2020-01-01")
    _git(repo, "add", ".agent-sync/skills/spec-plan/expectations.md")
    result = _run_hook(repo)
    assert result.returncode == 0


def test_pre_commit_hook_whitespace_change_still_blocks(tmp_path: Path):
    """EC-001: whitespace-only edit still triggers the hook."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".agent-sync" / "skills" / "spec-plan").mkdir(parents=True)
    (repo / ".agent-sync/skills/spec-plan/SKILL.md").write_text("hi", encoding="utf-8")
    _make_expectations(repo, "plan", date.today().isoformat())
    _git(
        repo,
        "add",
        ".agent-sync/skills/spec-plan/SKILL.md",
        ".agent-sync/skills/spec-plan/expectations.md",
    )
    _git(repo, "commit", "-q", "-m", "first", check=False)

    # Now modify only whitespace and roll the expectations date backwards.
    (repo / ".agent-sync/skills/spec-plan/SKILL.md").write_text("hi   \n", encoding="utf-8")
    _make_expectations(repo, "plan", "2020-01-01")
    _git(
        repo,
        "add",
        ".agent-sync/skills/spec-plan/SKILL.md",
        ".agent-sync/skills/spec-plan/expectations.md",
    )

    result = _run_hook(repo)
    assert result.returncode != 0
