# LiveSpec traceability anchors
# @spec(FR-001)

# @spec FR-003: validate_behavioral public API
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-003
# @spec FR-004: Kind detection rule
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-004
# @spec FR-005, FR-006, FR-007: PASS/WARNING/FAIL
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-005
# @spec FR-008: Canonical import path
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-008
# @spec FR-009: Stdlib + pinned deps only
# .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-009
"""Behavioral specs grammar v1.0 validator.

Canonical reference: ``system/grammar/behavioral-specs-v1.md``.

Public API
----------

- ``VALIDATION_RESULT`` — enum with values ``PASS``, ``WARNING``, ``FAIL``.
- ``ValidationOutcome`` — frozen dataclass returned by ``validate_behavioral``.
- ``validate_behavioral(path)`` — validates a single flow or screen file.

Kind detection rule (FR-004)
----------------------------

The artefact kind is detected by:

1. **Frontmatter hint first** — if the YAML frontmatter contains a ``kind``
   field whose value is ``"flow"`` or ``"screen"``, that value wins.
2. **Path convention fallback** — otherwise:
   - any path under ``.specs/flows/`` (any depth) → ``flow``;
   - any path under ``.specs/design/screens/`` (any depth) → ``screen``.
3. If neither rule matches → ``VALIDATION_RESULT.FAIL`` with diagnostic
   ``"cannot detect kind: file path is not under .specs/flows/ or
   .specs/design/screens/ and frontmatter has no kind hint"``.

Decision flow
-------------

See ``system/grammar/behavioral-specs-v1.md`` and the State Diagram in
``.specs/features/044-behavioral-grammar-v1-shared/plan.md``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

import frontmatter  # type: ignore[import-untyped]  # Dependency lacks typing metadata in this environment.
import yaml  # type: ignore[import-untyped]  # PyYAML is pinned in-repo, but stub packages are not installed.

# ─── Public enum (FR-003) ────────────────────────────────────────────────────


class VALIDATION_RESULT(str, Enum):  # noqa: UP042 — public API name, str-mixin kept for compat
    """Outcome of running the grammar validator on a single file.

    Three values, byte-compatible with F041's references:
    - ``PASS`` — all mandatory sections present, well-formed, no deviation.
    - ``WARNING`` — all mandatory present and parseable, non-fatal deviation.
    - ``FAIL`` — at least one mandatory absent/unparseable, or file/frontmatter error.
    """

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


# ─── Public dataclass (FR-003) ───────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationOutcome:
    """Validation result for a single behavioural spec file.

    Attributes:
        result: Terminal validator status for the file.
        diagnostics: Human-readable validation messages. Empty on ``PASS``.
        path: Validated file path.
        kind: Detected behavioural artefact kind, if detection succeeded.
    """

    result: VALIDATION_RESULT
    diagnostics: list[str] = field(default_factory=list)  # type: ignore[assignment]  # Pyright overinference on default_factory
    path: Path = Path()
    kind: Literal["flow", "screen"] | None = None


# ─── Frozen module-level constants (Step 2 of plan.md) ───────────────────────

MANDATORY_FLOW_SECTIONS: tuple[str, ...] = (
    "Acteur",
    "Préconditions",
    "Déclencheur",
    "Étapes nominales",
    "Règles métier",
    "Erreurs & exceptions",
    "Side-effects",
    "Postconditions",
)
"""@spec FR-005: Mandatory flow sections — spec.md#fr-005"""

MANDATORY_SCREEN_SECTIONS: tuple[str, ...] = (
    "Acteur",
    "Source d'entrée",
    "Sortie principale",
    "Données affichées",
    "Actions",
    "Validations",
    "États UI",
    "Erreurs",
)
"""@spec FR-005: Mandatory screen sections — spec.md#fr-005"""

OPTIONAL_FLOW_SECTIONS: tuple[str, ...] = ("Notes",)
"""@spec FR-006: Optional flow sections — spec.md#fr-006"""

