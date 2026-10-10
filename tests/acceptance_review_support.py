"""Documentary review inputs for isolated real-run acceptance boundary tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.review_support import grounded_response
from validator.normative_identity import normative_hash
from validator.semantic.acceptance_review import ingest_acceptance_review, prepare_acceptance_review


def add_documentary_acceptance(root: Path, feature: str, local_id: str = "AC-002") -> Path:
    """Add an explicit review obligation without replacing the existing executable contract."""
    directory = root / ".specs/features" / feature
    spec = directory / "spec.md"
    spec.write_text(
        spec.read_text() + f"\n## {local_id}\nCompare the migration documentation.\n"
        "**Evidence:** review\n**Review inputs:** [source](.reviews/doc-inputs.json)\n"
    )
    for name, text in [
        ("constitution.md", "Local tool."),
        ("project.md", "Addition tool."),
        ("stacks/_default.md", "Python."),
        ("semantic/config.yaml", "review_model: reviewer/v1\n"),
    ]:
        path = root / ".specs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (directory / "plan.md").write_text("Implement addition and preserve migration documentation.\n")
    (root / "migration.md").write_text(
        "The old truncation rule was replaced; unrelated contracts stay unchanged.\n"
    )
    refresh_documentary_inputs(root, feature)
    prepared = prepare_acceptance_review(root, feature, "reviewer/v1")
    _, receipt = ingest_acceptance_review(
        root, feature, [grounded_response(prepared)], model="reviewer/v1"
    )
    return receipt


def refresh_documentary_inputs(root: Path, feature: str) -> Path:
    """Record the actual current source inventory before independent transport fixtures run."""
    specs = sorted(
        path.relative_to(root).as_posix() for path in (root / ".specs/features").glob("*/spec.md")
    )
    hashes = {
        name: normative_hash(
            (root / name).read_text(),
            lifecycle_document=True,
        )
        if name == f".specs/features/{feature}/spec.md"
        else hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in specs
    }
    hashes["migration.md"] = hashlib.sha256((root / "migration.md").read_bytes()).hexdigest()
    path = root / ".specs/features" / feature / ".reviews/doc-inputs.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source_paths": ["migration.md"],
                "current_hashes": hashes,
                "feature_spec_paths": specs,
                "identity_policy": "normative-identity-v2",
            }
        )
    )
    return path
