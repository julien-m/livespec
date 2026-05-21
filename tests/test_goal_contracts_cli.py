"""CLI tests for `livespec goal`.

# @spec FR-008, FR-009, FR-010
#   — .specs/features/052-deterministic-command-goal-contracts/spec.md
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from validator.run_artifact import GitState, RunArtifact

EXPECTATIONS = """\
---
command: spec-demo
contract_version: "1.0"
last_reviewed: 2026-05-21
---

# Expectations — /spec-demo

## 1. Purpose
Demo command.
## 2. Preconditions
- `.specs/` exists.
## 3. Observable Signals
- "done"
## 4. Filesystem Effects
- none.
## 5. Git Effects
- none.
## 6. Produced Artifacts
- none.
## 7. Exit Codes
| 0 | success |
## 8. Outcome Matrix
- success.
## 9. Runtime Profile
- <1s.
## 10. Post-run Checks
- [ ] ok.
## 11. Troubleshooting
- rerun.
## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "done"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output
```
$ /spec-demo
> done
```
- line a
- line b
- line c

### Files Produced
- a
- b
- c

### Aligned / Drift / Missing
- aligned
- drift
- missing

### Runtime Profile
- cold
- warm
- worst

### Edge Cases
- missing
- bad output
- crash

### Post-run Actions
- success
- drift
- blocked
"""

SKILL = """\
# /spec-demo

## Definition of Done (Command-Level)

- [ ] Output contains `done`
- [ ] No traceback was emitted
"""


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validator.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".specs" / "expectations").mkdir(parents=True)
    (project / ".specs" / ".runs").mkdir()
    (project / ".specs" / "expectations" / "spec-demo.md").write_text(
        EXPECTATIONS,
        encoding="utf-8",
    )
    return project


def _write_artifact(project: Path, stdout: str) -> Path:
    artifact = RunArtifact(
        command="spec-demo",
        timestamp="2026-05-21T10:00:00Z",
        flags=["--auto"],
        stdout=stdout,
        stderr="",
        exit_code=0,
        duration_ms=10,
        cwd=str(project),
        git_state_before=GitState(),
        git_state_after=GitState(),
        fs_observed=[],
    )
    return artifact.write(project / ".specs" / ".runs")


def test_goal_render_json_outputs_hash_and_canonical_payload(tmp_path: Path) -> None:
    project = _project(tmp_path)

    result = _run(
        [
            "goal",
            "render",
            "demo",
            "--feature",
            "001-demo",
            "--flags",
            "--auto --strict",
            "--json",
        ],
        cwd=project,
    )

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["command"] == "spec-demo"
    assert len(data["hash"]) == 64
    assert data["canonical"]["normalized_flags"] == ["--auto", "--strict"]
    assert "Goal hash:" in data["objective"]


def test_goal_verify_success_uses_expectations_gate(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_artifact(project, "done")

    result = _run(["goal", "verify", "demo", "--feature", "001-demo"], cwd=project)

    assert result.returncode == 0
    assert "outcome=success" in result.stdout


def test_goal_verify_drift_exits_one(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _write_artifact(project, "not yet")

    result = _run(["goal", "verify", "demo", "--feature", "001-demo"], cwd=project)

    assert result.returncode == 1
    assert "outcome=drift" in result.stdout


def test_goal_verify_missing_artifact_exits_two(tmp_path: Path) -> None:
    project = _project(tmp_path)

    result = _run(["goal", "verify", "demo", "--feature", "001-demo"], cwd=project)

    assert result.returncode == 2
    assert "outcome=blocked" in result.stdout


def test_goal_verify_missing_expectations_json_exits_two(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specs").mkdir(parents=True)

    result = _run(["goal", "verify", "missing", "--json"], cwd=project)

    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["outcome"] == "blocked"
    assert data["expectations"] is None
