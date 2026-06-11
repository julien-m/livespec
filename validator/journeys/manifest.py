# LiveSpec traceability anchors
# @spec(FR-003)
# @spec(FR-029)
# @spec(FR-030)

"""Compiled manifest semantics for User Journeys v2."""

# @spec FR-029, FR-030: compiled manifest metadata and artifact marker traceability
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-029

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import cast

from .paths import journey_manifest_path, relative_to_project

MANIFEST_SCHEMA_VERSION = 1
# journeys-v2-3: fixture bootstrap contract waits (feature 060) — bumping the
# version invalidates every pre-contract compiled manifest unconditionally.
COMPILER_VERSION = "journeys-v2-3"


@dataclass(frozen=True)
class CompiledManifest:
    """Metadata written after successful ahead-of-time journey compilation."""

    # @spec FR-006: Version bump and additive fixtures_contract_hash
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-006
    journey_id: str
    source_path: str
    source_hash: str
    compiler_version: str
    runner: str
    native_output_paths: list[str] = field(default_factory=list)
    visual_contract_paths: list[str] = field(default_factory=list)
    fixtures_contract_hash: str = ""
    schema_version: int = MANIFEST_SCHEMA_VERSION


def write_compiled_manifest(
    project_root: Path,
    *,
    journey_id: str,
    source_path: Path,
    source_hash: str,
    runner: str,
    native_output_paths: list[Path],
    visual_contract_paths: list[Path] | None = None,
    fixtures_contract_hash: str = "",
) -> CompiledManifest:
    """Write a v2 compiled manifest and return the persisted model."""
    manifest = CompiledManifest(
        journey_id=journey_id,
        source_path=relative_to_project(project_root, source_path),
        source_hash=source_hash,
        compiler_version=COMPILER_VERSION,
        runner=runner,
        native_output_paths=[
            relative_to_project(project_root, path) for path in native_output_paths
        ],
        visual_contract_paths=[
            relative_to_project(project_root, path) for path in (visual_contract_paths or [])
        ],
        fixtures_contract_hash=fixtures_contract_hash,
    )
    path = journey_manifest_path(project_root, journey_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def read_compiled_manifest(project_root: Path, journey_id: str) -> CompiledManifest | None:
    """Read a v2 compiled manifest when it exists and is valid JSON."""
    path = journey_manifest_path(project_root, journey_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    # JSON list fields arrive as untyped data; cast to `object` before narrowing.
    native_output_paths = cast(object, data.get("native_output_paths"))
    visual_contract_paths = cast(object, data.get("visual_contract_paths"))
    return CompiledManifest(
        journey_id=str(data.get("journey_id", "")),
        source_path=str(data.get("source_path", "")),
        source_hash=str(data.get("source_hash", "")),
        compiler_version=str(data.get("compiler_version", "")),
        runner=str(data.get("runner", "")),
        native_output_paths=[str(item) for item in native_output_paths if isinstance(item, str)]
        if isinstance(native_output_paths, list)
        else [],
        visual_contract_paths=[str(item) for item in visual_contract_paths if isinstance(item, str)]
        if isinstance(visual_contract_paths, list)
        else [],
        # Backward compatibility: pre-060 manifests lack the field; they are
        # already rejected by the compiler-version check, so the tolerant ""
        # default never needs conditional staleness logic. Removable once no
        # consumer project predates journeys-v2-3.
        fixtures_contract_hash=str(data.get("fixtures_contract_hash", "")),
        schema_version=int(data.get("schema_version", 0)),
    )


__all__ = [
    "COMPILER_VERSION",
    "CompiledManifest",
    "read_compiled_manifest",
    "write_compiled_manifest",
]
