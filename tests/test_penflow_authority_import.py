"""Real import files with explicit CLI protocol doubles, not producer policy proofs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from validator import penflow_authority_import as importer
from validator.penflow_approval_files import PenflowApprovalError, digest
from validator.penflow_authority_import import (
    AUTHORITY_POINTER,
    authority_command,
    import_brainstorm_authority,
    load_imported_authority,
)


@dataclass
class AuthorityProtocolFixture:
    """A transport fixture that makes no claim about real Brainstorm certification."""

    consumer: Path
    origin: Path
    workspace: Path
    envelope: dict[str, Any]
    calls: list[list[str]] = field(default_factory=list)
    on_call: Callable[[int], None] | None = None
    returncode: int = 0

    def run(self, arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        if self.on_call:
            self.on_call(len(self.calls))
        return subprocess.CompletedProcess(
            arguments, self.returncode, json.dumps(self.envelope), ""
        )

    def import_authority(self) -> dict[str, Any]:
        return import_brainstorm_authority(
            self.consumer, self.workspace, source_project_root=self.origin
        )


@pytest.fixture
def protocol(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AuthorityProtocolFixture:
    origin = tmp_path / "brainstorm"
    workspace = origin / "exports/penflow"
    workspace.mkdir(parents=True)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    scope = {"project_root": str(origin), "workspace": str(workspace)}
    files = {
        workspace / "run-report.json": json.dumps(
            {"scope": scope, "fixture": "not-policy-proof"}
        ).encode(),
        workspace / "product-contract/product.json": b'{"requirements":["keep original bytes"]}\n',
        workspace / "flow-ui-contract/contract.json": b'{"original_scope":"never rewritten"}',
        origin / "reviews/history.bin": b"\x00\xff\x01binary evidence",
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    report = workspace / "run-report.json"
    envelope = {
        "kind": "penflow-authority-result",
        "version": 1,
        "operation": "collect",
        "status": "PASS",
        "issues": [],
        "data": {
            "scope": scope,
            "workspace": str(workspace),
            "report": {"path": str(report), "sha256": digest(files[report])},
            "files": [
                {"source_path": str(path), "path": str(path), "sha256": digest(content)}
                for path, content in sorted(files.items())
            ],
        },
    }
    fixture = AuthorityProtocolFixture(consumer, origin, workspace, envelope)
    monkeypatch.setattr(importer.shutil, "which", lambda _command: "/protocol-fixture/penflow")
    monkeypatch.setattr(importer.subprocess, "run", fixture.run)
    return fixture


# @spec AC-009: authenticated transport, bounded byte copies and interrupted import recovery
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-009
def test_import_preserves_all_bytes_scope_and_existing_workspace(
    protocol: AuthorityProtocolFixture,
) -> None:
    existing = protocol.consumer / "penflow"
    existing.mkdir()
    (existing / "user-work.txt").write_text("Never overwrite")
    reference = protocol.import_authority()
    assert json.loads((protocol.consumer / AUTHORITY_POINTER).read_text()) == reference
    assert reference["path"].startswith(".specs/penflow-approvals/authority-")
    package = load_imported_authority(protocol.consumer)
    assert package["origin_scope"] == protocol.envelope["data"]["scope"]
    assert len(package["files"]) == 4
    for entry in package["files"]:
        assert not Path(entry["path"]).is_absolute()
        assert (protocol.consumer / entry["path"]).read_bytes() == Path(
            entry["source_path"]
        ).read_bytes()
    assert (existing / "user-work.txt").read_text() == "Never overwrite"
    assert len(protocol.calls) == 2
    assert protocol.calls[0] == [
        "/protocol-fixture/penflow",
        "authority",
        "collect",
        str(protocol.workspace / "run-report.json"),
        "--project",
        str(protocol.origin),
        "--json",
    ]


def test_rebootstrap_is_idempotent(protocol: AuthorityProtocolFixture) -> None:
    first = protocol.import_authority()
    pointer = protocol.consumer / AUTHORITY_POINTER
    timestamp = pointer.stat().st_mtime_ns
    archives = sorted((protocol.consumer / ".specs/penflow-approvals").iterdir())
    assert protocol.import_authority() == first
    assert pointer.stat().st_mtime_ns == timestamp
    assert sorted((protocol.consumer / ".specs/penflow-approvals").iterdir()) == archives


@pytest.mark.parametrize("change", ["bytes", "same_bytes_retarget", "source_alias"])
def test_source_change_before_publication_rejects_authority(
    protocol: AuthorityProtocolFixture, change: str
) -> None:
    source = protocol.origin / "reviews/history.bin"
    real_workspace = protocol.workspace
    if change == "source_alias":
        alias = protocol.origin / "workspace-alias"
        alias.symlink_to(real_workspace, target_is_directory=True)
        protocol.workspace = alias

    def mutate(call: int) -> None:
        if call != 2:
            return
        if change == "bytes":
            source.write_bytes(b"Changed source")
        elif change == "same_bytes_retarget":
            replacement = source.with_suffix(".replacement")
            replacement.write_bytes(source.read_bytes())
            os.replace(replacement, source)
        else:
            alternative = protocol.origin / "alternative"
            shutil.copytree(real_workspace, alternative)
            protocol.workspace.unlink()
            protocol.workspace.symlink_to(alternative, target_is_directory=True)

    protocol.on_call = mutate
    with pytest.raises(PenflowApprovalError, match="source_changed_before_publication"):
        protocol.import_authority()
    assert not (protocol.consumer / AUTHORITY_POINTER).exists()


@pytest.mark.parametrize(
    "invalid",
    [
        "missing_hash",
        "wrong_scope",
        "version_bool",
        "issues",
        "operation",
        "duplicate",
        "cli_failure",
    ],
)
def test_invalid_transport_cannot_publish(protocol: AuthorityProtocolFixture, invalid: str) -> None:
    envelope = protocol.envelope
    if invalid == "missing_hash":
        del envelope["data"]["files"][0]["sha256"]
    elif invalid == "wrong_scope":
        envelope["data"]["scope"]["project_root"] = str(protocol.consumer)
    elif invalid == "version_bool":
        envelope["version"] = True
    elif invalid == "issues":
        envelope["issues"] = [{"code": "rejected", "message": "Protocol failure fixture"}]
    elif invalid == "operation":
        envelope["operation"] = "project"
    elif invalid == "duplicate":
        envelope["data"]["files"].append(envelope["data"]["files"][0])
    else:
        protocol.returncode = 1
    with pytest.raises(PenflowApprovalError):
        protocol.import_authority()
    assert not (protocol.consumer / AUTHORITY_POINTER).exists()


def test_interruption_before_pointer_can_retry(
    protocol: AuthorityProtocolFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = importer.write_with_hash_check

    def interrupt(path: Path, content: str) -> str:
        if path == protocol.consumer / AUTHORITY_POINTER:
            raise OSError("Protocol fixture interruption before pointer")
        return original(path, content)

    with monkeypatch.context() as patch:
        patch.setattr(importer, "write_with_hash_check", interrupt)
        with pytest.raises(PenflowApprovalError, match="interruption"):
            protocol.import_authority()
    assert not (protocol.consumer / AUTHORITY_POINTER).exists()
    reference = protocol.import_authority()
    assert json.loads((protocol.consumer / AUTHORITY_POINTER).read_text()) == reference
    load_imported_authority(protocol.consumer)


def test_local_authority_survives_original_directory_move(
    protocol: AuthorityProtocolFixture,
) -> None:
    protocol.import_authority()
    package = load_imported_authority(protocol.consumer)
    protocol.origin.rename(protocol.origin.with_name("moved-brainstorm"))
    assert load_imported_authority(protocol.consumer) == package
    assert len(protocol.calls) == 2


@pytest.mark.parametrize("target", ["archive", "package"])
def test_post_import_tampering_blocks_local_read(
    protocol: AuthorityProtocolFixture, target: str
) -> None:
    reference = protocol.import_authority()
    package = load_imported_authority(protocol.consumer)
    path = protocol.consumer / (
        package["files"][0]["path"] if target == "archive" else reference["path"]
    )
    path.write_bytes(path.read_bytes() + b" changed")
    with pytest.raises(PenflowApprovalError, match=r"archive_changed|reference_stale"):
        load_imported_authority(protocol.consumer)
    with pytest.raises(PenflowApprovalError):
        protocol.import_authority()


def test_shared_project_transport_checks_operation(protocol: AuthorityProtocolFixture) -> None:
    protocol.envelope["operation"] = "project"
    protocol.envelope["data"] = {"sources": [], "requirements": []}
    assert (
        authority_command(
            "project",
            ["package.json", "--contract", "contract.json"],
            project_root=protocol.consumer,
        )
        == protocol.envelope["data"]
    )
