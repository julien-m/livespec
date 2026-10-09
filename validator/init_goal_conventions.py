"""Resolve known legacy INIT convention references without mutating their index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# These exact files were emitted by the old bootstrap; other absent refs are errors.
LEGACY_CODE_FILES = frozenset(
    {"general.md", "python.md", "javascript.md", "cli.md", "stack-commands.md"}
)
LEGACY_CODE_PREFIX = "$AIRESOURCES/conventions/code/"


class InitConventionResolutionError(ValueError):
    """Report an INIT source that cannot be read before locking its contract."""


@dataclass(frozen=True)
class InitConventionRoot:
    """Carry the parsed root and optional literal legacy declaration provenance."""

    path: Path | None
    legacy_declaration: str | None = None


@dataclass(frozen=True)
class InitConventionSource:
    """Carry a real readable source and optional original invalid reference."""

    display_path: str
    real_path: Path
    original_path: str | None = None


def resolve_init_root(index_text: str, parsed_root: Path | None) -> InitConventionRoot:
    """Read only the known old literal root syntax, without shell evaluation.

    Args:
        index_text: Existing project routing index.
        parsed_root: Root recognized by the unchanged standard parser.
    Returns:
        Standard root unchanged, or an explicitly sourced legacy literal root.
    """
    if parsed_root is not None:
        return InitConventionRoot(parsed_root)
    # Match only the exact legacy default declaration; never expand shell/env code.
    match = re.search(r"^AIRESOURCES=\$\{AIRESOURCES:-([^}\n]+)\}\s*$", index_text, re.MULTILINE)
    if match is None:
        return InitConventionRoot(None)
    literal = match.group(1)
    if not Path(literal).is_absolute() or "$" in literal or "`" in literal:
        return InitConventionRoot(None)
    return InitConventionRoot(Path(literal), match.group(0).strip())


# @spec FR-003: Resolve legacy init routing readonly
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
def resolve_init_source(
    display_path: str, real_path: Path | None, ai_root: Path | None
) -> InitConventionSource:
    """Preserve existing references or resolve an allowlisted missing legacy file.

    Args:
        display_path: Exact reference from the current routing index.
        real_path: Standard parser resolution, if available.
        ai_root: Explicit root from the index, never a guessed global fallback.
    Returns:
        Existing reference unchanged, or real canonical path with original provenance.
    Raises:
        InitConventionResolutionError: Unknown, unresolved or missing canonical source.
    Side effects:
        None; this checks file existence without changing project/source contents.
    """
    if real_path is not None and real_path.is_file():
        return InitConventionSource(display_path, real_path)
    name = display_path.removeprefix(LEGACY_CODE_PREFIX)
    # Only absent old bootstrap paths may change; valid/custom references stay exact.
    if display_path.startswith(LEGACY_CODE_PREFIX) and name in LEGACY_CODE_FILES and ai_root:
        canonical = ai_root / "code-conventions" / name
        if canonical.is_file():
            return InitConventionSource(str(canonical.resolve()), canonical, display_path)
    raise InitConventionResolutionError(f"init_convention_source_unresolved: {display_path}")
