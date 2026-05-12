"""End-to-end tests for `livespec verify-output` and `livespec run` CLIs.

# @spec FR-006, FR-007 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

MINIMAL = """\
---
command: demo
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.demo

## 1. Purpose
demo.
## 2. Preconditions
- none.
## 3. Observable Signals
- "marker"
## 4. Filesystem Effects
- none.
## 5. Git Effects
- none.
## 6. Produced Artifacts
- none.
## 7. Exit Codes
| 0 | OK |
## 8. Outcome Matrix
- success.
## 9. Runtime Profile
- 1s.
## 10. Post-run Checks
- [ ] ok.
## 11. Troubleshooting
- _none_.
## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "marker"
  must_not:
    - contains: "Traceback"
```

## 13. Demo Session

### Live Console Output
```
$ demo
> marker
```
- step a
- step b
- step c

### Files Produced
- a.txt
- b.txt
- c.txt

### Aligned / Drift / Missing
- aligned: marker present.
- drift: marker absent.
- missing: command never ran.

### Runtime Profile (scenarios)
- cold: 1s
- warm: <1s
- worst: 2s

### Edge Cases
- empty: noop.
- crash: handled.
- unicode: ok.

### Post-run Actions
- success: done.
- drift: re-run.
- blocked: fix preconditions.
"""


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # The CLI is exercised through the real Python entry point so these tests
    # validate stdout/stderr and exit-code behavior end to end.
    return subprocess.run(
        [sys.executable, "-m", "validator.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Set up a project with .specs/ + a builtin expectations file."""
    project_root = tmp_path / "proj"
    (project_root / ".specs").mkdir(parents=True)
    (project_root / ".specs" / ".runs").mkdir(parents=True)
    # The CLI resolves the LiveSpec checkout via the module's parent.
    # We rely on the real checkout under /Users/julienm/projects/livespec
    # and override via .specs/expectations/<X>.md when needed.
    (project_root / ".specs" / "expectations").mkdir()
    (project_root / ".specs" / "expectations" / "demo.md").write_text(
        MINIMAL, encoding="utf-8"
    )
    return project_root


def test_run_wrap_creates_artifact(project: Path):
    # Use sh -c to keep portable.
    result = _run(
        ["run", "wrap", "demo", "--cwd", str(project), "--", "sh", "-c", "echo marker"],
        cwd=project,
    )
    assert result.returncode == 0
    runs = list((project / ".specs" / ".runs").glob("demo-*.json"))
    assert len(runs) == 1
    data = json.loads(runs[0].read_text(encoding="utf-8"))
    assert data["command"] == "demo"
    assert data["exit_code"] == 0
    assert "marker" in data["stdout"]


def test_verify_output_success(project: Path):
    # 1. Wrap a passing command.
    _run(
        ["run", "wrap", "demo", "--cwd", str(project), "--", "sh", "-c", "echo marker"],
        cwd=project,
    )
    # 2. Verify.
    result = _run(["verify-output", "demo"], cwd=project)
    assert result.returncode == 0
    assert "success" in result.stdout


def test_verify_output_drift(project: Path):
    # Run command that exits 0 but lacks the marker.
    _run(
        ["run", "wrap", "demo", "--cwd", str(project), "--", "sh", "-c", "echo other"],
        cwd=project,
    )
    result = _run(["verify-output", "demo"], cwd=project)
    assert result.returncode == 1
    assert "drift" in result.stdout


def test_verify_output_blocked_no_artifact(project: Path):
    result = _run(["verify-output", "demo"], cwd=project)
    assert result.returncode == 2
    assert "blocked" in result.stdout


def test_verify_output_json_output(project: Path):
    _run(
        ["run", "wrap", "demo", "--cwd", str(project), "--", "sh", "-c", "echo marker"],
        cwd=project,
    )
    result = _run(["verify-output", "demo", "--json"], cwd=project)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["outcome"] == "success"
    assert data["exit_code"] == 0
    assert isinstance(data["results"], list)


def test_run_record_writes_artifact_from_streams(project: Path, tmp_path: Path):
    out_file = tmp_path / "captured.out"
    out_file.write_text("recorded marker", encoding="utf-8")
    result = _run(
        [
            "run",
            "record",
            "--command",
            "demo",
            "--exit-code",
            "0",
            "--stdout-file",
            str(out_file),
            "--cwd",
            str(project),
        ],
        cwd=project,
    )
    assert result.returncode == 0
    runs = list((project / ".specs" / ".runs").glob("demo-*.json"))
    assert len(runs) == 1
    data = json.loads(runs[0].read_text(encoding="utf-8"))
    assert "recorded marker" in data["stdout"]
