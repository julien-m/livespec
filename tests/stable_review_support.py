"""A reviewed project whose spec separates requirements from other sections (feature 089)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.review_support import grounded_response
from validator.semantic.review_api import ingest_feature_review
from validator.semantic.review_files import prepare_feature_review

FEATURE = "001-export"
SPEC = """---
status: Approved
---
# Feature Spec: Export

## Scope

- **In scope:** exports.

## User Scenarios & Testing

```gherkin
Feature: Expiry
  Scenario: Expired export
    Given an export older than 24 hours
    Then it is deleted
```

## Acceptance Criteria

### AC-001

Exports older than 24 hours are absent.

## Functional Requirements

- **FR-001:** Delete exports after 24 hours. **Maps to:** AC-001.

## Edge Cases

- **Clock skew:** use the server clock.

## Quality Engineering

- **Risk:** Medium criticality; Local blast radius.
"""


def review_both(root: Path, max_chars: int | None = None) -> None:
    """Record ready spec and plan reviews of the current sources."""
    for kind in ("spec", "plan"):
        prepared = prepare_feature_review(root, FEATURE, kind, "reviewer/v1", max_chars)
        receipt, _ = ingest_feature_review(
            root, FEATURE, kind, [grounded_response(prepared)], max_chars=max_chars
        )
        assert receipt.ready, receipt.errors


def make_root(tmp_path: Path) -> Path:
    """Write the project and record ready spec and plan reviews."""
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    for name, text in (
        ("constitution.md", "Local execution."),
        ("project.md", "Exports."),
        ("stacks/_default.md", "Python."),
        ("semantic/config.yaml", "review_model: reviewer/v1\n"),
    ):
        (tmp_path / ".specs" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ".specs" / name).write_text(text)
    (feature / "spec.md").write_text(SPEC)
    (feature / "plan.md").write_text("# Plan\nFR-001 AC-001 Delete old exports hourly.\n")
    review_both(tmp_path)
    commit_all(tmp_path)
    return tmp_path


def commit_all(root: Path, message: str = "sources") -> str:
    """Commit every file of the project (initializing git once) and return the commit."""
    if not (root / ".git").exists():
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), *identity, "commit", "-qm", message, "--allow-empty"], check=True
    )
    head = ["git", "-C", str(root), "rev-parse", "HEAD"]
    return subprocess.run(head, check=True, capture_output=True, text=True).stdout.strip()


def edit_spec(root: Path, old: str, new: str) -> None:
    """Replace ``old`` with ``new`` in the spec."""
    spec = root / ".specs/features" / FEATURE / "spec.md"
    text = spec.read_text()
    assert old in text
    spec.write_text(text.replace(old, new))