OPTIONAL_SCREEN_SECTIONS: tuple[str, ...] = ("Side effects locaux", "Notes")
"""@spec FR-006: Optional screen sections — spec.md#fr-006"""

LIVESPEC_FRONTMATTER_FIELDS: tuple[str, ...] = (
    "brainstormSource",
    "brainstormGeneratedAt",
    "specStatus",
)
"""@spec FR-001: LiveSpec frontmatter contract fields — spec.md#fr-001"""


# ─── Internal helpers ────────────────────────────────────────────────────────


def _read_file(path: Path) -> str | None:
    """Return file text, or ``None`` if reading fails.

    Args:
        path: File path to read.

    Returns:
        The decoded UTF-8 file content, or ``None`` when the file cannot be
        read from disk.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str] | str:
    """Parse YAML frontmatter from a Markdown document.

    Args:
        text: Raw Markdown document text.

    Returns:
        A ``(metadata, body)`` tuple on success, or a diagnostic string when
        frontmatter parsing fails.
    """
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        return f"frontmatter unparseable: {exc}"
    except (ValueError, TypeError) as exc:
        return f"frontmatter unparseable: {exc}"
    return dict(post.metadata), post.content


def _detect_kind(path: Path, metadata: dict[str, object]) -> Literal["flow", "screen"] | None:
    """Detect the behavioural artefact kind.

    Args:
        path: File path being validated.
        metadata: Parsed frontmatter metadata.

    Returns:
        The detected kind, preferring a frontmatter ``kind`` hint and falling
        back to the repository path convention.
    """
    hint = metadata.get("kind")
    if isinstance(hint, str):
        norm = hint.strip().lower()
        if norm == "flow":
            return "flow"
        if norm == "screen":
            return "screen"

    parts = path.as_posix()
    if "/.specs/flows/" in parts or parts.startswith(".specs/flows/"):
        return "flow"
    if "/.specs/design/screens/" in parts or parts.startswith(".specs/design/screens/"):
        return "screen"
    return None


# Match second-level Markdown headings of the form ``## Title`` while trimming
# heading-edge whitespace so section comparisons stay exact.
_H2_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)


def _extract_h2_headings(body: str) -> list[str]:
    """Extract ordered H2 heading titles from the Markdown body.

    Args:
        body: Markdown body without the leading YAML frontmatter.

    Returns:
        Ordered H2 heading titles. Headings inside fenced code blocks are
        ignored so embedded fixtures do not affect validator output.
    """
    headings: list[str] = []
    in_fence = False
    fence_re = re.compile(r"^(```|~~~)")
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if fence_re.match(line.lstrip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _H2_HEADING_RE.match(line)
        if match:
            headings.append(match.group("title").strip())
    return headings


def _extract_section_bodies(body: str) -> dict[str, str]:
    """Extract the body content that belongs to each H2 heading.

    Args:
        body: Markdown body without the leading YAML frontmatter.

    Returns:
        A mapping from H2 heading title to the raw body text that follows it up
        to the next H2 heading or the end of the document.
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    in_fence = False
    fence_re = re.compile(r"^(```|~~~)")

    def flush() -> None:
        if current is not None:
            sections[current] = "\n".join(buffer).strip()

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        is_fence = bool(fence_re.match(line.lstrip()))
        if is_fence:
            in_fence = not in_fence
            if current is not None:
                buffer.append(raw_line)
            continue
        if not in_fence:
            match = _H2_HEADING_RE.match(line)
            if match:
                flush()
                current = match.group("title").strip()
                buffer = []
                continue
        if current is not None:
            buffer.append(raw_line)
    flush()
    return sections


