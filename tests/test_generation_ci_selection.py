"""The shipped CI privately supplies exact AST provenance and removes it after consumers."""

# @spec AC-006: Pinned private corpus, capability and cleanup
# ../.specs/features/079-validator-ci-prerequisites/spec.md#ac-006

import os
import shlex
import subprocess
from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import JsonValue, TypeAdapter

from tests._json_fixture import JsonFixture

REPO = Path(__file__).resolve().parents[1]
CORPUS_PATH = ".ci-deps/ai-ressources"
CORPUS_FILES = ("javascript.md", "rust.md", "swift-kotlin.md")


def _unit_job() -> JsonFixture:
    """Validate the workflow mapping before inspecting heterogeneous step fixtures."""
    raw = yaml.load((REPO / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    # Actions mappings vary by step; validate the JSON schema before fixture assertions.
    workflow = cast(JsonFixture, TypeAdapter(dict[str, JsonValue]).validate_python(raw))
    return cast(JsonFixture, workflow["jobs"]["unit-tests"])


def _named_step(name: str) -> JsonFixture:
    """Resolve the actual shipped step, failing when absent or duplicated."""
    matches = [step for step in _unit_job()["steps"] if step.get("name") == name]
    assert len(matches) == 1
    return cast(JsonFixture, matches[0])


def test_ast_corpus_checkout_pins_private_source_and_exact_sparse_files() -> None:
    step = _named_step("Checkout pinned normative corpus")
    assert step["uses"] == "actions/checkout@v4"
    assert step["with"] == {
        "repository": "julien-m/ai-ressources",
        "ref": "11976242fc5b9ae5f3a574e19339b78ebd18a0c4",
        "ssh-key": "${{ secrets.AIRESOURCES_READONLY_DEPLOY_KEY }}",
        "persist-credentials": "false",
        "path": CORPUS_PATH,
        "sparse-checkout": "".join(f"/code-conventions/{name}\n" for name in CORPUS_FILES),
        "sparse-checkout-cone-mode": "false",
    }
    assert _unit_job()["env"]["AIRESOURCES"] == "${{ github.workspace }}/" + CORPUS_PATH


def test_missing_private_corpus_capability_fails_before_checkout(tmp_path: Path) -> None:
    step = _named_step("Require read-only normative corpus capability")
    assert step["env"] == {"AIRESOURCES_KEY": "${{ secrets.AIRESOURCES_READONLY_DEPLOY_KEY }}"}
    # Exercise the shipped empty-key guard without network access or a credential.
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=tmp_path,
        env={**os.environ, "AIRESOURCES_KEY": ""},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "AST tests require AIRESOURCES_READONLY_DEPLOY_KEY for the pinned private corpus.\n"
    )


def test_corpus_cleanup_runs_after_all_consumers_even_when_a_check_fails(tmp_path: Path) -> None:
    step = _named_step("Remove private normative corpus")
    assert step["if"] == "always()"
    steps = _unit_job()["steps"]
    names = [row.get("name") for row in steps]
    assert names.index("Require read-only normative corpus capability") < names.index(
        "Checkout pinned normative corpus"
    )
    consumer_indices = [
        index for index, row in enumerate(steps) if row.get("run", "").startswith("pytest ")
    ]
    assert names.index("Checkout pinned normative corpus") < min(consumer_indices)
    assert names.index("Remove private normative corpus") > max(consumer_indices)
    corpus = tmp_path / CORPUS_PATH
    corpus.mkdir(parents=True)
    (corpus / "sentinel.md").write_text("isolated test fixture")
    retained = tmp_path / "keep.txt"
    retained.write_text("unrelated")
    # Exercise actual cleanup in an isolated cwd; unrelated files must survive.
    result = subprocess.run(
        ["bash", "-c", step["run"]], cwd=tmp_path, capture_output=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert not corpus.exists()
    assert retained.read_text() == "unrelated"


def test_private_source_is_not_uploaded_or_cached() -> None:
    steps = _unit_job()["steps"]
    uses = [step["uses"] for step in steps if "uses" in step]
    assert not any("upload-artifact" in action or "actions/cache" in action for action in uses)
    uv_steps = [step for step in steps if step.get("uses") == "astral-sh/setup-uv@v5"]
    assert len(uv_steps) == 1
    assert uv_steps[0]["with"]["enable-cache"] == "false"


@pytest.mark.parametrize(
    ("version", "expected_exit"), [("ast-grep 0.44.0", 0), ("sg from shadow", 1)]
)
def test_ast_backend_identity_guard_rejects_unix_group_command(
    tmp_path: Path, version: str, expected_exit: int
) -> None:
    install = _named_step("Install pinned AST backend")
    verify = _named_step("Verify AST backend identity")
    assert install["run"] == "npm install --global @ast-grep/cli@0.44.0"
    steps = _unit_job()["steps"]
    assert steps.index(install) < steps.index(verify)
    consumer = next(
        index for index, step in enumerate(steps) if step.get("run", "").startswith("pytest ")
    )
    assert steps.index(verify) < consumer
    binary = tmp_path / "sg"
    # Controlled versions test the shipped guard against Ubuntu's ambiguous command name.
    binary.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(version) + "\n")
    binary.chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", verify["run"]],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin"},
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == expected_exit
