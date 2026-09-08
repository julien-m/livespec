"""Preserved test cases and fixtures for test_goal_contracts.py."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

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

- `.specs/project.md` exists.

## 3. Observable Signals

- "done"

## 4. Filesystem Effects

- creates demo.txt.

## 5. Git Effects

- none.

## 6. Produced Artifacts

- demo.txt.

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | success |

## 8. Outcome Matrix

- success.

## 9. Runtime Profile

- <1s.

## 10. Post-run Checks

- [ ] output checked.

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
  when:
    - flag: "--strict"
      must:
        - exists: "demo.txt"
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

- demo.txt
- report.md
- summary.md

### Aligned / Drift / Missing

- aligned: done.
- drift: marker missing.
- missing: no artifact.

### Runtime Profile

- cold: <1s.
- warm: <1s.
- worst: 2s.

### Edge Cases

- missing file: blocked.
- bad output: drift.
- crash: error.

### Post-run Actions

- success: continue.
- drift: inspect output.
- blocked: restore artifact.
"""


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 4
    height = 4
    row = bytes((*color, 255)) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Definition of Done (Command-Level)

`/spec-demo` is complete only if all are true:

- [ ] `demo.txt` exists <!-- evidence:documentary -->
- [ ] Output contains `done` <!-- evidence:documentary -->
- [ ] No traceback was emitted <!-- evidence:documentary -->

If any item fails, fix before returning final output.
"""


EXECUTION_TASK_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Execution Tasks

- [always] Always task <!-- evidence:documentary -->
- [visual] Visual task <!-- evidence:documentary -->
- [penflow] Penflow task <!-- evidence:documentary -->
- [generate] Generate task <!-- evidence:documentary -->
- [visual-generate] Visual generate task <!-- evidence:documentary -->
- [execute] Execute task <!-- evidence:documentary -->
- [surfaces] Surfaces task <!-- evidence:documentary -->
- [quality-only] Quality task <!-- evidence:documentary -->
- [tree-only] Tree task <!-- evidence:documentary -->
- [visual-status] Visual status task <!-- evidence:documentary -->
- [multi] Multi task <!-- evidence:documentary -->
- [fix] Fix task <!-- evidence:documentary -->

## Definition of Done (Command-Level)

- [ ] Done <!-- evidence:documentary -->
"""


INLINE_INTERNAL_COMMAND_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

- [inline] `/spec-fix <feature>` — forbidden nested execution.

## Definition of Done (Command-Level)

- [ ] Done
"""


SUBAGENT_INTERNAL_COMMAND_SKILL = """\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

- [subagent] `/spec-fix <feature>` — guard: project_root cwd .specs/spec-system.md; child goal.
- [suggestion] `/spec-plan <feature>` — text-only next action.

## Definition of Done (Command-Level)

- [ ] Done
"""


def _fixture_roots(tmp_path: Path) -> tuple[Path, Path]:
    project_root = tmp_path / "project"
    livespec_root = tmp_path / "livespec"
    (project_root / ".specs").mkdir(parents=True)
    skill_dir = livespec_root / ".agent-sync" / "skills" / "spec-demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "expectations.md").write_text(EXPECTATIONS, encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(SKILL, encoding="utf-8")
    return project_root, livespec_root


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_execution_task_skill(livespec_root: Path) -> None:
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(EXECUTION_TASK_SKILL, encoding="utf-8")


def _write_internal_command_skill(livespec_root: Path, rows: list[str]) -> None:
    skill_path = livespec_root / ".agent-sync" / "skills" / "spec-demo" / "SKILL.md"
    skill_path.write_text(
        f"""\
---
name: spec-demo
description: Demo command
---

# /spec-demo

## Internal Command Invocations

{chr(10).join(rows)}

## Definition of Done (Command-Level)

- [ ] Done
""",
        encoding="utf-8",
    )


def _write_visual_feature(project_root: Path, feature: str = "001-visual") -> None:
    feature_dir = project_root / ".specs" / "features" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Visual Feature\n\n## Screens\n\n- Home screen",
        encoding="utf-8",
    )
