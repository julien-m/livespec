"""End-to-end smoke test: run wrap -> verify-output round trip.

# @spec SC-002, SC-003 — .specs/features/039-command-expectations-and-verify-output/spec.md
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXPECTATIONS = """\
---
command: spec-e2e
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.e2e
## 1. Purpose
e2e demo.
## 2. Preconditions
- none.
## 3. Observable Signals
- "ok".
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
    - contains: "MARKER-OK"
```

## 13. Demo Session

### Live Console Output
```
$ e2e
> MARKER-OK
```
- line1
- line2
- line3

### Files Produced
- a
- b
- c

### Aligned / Drift / Missing
- aligned: marker present.
- drift: marker absent.
- missing: never ran.

### Runtime Profile (scenarios)
- cold: 1s
- warm: <1s
- worst: 2s

### Edge Cases
- empty: noop.
- crash: caught.
- unicode: ok.

### Post-run Actions
- success: done.
- drift: re-run.
- blocked: fix.
"""


def _cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # The CLI is launched as a subprocess so the smoke test covers the full user
    # contract: argument parsing, output rendering, and process exit status.
    return subprocess.run(
        [sys.executable, "-m", "validator.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".specs" / ".runs").mkdir(parents=True)
    (project / ".specs" / "expectations").mkdir(parents=True)
    (project / ".specs" / "expectations" / "e2e.md").write_text(
        EXPECTATIONS, encoding="utf-8"
    )
    return project


def test_e2e_success_then_drift_then_blocked(tmp_path: Path):
    project = _setup_project(tmp_path)

    # 1. Wrap a passing command -> verify-output exits 0.
    _cli(
        ["run", "wrap", "e2e", "--cwd", str(project), "--", "sh", "-c", "echo MARKER-OK"],
        cwd=project,
    )
    r1 = _cli(["verify-output", "e2e"], cwd=project)
    assert r1.returncode == 0, r1.stdout
    assert "success" in r1.stdout

    # 2. Wrap a divergent command (no MARKER-OK) -> drift, exit 1.
    _cli(
        ["run", "wrap", "e2e", "--cwd", str(project), "--", "sh", "-c", "echo other"],
        cwd=project,
    )
    r2 = _cli(["verify-output", "e2e"], cwd=project)
    assert r2.returncode == 1
    assert "drift" in r2.stdout

    # 3. Delete all artifacts -> blocked, exit 2.
    for p in (project / ".specs" / ".runs").glob("spec-e2e-*.json"):
        p.unlink()
    r3 = _cli(["verify-output", "e2e"], cwd=project)
    assert r3.returncode == 2
    assert "blocked" in r3.stdout
