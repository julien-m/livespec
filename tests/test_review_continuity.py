"""Stored source roles and revision records verified at their commit (feature 094)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import pytest
from typer.testing import CliRunner

from tests.stable_review_support import FEATURE, commit_all, edit_spec, make_root, review_both
from validator.cli import app
from validator.progression_gate import ProgressionBlocked, require_progression
from validator.semantic.review_api import verify_feature_review
from validator.semantic.review_files import review_receipt_path

AC_EDIT = ("Exports older than 24 hours are absent.", "Exports older than 48 hours are absent.")
REVIEWS = Path(".specs/features") / FEATURE / ".reviews"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = make_root(tmp_path)
    monkeypatch.chdir(root)
    return root


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def _current(root: Path) -> tuple[bool, bool]:
    def check(kind: Literal["spec", "plan"]) -> bool:
        path = review_receipt_path(root, FEATURE, kind)
        return verify_feature_review(root, FEATURE, path, expected_kind=kind)

    return check("spec"), check("plan")


def _open() -> tuple[int, dict[str, object]]:
    args = ["delivery", "revision", "open", "--feature", FEATURE, "--json"]
    result = CliRunner().invoke(app, args, catch_exceptions=False)
    return result.exit_code, json.loads(result.output)


def _hand_written_record(root: Path, commit: str | None) -> None:
    record: dict[str, object] = {"schema_version": "1", "feature": FEATURE}
    for kind in ("spec", "plan"):
        record[kind] = json.loads((root / REVIEWS / f"{kind}.json").read_text())["context_hash"]
    if commit is not None:
        record["commit"] = commit
    (root / REVIEWS / "spec-revision.json").write_text(json.dumps(record))


# @spec AC-001: Stored source roles
#   — .specs/features/094-verified-review-continuity/spec.md#ac-001
def test_empty_informative_document_keeps_the_review_stable(root: Path) -> None:
    (root / ".specs/features" / FEATURE / "notes.md").write_text("")
    edit_spec(root, "## Scope\n", "## Scope\n\nInformative: [notes](notes.md).\n")
    review_both(root)
    receipt = json.loads((root / REVIEWS / "spec.json").read_text())
    assert receipt["reviewed"]["source_roles"][f".specs/features/{FEATURE}/notes.md"] == "context"
    edit_spec(root, "use the server clock", "use NTP time")
    assert _current(root) == (True, True)


def test_reviewed_context_without_roles_uses_the_inferred_roles(root: Path) -> None:
    for kind in ("spec", "plan"):
        path = root / REVIEWS / f"{kind}.json"
        data = json.loads(path.read_text())
        del data["reviewed"]["source_roles"]
        path.write_text(json.dumps(data))
    edit_spec(root, "use the server clock", "use NTP time")
    assert _current(root) == (True, True)


# @spec AC-002: The record names the opening commit
#   — .specs/features/094-verified-review-continuity/spec.md#ac-002
def test_open_records_the_head_commit(root: Path) -> None:
    head = commit_all(root, "reviews")
    code, payload = _open()
    assert (code, payload["commit"]) == (0, head)


def test_open_refuses_reviews_of_uncommitted_requirements(root: Path) -> None:
    edit_spec(root, *AC_EDIT)
    review_both(root)
    code, payload = _open()
    assert (code, payload["error"]) == (1, "spec_revision_uncommitted")


def test_open_accepts_committed_crlf_configuration(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "config", "core.autocrlf", "true"], check=True)
    (root / ".specs/semantic/config.yaml").write_bytes(b"review_model: reviewer/v1\r\n")
    review_both(root)
    commit_all(root, "crlf")
    assert _open()[0] == 0


def test_open_accepts_a_committed_symlinked_source(root: Path) -> None:
    (root / "docs").mkdir()
    (root / ".specs/project.md").rename(root / "docs/project.md")
    (root / ".specs/project.md").symlink_to("../docs/project.md")
    review_both(root)
    commit_all(root, "symlink")
    assert _open()[0] == 0


def test_project_in_a_repository_subdirectory_opens_and_verifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path / "sub")
    shutil.rmtree(root / ".git")
    commit_all(tmp_path, "monorepo")
    monkeypatch.chdir(root)
    assert _open()[0] == 0
    edit_spec(root, *AC_EDIT)
    require_progression(root, FEATURE, "implement", model="reviewer/v1")


def test_open_outside_git_is_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    shutil.rmtree(root / ".git")
    monkeypatch.chdir(root)
    assert _open()[1]["error"] == "spec_revision_unverified"


# @spec AC-003: Recorded receipts verified at the commit
#   — .specs/features/094-verified-review-continuity/spec.md#ac-003
def test_opened_revision_still_accepts_its_reviews(root: Path) -> None:
    _open()
    edit_spec(root, *AC_EDIT)
    commit_all(root, "revise")
    require_progression(root, FEATURE, "implement", model="reviewer/v1")


@pytest.mark.parametrize(
    "commit",
    ["latest", None, "0" * 40, "HEAD~1", "side"],
    ids=["no-match", "none", "unknown", "symbolic", "not-ancestor"],
)
def test_hand_written_record_for_stale_reviews_is_refused(root: Path, commit: str | None) -> None:
    side = ""
    if commit == "side":
        _git(root, "checkout", "-qb", "side")
        side = commit_all(root, "side")
        _git(root, "checkout", "-q", "-")
    edit_spec(root, *AC_EDIT)
    latest = commit_all(root, "revise")  # The reviews never matched this commit.
    _hand_written_record(root, {"latest": latest, "side": side}.get(str(commit), commit))
    with pytest.raises(ProgressionBlocked, match="spec_revision_unverified"):
        require_progression(root, FEATURE, "implement", model="reviewer/v1")


def test_hand_written_record_misses_no_linked_document(root: Path) -> None:
    feature = root / ".specs/features" / FEATURE
    (feature / "extra.md").write_text("Exports must be encrypted at rest.\n")
    edit_spec(root, "## Scope\n", "## Scope\n\nRead [extra](extra.md).\n")
    linked = commit_all(root, "link")  # The reviews never saw extra.md.
    _hand_written_record(root, linked)
    with pytest.raises(ProgressionBlocked, match="spec_revision_unverified"):
        require_progression(root, FEATURE, "implement", model="reviewer/v1")


def test_local_filters_and_attributes_do_not_change_the_commit(root: Path) -> None:
    reviewed = root / "reviewed-spec.md"
    shutil.copy(root / ".specs/features" / FEATURE / "spec.md", reviewed)
    edit_spec(root, *AC_EDIT)
    changed = commit_all(root, "revise")  # The reviews never matched this commit.
    _git(root, "config", "filter.old.smudge", f"cat {reviewed}")
    attributes = f".specs/features/{FEATURE}/spec.md filter=old\n"
    (root / ".git/info/attributes").write_text(attributes)
    _hand_written_record(root, changed)
    with pytest.raises(ProgressionBlocked, match="spec_revision_unverified"):
        require_progression(root, FEATURE, "implement", model="reviewer/v1")


def test_export_attributes_do_not_hide_committed_sources(root: Path) -> None:
    attributes = ".specs/** export-ignore\n.specs/project.md export-subst\n"
    (root / ".gitattributes").write_text(attributes)
    commit_all(root, "attributes")
    assert _open()[0] == 0


def test_symlink_loop_at_the_commit_is_refused_without_crashing(root: Path) -> None:
    (root / ".specs/features" / FEATURE / "loop.md").symlink_to("loop.md")
    edit_spec(root, "## Scope\n", "## Scope\n\nRead [loop](loop.md).\n")
    looped = commit_all(root, "loop")
    _hand_written_record(root, looped)
    with pytest.raises(ProgressionBlocked):
        require_progression(root, FEATURE, "implement", model="reviewer/v1")


def test_record_naming_a_commit_where_the_reviews_held_is_accepted(root: Path) -> None:
    reviewed_at = commit_all(root, "reviews")
    edit_spec(root, *AC_EDIT)
    commit_all(root, "revise")
    _hand_written_record(root, reviewed_at)
    require_progression(root, FEATURE, "implement", model="reviewer/v1")
    with pytest.raises(ProgressionBlocked, match="spec_revision_open"):
        require_progression(root, FEATURE, "complete", model="reviewer/v1")