def _check_sections(
    headings: list[str],
    section_bodies: dict[str, str],
    mandatory: tuple[str, ...],
    optional: tuple[str, ...],
    path: Path,
) -> tuple[VALIDATION_RESULT, list[str]]:
    """Evaluate section presence, emptiness, and non-fatal deviations.

    Args:
        headings: Ordered H2 headings extracted from the document.
        section_bodies: Raw section body text keyed by heading title.
        mandatory: Required headings for the detected kind.
        optional: Supported optional headings for the detected kind.
        path: Path of the file being validated.

    Returns:
        The terminal validation result together with diagnostics.
    """
    diagnostics: list[str] = []

    # 1. Missing mandatory sections → FAIL
    missing = [name for name in mandatory if name not in section_bodies]
    for name in missing:
        diagnostics.append(f'{path}: mandatory section "{name}" is missing')

    # 2. Present-but-empty mandatory sections → FAIL
    empty = [
        name for name in mandatory if name in section_bodies and not section_bodies[name].strip()
    ]
    for name in empty:
        diagnostics.append(f'{path}: mandatory section "{name}" is present but empty')

    if missing or empty:
        return VALIDATION_RESULT.FAIL, diagnostics

    # 3. Non-fatal deviations → WARNING
    deviations: list[str] = []

    # 3a. Optional sections missing
    for name in optional:
        if name not in section_bodies:
            deviations.append(f'{path}: optional section "{name}" is absent (non-fatal)')

    # 3b. Extra unknown sections
    known = set(mandatory) | set(optional)
    extra = [h for h in headings if h not in known]
    for name in extra:
        deviations.append(f'{path}: unknown extra section "{name}" (non-fatal)')

    # 3c. Wrong order of mandatory sections
    encountered_mandatory_order = [h for h in headings if h in mandatory]
    expected_order = list(mandatory)
    if encountered_mandatory_order != expected_order:
        deviations.append(
            f"{path}: mandatory sections out of order — "
            f"expected {expected_order}, got {encountered_mandatory_order}"
        )

    if deviations:
        return VALIDATION_RESULT.WARNING, deviations

    return VALIDATION_RESULT.PASS, []


# ─── Public entry point (FR-003) ─────────────────────────────────────────────


def validate_behavioral(path: Path) -> ValidationOutcome:
    """Validate a behavioural flow or screen spec against grammar v1.0.

    Args:
        path: Markdown file path to validate.

    Returns:
        The validation outcome for the requested file.
    """
    text = _read_file(path)
    if text is None:
        return ValidationOutcome(
            result=VALIDATION_RESULT.FAIL,
            diagnostics=[f"file not found: {path}"],
            path=path,
            kind=None,
        )

    if not text.strip():
        return ValidationOutcome(
            result=VALIDATION_RESULT.FAIL,
            diagnostics=[f"{path}: file is empty"],
            path=path,
            kind=None,
        )

    parsed = _parse_frontmatter(text)
    if isinstance(parsed, str):
        return ValidationOutcome(
            result=VALIDATION_RESULT.FAIL,
            diagnostics=[f"{path}: {parsed}"],
            path=path,
            kind=None,
        )

    metadata, body = parsed
    kind = _detect_kind(path, metadata)
    if kind is None:
        return ValidationOutcome(
            result=VALIDATION_RESULT.FAIL,
            diagnostics=[
                f"{path}: cannot detect kind: file path is not under "
                ".specs/flows/ or .specs/design/screens/ and frontmatter "
                "has no kind hint"
            ],
            path=path,
            kind=None,
        )

    if kind == "flow":
        mandatory = MANDATORY_FLOW_SECTIONS
        optional = OPTIONAL_FLOW_SECTIONS
    else:
        mandatory = MANDATORY_SCREEN_SECTIONS
        optional = OPTIONAL_SCREEN_SECTIONS

    headings = _extract_h2_headings(body)
    section_bodies = _extract_section_bodies(body)
    result, diagnostics = _check_sections(
        headings=headings,
        section_bodies=section_bodies,
        mandatory=mandatory,
        optional=optional,
        path=path,
    )

    return ValidationOutcome(
        result=result,
        diagnostics=diagnostics,
        path=path,
        kind=kind,
    )


# ─── F045 mode detection (additive — does not affect existing F044 behavior) ─


