"""Render project-local convention routing for generation and refresh."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from sys import maxsize

import yaml


def render_manifest(
    project_name: str, sources: Mapping[str, list[str]], resources: Path | None
) -> str:
    """Serialize the source paths by domain, with the metadata used by refresh."""
    manifest: dict[str, object] = {
        "generated": datetime.now(UTC).date(),
        "project": project_name,
        "domains": {domain: {"sources": paths} for domain, paths in sources.items()},
    }
    if resources is not None:
        manifest["ai_resources_path"] = str(resources)
    # Keep machine-local paths on one line for shell convention loaders.
    return yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=maxsize)
