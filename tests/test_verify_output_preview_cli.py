"""CLI tests for `livespec verify-output --preview`.

# @spec FR-005: --preview branch
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-005
# @spec FR-008: --save flag
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-008
# @spec FR-009: canonical error strings
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md#fr-009
# @spec AC-008, AC-009, AC-010 error messages
#   — .specs/features/040-expectations-rich-and-verify-preview/spec.md
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

VALID = """---
command: previewdemo
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.previewdemo

## 1. Purpose
demo.
## 2. Preconditions
- none.
## 3. Observable Signals
- "ok"
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
- none.
## 12. Verify Contract
```yaml
verify:
  must:
    - exit_code: 0
```

## 13. Demo Session

### Live Console Output
```
$ previewdemo
> running on <feature>
```
- ran on <stack>
- l2
- l3

### Files Produced
- <feature>/spec.md
- log
- summary

### Aligned / Drift / Missing
- aligned: ok.
- drift: missing.
- missing: blocked.

### Runtime Profile (scenarios)
- cold: 1s
- warm: <1s
- worst: 2s

### Edge Cases
- a
- b
- c

### Post-run Actions
- s
- d
- b
"""

MISSING_S13 = VALID.split("## 13. Demo Session", 1)[0]

EMPTY_SUBSECTION = VALID.replace(
    "### Files Produced\n- <feature>/spec.md\n- log\n- summary",
    "### Files Produced\n",
)


def _cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "validator.cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _setup_project(tmp_path: Path, expectations_body: str) -> Path:
    project = tmp_path / "proj"
    (project / ".specs" / "expectations").mkdir(parents=True)
    (project / ".specs" / "stacks").mkdir(parents=True)
    (project / ".specs" / "stacks" / "_default.md").write_text(
        "# CLI Test Stack\n", encoding="utf-8"
    )
    (project / ".specs" / "features" / "001-cli-feat").mkdir(parents=True)
    (project / ".specs" / "expectations" / "previewdemo.md").write_text(
        expectations_body, encoding="utf-8"
    )
    return project


def test_preview_success_renders_markdown(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, VALID)
    res = _cli(["verify-output", "previewdemo", "--preview"], cwd=project)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "001-cli-feat" in res.stdout
    assert "CLI Test Stack" in res.stdout
    assert "<feature>" not in res.stdout  # all resolved


def test_preview_save_writes_file(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, VALID)
    res = _cli(
        ["verify-output", "previewdemo", "--preview", "--save"], cwd=project
    )
    assert res.returncode == 0
    previews = list((project / ".specs" / ".previews").glob("previewdemo-*.md"))
    assert len(previews) == 1
    assert previews[0].read_text(encoding="utf-8").strip() == res.stdout.strip()


def test_preview_missing_section_13_blocks(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, MISSING_S13)
    res = _cli(["verify-output", "previewdemo", "--preview"], cwd=project)
    assert res.returncode == 2
    assert "section 13 missing in" in res.stderr


def test_preview_empty_subsection_blocks(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, EMPTY_SUBSECTION)
    res = _cli(["verify-output", "previewdemo", "--preview"], cwd=project)
    assert res.returncode == 2
    assert "section 13 sub-section 'Files Produced' is empty" in res.stderr


def test_preview_without_specs_dir_blocks(tmp_path: Path) -> None:
    # tmp_path itself has no .specs/.
    res = _cli(["verify-output", "previewdemo", "--preview"], cwd=tmp_path)
    assert res.returncode == 2
    assert "preview requires a LiveSpec project (no .specs/ found)" in res.stderr


def test_preview_json_emits_envelope(tmp_path: Path) -> None:
    project = _setup_project(tmp_path, VALID)
    res = _cli(
        ["verify-output", "previewdemo", "--preview", "--json"], cwd=project
    )
    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["command"] == "previewdemo"
    assert "001-cli-feat" in payload["markdown"]
    assert payload["timestamp"]
