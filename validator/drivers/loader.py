# LiveSpec traceability anchors
# @spec(FR-008)

"""YAML loader for driver manifests."""

# @spec FR-008: Manifest loading validates YAML shape and schema before use.
# @spec AC-014: Malformed driver files are logged and skipped without aborting discovery.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]  # PyYAML is a runtime dependency here but the repo does not ship its mypy stubs.
from pydantic import ValidationError

from .schemas import DriverManifest

log = logging.getLogger(__name__)


def load_manifest(path: Path, *, is_custom: bool = False) -> DriverManifest | None:
    """Load and validate a driver manifest.

    Args:
        path: YAML manifest path to read from disk.
        is_custom: Whether the manifest came from the project override directory.

    Returns:
        The validated manifest, or ``None`` when the file cannot be used.

    Side Effects:
        Emits warning logs when the file cannot be read or validated.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("Skipping driver %s: cannot read file (%s)", path.name, exc)
        return None

    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        log.warning("Skipping malformed driver: %s (%s)", path.name, exc)
        return None

    if not isinstance(raw, dict):
        log.warning("Skipping malformed driver: %s (root is not a mapping)", path.name)
        return None

    raw.setdefault("name", path.stem)  # type: ignore[union-attr]  # isinstance guard above

    try:
        manifest = DriverManifest.model_validate(raw)
    except ValidationError as exc:
        log.warning("Skipping malformed driver: %s (%s)", path.name, exc)
        return None

    return manifest.model_copy(update={"source_path": path, "is_custom": is_custom})
