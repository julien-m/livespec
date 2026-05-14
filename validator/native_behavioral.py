# @spec FR-003: Mode B native interview generator
# .specs/features/045-native-behavioral-specs/spec.md#fr-003
# @spec FR-004: Mode B screen interview
# .specs/features/045-native-behavioral-specs/spec.md#fr-004
# @spec FR-005: skip / empty → (to fill later)
# .specs/features/045-native-behavioral-specs/spec.md#fr-005
# @spec FR-006: Mode C mockup-derived generator
# .specs/features/045-native-behavioral-specs/spec.md#fr-006
# @spec FR-007: Frontmatter contract for native artefacts
# .specs/features/045-native-behavioral-specs/spec.md#fr-007
# @spec FR-008, FR-009, FR-010: Validator gate
# .specs/features/045-native-behavioral-specs/spec.md#fr-008
# @spec FR-011: Body byte-identical to F041 imports
# .specs/features/045-native-behavioral-specs/spec.md#fr-011
# @spec FR-013: Unreadable mockup → fallback to Mode B
# .specs/features/045-native-behavioral-specs/spec.md#fr-013
"""F045 native behavioral artefact generators (Mode B + Mode C) + validator gate.

This module is the in-process implementation of F045's two new producers:

- :func:`run_native_interview` — Mode B — full 8-question interview that
  emits a behavioral artefact (flow or screen) populated solely from user
  answers, with frozen prompts (no LLM open-ended generation).
- :func:`run_mockup_derived` — Mode C — short 5-question interview for
  non-visual sections; visual sections are populated as
  ``(to fill later — populated from mockup analysis)`` placeholders. The
  stack does not currently include image-decoding or Pencil-decode
  capability, so visual content stays as a placeholder hook (validator
  returns ``WARNING``, never ``FAIL``).
- :func:`apply_validation_gate` — wraps :func:`validate_behavioral` and
  enforces FAIL → discard + ``BLOCKED`` + non-zero exit (FR-009).

All generators emit artefacts that:

- Carry frontmatter ``specStatus: manual`` (Mode B) or
  ``specStatus: manual`` + ``derivedFrom: native-mockups`` (Mode C).
- Have body section structure byte-identical to F041 imports (FR-011) —
  same H2 headings, same count, same canonical order from
  :data:`MANDATORY_FLOW_SECTIONS` / :data:`MANDATORY_SCREEN_SECTIONS`.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import frontmatter  # type: ignore[import-untyped]

from validator.behavioral_grammar import (
    MANDATORY_FLOW_SECTIONS,
    MANDATORY_SCREEN_SECTIONS,
    VALIDATION_RESULT,
    validate_behavioral,
)
from validator.native_behavioral_templates import (
    FLOW_QUESTIONS,
    MOCKUP_DERIVED_QUESTIONS,
    SCREEN_QUESTIONS,
    InterviewQuestion,
)

# ─── Constants ───────────────────────────────────────────────────────────────

PLACEHOLDER_TO_FILL = "(to fill later)"
"""@spec FR-005: Empty/skip placeholder body — spec.md#fr-005"""

PLACEHOLDER_MOCKUP_VISUAL = (
    "(to fill later — populated from mockup analysis)"
)
"""@spec FR-006: Mode C visual-section placeholder — spec.md#fr-006

The stack does not embed an image decoder; this string is the explicit
upgrade hook for a future iteration that wires real mockup analysis.
"""

# Visual sections in a F044 screen artefact — Mode C populates these from
# mockup analysis (or placeholder) instead of asking the user. `Validations`
# and `Erreurs` stay interview-driven because they are the only canonical F044
# screen headings that can carry non-visual rules without inventing new
# sections and breaking F041/F044 structural compatibility.
SCREEN_VISUAL_SECTIONS: tuple[str, ...] = (
    "Données affichées",
    "Actions",
    "États UI",
)


# ─── Data classes ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NativeArtefact:
    """A generated F045 artefact, ready for the validator gate.

    Attributes:
        path: Canonical destination path on disk (where it will land if
            the validator gate accepts it).
        kind: Either ``"flow"`` or ``"screen"``.
        frontmatter: LiveSpec frontmatter dict (will be serialised to YAML).
        body: Markdown body without frontmatter — 8 mandatory H2 sections
            in canonical F044 order, each followed by a non-empty body
            (real answer or :data:`PLACEHOLDER_TO_FILL`).
    """

    path: Path
    kind: Literal["flow", "screen"]
    frontmatter: dict[str, object] = field(default_factory=dict)  # type: ignore[assignment]
    body: str = ""


# ─── Pure renderers (no I/O) ─────────────────────────────────────────────────


def _normalise_answer(raw: str) -> str:
    """Return ``raw`` stripped, or :data:`PLACEHOLDER_TO_FILL` for skip.

    Empty input or the literal token ``skip`` (case-insensitive, trimmed)
    becomes the placeholder. All other input is preserved verbatim
    (trailing whitespace stripped) so the user's wording lands in the
    artefact unchanged.
    """
    text = (raw or "").strip()
    if text == "" or text.lower() == "skip":
        return PLACEHOLDER_TO_FILL
    return text


