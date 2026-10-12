"""Doctor reuses the full coherence result, including in-progress suppressions (055 FR-004)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from validator.doctor.models import DoctorSeverity
from validator.doctor.scanner import run_doctor


def _implemented_but_unchecked(project: Path) -> Path:
    """An Implemented feature whose roadmap item is unchecked triggers suppressible R1.3."""
    specs = project / ".specs"
    feature = specs / "features" / "001-auth"
    feature.mkdir(parents=True)
    spec = feature / "spec.md"
    spec.write_text("---\nstatus: Implemented\n---\n# Auth\n")
    (specs / "roadmap.md").write_text("- [ ] [Auth](features/001-auth/)\n")
    return spec


def _coherence(project: Path, code: str) -> list:
    return [f for f in run_doctor(project).findings if f.category == "coherence" and f.code == code]


def test_doctor_reports_in_progress_coherence_violation_as_info(tmp_path: Path) -> None:
    _implemented_but_unchecked(tmp_path)

    [finding] = _coherence(tmp_path, "R1.3")

    assert finding.severity == DoctorSeverity.INFO
    assert finding.message.startswith("[in-progress, 0min] ")
    assert finding.feature == "001-auth"


def test_doctor_attributes_settled_coherence_violation_to_its_feature(tmp_path: Path) -> None:
    spec = _implemented_but_unchecked(tmp_path)
    old = time.time() - 2 * 60 * 60
    os.utime(spec, (old, old))

    [finding] = _coherence(tmp_path, "R1.3")

    assert finding.severity != DoctorSeverity.INFO
    assert not finding.message.startswith("[in-progress")
    assert finding.feature == "001-auth"
