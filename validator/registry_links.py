"""Registry-link validation for the LiveSpec visual gate.

# @spec FR-001: Canonical no-copy registry — feature TBD (visual-gate-fix cycle)
# @spec FR-002: Symlink-default with manifest fallback — feature TBD (visual-gate-fix cycle)
# @spec FR-003: Runtime-capture misplacement detector — feature TBD (visual-gate-fix cycle)

The module exposes the deterministic rules used by ``visual_gate`` to decide
whether the on-disk layout under ``.specs/design/`` and
``.specs/features/<slug>/`` honours the canonical structure:

* ``.specs/design/screens/<slug>/<screen>.png`` is the **mockup registry**
  (design artefacts produced by Pencil / Mockup Factory). Runtime captures
  are forbidden here.
* ``.specs/design/baselines/<slug>/<target>/<screen>.png`` is the **approved
  runtime baseline registry**. Promoted captures live here.
* Feature-local references at ``.specs/features/<slug>/baselines/<screen>.png``
  must be relative POSIX symlinks pointing into the baseline registry, OR a
  manifest reference (``baseline.manifest.yml`` / ``manifest.json``) when the
  underlying filesystem cannot create symlinks. The default mode is
  ``symlink``; ``manifest`` is the explicit fallback.

The module is pure / IO-only on the local filesystem. It does not import the
typer CLI or run subprocesses. This keeps the surface unit-testable with
``tmp_path`` fixtures.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

DESIGN_REGISTRY_DIR = Path(".specs") / "design"
SCREENS_DIRNAME = "screens"
BASELINES_DIRNAME = "baselines"
LINK_MODE_FILE = Path(".specs") / "design" / ".link-mode"
FEATURE_BASELINES_REL = Path("baselines")
MANIFEST_FILENAME = "baseline.manifest.yml"
MANIFEST_JSON_FILENAME = "manifest.json"

LinkMode = Literal["symlink", "manifest"]
EntryKind = Literal["symlink", "ref"]
ViolationKind = Literal[
    "physical_copy_where_link_required",
    "broken_symlink",
    "manifest_missing_registry_path",
    "manifest_sha_mismatch",
    "runtime_under_design_screens",
    "manifest_unreadable",
    "registry_path_missing",
    "feature_local_path_missing",
]


@dataclass(frozen=True)
class LinkViolation:
    """One actionable violation of the canonical link/manifest contract."""

    kind: ViolationKind
    feature_slug: str
    target: str | None
    screen: str | None
    path: Path
    message: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""
        return {
            "kind": self.kind,
            "feature_slug": self.feature_slug,
            "target": self.target,
            "screen": self.screen,
            "path": str(self.path),
            "message": self.message,
        }


@dataclass(frozen=True)
class ManifestEntry:
    """One row of the canonical baseline manifest."""

    screen: str
    kind: EntryKind
    registry_path: Path
    feature_local_path: Path | None
    sha256: str | None
    approved_at: str | None = None

    @classmethod
    def from_mapping(cls, raw: dict[str, object]) -> ManifestEntry:
        """Build an entry from a raw mapping; tolerant of partial input."""
        registry_path = Path(str(raw.get("registry_path", "")))
        local_raw = raw.get("feature_local_path")
        local_path = Path(str(local_raw)) if isinstance(local_raw, str) else None
        kind_raw = str(raw.get("kind", "ref")).lower()
        kind: EntryKind = "symlink" if kind_raw == "symlink" else "ref"
        sha = raw.get("sha256")
        sha_str = str(sha) if isinstance(sha, str) else None
        approved = raw.get("approved_at")
        approved_str = str(approved) if isinstance(approved, str) else None
        return cls(
            screen=str(raw.get("screen", "")),
            kind=kind,
            registry_path=registry_path,
            feature_local_path=local_path,
            sha256=sha_str,
            approved_at=approved_str,
        )


@dataclass(frozen=True)
class ManifestStatus:
    """Outcome of reading a baseline manifest."""

    path: Path
    found: bool
    feature_slug: str
    target: str | None
    entries: list[ManifestEntry] = field(default_factory=lambda: cast(list[ManifestEntry], []))
    parse_error: str | None = None


def detect_link_capability(project_root: Path) -> LinkMode:
    """Detect whether the current filesystem supports relative POSIX symlinks.

    Probes by creating a dummy target file and a relative symlink under
    ``.specs/design/.probe/`` (created best-effort, removed after the test).
    Falls back to ``"manifest"`` on any ``OSError`` (Windows without
    SeCreateSymbolicLinkPrivilege, restricted FUSE mounts, etc.).
    """
    probe_dir = project_root / DESIGN_REGISTRY_DIR / ".probe"
    target = probe_dir / "target.txt"
    link = probe_dir / "link.txt"
    is_link = False
    try:
        try:
            probe_dir.mkdir(parents=True, exist_ok=True)
            target.write_text("probe", encoding="utf-8")
            if link.is_symlink() or link.exists():
                link.unlink()
            try:
                os.symlink("target.txt", link)
            except OSError:
                return "manifest"
            is_link = link.is_symlink()
            return "symlink" if is_link else "manifest"
        except OSError:
            return "manifest"
    finally:
        # Always remove probe artefacts — even when the symlink attempt
        # raises, we must not leave `.specs/design/.probe/target.txt`
        # behind for downstream `find` / git status churn.
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
        except OSError:
            pass
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass
        try:
            probe_dir.rmdir()
        except OSError:
            pass


def write_link_mode(project_root: Path, mode: LinkMode) -> Path:
    """Persist the detected link mode under ``.specs/design/.link-mode``."""
    target = project_root / LINK_MODE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(mode + "\n", encoding="utf-8")
    return target


def read_link_mode(project_root: Path) -> LinkMode | None:
    """Read the cached link mode, returning ``None`` when absent or invalid."""
    target = project_root / LINK_MODE_FILE
    if not target.exists():
        return None
    raw = target.read_text(encoding="utf-8").strip().lower()
    if raw == "symlink":
        return "symlink"
    if raw == "manifest":
        return "manifest"
    return None


def expected_registry_baseline_path(
    *, feature_slug: str, target: str, screen: str
) -> Path:
    """Return the canonical registry path for an approved baseline."""
    safe_screen = screen if screen.endswith(".png") else f"{screen}.png"
    return (
        DESIGN_REGISTRY_DIR
        / BASELINES_DIRNAME
        / feature_slug
        / target
        / safe_screen
    )


def expected_registry_mockup_path(*, feature_slug: str, screen: str) -> Path:
    """Return the canonical registry path for a design / mockup screenshot."""
    safe_screen = screen if screen.endswith(".png") else f"{screen}.png"
    return DESIGN_REGISTRY_DIR / SCREENS_DIRNAME / feature_slug / safe_screen


def expected_feature_local_path(
    *, feature_slug: str, screen: str, project_root: Path | None = None
) -> Path:
    """Return the feature-local symlink path for a baseline screen."""
    safe_screen = screen if screen.endswith(".png") else f"{screen}.png"
    rel = (
        Path(".specs")
        / "features"
        / feature_slug
        / FEATURE_BASELINES_REL
        / safe_screen
    )
    if project_root is None:
        return rel
    return project_root / rel


def sha256_of(path: Path) -> str:
    """Return the lowercase hex sha256 of a file's bytes."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_runtime_capture_misplaced(
    *, candidate: Path, registry_baselines_dir: Path
) -> bool:
    """Return True when ``candidate`` lives under ``.specs/design/screens/`` AND
    its sha256 matches at least one baseline under ``registry_baselines_dir``.

    The check is intentionally conservative: only *hash collisions* between
    the design/mockup tree and the runtime baseline registry are treated as
    misplacement, since that is the exact failure mode observed in the
    test app (scenario-b-gatefix-20260522002450).
    """
    if not candidate.exists() or not candidate.is_file():
        return False
    candidate_resolved = candidate.resolve()
    # Constrain the check to artefacts that actually live under the design
    # screens registry; runtime captures elsewhere are out of scope here.
    if "/.specs/design/screens/" not in str(candidate_resolved) + "/":
        parts = candidate_resolved.parts
        if not (
            ".specs" in parts
            and "design" in parts
            and "screens" in parts
        ):
            return False
    if not registry_baselines_dir.exists():
        return False
    candidate_hash = sha256_of(candidate_resolved)
    for baseline in registry_baselines_dir.rglob("*.png"):
        try:
            if sha256_of(baseline) == candidate_hash:
                return True
        except OSError:
            continue
    return False


