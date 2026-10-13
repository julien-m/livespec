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
