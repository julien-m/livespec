# @spec FR-001: Shared ai-ressources resolution
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-001

"""Shared resolution of the ai-ressources corpus root for a LiveSpec project.

Every validator consumer (AST catalog, corpus manifest, conventions compiler,
R7.3 coherence rule, conventions validity check and ``init --from-code``)
locates ai-ressources through :func:`resolve_ai_resources_root`. The rule only
reads the ``AIRESOURCES`` environment variable and the project's
``.conventions/`` files; it writes nothing and never guesses a location.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from validator.exceptions import AiResourcesResolutionError

AIRESOURCES_ENV_VAR = "AIRESOURCES"
"""Only environment variable naming the ai-ressources clone (set by its ``setup.sh``)."""

MANIFEST_RELATIVE_PATH = Path(".conventions/manifest.yaml")
"""Project manifest whose top-level ``ai_resources_path`` records a root."""

INDEX_RELATIVE_PATH = Path(".conventions/index.md")
"""Project conventions index whose ``$AIRESOURCES`` declaration records a root."""

# Matches the index declaration `` `$AIRESOURCES` = `<path>` `` (backticks around the
# variable optional) and captures the path between the second pair of backticks.
INDEX_DECLARATION_RE = re.compile(r"`?\$AIRESOURCES`?\s*=\s*`([^`]+)`")
"""Declaration form written by ai-ressources ``build-conventions.ts`` in ``index.md``."""

ResolutionSource = Literal["env", "manifest", "index"]
"""Where a resolved root came from."""

_SOURCE_FILES: dict[ResolutionSource, str] = {
    "env": AIRESOURCES_ENV_VAR,
    "manifest": MANIFEST_RELATIVE_PATH.as_posix(),
    "index": INDEX_RELATIVE_PATH.as_posix(),
}


@dataclass(frozen=True)
class ResolvedAiResources:
    """Result of one successful ai-ressources resolution.

    Attributes:
        path: Absolute ai-ressources root directory.
        source: Which input provided the root (``env``, ``manifest`` or ``index``).
    """

    path: Path
    source: ResolutionSource


# @spec FR-001: Shared resolution order and source, FR-002: Dedicated error
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-001
def resolve_ai_resources_root(
    project_root: Path | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> ResolvedAiResources:
    """Resolve the ai-ressources root of a project through the single shared rule.

    Args:
        project_root: Project whose ``.conventions/`` may record a root; ``None`` = env only.
        environ: Environment to read; defaults to ``os.environ`` at call time.

    Returns:
        The absolute root with its source.

    Raises:
        AiResourcesResolutionError: Neither ``AIRESOURCES`` nor an existing recorded directory.
    """
    env_root = _environment_root(os.environ if environ is None else environ)
    # The environment wins: committed `.conventions/` files may record another machine's path.
    if env_root is not None:
        return ResolvedAiResources(path=env_root, source="env")
    if project_root is None:
        raise AiResourcesResolutionError(None, ())
    rejected: list[tuple[Path, str]] = []
    # Manifest before index: the generator writes both and the manifest is the structured record.
    for source, raw in _recorded_values(project_root):
        candidate = _recorded_path(project_root, raw)
        if candidate.is_dir():
            return ResolvedAiResources(path=candidate, source=source)
        rejected.append((candidate, _SOURCE_FILES[source]))
    raise AiResourcesResolutionError(project_root.resolve(), rejected)


def _environment_root(environ: Mapping[str, str]) -> Path | None:
    value = environ.get(AIRESOURCES_ENV_VAR, "").strip()
    if not value:
        return None
    # Explicit operator intent: used as is, without an existence check.
    return (Path.cwd() / Path(value).expanduser()).resolve()


def _recorded_values(project_root: Path) -> list[tuple[ResolutionSource, str]]:
    values: list[tuple[ResolutionSource, str]] = []
    manifest_value = _manifest_value(project_root)
    if manifest_value is not None:
        values.append(("manifest", manifest_value))
    index_value = _index_value(project_root)
    if index_value is not None:
        values.append(("index", index_value))
    return values


def _manifest_value(project_root: Path) -> str | None:
    manifest = project_root / MANIFEST_RELATIVE_PATH
    if not manifest.is_file():
        return None
    try:
        raw: object = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        # A malformed manifest is not a source of recorded path; the index may still resolve.
        return None
    if not isinstance(raw, dict):
        return None
    value: object = raw.get("ai_resources_path")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _index_value(project_root: Path) -> str | None:
    index = project_root / INDEX_RELATIVE_PATH
    if not index.is_file():
        return None
    try:
        text = index.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # An unreadable index records nothing; resolution then reports the explicit error.
        return None
    match = INDEX_DECLARATION_RE.search(text)
    if match is None or not match.group(1).strip():
        return None
    return match.group(1).strip()


def _recorded_path(project_root: Path, raw: str) -> Path:
    # Relative recorded paths are anchored on the project root so hand edits stay deterministic.
    return (project_root / Path(raw).expanduser()).resolve()