def _render_body(
    kind: Literal["flow", "screen"],
    slug: str,
    section_bodies: dict[str, str],
) -> str:
    """Render the markdown body for ``kind`` from per-section answers.

    Args:
        kind: Artefact kind — drives mandatory section list and H1 title.
        slug: Slug used in the H1 title.
        section_bodies: Mapping ``section_id`` → body text. Sections not
            present in the mapping are filled with
            :data:`PLACEHOLDER_TO_FILL`.

    Returns:
        Markdown body — ``# H1\\n\\n## section\\n\\nbody`` for each of
        the 8 mandatory sections in canonical F044 order. No trailing
        newline beyond the last paragraph.
    """
    if kind == "flow":
        sections = MANDATORY_FLOW_SECTIONS
        title = f"# Flow — {slug}"
    else:
        sections = MANDATORY_SCREEN_SECTIONS
        title = f"# Écran — {slug}"

    parts: list[str] = [title, ""]
    for section_id in sections:
        body = section_bodies.get(section_id, PLACEHOLDER_TO_FILL).strip()
        if not body:
            body = PLACEHOLDER_TO_FILL
        parts.append(f"## {section_id}")
        parts.append("")
        parts.append(body)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _serialise(artefact: NativeArtefact) -> str:
    """Serialise an artefact to a full file string (frontmatter + body)."""
    post = frontmatter.Post(content=artefact.body, **artefact.frontmatter)  # type: ignore[arg-type]  # frontmatter.Post **kwargs accepts arbitrary metadata; pyright collides with `handler` kwarg
    return frontmatter.dumps(post) + "\n"  # type: ignore[no-any-return]


# ─── Path resolution ─────────────────────────────────────────────────────────


def _canonical_path(
    kind: Literal["flow", "screen"],
    slug: str,
    specs_root: Path,
) -> Path:
    """Return the canonical on-disk destination for a generated artefact."""
    if kind == "flow":
        return specs_root / "flows" / f"{slug}.md"
    return specs_root / "design" / "screens" / f"{slug}.md"


# ─── Mode B — Native interview ───────────────────────────────────────────────


def run_native_interview(
    slug: str,
    kind: Literal["flow", "screen"],
    specs_root: Path,
    *,
    asker: Callable[[InterviewQuestion], str],
) -> NativeArtefact:
    """Run the full 8-question native interview for ``slug``.

    Args:
        slug: Artefact slug.
        kind: Either ``"flow"`` or ``"screen"``.
        specs_root: ``.specs`` directory used to resolve the canonical
            destination path.
        asker: Injected dependency that prompts the user. In production
            this is wired to ``input``; tests inject a deterministic stub.

    Returns:
        A :class:`NativeArtefact` ready for the validator gate. Frontmatter
        carries ``specStatus: manual``; ``brainstormSource`` and
        ``derivedFrom`` are absent (FR-007).
    """
    questions = FLOW_QUESTIONS if kind == "flow" else SCREEN_QUESTIONS

    section_bodies: dict[str, str] = {}
    for question in questions:
        raw = asker(question)
        section_bodies[question.section_id] = _normalise_answer(raw)

    body = _render_body(kind, slug, section_bodies)
    fm: dict[str, object] = {"specStatus": "manual", "kind": kind}
    return NativeArtefact(
        path=_canonical_path(kind, slug, specs_root),
        kind=kind,
        frontmatter=fm,
        body=body,
    )


# ─── Mode C — Mockup-derived ─────────────────────────────────────────────────


def _pick_priority_mockup(mockup_paths: list[Path]) -> Path | None:
    """Return the highest-priority readable mockup path, or ``None``.

    Selection order: `.pen` first, then `.png`. A file with size 0 is
    treated as unreadable and skipped (FR-013 fallback).
    """
    by_ext: dict[str, Path] = {}
    for path in mockup_paths:
        try:
            if not path.exists() or os.stat(path).st_size <= 0:
                continue
        except OSError:
            continue
        by_ext.setdefault(path.suffix.lower().lstrip("."), path)
    for ext in ("pen", "png"):
        if ext in by_ext:
            return by_ext[ext]
    return None


