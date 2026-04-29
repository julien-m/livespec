"""Detect brainstorm artifacts in the current working directory.

Returns counts and presence flags for `specs/flows/*.md`,
`specs/screens/*.md`, `mockups/manifest.json` (asserting schemaVersion 2),
`mockups/*.png`, `project-profile.md`, and `specs/flows/_index.md`.

The slash command (`/spec.init`) drives ingestion based on this output.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Detected:
    """Snapshot of brainstorm artifacts present in `cwd`."""

    flows_count: int
    screens_count: int
    mockups_count: int
    has_manifest: bool
    manifest_schema_ok: bool
    has_project_profile: bool
    has_flows_index: bool
    has_specs_dir: bool

    @property
    def has_artifacts(self) -> bool:
        return (
            self.flows_count > 0
            or self.screens_count > 0
            or self.mockups_count > 0
            or self.has_project_profile
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# @spec FR-001: Detect artifacts — .specs/features/012-brainstorm-ingestion/spec.md#fr-001
def detect(cwd: Path) -> Detected:
    """Scan `cwd` for brainstorm artifacts."""
    flows_dir = cwd / "specs" / "flows"
    screens_dir = cwd / "specs" / "screens"
    mockups_dir = cwd / "mockups"
    manifest = mockups_dir / "manifest.json"
    profile = cwd / "project-profile.md"
    index = flows_dir / "_index.md"
    specs_root = cwd / ".specs"

    flows_count = (
        sum(1 for p in flows_dir.glob("*.md") if p.name != "_index.md")
        if flows_dir.exists()
        else 0
    )
    screens_count = (
        sum(1 for p in screens_dir.glob("*.md") if p.name != "_index.md")
        if screens_dir.exists()
        else 0
    )
    mockups_count = (
        sum(1 for _ in mockups_dir.glob("*.png")) if mockups_dir.exists() else 0
    )

    schema_ok = False
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            schema_ok = data.get("schemaVersion") == 2
        except Exception:  # pragma: no cover
            schema_ok = False

    return Detected(
        flows_count=flows_count,
        screens_count=screens_count,
        mockups_count=mockups_count,
        has_manifest=manifest.exists(),
        manifest_schema_ok=schema_ok,
        has_project_profile=profile.exists(),
        has_flows_index=index.exists(),
        has_specs_dir=specs_root.exists(),
    )
