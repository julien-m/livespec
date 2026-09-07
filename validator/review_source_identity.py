"""Recheck prepared source bytes at gate consumption, including lifecycle-only metadata."""

from __future__ import annotations

import hashlib
from pathlib import Path

from validator.normative_identity import normative_hash
from validator.semantic.review_context import PreparedReview


def prepared_sources_current(
    prepared: PreparedReview,
    feature_dir: Path,
    constitution_path: Path,
) -> bool:
    """A prepared object cannot hide later changes in its source files."""
    root = feature_dir.parents[2] if feature_dir.parent.name == "features" else feature_dir.parent
    if "semantic_config" in prepared.dependencies:
        config = root / ".specs/semantic/config.yaml"
        try:
            raw = config.read_bytes() if config.exists() else b""
        except OSError:
            return False
        if hashlib.sha256(raw).hexdigest() != prepared.dependencies["semantic_config"]:
            return False
    canonical = {
        "spec": feature_dir / "spec.md",
        "plan": feature_dir / "plan.md",
        "constitution": constitution_path,
        "stack": root / ".specs/stacks/_default.md",
        "project": root / ".specs/project.md",
    }
    for source in prepared.source_hashes:
        sections = [section for section in prepared.sections if section.source == source]
        if not sections:
            return False
        role = sections[0].role
        path = canonical.get(role, root / source)
        try:
            current = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError):
            return False
        original = "".join(section.text for section in sections)
        lifecycle = role in ("spec", "plan")
        if normative_hash(current, lifecycle_document=lifecycle) != normative_hash(
            original,
            lifecycle_document=lifecycle,
        ):
            return False
    return prepared.feature == feature_dir.name
