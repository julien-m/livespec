"""Temporary git projects with reviewed specs for delivery lane tests (feature 086)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner, Result

from validator.cli import app
from validator.semantic.review_contract import validate_review_result
from validator.semantic.review_files import prepare_feature_review, review_receipt_path
from validator.semantic.review_receipts import save_review_receipt

FEATURE = "001-calc"
MODEL = "reviewer-v1"
QE_MEDIUM = "- **Risk:** Medium criticality; Shared blast radius; primary risk Functional."


def spec_text(qe: str | None = QE_MEDIUM) -> str:
    """Return a minimal spec, with a Quality Engineering section when ``qe`` is given."""
    section = f"\n## Quality Engineering\n\n{qe}\n" if qe is not None else ""
    return (
        "# Feature Spec: Calc\n\n- **Status:** Planned\n\n## Acceptance Criteria\n\n"
        "### AC-001\n\nGiven two numbers, add returns their sum.\n\n"
        "## Functional Requirements\n\n- **FR-001:** Provide add. **Maps to:** AC-001.\n"
        f"{section}"
    )


def git(root: Path, *args: str) -> str:
    """Run git in the temporary project and return stdout."""
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


@dataclass
class DeliveryProject:
    """A committed temporary project with one planned feature."""

    root: Path

    @property
    def feature_dir(self) -> Path:
        """Return the feature directory."""
        return self.root / ".specs" / "features" / FEATURE

    def write(self, relative: str, text: str) -> None:
        """Write a project file, creating parents."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run(self, *args: str) -> Result:
        """Invoke the real CLI from the project root."""
        return CliRunner().invoke(app, list(args), catch_exceptions=False)

    def json(self, *args: str) -> tuple[int, dict[str, object]]:
        """Invoke the CLI with ``--json`` and parse stdout."""
        result = self.run(*args, "--json")
        return result.exit_code, json.loads(result.output)

    def review_spec(self) -> Path:
        """Write a complete ready spec review receipt for the current spec."""
        prepared = prepare_feature_review(self.root, FEATURE, "spec", MODEL)
        sections = {s.section_id: s for s in prepared.sections}
        batch = prepared.batches[0]
        conclusions = [
            {
                "requirement_id": r.requirement_id,
                "disposition": "covered",
                "rationale": "Independent judgment.",
                "source_citations": [
                    {"section_id": r.section_ids[0], "excerpt": sections[r.section_ids[0]].text}
                ],
            }
            for r in prepared.requirements
        ]
        raw = json.dumps(
            {
                "batch_id": batch.batch_id,
                "reviewed_section_ids": list(batch.section_ids),
                "conclusions": conclusions,
                "ambiguities": [],
                "extra_scope": [],
                "findings": [],
                "confidence": 5,
            }
        )
        receipt = validate_review_result(prepared, [raw])
        assert receipt.ready, receipt.errors
        return save_review_receipt(review_receipt_path(self.root, FEATURE, "spec"), receipt)


def make_project(tmp_path: Path, spec: str | None = None) -> DeliveryProject:
    """Create and commit a project with one feature and a source module."""
    project = DeliveryProject(tmp_path / "project")
    project.root.mkdir(parents=True)
    project.write(f".specs/features/{FEATURE}/spec.md", spec or spec_text())
    project.write(".specs/constitution.md", "# Constitution\n\nKeep it simple.\n")
    project.write(".specs/project.md", "# Project\n\nA calculator.\n")
    project.write(".specs/stacks/_default.md", "# Stack\n\nPython.\n")
    project.write("calc.py", "def add(a, b):\n    return a + b\n")
    project.write(".gitignore", "__pycache__/\n")
    git(project.root, "init", "-q")
    git(project.root, "config", "user.email", "t@example.invalid")
    git(project.root, "config", "user.name", "t")
    git(project.root, "add", "-A")
    git(project.root, "commit", "-qm", "base")
    return project


def report(
    files: list[str],
    *,
    verdict: str = "PASS",
    blocking: int = 0,
    effort: str = "high",
    failed_check: bool = False,
) -> dict[str, object]:
    """Return a reviewer report covering ``files``."""
    return {
        "schema_version": "1",
        "reviewer": {"agent": "native-reviewer", "model": MODEL, "effort": effort},
        "verdict": verdict,
        "reviewed_files": files,
        "checks": [{"command": "pytest -q", "exit_code": 1 if failed_check else 0}],
        "findings": [
            {"severity": "blocking", "file": files[0], "line": 1, "evidence": "Wrong result."}
            for _ in range(blocking)
        ],
    }
