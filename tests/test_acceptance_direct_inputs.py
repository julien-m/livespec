"""Documentary acceptance consumes direct contracts and strict generated manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.acceptance_review_support import add_documentary_acceptance
from tests.review_support import grounded_response, reviewed_project
from validator.cli import app
from validator.semantic.acceptance_review import (
    ingest_acceptance_review,
    prepare_acceptance_review,
    verify_acceptance_review,
)


def _direct_inputs(root: Path) -> tuple[Path, list[str]]:
    directory = reviewed_project(root)
    sources = [
        ".specs/constitution.md",
        ".specs/stacks/_default.md",
        ".specs/testing/strategy.md",
        ".specs/features/010-contract/spec.md",
    ]
    for name in sources[2:]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Approved contract\nRetention must be bounded.\n")
    links = " ".join(f"[contract]({Path('../../../') / name})" for name in sources)
    spec = directory / "spec.md"
    spec.write_text(
        spec.read_text() + "\n## AC-002\nReview the operator documentation.\n"
        f"**Evidence:** review\n**Review inputs:** {links}\n"
    )
    return directory, sources


# @spec FR-016: direct documentary contracts retain source roles and exact identity
# — .specs/features/078-requirement-evidence-integrity/spec.md#fr-016
def test_direct_markdown_cli_preserves_roles_bytes_and_freshness(tmp_path: Path) -> None:
    directory, sources = _direct_inputs(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "validate",
            str(directory),
            "--prepare-review",
            "acceptance",
            "--model",
            "reviewer/v1",
            "--review-max-chars",
            "200000",
        ],
    )
    assert result.exit_code == 0, result.output
    prepared = prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1", 200000)
    assert prepared.requirement_scope == (f"{directory.name}:AC-002",)
    assert prepared.source_roles[sources[0]] == "constitution"
    assert prepared.source_roles[sources[1]] == "stack"
    assert prepared.source_roles[sources[3]] == "reference"
    for name in sources:
        raw = (tmp_path / name).read_bytes()
        assert "".join(s.text for s in prepared.sections if s.source == name) == raw.decode()
        assert prepared.source_hashes[name] == hashlib.sha256(raw).hexdigest()
    receipt, path = ingest_acceptance_review(
        tmp_path,
        directory.name,
        [grounded_response(prepared)],
        model="reviewer/v1",
        max_chars=200000,
    )
    assert receipt.ready, receipt.errors
    assert verify_acceptance_review(
        tmp_path, directory.name, path, model="reviewer/v1", max_chars=200000
    )
    for name in sources:
        source = tmp_path / name
        original = source.read_bytes()
        source.write_bytes(original + b"Retention is unlimited.\n")
        assert not verify_acceptance_review(
            tmp_path, directory.name, path, model="reviewer/v1", max_chars=200000
        )
        source.write_bytes(original)


def test_json_manifests_still_require_valid_shape_and_current_sources(tmp_path: Path) -> None:
    directory = reviewed_project(tmp_path)
    add_documentary_acceptance(tmp_path, directory.name)
    path = directory / ".reviews/doc-inputs.json"
    original = path.read_bytes()
    for invalid in ("# Constitution\n", "{}", '{"source_paths":[]}'):
        path.write_text(invalid)
        with pytest.raises(ValueError):
            prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
    path.write_bytes(original)
    manifest = json.loads(original)
    manifest["current_hashes"]["migration.md"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match=r"acceptance_input_stale:migration\.md"):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")


def test_direct_input_missing_unreadable_or_outside_root_is_rejected(tmp_path: Path) -> None:
    directory, sources = _direct_inputs(tmp_path)
    source = tmp_path / sources[2]
    original = source.read_bytes()
    source.unlink()
    with pytest.raises(FileNotFoundError):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
    source.write_bytes(b"\xff")
    with pytest.raises(UnicodeError):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
    source.write_bytes(original)
    spec = directory / "spec.md"
    spec.write_text(
        spec.read_text().replace("../../../.specs/testing/strategy.md", "../../../../outside.md")
    )
    with pytest.raises(ValueError):
        prepare_acceptance_review(tmp_path, directory.name, "reviewer/v1")
