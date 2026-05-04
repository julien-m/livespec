"""Feature slug identity resolution.

Spec anchors (Chantier 4 / Feature 013 — see
``.specs/features/013-state-model-identity-resolution/spec.md``):

- @spec FR-001: Single ``resolve_feature_slug`` helper.
- @spec FR-002: Pre-side-effect resolution.
- @spec FR-009: Reject literal placeholder.

This module is the **single source of truth** for converting a user-supplied
feature description (or an existing slug) into a validated, deterministic
``feature_slug`` of the form ``NNN-kebab-case-name``. All ``/spec.*`` commands
that need a slug — and especially every code path that creates side-effects
keyed on the slug (directory creation, ``livespec pipeline init``, subagent
dispatch) — MUST call :func:`resolve_feature_slug` first.

The literal placeholder ``NNN-feature-name`` is explicitly rejected (it appears
in command markdown as a template variable and must never propagate to runtime).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# @spec FR-002: Canonical slug regex — spec.md#fr-002
SLUG_REGEX = re.compile(r"^\d{3}-[a-z0-9]+(-[a-z0-9]+)*$")

# Literal placeholder used in command markdown as a template variable.
# It MUST never appear as a resolved slug.
PLACEHOLDER_LITERAL = "NNN-feature-name"

_KEBAB_SAFE = re.compile(r"[^a-z0-9]+")
_MAX_SLUG_NAME_LEN = 60


class IdentityResolutionError(ValueError):
    """Raised when a feature slug cannot be resolved or fails validation.

    The ``BLOCKED`` line emitted by callers should follow the canonical
    ``BLOCKED at step <N> - state_invalid - <reason>`` format defined in
    ``system/anti-drift-block.md``.
    """


@dataclass(frozen=True)
class FeatureSlug:
    """A validated feature identifier.

    Attributes:
        nnn: Zero-padded 3-digit number (e.g. ``"013"``).
        name: kebab-case slug (e.g. ``"state-model-identity-resolution"``).
        full: Concatenated ``NNN-name`` form (e.g. ``"013-state-model-identity-resolution"``).
    """

    nnn: str
    name: str
    full: str

    def __str__(self) -> str:  # pragma: no cover — trivial
        return self.full


def _slugify(text: str) -> str:
    """Convert free text to kebab-case, trimmed to ``_MAX_SLUG_NAME_LEN``."""
    lowered = text.lower().strip()
    kebab = _KEBAB_SAFE.sub("-", lowered).strip("-")
    return kebab[:_MAX_SLUG_NAME_LEN].rstrip("-")


def _next_nnn(specs_root: Path) -> str:
    """Return the next available 3-digit NNN by scanning ``.specs/features/``.

    NOTE: this is a non-atomic scan; concurrent ``/spec.specify`` runs can
    collide. Atomic reservation is the responsibility of Chantier 3
    (Feature 015 — Global Write Locks & Atomic NNN Reservation), which wraps
    this helper with a ``mkdir``-based reservation. Callers requiring atomicity
    must use that wrapper instead of calling :func:`_next_nnn` directly.
    """
    features_dir = specs_root / "features"
    if not features_dir.is_dir():
        return "001"

    max_nnn = 0
    for entry in features_dir.iterdir():
        if not entry.is_dir():
            continue
        match = re.match(r"^(\d{3})-", entry.name)
        if match:
            max_nnn = max(max_nnn, int(match.group(1)))
    return f"{max_nnn + 1:03d}"


def parse_slug(value: str) -> FeatureSlug:
    """Parse and validate an existing slug string.

    Args:
        value: The slug to parse, e.g. ``"013-state-model-identity-resolution"``.

    Returns:
        A :class:`FeatureSlug` if ``value`` is a valid slug.

    Raises:
        IdentityResolutionError: If ``value`` is the placeholder literal,
            empty, or fails the canonical regex.
    """
    if value == PLACEHOLDER_LITERAL:
        raise IdentityResolutionError(
            f"feature_slug not resolved (got literal placeholder: {value!r})"
        )
    if not value or not SLUG_REGEX.match(value):
        raise IdentityResolutionError(
            f"feature_slug fails canonical regex {SLUG_REGEX.pattern!r} (got: {value!r})"
        )
    nnn, _, name = value.partition("-")
    return FeatureSlug(nnn=nnn, name=name, full=value)


def resolve_feature_slug(
    description_or_slug: str,
    specs_root: Path | None = None,
) -> FeatureSlug:
    """Resolve a user-supplied input to a validated :class:`FeatureSlug`.

    Resolution priority:

    1. If ``description_or_slug`` already matches the canonical slug regex,
       it is returned as-is (no NNN allocation).
    2. Otherwise, ``description_or_slug`` is treated as a free-text feature
       description: the next available NNN is allocated by scanning
       ``specs_root/features/``, the description is slugified, and the two
       are joined.

    Args:
        description_or_slug: Either an existing ``NNN-name`` slug or a
            free-text feature description.
        specs_root: Root of the ``.specs/`` directory. When omitted, the
            current working directory's ``.specs/`` is used. When the
            input is already a valid slug, this argument is unused.

    Returns:
        A :class:`FeatureSlug` instance.

    Raises:
        IdentityResolutionError: If the input is empty, is the placeholder
            literal, or yields an empty slugified name.
    """
    if not description_or_slug or not description_or_slug.strip():
        raise IdentityResolutionError("feature description must be non-empty")

    candidate = description_or_slug.strip()

    # @spec FR-009: Reject placeholder literal — spec.md#fr-009
    if candidate == PLACEHOLDER_LITERAL:
        raise IdentityResolutionError(
            f"feature_slug not resolved (got literal placeholder: {candidate!r})"
        )

    # Path 1: already a valid slug
    if SLUG_REGEX.match(candidate):
        return parse_slug(candidate)

    # Path 2: free-text description → allocate NNN + slugify
    root = specs_root if specs_root is not None else Path.cwd() / ".specs"
    name = _slugify(candidate)
    if not name:
        raise IdentityResolutionError(
            f"feature description yields empty slug after slugify (got: {candidate!r})"
        )
    nnn = _next_nnn(root)
    full = f"{nnn}-{name}"
    return FeatureSlug(nnn=nnn, name=name, full=full)


def assert_resolved(value: str) -> None:
    """Assert that ``value`` is a fully resolved slug, raise otherwise.

    Convenience guard for code paths that receive a slug from an external
    source (subagent payload, ``pipeline.md``, CLI arg) and must refuse to
    proceed with an unresolved placeholder.

    Raises:
        IdentityResolutionError: If ``value`` fails :func:`parse_slug`.
    """
    parse_slug(value)
