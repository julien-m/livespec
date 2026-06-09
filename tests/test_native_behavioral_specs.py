# LiveSpec traceability anchors
# @spec(FR-016)

# @spec FR-016: Mode-detection unit tests for 4 branches
# .specs/features/045-native-behavioral-specs/spec.md#fr-016
# @spec FR-017: E2E smoke (in companion integration file)
# .specs/features/045-native-behavioral-specs/spec.md#fr-017
"""Unit tests for F045 native behavioral generators + validator gate.

Maps every AC of `.specs/features/045-native-behavioral-specs/spec.md`
to at least one test row.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]
import pytest

from validator.behavioral_grammar import (
    GenerationMode,
    detect_mode,
)
from validator.native_behavioral import (
    PLACEHOLDER_TO_FILL,
    SCREEN_VISUAL_SECTIONS,
    NativeArtefact,
    apply_validation_gate,
    run_mockup_derived,
    run_native_interview,
)
from validator.native_behavioral_templates import (
    FLOW_QUESTIONS,
    MOCKUP_DERIVED_QUESTIONS,
    SCREEN_QUESTIONS,
    InterviewQuestion,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def specs_root(tmp_path: Path) -> Path:
    root = tmp_path / ".specs"
    root.mkdir()
    return root


@pytest.fixture
def feature_dir(specs_root: Path) -> Path:
    fd = specs_root / "features" / "045-native-behavioral-specs"
    fd.mkdir(parents=True)
    return fd


def _const_asker(answer: str) -> Callable[[InterviewQuestion], str]:
    return lambda q: answer


def _scripted_asker(
    answers: dict[str, str],
    seen: list[str] | None = None,
) -> Callable[[InterviewQuestion], str]:
    def asker(q: InterviewQuestion) -> str:
        if seen is not None:
            seen.append(q.section_id)
        return answers.get(q.section_id, "skip")

    return asker


# ─── detect_mode (FR-001, FR-016, AC-001/2/3/16/18/20) ───────────────────────


def test_detect_mode_reuse_when_flow_exists(specs_root: Path) -> None:
    flow = specs_root / "flows" / "foo.md"
    flow.parent.mkdir(parents=True)
    flow.write_text("---\nspecStatus: fresh\n---\n# Flow\n")
    assert detect_mode("foo", specs_root) is GenerationMode.REUSE


def test_detect_mode_mockup_derived_when_png_exists(specs_root: Path) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG\r\n")  # nonzero
    assert detect_mode("foo", specs_root) is GenerationMode.MOCKUP_DERIVED


def test_detect_mode_mockup_derived_when_pen_exists(specs_root: Path) -> None:
    pen = specs_root / "design" / "screens" / "foo.pen"
    pen.parent.mkdir(parents=True)
    pen.write_bytes(b"PENCIL")
    assert detect_mode("foo", specs_root) is GenerationMode.MOCKUP_DERIVED


def test_detect_mode_native_when_nothing_exists(specs_root: Path) -> None:
    assert detect_mode("foo", specs_root) is GenerationMode.NATIVE_INTERVIEW


def test_detect_mode_native_when_mockup_zero_bytes(specs_root: Path) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"")  # zero-byte
    assert detect_mode("foo", specs_root) is GenerationMode.NATIVE_INTERVIEW


def test_detect_mode_override_native_wins_over_existing_flow(
    specs_root: Path,
) -> None:
    flow = specs_root / "flows" / "foo.md"
    flow.parent.mkdir(parents=True)
    flow.write_text("---\nspecStatus: fresh\n---\n# Flow\n")
    assert (
        detect_mode("foo", specs_root, override=GenerationMode.NATIVE_INTERVIEW)
        is GenerationMode.NATIVE_INTERVIEW
    )


# ─── Mode B interview (FR-003, FR-004, FR-005, AC-004/5/6) ───────────────────


def test_native_interview_8_questions_canonical_order_flow(
    specs_root: Path,
) -> None:
    seen: list[str] = []
    asker = _scripted_asker({}, seen=seen)
    run_native_interview("foo", "flow", specs_root, asker=asker)
    assert seen == [q.section_id for q in FLOW_QUESTIONS]
    assert len(seen) == 8


def test_native_interview_8_questions_canonical_order_screen(
    specs_root: Path,
) -> None:
    seen: list[str] = []
    asker = _scripted_asker({}, seen=seen)
    run_native_interview("foo", "screen", specs_root, asker=asker)
    assert seen == [q.section_id for q in SCREEN_QUESTIONS]
    assert len(seen) == 8


def test_skip_becomes_to_fill_later(specs_root: Path) -> None:
    asker = _scripted_asker({"Acteur": "skip", "Préconditions": "real value"})
    artefact = run_native_interview("foo", "flow", specs_root, asker=asker)
    assert "## Acteur\n\n(to fill later)" in artefact.body
    assert "## Préconditions\n\nreal value" in artefact.body


def test_empty_answer_becomes_to_fill_later(specs_root: Path) -> None:
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker(""))
    # All 8 sections should contain placeholder.
    assert artefact.body.count(PLACEHOLDER_TO_FILL) == 8


# ─── Frontmatter (FR-007, AC-008/9) ──────────────────────────────────────────


def test_native_frontmatter_specStatus_manual_no_brainstormSource(
    specs_root: Path,
) -> None:
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker("body"))
    assert artefact.frontmatter.get("specStatus") == "manual"
    assert "brainstormSource" not in artefact.frontmatter
    assert "derivedFrom" not in artefact.frontmatter


def test_mockup_derived_frontmatter_has_derivedFrom_native_mockups(
    specs_root: Path,
) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG")
    artefact = run_mockup_derived(
        "foo",
        specs_root,
        asker=_const_asker("body"),
        mockup_paths=[png],
    )
    assert artefact.frontmatter.get("derivedFrom") == "native-mockups"
    assert artefact.frontmatter.get("specStatus") == "manual"
    assert "brainstormSource" not in artefact.frontmatter


# ─── Mode C ≤5 questions (AC-007) ────────────────────────────────────────────


def test_mockup_derived_max_5_questions(specs_root: Path) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG")
    seen: list[str] = []
    run_mockup_derived(
        "foo",
        specs_root,
        asker=_scripted_asker({}, seen=seen),
        mockup_paths=[png],
    )
    assert len(seen) <= 5
    assert len(seen) == len(MOCKUP_DERIVED_QUESTIONS)
    # Visual sections must NOT have been asked.
    for visual in SCREEN_VISUAL_SECTIONS:
        assert visual not in seen


def test_mockup_derived_non_visual_answers_are_preserved(
    specs_root: Path,
) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"\x89PNG")
    artefact = run_mockup_derived(
        "foo",
        specs_root,
        asker=_scripted_asker(
            {
                "Acteur": "admin",
                "Source d'entrée": "dashboard",
                "Sortie principale": "details",
                "Validations": "amount must be positive",
                "Erreurs": "emit audit event on failure",
            }
        ),
        mockup_paths=[png],
    )
    assert "## Validations\n\namount must be positive" in artefact.body
    assert "## Erreurs\n\nemit audit event on failure" in artefact.body


def test_mockup_zero_bytes_falls_back_to_modeb_no_derivedFrom(
    specs_root: Path,
) -> None:
    png = specs_root / "design" / "screens" / "foo.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"")  # 0 bytes — unreadable
    logged: list[str] = []
    artefact = run_mockup_derived(
        "foo",
        specs_root,
        asker=_const_asker("body"),
        mockup_paths=[png],
        log=logged.append,
    )
    assert "derivedFrom" not in artefact.frontmatter
    assert any("falling back" in m for m in logged)
    # 8 questions asked (full Mode B), not 5.
    # We can verify by checking the body has all 8 mandatory sections.
    for section in (
        "Acteur",
        "Source d'entrée",
        "Sortie principale",
        "Données affichées",
        "Actions",
        "Validations",
        "États UI",
        "Erreurs",
    ):
        assert f"## {section}" in artefact.body


# ─── Validator gate (FR-008/9/10, AC-010/11/12) ──────────────────────────────


def test_validator_gate_PASS_writes_silently(
    specs_root: Path, feature_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker("body content"))
    # Add Notes optional section to body to suppress WARNING about it.
    artefact = NativeArtefact(
        path=artefact.path,
        kind=artefact.kind,
        frontmatter=artefact.frontmatter,
        body=artefact.body.rstrip() + "\n\n## Notes\n\nN/A\n",
    )
    rc = apply_validation_gate(artefact, feature_dir)
    assert rc == 0
    assert artefact.path.exists()
    captured = capsys.readouterr()
    # Only the structured log line should appear, no diagnostic body lines.
    assert '"result": "PASS"' in captured.err


def test_validator_gate_WARNING_writes_and_logs(
    specs_root: Path, feature_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker("skip"))
    rc = apply_validation_gate(artefact, feature_dir)
    assert rc == 0
    assert artefact.path.exists()
    captured = capsys.readouterr()
    assert '"result": "WARNING"' in captured.err
    # At least one diagnostic line beyond the JSON log.
    assert "Notes" in captured.err  # diagnostic about absent optional section


def test_validator_gate_FAIL_discards_and_blocks(
    specs_root: Path, feature_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Build a flow body missing `## Postconditions` deliberately.
    bad_body = (
        "# Flow — foo\n\n"
        "## Acteur\n\nx\n\n"
        "## Préconditions\n\nx\n\n"
        "## Déclencheur\n\nx\n\n"
        "## Étapes nominales\n\nx\n\n"
        "## Règles métier\n\nx\n\n"
        "## Erreurs & exceptions\n\nx\n\n"
        "## Side-effects\n\nx\n"
    )
    canonical = specs_root / "flows" / "foo.md"
    artefact = NativeArtefact(
        path=canonical,
        kind="flow",
        frontmatter={"specStatus": "manual", "kind": "flow"},
        body=bad_body,
    )
    rc = apply_validation_gate(artefact, feature_dir)
    assert rc == 1
    assert not canonical.exists()
    assert not canonical.with_suffix(".md.tmp").exists()
    assert (feature_dir / "error.md").exists()
    captured = capsys.readouterr()
    assert "BLOCKED" in captured.out


def test_validator_invoked_per_artefact_log_line(
    specs_root: Path, feature_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker("skip"))
    apply_validation_gate(artefact, feature_dir)
    err = capsys.readouterr().err
    # Exactly one structured log line per artefact.
    assert err.count('"event": "validate_behavioral"') == 1


# ─── Body byte-equivalence to F041 import (FR-011, AC-013) ───────────────────


def test_body_byte_equivalent_to_f041_import(specs_root: Path) -> None:
    """Section structure (headings, count, order) matches F041 imports.

    F041 imports use the same `## <section>` headings in canonical F044
    order. We extract H2 headings from a Mode B body and assert they
    equal `MANDATORY_FLOW_SECTIONS` exactly.
    """
    artefact = run_native_interview("foo", "flow", specs_root, asker=_const_asker("body content"))
    headings = [line[3:].strip() for line in artefact.body.splitlines() if line.startswith("## ")]
    from validator.behavioral_grammar import MANDATORY_FLOW_SECTIONS

    assert tuple(headings) == MANDATORY_FLOW_SECTIONS


# ─── --force / specStatus: manual guard (FR-014, AC-017) ─────────────────────


def test_specStatus_manual_target_protected(specs_root: Path) -> None:
    """Producer-side: a manual file's frontmatter is detectable.

    The actual `--force` flag handling lives in the slash-command Step 4.5
    (markdown). This test verifies the producer leaves frontmatter
    introspectable so Step 4.5 can implement the guard cheaply.
    """
    target = specs_root / "flows" / "foo.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        "---\nspecStatus: manual\nkind: flow\n---\n# Flow\n"
        "## Acteur\nx\n## Préconditions\nx\n## Déclencheur\nx\n"
        "## Étapes nominales\nx\n## Règles métier\nx\n"
        "## Erreurs & exceptions\nx\n## Side-effects\nx\n"
        "## Postconditions\nx\n"
    )
    parsed = frontmatter.load(target)
    assert parsed.metadata.get("specStatus") == "manual"


# ─── --from-mockups impossible-mode block (FR-015, AC-019) ───────────────────


def test_from_mockups_with_no_mockup_falls_back_in_module(
    specs_root: Path,
) -> None:
    """Module-level: ``run_mockup_derived`` with no readable mockup falls
    back to Mode B with no `derivedFrom`. The slash-command Step 4.5 is
    the layer that converts an *explicit* `--from-mockups` flag into a
    BLOCKED exit; the underlying generator stays additive (FR-013).
    """
    artefact = run_mockup_derived(
        "foo",
        specs_root,
        asker=_const_asker("x"),
        mockup_paths=[],
    )
    assert "derivedFrom" not in artefact.frontmatter
