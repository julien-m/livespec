"""Discovery and retargeting of LiveSpec-owned links under ``.agent-sync.local``.

A LiveSpec-owned link is a symlink directly under ``.agent-sync.local/skills/``
or ``.agent-sync.local/rules/`` whose link text points inside the ``.agent-sync/``
directory of a LiveSpec root. Classification uses the link text; a broken link is
owned only when its root is the one recorded in ``.specs/.livespec-path`` (trusted
provenance, e.g. a deleted runtime). Project-owned files, directories and foreign
symlinks are never touched.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .home import is_livespec_root
from .models import LIVESPEC_PATH_RELPATH, LinkReport

LINK_DIRECTORIES = ("skills", "rules")
AGENT_SYNC = ".agent-sync"


@dataclass(frozen=True)
class OwnedLink:
    """One LiveSpec-owned link and the LiveSpec root its text points into."""

    path: Path
    text: str
    root: Path
    relative: str

    def target_in(self, runtime_root: Path) -> Path:
        """Return the same ``.agent-sync``-relative path inside ``runtime_root``."""
        return runtime_root / AGENT_SYNC / self.relative


@dataclass(frozen=True)
class LinkUpdate:
    """Planned change for one owned link: ``retarget``, ``missing`` or ``unchanged``."""

    link: OwnedLink
    target: Path
    action: str


def recorded_root(project: Path) -> Path | None:
    """Return the resolved LiveSpec root recorded in ``.specs/.livespec-path``, if any."""
    path_file = project / LIVESPEC_PATH_RELPATH
    try:
        text = path_file.read_text(encoding="utf-8").strip() if path_file.is_file() else ""
        candidate = Path(text).expanduser()
        # Only an absolute recorded root is trusted; relative or unreadable values are ignored.
        return candidate.resolve() if text and candidate.is_absolute() else None
    except (OSError, UnicodeError, ValueError, RuntimeError):
        # Malformed provenance means "no trusted root": broken links then stay untouched.
        return None


# @spec FR-006: Owned-link provenance
#   — .specs/features/083-pinned-runtime-isolation/spec.md#fr-006
def _classify(entry: Path, trusted_root: Path | None) -> OwnedLink | None:
    text = os.readlink(entry)
    absolute = Path(os.path.normpath(os.path.join(entry.parent.resolve(), text)))
    parts = absolute.parts
    if AGENT_SYNC not in parts:
        return None
    index = parts.index(AGENT_SYNC)
    root, relative = Path(*parts[:index]), "/".join(parts[index + 1 :])
    if not relative:
        return None
    if root.exists():
        # An existing root must really be a LiveSpec root.
        if not is_livespec_root(root.resolve()):
            return None
        root = root.resolve()
    elif trusted_root is None or root.resolve() != trusted_root:
        # A vanished root is LiveSpec-owned only with trusted provenance: the root the
        # project recorded in .specs/.livespec-path. Any other broken link stays foreign.
        return None
    return OwnedLink(path=entry, text=text, root=root, relative=relative)


def owned_links(project: Path) -> list[OwnedLink]:
    """List the LiveSpec-owned links of ``project`` sorted by path.

    Args:
        project: Project root.

    Returns:
        Owned links found directly under the skills and rules directories.
    """
    links: list[OwnedLink] = []
    trusted_root = recorded_root(project)
    for name in LINK_DIRECTORIES:
        directory = project / ".agent-sync.local" / name
        if not directory.is_dir():
            continue
        for entry in sorted(directory.iterdir()):
            link = _classify(entry, trusted_root) if entry.is_symlink() else None
            if link is not None:
                links.append(link)
    return links


def plan_link_updates(project: Path, runtime_root: Path) -> list[LinkUpdate]:
    """Compute, without writing, how each owned link maps onto ``runtime_root``.

    Args:
        project: Project root.
        runtime_root: Selected snapshot or dev checkout root.

    Returns:
        One planned update per owned link.
    """
    updates: list[LinkUpdate] = []
    for link in owned_links(project):
        target = link.target_in(runtime_root)
        if not os.path.lexists(target):
            action = "missing"
        elif link.text == str(target):
            action = "unchanged"
        else:
            action = "retarget"
        updates.append(LinkUpdate(link=link, target=target, action=action))
    return updates


def replace_symlink(path: Path, target: Path | str) -> None:
    """Atomically point the symlink ``path`` at ``target`` (sibling link + rename)."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.is_symlink():
        temporary.unlink()
    # Create beside the link, then rename over it: readers see the old or new link only.
    os.symlink(str(target), temporary)
    os.replace(temporary, path)


# @spec FR-006: Link retargeting — .specs/features/083-pinned-runtime-isolation/spec.md#fr-006
def apply_link_updates(project: Path, updates: list[LinkUpdate]) -> LinkReport:
    """Retarget planned links; missing targets stay unchanged and are reported.

    Args:
        project: Project root used for relative report paths.
        updates: Plan from ``plan_link_updates``.

    Returns:
        Project-relative paths grouped by outcome.
    """
    grouped: dict[str, list[str]] = {"retarget": [], "missing": [], "unchanged": []}
    for update in updates:
        if update.action == "retarget":
            replace_symlink(update.link.path, update.target)
        grouped[update.action].append(update.link.path.relative_to(project).as_posix())
    return LinkReport(
        retargeted=tuple(grouped["retarget"]),
        missing=tuple(grouped["missing"]),
        unchanged=tuple(grouped["unchanged"]),
    )
