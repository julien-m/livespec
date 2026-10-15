"""Pinned snapshots ship the conventions test evidence the bundled catalogs cite (083 FR-001).

Regression for the Handy pinned runtime: ``livespec conventions verify`` failed with
``fixture missing: tests/fixtures/conventions_ast/...`` because the snapshot dropped
every top-level ``tests/`` path, so the conventions gate was always BLOCKED.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.runtime_support import commit_all, install, make_source, restore_write_bits, write
from validator.runtime import models
from validator.runtime.errors import RuntimeSnapshotError, RuntimeSourceError
from validator.runtime.evidence import POLICY_PATH, declared_policy, missing_evidence
from validator.runtime.home import RuntimeHome
from validator.runtime.models import SNAPSHOT_TEST_EVIDENCE, ships_in_snapshot

ROOT = Path(__file__).resolve().parents[1]
_CITED = re.compile(r"tests/[A-Za-z0-9_./{}-]+")


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[RuntimeHome]:
    monkeypatch.setenv("HOME", str(tmp_path / "user-home"))
    root = (tmp_path / "runtime-home").resolve()
    monkeypatch.setenv("LIVESPEC_HOME", str(root))
    yield RuntimeHome(root)
    restore_write_bits(tmp_path)


# @spec FR-001: Snapshot ships conventions test evidence
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
def test_snapshot_ships_conventions_evidence_and_still_drops_other_tests(
    home: RuntimeHome, tmp_path: Path
) -> None:
    source = make_source(tmp_path / "livespec-src")
    shipped = [
        "tests/fixtures/conventions_ast/ts/no_as_any/pass.ts",
        "tests/fixtures/conventions_ast/ars_rules/rule/fail.py",
        *(path for path in SNAPSHOT_TEST_EVIDENCE if not path.endswith("/")),
    ]
    for relative in shipped:
        write(source / relative, "# conventions evidence\n")
    write(source / "tests/fixtures/other/data.json", "{}\n")
    commit_all(source, "conventions evidence")
    snapshot = install(home, source).snapshot
    for relative in shipped:
        assert (snapshot / relative).is_file(), relative
    for relative in ("tests/test_excluded.py", "tests/fixtures/other/data.json", ".specs"):
        assert not (snapshot / relative).exists(), relative


def test_every_test_path_cited_by_conventions_runtime_ships() -> None:
    """Drift guard: a new cited fixture or test must be covered by the snapshot policy."""
    sources = [
        *sorted((ROOT / "validator/conventions_ast/rule_catalog").iterdir()),
        *sorted((ROOT / "validator/conventions_ast").glob("*.py")),
    ]
    cited = {
        match.rstrip(".").split("{", 1)[0]
        for source in sources
        for match in _CITED.findall(source.read_text(encoding="utf-8"))
    }
    assert cited, "the bundled catalogs cite their deterministic test evidence"
    for path in sorted(cited):
        assert ships_in_snapshot(f"{path}/" if (ROOT / path).is_dir() else path), path
        if "{" not in path and not path.endswith("/") and "." in Path(path).name:
            assert (ROOT / path).is_file(), path


_TARGET_POLICY = 'SNAPSHOT_TEST_EVIDENCE = ("tests/fixtures/conventions_ast/",)\n'
_TARGET_CATALOG = """rules:
  - id: ts.rule
    fixtures:
      pass: tests/fixtures/conventions_ast/ts/rule/pass.ts
      fail: tests/fixtures/conventions_ast/ts/rule/fail.ts
    deterministic_test_evidence:
      - test: tests/test_cited_by_catalog.py
"""
_CITED_BY_TARGET = (
    "tests/fixtures/conventions_ast/ts/rule/pass.ts",
    "tests/fixtures/conventions_ast/ts/rule/fail.ts",
    "tests/test_cited_by_catalog.py",
)


def _target_source(tmp_path: Path, *, omit: str | None = None) -> Path:
    """Source whose committed tree declares its own evidence policy and catalog."""
    source = make_source(tmp_path / "livespec-src")
    write(source / "validator/runtime/models.py", _TARGET_POLICY)
    write(source / "validator/conventions_ast/rule_catalog/ast_high.yaml", _TARGET_CATALOG)
    for relative in (*_CITED_BY_TARGET, "tests/fixtures/conventions_ast/generated/f/pass.sql"):
        if relative != omit:
            write(source / relative, "# evidence\n")
    commit_all(source, "target evidence policy")
    return source


def _simulate_older_builder(monkeypatch: pytest.MonkeyPatch, *, unchecked: bool) -> None:
    """Run the install with a builder that predates the target's evidence rules."""
    monkeypatch.setattr(models, "SNAPSHOT_TEST_EVIDENCE", ())
    if unchecked:
        # A builder from before the fix neither reads the target rules nor checks them.
        monkeypatch.setattr(
            "validator.runtime.git_tree.target_evidence", lambda *_: (), raising=False
        )
        monkeypatch.setattr(
            "validator.runtime.snapshot.missing_evidence", lambda _: [], raising=False
        )


