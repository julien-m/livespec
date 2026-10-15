"""Plans with release evidence for the feature 090 tests."""

from __future__ import annotations

from pathlib import Path

from tests.stable_review_support import FEATURE

MODEL = "reviewer/v1"
LIVESPEC_ROOT = Path(__file__).resolve().parents[1]

RELEASE_PLAN = """---
title: Plan
spec_ref: spec.md
created: 2026-10-15
---
# Plan

## Summary

Delete expired exports. FR-001 AC-001.

## Implementation Plan

### Step 1 — Purge job

Delete exports older than 24 hours.

### Step 2 — Signed build

Ship the signed purge daemon.

**Evidence class:** release

## Testing Strategy

pytest.

## Risks

None.

```mermaid
flowchart TD
    A --> B
```
"""


def plan_text(steps: str) -> str:
    """A minimal plan whose Implementation Plan section holds ``steps``."""
    return f"# Plan\n\n## Implementation Plan\n\n{steps}\n\n## Testing Strategy\n\npytest.\n"


def write_plan(root: Path, text: str) -> None:
    """Replace the feature plan of the project at ``root``."""
    (root / ".specs/features" / FEATURE / "plan.md").write_text(text)