def run_mockup_derived(
    slug: str,
    specs_root: Path,
    *,
    asker: Callable[[InterviewQuestion], str],
    mockup_paths: list[Path],
    log: Callable[[str], None] | None = None,
) -> NativeArtefact:
    """Run the Mode C mockup-derived generator for a screen ``slug``.

    Visual sections (``Données affichées``, ``Actions``, ``États UI``) are
    populated with :data:`PLACEHOLDER_MOCKUP_VISUAL` (no image decoder is
    wired in the current stack — see module docstring). The remaining
    canonical screen sections come from a 5-question interview so answers land
    under F044-approved headings instead of being silently discarded.

    Args:
        slug: Screen slug.
        specs_root: ``.specs`` root directory.
        asker: Injected interview prompt callable.
        mockup_paths: Candidate mockup file paths in priority order.
        log: Optional structured logger; defaults to writing to stderr.

    Returns:
        A :class:`NativeArtefact` with ``derivedFrom: native-mockups`` in
        frontmatter, OR (when no readable mockup is found) the result of
        :func:`run_native_interview` — without ``derivedFrom`` (FR-013).
    """
    emit: Callable[[str], None] = log or (lambda msg: print(msg, file=sys.stderr))

    chosen = _pick_priority_mockup(mockup_paths)
    if chosen is None:
        emit("mockup unreadable — falling back to native interview")
        return run_native_interview(
            slug=slug, kind="screen", specs_root=specs_root, asker=asker
        )

    # Log additional mockups that were ignored, for traceability.
    for path in mockup_paths:
        if path != chosen and path.exists():
            emit(f"additional mockup ignored: {path}")

    # Run non-visual interview (≤ 5 questions, AC-007).
    section_bodies: dict[str, str] = {}
    for question in MOCKUP_DERIVED_QUESTIONS:
        raw = asker(question)
        section_bodies[question.section_id] = _normalise_answer(raw)

    # Visual sections → placeholder (upgrade hook for future decoder).
    for section_id in SCREEN_VISUAL_SECTIONS:
        section_bodies.setdefault(section_id, PLACEHOLDER_MOCKUP_VISUAL)

    body = _render_body("screen", slug, section_bodies)
    fm: dict[str, object] = {
        "specStatus": "manual",
        "kind": "screen",
        "derivedFrom": "native-mockups",
    }
    return NativeArtefact(
        path=_canonical_path("screen", slug, specs_root),
        kind="screen",
        frontmatter=fm,
        body=body,
    )


# ─── Validator gate (FR-008, FR-009, FR-010) ─────────────────────────────────


def apply_validation_gate(
    artefact: NativeArtefact,
    feature_dir: Path,
    *,
    log: Callable[[str], None] | None = None,
) -> int:
    """Validate ``artefact`` and write or block per FR-008/9/10.

    Workflow:

    1. Write ``artefact`` (frontmatter + body) to a sibling tmp path.
    2. Call :func:`validate_behavioral` on the tmp file.
    3. Emit one structured log line per artefact (FR-008).
    4. Branch:
       - PASS → ``os.replace`` tmp → canonical, return 0, no extra log.
       - WARNING → ``os.replace`` tmp → canonical, log every diagnostic,
         return 0.
       - FAIL → ``unlink`` tmp, write ``feature_dir / "error.md"`` with
         verbatim diagnostics, print literal ``BLOCKED`` to stdout,
         return 1.

    Args:
        artefact: Generated artefact to validate.
        feature_dir: Feature directory under ``.specs/features/045-…``
            where ``error.md`` is written on FAIL.
        log: Optional structured logger; defaults to writing to stderr.

    Returns:
        Process-style exit code — ``0`` on PASS / WARNING, ``1`` on FAIL.
    """
    emit: Callable[[str], None] = log or (lambda msg: print(msg, file=sys.stderr))

    canonical = artefact.path
    canonical.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = canonical.with_suffix(canonical.suffix + ".tmp")
    tmp_path.write_text(_serialise(artefact), encoding="utf-8")

    outcome = validate_behavioral(tmp_path)

    log_line = json.dumps(
        {
            "event": "validate_behavioral",
            "path": str(canonical),
            "result": outcome.result.value,
        },
        ensure_ascii=False,
    )
    emit(log_line)

    if outcome.result == VALIDATION_RESULT.PASS:
        os.replace(tmp_path, canonical)
        return 0

    if outcome.result == VALIDATION_RESULT.WARNING:
        os.replace(tmp_path, canonical)
        for diagnostic in outcome.diagnostics:
            emit(diagnostic)
        return 0

    # FAIL — discard, write error.md, BLOCKED, exit non-zero.
    with contextlib.suppress(FileNotFoundError):
        tmp_path.unlink()

    feature_dir.mkdir(parents=True, exist_ok=True)
    error_path = feature_dir / "error.md"
    error_body = "# F045 validator gate — FAIL\n\n"
    error_body += f"Artefact path: `{canonical}`\n\n"
    error_body += "## Diagnostics\n\n"
    for diagnostic in outcome.diagnostics:
        error_body += f"- {diagnostic}\n"
    error_path.write_text(error_body, encoding="utf-8")

    print("BLOCKED", flush=True)
    return 1


__all__ = [
    "PLACEHOLDER_MOCKUP_VISUAL",
    "PLACEHOLDER_TO_FILL",
    "SCREEN_VISUAL_SECTIONS",
    "NativeArtefact",
    "apply_validation_gate",
    "run_mockup_derived",
    "run_native_interview",
]
