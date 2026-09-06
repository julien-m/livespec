"""Feature 077 active spec UI declarations cannot disappear from closure signals."""

from pathlib import Path

import pytest

from validator.penflow_closure import PenflowClosureError, require_penflow_closure
from validator.visual_gate import detect_visual_feature


def _write_spec(root: Path, content: str, *, nonvisual: bool = False) -> None:
    spec = root / ".specs/features/001-feature/spec.md"
    spec.parent.mkdir(parents=True)
    prefix = "---\nvisual: false\n---\n" if nonvisual else ""
    spec.write_text(prefix + "# Feature\n\n" + content)


# @spec AC-007: classify active UI source declarations
# — .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#ac-007
@pytest.mark.parametrize(
    "content",
    [
        "## Screens\n\n| Screen | Route |\n|---|---|\n| Checkout | /checkout |\n",
        "## Penflow Contract\n\n- semantic_id: checkout.submit\n",
        "## Screens\n\nThe checkout page displays validation errors.\n",
        "## Screens\n\n### Checkout\n\n- Confirm purchase\n",
    ],
)
def test_real_ui_sections_are_visual_without_artifacts(tmp_path: Path, content: str) -> None:
    _write_spec(tmp_path, content)
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.classification == "VISUAL"
    assert result.signals.s7_spec_ui_sections is True
    assert result.signals.to_dict()["s7_spec_ui_sections"] is True


@pytest.mark.parametrize(
    "content",
    [
        "## Screens\n",
        "## Screens\n\nN/A\n",
        "## Penflow Contract\n\nNot applicable.\n",
        "## Screens\n\n| Screen | Route |\n|---|---|\n",
        "## Screens\n\n| Screen |\n|---|\n| N/A |\n",
        "```markdown\n## Screens\n\n- Checkout\n```\n",
        "> ## Screens\n> - Checkout\n",
        "## Screens\n\n```text\n- Example only\n```\n",
        "## Screens\n\n<!-- Example: Checkout -->\n",
        "## Screens\n\nN/A\n\n## Architecture\n\nActual CLI behavior\n",
    ],
)
def test_templates_and_nonapplicable_sections_are_not_ui(tmp_path: Path, content: str) -> None:
    _write_spec(tmp_path, content)
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.classification == "NON_VISUAL"
    assert result.signals.s7_spec_ui_sections is False


def test_explicit_false_preserves_active_ui_signal_for_closure(tmp_path: Path) -> None:
    _write_spec(tmp_path, "## Screens\n\n- Checkout\n", nonvisual=True)
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.classification == "NON_VISUAL"
    assert result.signals.s1_spec_explicit_false is True
    assert result.signals.s7_spec_ui_sections is True
    assert result.signals.strong_count == 1
    with pytest.raises(PenflowClosureError, match="visual_authority_conflict"):
        require_penflow_closure(tmp_path, "001-feature")


@pytest.mark.parametrize(
    "example",
    [
        "```yaml\nvisual: false\n```",
        "> visual: false",
        "<!-- visual: false -->",
        "The example is `visual: false`.",
    ],
)
def test_false_example_cannot_override_authoritative_true(tmp_path: Path, example: str) -> None:
    _write_spec(tmp_path, "## Notes\n\n" + example)
    spec = tmp_path / ".specs/features/001-feature/spec.md"
    spec.write_text("---\nvisual: true\nstatus: Implemented\n---\n" + spec.read_text())
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.signals.s1_spec_marker is True
    assert result.signals.s1_spec_explicit_false is False
    with pytest.raises(PenflowClosureError):
        require_penflow_closure(tmp_path, "001-feature")


@pytest.mark.parametrize(
    "content",
    [
        "```yaml\nvisual: true\n```",
        "```markdown\n[visual]\n```",
        "> [surface=web]",
        "<!-- [visual] -->",
        "The example uses `[visual]`.",
    ],
)
def test_example_marker_does_not_create_visual_authority(tmp_path: Path, content: str) -> None:
    _write_spec(tmp_path, "## Notes\n\n" + content)
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.classification == "NON_VISUAL"
    assert result.signals.s1_spec_marker is False


@pytest.mark.parametrize(
    "tag,explicit_false",
    [
        ("[visual]", False),
        ("[surface=web]", False),
        ("[visual:false]", True),
    ],
)
def test_actual_portable_inline_marker_is_preserved(
    tmp_path: Path, tag: str, explicit_false: bool
) -> None:
    _write_spec(tmp_path, "Feature annotation: " + tag)
    result = detect_visual_feature(project_root=tmp_path, feature_slug="001-feature")
    assert result.signals.s1_spec_marker is True
    assert result.signals.s1_spec_explicit_false is explicit_false
