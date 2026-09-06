"""Import CLI-authenticated Brainstorm ancestry without rewriting source evidence."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError

from .locks import acquire_lock, write_with_hash_check
from .penflow_approval_files import (
    JsonObject,
    PenflowApprovalError,
    archive_json,
    bounded,
    digest,
    json_bytes,
    load_object,
    read_ref,
)
from .penflow_approval_models import (
    AuthorityImport,
    File,
    ImportedAuthorityFile,
    NonemptyString,
    Scope,
    StrictModel,
    VersionOne,
)

AUTHORITY_POINTER = Path(".specs/penflow-brainstorm-authority.json")
AUTHORITY_ARCHIVE = Path(".specs/penflow-authority")


class _Collection(StrictModel):
    scope: Scope
    workspace: NonemptyString
    report: File
    files: Annotated[list[ImportedAuthorityFile], Field(min_length=1)]


class _CollectResult(StrictModel):
    kind: Literal["penflow-authority-result"]
    version: VersionOne
    status: Literal["PASS"]
    operation: Literal["collect", "project"]
    data: JsonObject
    issues: list[object]


@dataclass(frozen=True)
class _Source:
    path: Path
    content: bytes
    fingerprint: tuple[int, int, int, int]


def _source(path: Path) -> _Source:
    if path.resolve(strict=True) != path or not path.is_file():
        raise PenflowApprovalError(f"authority_source_path_changed: {path}")
    before = path.stat()
    content = path.read_bytes()
    after = path.stat()

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return value.st_dev, value.st_ino, value.st_mtime_ns, value.st_ctime_ns

    if identity(before) != identity(after):
        raise PenflowApprovalError(f"authority_source_changed: {path}")
    return _Source(path, content, identity(after))


def authority_command(
    operation: Literal["collect", "project"], arguments: list[str], *, project_root: Path
) -> JsonObject:
    """Run one public authority command and accept only its exact successful envelope.

    Args:
        operation: Authority operation whose response must match this invocation.
        arguments: Explicit operation arguments, without project or JSON flags.
        project_root: Project identity forwarded to Penflow.

    Returns:
        Authority data; the caller validates operation-specific path and hash bindings.

    Raises:
        PenflowApprovalError: Missing CLI, execution failure or noncertifying response.
    """
    try:
        executable = shutil.which("penflow")
        if executable is None:
            raise PenflowApprovalError("authority_cli_required")
        result = subprocess.run(
            [
                executable,
                "authority",
                operation,
                *arguments,
                "--project",
                str(project_root.resolve()),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise PenflowApprovalError("authority_command_rejected")
        envelope = _CollectResult.model_validate(load_object(result.stdout.encode("utf-8")))
        if envelope.issues or envelope.operation != operation:
            raise PenflowApprovalError("authority_noncertifying_response")
        return envelope.data
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise PenflowApprovalError(f"authority_command_failed: {exc}") from exc


def _collect(workspace: Path, project: Path) -> JsonObject:
    raw = authority_command("collect", [str(workspace / "run-report.json")], project_root=project)
    data = _Collection.model_validate(raw).model_dump(mode="json")
    if data["scope"] != {"project_root": str(project), "workspace": str(workspace)} or data[
        "workspace"
    ] != str(workspace):
        raise PenflowApprovalError("authority_collect_scope_mismatch")
    if data["report"]["path"] != str(workspace / "run-report.json"):
        raise PenflowApprovalError("authority_collect_report_mismatch")
    paths = [item["path"] for item in data["files"]]
    if paths != sorted(set(paths)):
        raise PenflowApprovalError("authority_collect_duplicate_or_unsorted_files")
    for item in data["files"]:
        path = Path(item["path"])
        if (
            item["source_path"] != item["path"]
            or not path.is_absolute()
            or not path.is_relative_to(project)
        ):
            raise PenflowApprovalError("authority_collect_foreign_file")
    if not any(
        {"path": row["path"], "sha256": row["sha256"]} == data["report"] for row in data["files"]
    ):
        raise PenflowApprovalError("authority_collect_report_not_in_inventory")
    return data


def _package(data: JsonObject) -> JsonObject:
    origin = Path(data["scope"]["project_root"])
    tree = AUTHORITY_ARCHIVE / digest(json_bytes(data)) / "tree"
    return AuthorityImport.model_validate(
        {
            "kind": "penflow-brainstorm-authority-import",
            "version": 1,
            "origin_scope": data["scope"],
            "workspace": str(tree / Path(data["workspace"]).relative_to(origin)),
            "report": {
                "path": str(tree / Path(data["report"]["path"]).relative_to(origin)),
                "sha256": data["report"]["sha256"],
            },
            "files": [
                {
                    "source_path": row["source_path"],
                    "path": str(tree / Path(row["path"]).relative_to(origin)),
                    "sha256": row["sha256"],
                }
                for row in data["files"]
            ],
        }
    ).model_dump(mode="json")


def _check_local_package(root: Path, package: JsonObject) -> None:
    origin = Path(package["origin_scope"]["project_root"])
    workspace = Path(package["origin_scope"]["workspace"])
    if not origin.is_absolute() or not workspace.is_relative_to(origin) or ".." in workspace.parts:
        raise PenflowApprovalError("authority_import_invalid_origin")
    data = {
        "scope": package["origin_scope"],
        "workspace": str(workspace),
        "report": {
            "path": str(workspace / "run-report.json"),
            "sha256": package["report"]["sha256"],
        },
        "files": [
            {"source_path": row["source_path"], "path": row["source_path"], "sha256": row["sha256"]}
            for row in package["files"]
        ],
    }
    paths = [row["source_path"] for row in package["files"]]
    if paths != sorted(set(paths)) or package != _package(data):
        raise PenflowApprovalError("authority_import_path_identity_mismatch")
    for row in package["files"]:
        path = root / row["path"]
        if path.resolve(strict=True) != path or digest(path.read_bytes()) != row["sha256"]:
            raise PenflowApprovalError(f"authority_import_archive_changed: {row['path']}")
    read_ref(root, package["report"])


def load_imported_authority(project_root: Path) -> JsonObject:
    """Read and rehash the immutable local import without accessing its historical source.

    Args:
        project_root: Consumer root containing the fixed authority pointer.

    Returns:
        Validated import package with historical scope and relative local references.

    Raises:
        PenflowApprovalError: Pointer, package or archived files are absent or changed.
    """
    root = project_root.resolve()
    try:
        reference = File.model_validate(
            load_object(bounded(root, AUTHORITY_POINTER).read_bytes())
        ).model_dump(mode="json")
        if reference["path"] != f".specs/penflow-approvals/authority-{reference['sha256']}.json":
            raise PenflowApprovalError("authority_import_invalid_package_reference")
        package = AuthorityImport.model_validate(load_object(read_ref(root, reference))).model_dump(
            mode="json"
        )
        _check_local_package(root, package)
        return package
    except (OSError, ValueError, RuntimeError) as exc:
        raise PenflowApprovalError(f"authority_import_unreadable: {exc}") from exc


def _archive_files(root: Path, data: JsonObject, sources: list[_Source]) -> None:
    destination = bounded(root, AUTHORITY_ARCHIVE / digest(json_bytes(data)))
    if destination.exists():
        _check_local_package(root, _package(data))
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tmp-authority-", dir=destination.parent) as temporary:
        staged = Path(temporary) / "archive"
        for source in sources:
            local = staged / "tree" / source.path.relative_to(data["scope"]["project_root"])
            local.parent.mkdir(parents=True, exist_ok=True)
            with local.open("xb") as handle:
                handle.write(source.content)
                handle.flush()
                os.fsync(handle.fileno())
            if local.read_bytes() != source.content:
                raise PenflowApprovalError("authority_import_copy_mismatch")
        os.replace(staged, destination)


# @spec FR-008: import accepted source ancestry before consumer review
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-008
def import_brainstorm_authority(
    project_root: Path, source_workspace: Path, *, source_project_root: Path
) -> JsonObject:
    """Authenticate and archive source ancestry, returning an immutable package reference.

    Args:
        project_root: Consumer project whose existing workspace is never overwritten.
        source_workspace: Explicit original workspace containing run-report.json.
        source_project_root: Explicit original project passed to Penflow validation.

    Returns:
        Relative path and SHA256 of the immutable imported authority package.

    Raises:
        PenflowApprovalError: CLI rejection, source drift, archive conflict or I/O failure.
    """
    try:
        root = project_root.resolve()
        origin = source_project_root.resolve(strict=True)
        workspace = source_workspace.resolve(strict=True)
        if not workspace.is_relative_to(origin):
            raise PenflowApprovalError("authority_source_workspace_outside_project")
        report = _source(workspace / "run-report.json")
        data = _collect(workspace, origin)
        sources = [_source(Path(row["path"])) for row in data["files"]]
        if any(
            digest(source.content) != row["sha256"]
            for source, row in zip(sources, data["files"], strict=True)
        ) or report != _source(report.path):
            raise PenflowApprovalError("authority_source_changed")
        package = _package(data)
        with acquire_lock(root / ".specs"):
            _archive_files(root, data, sources)
            if (
                _collect(workspace, origin) != data
                or source_workspace.resolve(strict=True) != workspace
                or source_project_root.resolve(strict=True) != origin
                or any(_source(source.path) != source for source in sources)
            ):
                raise PenflowApprovalError("authority_source_changed_before_publication")
            _check_local_package(root, package)
            reference = archive_json(root, package, prefix="authority")
            pointer = bounded(root, AUTHORITY_POINTER)
            if pointer.exists():
                load_imported_authority(root)
                if load_object(pointer.read_bytes()) != reference:
                    raise PenflowApprovalError("authority_import_already_established")
            else:
                write_with_hash_check(pointer, json_bytes(reference).decode("utf-8"))
            return reference
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, ValidationError) as exc:
        raise PenflowApprovalError(f"authority_import_failed: {exc}") from exc
