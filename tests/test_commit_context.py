"""Tests for validator.commit_context — commit context bridge CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app

runner = CliRunner()


@pytest.fixture()
def specs_root(tmp_path: Path) -> Path:
    specs = tmp_path / ".specs"
    specs.mkdir()
    feature_dir = specs / "features" / "001-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# spec")
    (feature_dir / "plan.md").write_text("# plan")
    return specs


class TestCommitContextWrite:
    def test_creates_file_schema_v1(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            context_path = specs_root / "hooks" / ".commit-context.json"
            assert context_path.exists()
            data = json.loads(context_path.read_text())
            assert data["version"] == 1
            assert "spec.md" in data["spec_path"]
            assert "plan.md" in data["plan_path"]
            assert isinstance(data["adr_paths"], str)
        finally:
            os.chdir(original)

    def test_overwrites_stale(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir(exist_ok=True)
        (specs_root / "hooks" / ".commit-context.json").write_text('{"old": "data"}')
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert "version" in data  # New schema, not old data
        finally:
            os.chdir(original)

    def test_creates_hooks_dir_when_missing(self, specs_root: Path) -> None:
        """write must succeed even when .specs/hooks/ doesn't exist yet."""
        import os
        assert not (specs_root / "hooks").exists()
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            assert (specs_root / "hooks" / ".commit-context.json").exists()
        finally:
            os.chdir(original)

    def test_adr_paths_empty_when_no_adrs(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert data["adr_paths"] == ""
        finally:
            os.chdir(original)

    def test_adr_paths_populated_when_adrs_exist(self, specs_root: Path) -> None:
        import os
        adr_dir = specs_root / "stacks" / "decisions"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-001-auth.md").write_text("# ADR-001")
        (adr_dir / "ADR-002-db.md").write_text("# ADR-002")
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "write", "--feature", "001-test"], catch_exceptions=False)
            assert result.exit_code == 0
            data = json.loads((specs_root / "hooks" / ".commit-context.json").read_text())
            assert "ADR-001-auth.md" in data["adr_paths"]
            assert "ADR-002-db.md" in data["adr_paths"]
        finally:
            os.chdir(original)


class TestCommitContextRead:
    def test_prints_json(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir()
        ctx = {"version": 1, "feature_name": "001-test", "spec_path": "/x/spec.md", "plan_path": "/x/plan.md", "adr_paths": ""}
        (specs_root / "hooks" / ".commit-context.json").write_text(json.dumps(ctx))
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "read"], catch_exceptions=False)
            assert result.exit_code == 0
            assert json.loads(result.output)["feature_name"] == "001-test"
        finally:
            os.chdir(original)

    def test_exits_1_when_missing(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "read"])
            assert result.exit_code == 1
        finally:
            os.chdir(original)


class TestCommitContextClear:
    def test_removes_file(self, specs_root: Path) -> None:
        import os
        (specs_root / "hooks").mkdir()
        ctx_path = specs_root / "hooks" / ".commit-context.json"
        ctx_path.write_text('{"version": 1}')
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "clear"], catch_exceptions=False)
            assert result.exit_code == 0
            assert not ctx_path.exists()
        finally:
            os.chdir(original)

    def test_idempotent(self, specs_root: Path) -> None:
        import os
        original = os.getcwd()
        os.chdir(specs_root.parent)
        try:
            result = runner.invoke(app, ["commit-context", "clear"], catch_exceptions=False)
            assert result.exit_code == 0  # No error when file is already absent
        finally:
            os.chdir(original)
