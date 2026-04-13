"""Tests for validator.git_ops — git CLI operations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True
    )
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# spec")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


class TestGitBranch:
    def test_creates_branch(self, git_repo: Path) -> None:
        import os

        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(
                app, ["git", "branch", "feature/test-branch"], catch_exceptions=False
            )
            assert result.exit_code == 0
            check = subprocess.run(
                ["git", "branch", "--show-current"], cwd=git_repo, capture_output=True, text=True
            )
            assert check.stdout.strip() == "feature/test-branch"
        finally:
            os.chdir(original)

    def test_already_exists_exits_1(self, git_repo: Path) -> None:
        import os

        original = os.getcwd()
        os.chdir(git_repo)
        try:
            runner.invoke(app, ["git", "branch", "feature/dup"])
            result = runner.invoke(app, ["git", "branch", "feature/dup"])
            assert result.exit_code == 1
        finally:
            os.chdir(original)


class TestGitStage:
    def test_stages_feature_files(self, git_repo: Path) -> None:
        import os

        (git_repo / ".specs" / "features" / "001-test" / "plan.md").write_text("# plan")
        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(
                app, ["git", "stage", "--feature", "001-test"], catch_exceptions=False
            )
            assert result.exit_code == 0
            assert "files staged" in result.output
        finally:
            os.chdir(original)


class TestGitMerge:
    def test_conflict_always_exits_2(self, git_repo: Path) -> None:
        """Exit 2 even when git merge --abort also fails."""
        import os

        original = os.getcwd()
        os.chdir(git_repo)
        try:
            with patch("subprocess.run") as mock_run:
                # merge fails with CONFLICT
                conflict_result = MagicMock()
                conflict_result.returncode = 1
                conflict_result.stdout = "CONFLICT (content): Merge conflict in file.txt"
                conflict_result.stderr = ""
                # abort also fails
                abort_result = MagicMock()
                abort_result.returncode = 1
                abort_result.stderr = "fatal: There is no merge to abort."
                mock_run.side_effect = [conflict_result, abort_result]
                result = runner.invoke(app, ["git", "merge", "some-branch"])
                assert result.exit_code == 2  # Always 2, even when abort fails
        finally:
            os.chdir(original)


class TestGitDelete:
    def test_not_merged_exits_2(self, git_repo: Path) -> None:
        import os

        original = os.getcwd()
        os.chdir(git_repo)
        try:
            # Create an unmerged branch
            subprocess.run(
                ["git", "checkout", "-b", "unmerged-branch"], cwd=git_repo, capture_output=True
            )
            (git_repo / ".specs" / "features" / "001-test" / "new.md").write_text("new")
            subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
            subprocess.run(["git", "commit", "-m", "unmerged"], cwd=git_repo, capture_output=True)
            subprocess.run(["git", "checkout", "-"], cwd=git_repo, capture_output=True)
            result = runner.invoke(app, ["git", "delete", "unmerged-branch"])
            assert result.exit_code == 2  # "not fully merged" → exit 2
        finally:
            os.chdir(original)


class TestGitStatus:
    def test_outputs_valid_json(self, git_repo: Path) -> None:
        import os

        original = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(app, ["git", "status"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "branch" in data
            assert "staged" in data
            assert "ahead" in data
            assert "behind" in data
        finally:
            os.chdir(original)
