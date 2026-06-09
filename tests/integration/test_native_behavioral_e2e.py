# LiveSpec traceability anchors
# @spec(FR-017)

# @spec FR-017: E2E smoke fixture (no brainstorm, no mockups, all skip → WARNING)
# .specs/features/045-native-behavioral-specs/spec.md#fr-017
"""End-to-end smoke for F045 native behavioral generation."""

from __future__ import annotations

from pathlib import Path

from validator.behavioral_grammar import (
    VALIDATION_RESULT,
    GenerationMode,
    detect_mode,
    validate_behavioral,
)
from validator.native_behavioral import (
    apply_validation_gate,
    run_native_interview,
)


def test_e2e_smoke_no_brainstorm_no_mockups_skip_all(tmp_path: Path) -> None:
    """SC-001 + AC-015: fresh project, all skip, validator returns WARNING."""
    specs_root = tmp_path / ".specs"
    specs_root.mkdir()
    feature_dir = specs_root / "features" / "045-native-behavioral-specs"
    feature_dir.mkdir(parents=True)

    # No brainstorm, no flow file, no mockups.
    assert detect_mode("booking", specs_root) is GenerationMode.NATIVE_INTERVIEW

    artefact = run_native_interview("booking", "flow", specs_root, asker=lambda q: "skip")

    rc = apply_validation_gate(artefact, feature_dir)
    assert rc == 0  # WARNING is not blocking

    canonical = specs_root / "flows" / "booking.md"
    assert canonical.exists()
    outcome = validate_behavioral(canonical)
    assert outcome.result is VALIDATION_RESULT.WARNING
    # Diagnostics must mention the absent optional `Notes` section.
    assert any("Notes" in d for d in outcome.diagnostics)