# @spec FR-001: Mode detection — .specs/features/045-native-behavioral-specs/spec.md#fr-001
# @spec FR-016: Mode-detection unit-tested across 4 branches — spec.md#fr-016
class GenerationMode(str, Enum):  # noqa: UP042 — public API name, str-mixin kept for compat
    """Behavioral artefact generation mode for ``/spec-specify``.

    Three mutually-exclusive values matching F045 spec.md (Story 1/2/4):

    - ``REUSE`` — Mode A — `.specs/flows/<slug>.md` exists, delegate to F042.
    - ``MOCKUP_DERIVED`` — Mode C — readable mockup exists, no flow file.
    - ``NATIVE_INTERVIEW`` — Mode B — nothing exists, run full interview.
    """

    REUSE = "reuse"
    MOCKUP_DERIVED = "mockup-derived"
    NATIVE_INTERVIEW = "native-interview"


# File extensions considered as mockup sources for Mode C detection. Order
# matters — `.pen` is highest-priority per spec.md Edge Cases (multiple
# mockups → `.pen` first, else PNG).
MOCKUP_EXTENSIONS: tuple[str, ...] = ("pen", "png")
"""@spec FR-001: Mockup extensions for Mode C detection — spec.md#fr-001"""


def _flow_path_for(specs_root: Path, slug: str) -> Path:
    """Return the canonical flow path for a slug under ``specs_root``."""
    return specs_root / "flows" / f"{slug}.md"


def _candidate_mockup_paths(specs_root: Path, slug: str) -> list[Path]:
    """List candidate mockup paths for a slug, in priority order.

    Order matches :data:`MOCKUP_EXTENSIONS` — `.pen` first, then `.png`.
    """
    return [specs_root / "design" / "screens" / f"{slug}.{ext}" for ext in MOCKUP_EXTENSIONS]


def _has_readable_mockup(specs_root: Path, slug: str) -> bool:
    """Return ``True`` iff at least one candidate mockup file is non-empty.

    Files of size zero (or unreadable via ``os.stat``) are NOT considered
    readable — Mode C is expected to fall back to Mode B in that case
    (FR-013).
    """
    for path in _candidate_mockup_paths(specs_root, slug):
        try:
            if path.exists() and os.stat(path).st_size > 0:
                return True
        except OSError:
            continue
    return False


def detect_mode(
    slug: str,
    specs_root: Path,
    override: GenerationMode | None = None,
) -> GenerationMode:
    """Detect the F045 generation mode for ``slug`` under ``specs_root``.

    Precedence (FR-001, AC-018): ``override`` (if any) > A (reuse) > C
    (mockup-derived) > B (native-interview).

    Args:
        slug: Feature / artefact slug, e.g. ``"booking"``.
        specs_root: ``.specs`` directory root (typically project root /
            ``.specs``).
        override: Optional caller-provided override. When set, returned
            verbatim — feasibility (e.g. ``MOCKUP_DERIVED`` requires an
            actual mockup file) is the caller's responsibility.

    Returns:
        The selected :class:`GenerationMode`.
    """
    if override is not None:
        return override

    if _flow_path_for(specs_root, slug).exists():
        return GenerationMode.REUSE

    if _has_readable_mockup(specs_root, slug):
        return GenerationMode.MOCKUP_DERIVED

    return GenerationMode.NATIVE_INTERVIEW


# Export the documented public API so downstream imports stay stable even if
# private helpers evolve.
__all__ = [
    "LIVESPEC_FRONTMATTER_FIELDS",
    "MANDATORY_FLOW_SECTIONS",
    "MANDATORY_SCREEN_SECTIONS",
    "MOCKUP_EXTENSIONS",
    "OPTIONAL_FLOW_SECTIONS",
    "OPTIONAL_SCREEN_SECTIONS",
    "VALIDATION_RESULT",
    "GenerationMode",
    "ValidationOutcome",
    "detect_mode",
    "validate_behavioral",
]
