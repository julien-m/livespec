"""Root-created features retain complete scope and Git state (096 AC-001 through AC-006)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from tests.delivery_support import FEATURE, DeliveryProject, git, spec_text
from tests.test_delivery_review_base import _prepare, _record, _verify

pytestmark = pytest.mark.integration


@pytest.fixture(params=["feature-only", "bootstrap", "code"])
def root_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> DeliveryProject:
    """Create a real root commit with the spec and optional mixed bootstrap content."""
    project = DeliveryProject(tmp_path / "project")
    project.write(f".specs/features/{FEATURE}/spec.md", spec_text())
    project.write(f".specs/features/{FEATURE}/progress.md", "# Progress\n")
    project.write(
        f".specs/features/{FEATURE}/plan.md",
        "# Plan\n\n- **Status:** Draft\n\nKeep the calculation.\n",
    )
    if request.param != "feature-only":
        project.write(".specs/README.md", "# Registry\n")
        project.write("README.md", "# Bootstrap\n")
        project.write(".specs/constitution.md", "# Constitution\n")
        for number in range(2, 9):
            project.write(f".specs/features/{number:03}-future/spec.md", "# Draft\n")
    if request.param == "code":
        project.write("bootstrap.py", "answer = 42\n")
        project.write("removed.py", "original = True\n")
    git(project.root, "init", "-q")
    git(project.root, "config", "user.email", "t@example.invalid")
    git(project.root, "config", "user.name", "t")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "bootstrap with draft specs")
    monkeypatch.chdir(project.root)
    project.write(".specs/constitution.md", "# Constitution\n")
    project.write(".specs/project.md", "# Project\n")
    project.write(".specs/stacks/_default.md", "# Stack\n")
    project.review_spec()
    project.write("calc.py", "def add(a, b):\n    return a + b\n")
    return project


# @spec AC-001: Preserve root SHA — .specs/features/096-root-feature-delivery-review/spec.md#ac-001
# @spec AC-002: Complete root tree — .specs/features/096-root-feature-delivery-review/spec.md#ac-002
def test_root_baseline_covers_bootstrap_and_preserves_identity(
    root_project: DeliveryProject,
) -> None:
    project = root_project
    root_commit = git(project.root, "rev-parse", "HEAD").strip()
    original_paths = git(project.root, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    if (project.root / "removed.py").exists():
        git(project.root, "rm", "removed.py")
    index_before = git(project.root, "ls-files", "--stage")
    code, scope = _prepare(project, root_commit)
    assert code == 0, scope
    files = cast(dict[str, str], scope["files"])
    assert set(files) == (
        set(original_paths)
        | {"calc.py", ".specs/constitution.md", ".specs/project.md", ".specs/stacks/_default.md"}
    ) - {f".specs/features/{FEATURE}/progress.md", ".specs/README.md"}
    assert scope["base_commit"] == root_commit
    assert files["calc.py"] == hashlib.sha256((project.root / "calc.py").read_bytes()).hexdigest()
    assert files[f".specs/features/{FEATURE}/spec.md"].startswith("normative:")
    if "removed.py" in original_paths:
        assert files["removed.py"] == "deleted"
    assert git(project.root, "ls-files", "--stage") == index_before
    assert _record(project, "review", sorted(files), "reviewer") == []
    assert _record(project, "audit", sorted(files), "auditor") == []
    assert _verify(project) == []
    project.write(f".specs/features/{FEATURE}/plan.md", "changed bootstrap content\n")
    assert "scope_changed" in _verify(project)
    assert "scope_changed" in _record(project, "review", sorted(files), "reviewer")


# @spec AC-004: Reject newer bases — .specs/features/096-root-feature-delivery-review/spec.md#ac-004
def test_root_feature_rejects_newer_base(root_project: DeliveryProject) -> None:
    project = root_project
    root_commit = git(project.root, "rev-parse", "HEAD").strip()
    git(project.root, "add", "calc.py")
    git(project.root, "commit", "-qm", "implement")
    assert _prepare(project, root_commit)[0] == 0
    code, scope = _prepare(project, "HEAD")
    assert (code, scope["error"]) == (1, "base_not_feature_start")


def test_root_newer_base_cannot_be_forged_into_scope_or_receipt(
    root_project: DeliveryProject,
) -> None:
    project = root_project
    root_commit = git(project.root, "rev-parse", "HEAD").strip()
    git(project.root, "add", "calc.py")
    git(project.root, "commit", "-qm", "implement")
    assert _prepare(project, root_commit)[0] == 0
    path = project.feature_dir / ".reviews" / "delivery-scope.json"
    original = path.read_text()
    scope = json.loads(original)
    files = sorted(scope["files"])
    scope["base_commit"] = git(project.root, "rev-parse", "HEAD").strip()
    path.write_text(json.dumps(scope))
    assert _record(project, "review", files, "reviewer") == ["base_not_feature_start"]
    path.write_text(original)
    assert _record(project, "review", files, "reviewer") == []
    assert _record(project, "audit", files, "auditor") == []
    path = project.feature_dir / ".reviews" / "delivery.json"
    receipt = json.loads(path.read_text())
    receipt["kinds"]["audit"]["rounds"][-1]["base_commit"] = scope["base_commit"]
    path.write_text(json.dumps(receipt))
    assert _verify(project) == ["base_not_feature_start"]
    unrelated = git(project.root, "commit-tree", "HEAD^{tree}", "-m", "unrelated root").strip()
    code, refused = _prepare(project, unrelated)
    assert (code, refused["error"]) == (1, "base_not_feature_start")
    scope["base_commit"] = unrelated
    (project.feature_dir / ".reviews" / "delivery-scope.json").write_text(json.dumps(scope))
    assert _record(project, "review", files, "reviewer") == ["base_not_feature_start"]
    receipt["kinds"]["audit"]["rounds"][-1]["base_commit"] = unrelated
    path.write_text(json.dumps(receipt))
    assert _verify(project) == ["base_not_feature_start"]


def _git_state(project: DeliveryProject) -> tuple[str, bytes, str, str]:
    """Snapshot objects, raw index and complete reachable commit/ref identities."""
    return (
        git(project.root, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)"),
        (project.root / ".git" / "index").read_bytes(),
        git(project.root, "rev-parse", "HEAD"),
        git(project.root, "show-ref") + git(project.root, "rev-list", "--all", "--parents"),
    )


# @spec AC-006: Preserve Git state — .specs/features/096-root-feature-delivery-review/spec.md#ac-006
@pytest.mark.parametrize("root_project", ["code"], indirect=True)
def test_root_cycle_preserves_git_and_covers_bootstrap(root_project: DeliveryProject) -> None:
    project = root_project
    root_commit = git(project.root, "rev-parse", "HEAD").strip()
    (project.root / "link.py").symlink_to("bootstrap.py")
    git(project.root, "update-index", "--add", "--cacheinfo", f"160000,{root_commit},sub")
    (project.root / "sub").mkdir()
    before = _git_state(project)
    code, scope = _prepare(project, root_commit)
    assert code == 0, scope
    files = cast(dict[str, str], scope["files"])
    assert files["link.py"] == "symlink:bootstrap.py"
    assert files["sub"] == f"gitlink:{root_commit}"
    assert _record(project, "review", sorted(files), "reviewer") == []
    assert _record(project, "audit", sorted(files), "auditor") == []
    assert _verify(project) == []
    assert _git_state(project) == before


# @spec AC-005: Coverage — .specs/features/096-root-feature-delivery-review/spec.md#ac-005
@pytest.mark.parametrize("root_project", ["code"], indirect=True)
def test_root_report_cannot_omit_bootstrap(root_project: DeliveryProject) -> None:
    project = root_project
    code, scope = _prepare(project, "HEAD")
    assert code == 0, scope
    files = cast(dict[str, str], scope["files"])
    assert "bootstrap.py" in files
    assert _record(project, "review", sorted(set(files) - {"bootstrap.py"}), "reviewer") == [
        "scope_not_covered"
    ]


# @spec AC-003: Currency — .specs/features/096-root-feature-delivery-review/spec.md#ac-003
@pytest.mark.parametrize("root_project", ["code"], indirect=True)
def test_root_lifecycle_stability_and_normative_currency(root_project: DeliveryProject) -> None:
    project = root_project
    code, scope = _prepare(project, "HEAD")
    assert code == 0, scope
    files = sorted(cast(dict[str, str], scope["files"]))
    assert _record(project, "review", files, "reviewer") == []
    assert _record(project, "audit", files, "auditor") == []
    for name in ("spec.md", "plan.md"):
        path = project.feature_dir / name
        path.write_text(
            path.read_text()
            .replace("**Status:** Planned", "**Status:** In Progress")
            .replace("**Status:** Draft", "**Status:** In Progress")
        )
    assert _verify(project) == []
    assert _record(project, "review", files, "reviewer") == []
    for relative in (
        "calc.py",
        f".specs/features/{FEATURE}/spec.md",
        f".specs/features/{FEATURE}/plan.md",
    ):
        path = project.root / relative
        original = path.read_bytes()
        path.write_bytes(original + b"\nChanged normative content.\n")
        assert "scope_changed" in _verify(project)
        assert "scope_changed" in _record(project, "review", files, "reviewer")
        path.write_bytes(original)

    added = project.root / "new_scope.py"
    added.write_text("new = True\n")
    assert "scope_changed" in _verify(project)
    assert "scope_changed" in _record(project, "review", files, "reviewer")
    added.unlink()
    deleted = project.root / "bootstrap.py"
    deleted.unlink()
    assert "scope_changed" in _verify(project)
    assert "scope_changed" in _record(project, "review", files, "reviewer")