def check_link(
    *,
    feature_local_path: Path,
    expected_registry_path: Path,
    project_root: Path,
    feature_slug: str,
    target: str | None,
    screen: str | None,
) -> LinkViolation | None:
    """Validate that ``feature_local_path`` honours the symlink-default rule.

    Returns ``None`` when the relation is valid; otherwise an actionable
    ``LinkViolation``.

    Validity matrix:
      * ``feature_local_path`` is a relative symlink whose resolved real path
        equals ``project_root / expected_registry_path`` → OK.
      * ``feature_local_path`` does not exist → registry-only mode is OK
        ONLY if the manifest entry kind is ``ref`` (checked by
        :func:`validate_manifest_entry`, not here).
      * ``feature_local_path`` is a *plain file* (not a symlink) → violation
        ``physical_copy_where_link_required``.
      * ``feature_local_path`` is a broken symlink → violation
        ``broken_symlink``.
    """
    if not feature_local_path.exists() and not feature_local_path.is_symlink():
        return None
    if feature_local_path.is_symlink():
        try:
            real = feature_local_path.resolve(strict=True)
        except (FileNotFoundError, OSError):
            return LinkViolation(
                kind="broken_symlink",
                feature_slug=feature_slug,
                target=target,
                screen=screen,
                path=feature_local_path,
                message=(
                    f"Symlink {feature_local_path} does not resolve to a "
                    f"file. Expected target: {expected_registry_path}."
                ),
            )
        expected_real = (project_root / expected_registry_path).resolve()
        if real != expected_real:
            return LinkViolation(
                kind="broken_symlink",
                feature_slug=feature_slug,
                target=target,
                screen=screen,
                path=feature_local_path,
                message=(
                    f"Symlink {feature_local_path} resolves to {real} but "
                    f"expected {expected_real}."
                ),
            )
        return None
    # Plain file: forbidden under symlink mode.
    return LinkViolation(
        kind="physical_copy_where_link_required",
        feature_slug=feature_slug,
        target=target,
        screen=screen,
        path=feature_local_path,
        message=(
            f"{feature_local_path} is a plain file. Expected a relative "
            f"symlink to {expected_registry_path} (or a manifest ref entry "
            f"with kind=ref). See `livespec visual-gate cleanup --dry-run`."
        ),
    )