# @spec FR-001: Inclusion rules come from the installed commit
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-001
def test_older_builder_ships_the_evidence_the_target_commit_declares(
    home: RuntimeHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _target_source(tmp_path)
    _simulate_older_builder(monkeypatch, unchecked=False)
    snapshot = install(home, source).snapshot
    for relative in (*_CITED_BY_TARGET, "tests/fixtures/conventions_ast/generated/f/pass.sql"):
        assert (snapshot / relative).is_file(), relative
    assert not (snapshot / "tests/test_excluded.py").exists()


def test_install_refuses_a_commit_whose_catalog_cites_a_missing_file(
    home: RuntimeHome, tmp_path: Path
) -> None:
    source = _target_source(tmp_path, omit="tests/test_cited_by_catalog.py")
    with pytest.raises(RuntimeSourceError, match=r"tests/test_cited_by_catalog\.py"):
        install(home, source)
    assert not home.versions.exists() or not any(home.versions.iterdir())


# @spec FR-003: Reuse refuses an incomplete snapshot
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-003
def test_reuse_refuses_a_snapshot_an_older_builder_left_incomplete(
    home: RuntimeHome, tmp_path: Path
) -> None:
    source = _target_source(tmp_path)
    with pytest.MonkeyPatch.context() as older:
        _simulate_older_builder(older, unchecked=True)
        incomplete = install(home, source).snapshot
    assert not (incomplete / "tests").exists()
    with pytest.raises(RuntimeSnapshotError) as refused:
        install(home, source)
    message = str(refused.value)
    assert "tests/fixtures/conventions_ast/ts/rule/pass.ts" in message
    assert "rebuild" in message and str(incomplete) in message


def test_install_refuses_a_commit_missing_evidence_its_policy_declares(
    home: RuntimeHome, tmp_path: Path
) -> None:
    """A policy entry no catalog cites is still required, as a file or a directory."""
    source = _target_source(tmp_path)
    policy = 'SNAPSHOT_TEST_EVIDENCE = ("tests/fixtures/declared_only/", "tests/test_read.py")\n'
    write(source / "validator/runtime/models.py", policy)
    commit_all(source, "declare evidence no catalog cites")
    with pytest.raises(RuntimeSourceError) as refused:
        install(home, source)
    assert "tests/fixtures/declared_only/" in str(refused.value)
    assert "tests/test_read.py" in str(refused.value)


def test_lost_rename_race_refuses_an_incomplete_winner(home: RuntimeHome, tmp_path: Path) -> None:
    """An older installer that wins the rename leaves an incomplete snapshot: never reuse it."""
    from validator.runtime import snapshot as snapshot_module
    from validator.runtime.manifest import read_manifest

    source = _target_source(tmp_path)
    with pytest.MonkeyPatch.context() as older:
        _simulate_older_builder(older, unchecked=True)
        incomplete = install(home, source).snapshot
    base = read_manifest(incomplete)
    entries = snapshot_module.list_snapshot_entries(source.resolve(), base.commit)
    blobs = snapshot_module.read_blobs(source.resolve(), [entry.oid for entry in entries])
    with pytest.raises(RuntimeSnapshotError, match="incomplete"):
        snapshot_module._build_snapshot(home, base, entries, blobs)  # pyright: ignore[reportPrivateUsage]


def test_target_rules_read_this_repository_policy_and_catalogs() -> None:
    """A future installer reads this commit's rules exactly as this code declares them."""
    assert declared_policy((ROOT / POLICY_PATH).read_text(encoding="utf-8")) == (
        SNAPSHOT_TEST_EVIDENCE
    )
    assert missing_evidence(ROOT) == []


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("validator/cli.py", True),
        ("tests/fixtures/conventions_ast/rust/rule/pass.rs", True),
        ("tests/test_conventions_ast_multilang.py", True),
        ("tests/test_runtime_snapshot.py", False),
        ("tests/fixtures/conventions_ast_other/x.py", False),
        (".specs/features/001/spec.md", False),
    ],
)
def test_snapshot_policy(path: str, expected: bool) -> None:
    assert ships_in_snapshot(path) is expected