def validate_manifest(
    *,
    manifest_path: Path,
    project_root: Path,
    feature_slug: str,
    target: str | None,
) -> tuple[ManifestStatus, list[LinkViolation]]:
    """Read and validate the canonical baseline manifest.

    Accepts either YAML or JSON depending on the filename; both are parsed
    via the stdlib JSON loader when ``manifest_path`` ends in ``.json``, and
    via ``yaml.safe_load`` when it ends in ``.yml`` / ``.yaml``.
    """
    if not manifest_path.exists():
        return (
            ManifestStatus(
                path=manifest_path,
                found=False,
                feature_slug=feature_slug,
                target=target,
            ),
            [],
        )
    raw_text = manifest_path.read_text(encoding="utf-8")
    import yaml  # type: ignore[import-untyped]  # local import keeps the module import-light

    payload: object
    try:
        if manifest_path.suffix.lower() == ".json":
            payload = json.loads(raw_text)
        else:
            payload = yaml.safe_load(raw_text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        return (
            ManifestStatus(
                path=manifest_path,
                found=True,
                feature_slug=feature_slug,
                target=target,
                parse_error=str(exc),
            ),
            [
                LinkViolation(
                    kind="manifest_unreadable",
                    feature_slug=feature_slug,
                    target=target,
                    screen=None,
                    path=manifest_path,
                    message=f"Manifest unreadable: {exc}",
                )
            ],
        )
    if not isinstance(payload, dict):
        return (
            ManifestStatus(
                path=manifest_path,
                found=True,
                feature_slug=feature_slug,
                target=target,
                parse_error="manifest root is not a mapping",
            ),
            [
                LinkViolation(
                    kind="manifest_unreadable",
                    feature_slug=feature_slug,
                    target=target,
                    screen=None,
                    path=manifest_path,
                    message="Manifest root is not a mapping.",
                )
            ],
        )
    payload_dict = cast(dict[str, Any], payload)
    entries_raw_obj: Any = payload_dict.get("entries", [])
    entries: list[ManifestEntry] = []
    if isinstance(entries_raw_obj, list):
        entries_list = cast(list[Any], entries_raw_obj)
        for raw in entries_list:
            if isinstance(raw, dict):
                entries.append(ManifestEntry.from_mapping(cast(dict[str, Any], raw)))
    resolved_target = (
        target
        if target is not None
        else str(payload_dict.get("target") or "")
    )
    status = ManifestStatus(
        path=manifest_path,
        found=True,
        feature_slug=feature_slug,
        target=resolved_target,
        entries=entries,
    )
    violations = list(_iter_manifest_violations(status, project_root))
    return status, violations


def _iter_manifest_violations(
    status: ManifestStatus, project_root: Path
) -> Iterator[LinkViolation]:
    for entry in status.entries:
        if not entry.registry_path or str(entry.registry_path) in ("", "."):
            yield LinkViolation(
                kind="manifest_missing_registry_path",
                feature_slug=status.feature_slug,
                target=status.target,
                screen=entry.screen,
                path=status.path,
                message=(
                    f"Manifest entry '{entry.screen}' has no registry_path."
                ),
            )
            continue
        registry_abs = (project_root / entry.registry_path).resolve()
        if not registry_abs.exists():
            yield LinkViolation(
                kind="registry_path_missing",
                feature_slug=status.feature_slug,
                target=status.target,
                screen=entry.screen,
                path=registry_abs,
                message=(
                    f"Registry baseline missing for screen '{entry.screen}': "
                    f"{registry_abs}."
                ),
            )
            continue
        if entry.sha256:
            try:
                actual = sha256_of(registry_abs)
            except OSError as exc:
                yield LinkViolation(
                    kind="manifest_unreadable",
                    feature_slug=status.feature_slug,
                    target=status.target,
                    screen=entry.screen,
                    path=registry_abs,
                    message=f"Cannot hash registry baseline: {exc}",
                )
                continue
            if actual.lower() != entry.sha256.lower():
                yield LinkViolation(
                    kind="manifest_sha_mismatch",
                    feature_slug=status.feature_slug,
                    target=status.target,
                    screen=entry.screen,
                    path=registry_abs,
                    message=(
                        f"sha256 mismatch for screen '{entry.screen}': "
                        f"manifest={entry.sha256[:12]}…, actual="
                        f"{actual[:12]}…."
                    ),
                )
        if entry.kind == "symlink":
            if entry.feature_local_path is None:
                yield LinkViolation(
                    kind="feature_local_path_missing",
                    feature_slug=status.feature_slug,
                    target=status.target,
                    screen=entry.screen,
                    path=status.path,
                    message=(
                        f"Manifest entry '{entry.screen}' has kind=symlink "
                        f"but no feature_local_path."
                    ),
                )
                continue
            local_abs = project_root / entry.feature_local_path
            violation = check_link(
                feature_local_path=local_abs,
                expected_registry_path=entry.registry_path,
                project_root=project_root,
                feature_slug=status.feature_slug,
                target=status.target,
                screen=entry.screen,
            )
            if violation is not None:
                yield violation


def find_runtime_misplaced_under_design_screens(
    *, project_root: Path, feature_slug: str
) -> list[Path]:
    """List every ``*.png`` under ``.specs/design/screens/`` whose sha256
    collides with at least one baseline owned by ``feature_slug``.

    Covers BOTH canonical layouts so the same gate works on:
    * Canonical: ``.specs/design/screens/<slug>/<screen>.png``.
    * Legacy flat: ``.specs/design/screens/<screen>.png`` (the layout of
      scenario-b-gatefix-20260522002450 and other pre-visual-gate apps).

    Baseline comparison sources include both the approved baseline registry
    AND the feature-local baselines so legacy projects without a registry
    still surface circular comparisons.
    """
    # Source selection: prefer the nested slug dir when present so PNGs that
    # belong to *other* features cannot bleed into this slug's misplacement
    # report. Fallback to the legacy flat root only when the slug-scoped dir
    # is absent, and in that case we scan ONLY direct *.png children (not
    # recursive) to avoid pulling sibling-slug nested dirs.
    nested = project_root / DESIGN_REGISTRY_DIR / SCREENS_DIRNAME / feature_slug
    flat = project_root / DESIGN_REGISTRY_DIR / SCREENS_DIRNAME
    use_nested = nested.exists()
    if not use_nested and not flat.exists():
        return []

    baseline_sources: list[Path] = []
    registry_baselines = (
        project_root / DESIGN_REGISTRY_DIR / BASELINES_DIRNAME / feature_slug
    )
    if registry_baselines.exists():
        baseline_sources.append(registry_baselines)
    feature_local_baselines = (
        project_root / ".specs" / "features" / feature_slug / "baselines"
    )
    if feature_local_baselines.exists():
        baseline_sources.append(feature_local_baselines)
    if not baseline_sources:
        return []

    baseline_hashes: set[str] = set()
    for source in baseline_sources:
        for baseline in source.rglob("*.png"):
            if baseline.is_symlink():
                # Symlinked baselines are the canonical case — the underlying
                # file is in the registry; including it would double-count.
                continue
            try:
                baseline_hashes.add(sha256_of(baseline))
            except OSError:
                continue

    misplaced: list[Path] = []
    seen: set[Path] = set()
    candidates: Iterator[Path]
    if use_nested:
        candidates = nested.rglob("*.png")
    else:
        # Legacy flat layout: only direct *.png children at the screens root.
        # Going recursive here would scan sibling slug directories and falsely
        # attribute their PNGs to this feature.
        candidates = (p for p in flat.iterdir() if p.is_file() and p.suffix == ".png")
    for candidate in candidates:
        if candidate in seen:
            continue
        if "_quarantine" in candidate.parts:
            continue
        try:
            if sha256_of(candidate) in baseline_hashes:
                misplaced.append(candidate)
                seen.add(candidate)
        except OSError:
            continue
    return misplaced


__all__ = [
    "BASELINES_DIRNAME",
    "DESIGN_REGISTRY_DIR",
    "LINK_MODE_FILE",
    "LinkMode",
    "LinkViolation",
    "MANIFEST_FILENAME",
    "MANIFEST_JSON_FILENAME",
    "ManifestEntry",
    "ManifestStatus",
    "SCREENS_DIRNAME",
    "ViolationKind",
    "check_link",
    "detect_link_capability",
    "expected_feature_local_path",
    "expected_registry_baseline_path",
    "expected_registry_mockup_path",
    "find_runtime_misplaced_under_design_screens",
    "is_runtime_capture_misplaced",
    "read_link_mode",
    "sha256_of",
    "validate_manifest",
    "write_link_mode",
]
