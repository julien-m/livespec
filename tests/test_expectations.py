"""Tests for validator/expectations.py (parser + override resolver).

# @spec FR-003: parser tests
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-003
# @spec FR-008: override total no merge
#   — .specs/features/039-command-expectations-and-verify-output/spec.md#fr-008
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.exceptions import (
    ExpectationsInvalid,
    ExpectationsMissing,
    OverrideMalformed,
)
from validator.expectations import (
    REQUIRED_SECTIONS,
    load_expectations,
    parse_expectations,
)

MINIMAL_VALID = """\
---
command: demo
contract_version: "1.0"
last_reviewed: 2026-05-12
---

# Expectations — /spec.demo

## 1. Purpose

Demo.

## 2. Preconditions

- nothing.

## 3. Observable Signals

**stdout must_contain:**
- "hello"

## 4. Filesystem Effects

**create:** none.

## 5. Git Effects

clean.

## 6. Produced Artifacts

- none.

## 7. Exit Codes

| Code | Meaning |
|------|---------|
| 0    | OK      |

## 8. Outcome Matrix

- success.

## 9. Runtime Profile

- 1-2 seconds.

## 10. Post-run Checks

- [ ] ok.

## 11. Troubleshooting

- _none_.

## 12. Verify Contract

```yaml
verify:
  must:
    - exit_code: 0
    - contains: "hello"
  must_not:
    - contains: "Traceback"
```
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_valid_minimal_parses(tmp_path):
    path = _write(tmp_path, "demo.md", MINIMAL_VALID)
    e = parse_expectations(path)
    assert e.command == "demo"
    assert e.last_reviewed == "2026-05-12"
    assert set(e.prose_sections) == set(REQUIRED_SECTIONS)
    assert len(e.verify.must) == 2
    assert any(r.kind == "exit_code" for r in e.verify.must)
    assert any(r.kind == "contains" for r in e.verify.must)
    assert len(e.verify.must_not) == 1


def test_missing_section_blocks(tmp_path):
    body = MINIMAL_VALID.replace("## 8. Outcome Matrix\n\n- success.\n\n", "")
    path = _write(tmp_path, "bad.md", body)
    with pytest.raises(ExpectationsInvalid, match="missing required section"):
        parse_expectations(path)


def test_missing_frontmatter_blocks(tmp_path):
    body = MINIMAL_VALID.split("---", 2)[2]  # drop frontmatter
    path = _write(tmp_path, "nofm.md", body)
    with pytest.raises(ExpectationsInvalid):
        parse_expectations(path)


def test_missing_last_reviewed_blocks(tmp_path):
    body = MINIMAL_VALID.replace("last_reviewed: 2026-05-12\n", "")
    path = _write(tmp_path, "nolr.md", body)
    with pytest.raises(ExpectationsInvalid, match="last_reviewed"):
        parse_expectations(path)


def test_malformed_yaml_in_verify_blocks(tmp_path):
    body = MINIMAL_VALID.replace(
        '    - contains: "hello"',
        '    - contains: "unterminated',
    )
    path = _write(tmp_path, "badyaml.md", body)
    with pytest.raises(ExpectationsInvalid, match="verify"):
        parse_expectations(path)


def test_load_expectations_prefers_override(tmp_path):
    """Project override wins over the builtin (total replacement, AC-007)."""
    project_root = tmp_path / "proj"
    livespec_root = tmp_path / "ls"
    (project_root / ".specs" / "expectations").mkdir(parents=True)
    (livespec_root / "commands").mkdir(parents=True)
    override = project_root / ".specs" / "expectations" / "demo.md"
    builtin = livespec_root / "commands" / "demo.expectations.md"
    override.write_text(
        MINIMAL_VALID.replace(
            'contract_version: "1.0"',
            'contract_version: "override"',
        ),
        encoding="utf-8",
    )
    builtin.write_text(MINIMAL_VALID, encoding="utf-8")

    e = load_expectations("demo", project_root, livespec_root)
    assert e.contract_version == "override"
    assert e.source_path == override


def test_load_expectations_falls_back_to_builtin(tmp_path):
    project_root = tmp_path / "proj"
    livespec_root = tmp_path / "ls"
    project_root.mkdir()
    (livespec_root / "commands").mkdir(parents=True)
    builtin = livespec_root / "commands" / "demo.expectations.md"
    builtin.write_text(MINIMAL_VALID, encoding="utf-8")

    e = load_expectations("demo", project_root, livespec_root)
    assert e.source_path == builtin


def test_override_malformed_blocks_no_fallback(tmp_path):
    """AC-007: malformed override raises OverrideMalformed (no silent fallback)."""
    project_root = tmp_path / "proj"
    livespec_root = tmp_path / "ls"
    (project_root / ".specs" / "expectations").mkdir(parents=True)
    (livespec_root / "commands").mkdir(parents=True)
    override = project_root / ".specs" / "expectations" / "demo.md"
    builtin = livespec_root / "commands" / "demo.expectations.md"
    # Override missing a required section.
    override.write_text(
        MINIMAL_VALID.replace("## 8. Outcome Matrix\n\n- success.\n\n", ""),
        encoding="utf-8",
    )
    builtin.write_text(MINIMAL_VALID, encoding="utf-8")

    with pytest.raises(OverrideMalformed):
        load_expectations("demo", project_root, livespec_root)


def test_load_expectations_missing_raises(tmp_path):
    project_root = tmp_path / "proj"
    livespec_root = tmp_path / "ls"
    project_root.mkdir()
    (livespec_root / "commands").mkdir(parents=True)
    with pytest.raises(ExpectationsMissing):
        load_expectations("nope", project_root, livespec_root)


def test_when_branches_parse(tmp_path):
    body = MINIMAL_VALID.replace(
        '    - contains: "Traceback"\n',
        (
            '    - contains: "Traceback"\n'
            '  when:\n'
            '    - flag: "--visual"\n'
            '      must:\n'
            '        - contains: "baselines"\n'
        ),
    )
    path = _write(tmp_path, "when.md", body)
    e = parse_expectations(path)
    assert len(e.verify.when) == 1
    assert e.verify.when[0].flag == "--visual"
    assert len(e.verify.when[0].must) == 1
    assert e.verify.when[0].must[0].payload == "baselines"


def test_produces_artifact_rule_parses(tmp_path):
    body = MINIMAL_VALID.replace(
        '    - exit_code: 0\n',
        (
            '    - exit_code: 0\n'
            '    - produces_artifact: "spec.md"\n'
            '      contains_sections:\n'
            '        - "User Scenarios"\n'
        ),
    )
    path = _write(tmp_path, "art.md", body)
    e = parse_expectations(path)
    art = [r for r in e.verify.must if r.kind == "produces_artifact"]
    assert len(art) == 1
    assert art[0].payload["path"] == "spec.md"
    assert art[0].payload["contains_sections"] == ["User Scenarios"]


def test_override_total_no_merge(tmp_path):
    """AC-007 / FR-008: project override completely replaces the builtin.

    Specifically: rules declared in the builtin but not in the override
    MUST NOT appear in the loaded ExpectationsFile.
    """
    project_root = tmp_path / "proj"
    livespec_root = tmp_path / "ls"
    (project_root / ".specs" / "expectations").mkdir(parents=True)
    (livespec_root / "commands").mkdir(parents=True)

    # Builtin has 2 must rules; override has only 1 — verify only the
    # override's rule survives.
    override_body = MINIMAL_VALID.replace(
        '  must:\n    - exit_code: 0\n    - contains: "hello"\n',
        '  must:\n    - contains: "only-override"\n',
    )
    (project_root / ".specs" / "expectations" / "demo.md").write_text(
        override_body, encoding="utf-8"
    )
    (livespec_root / "commands" / "demo.expectations.md").write_text(
        MINIMAL_VALID, encoding="utf-8"
    )

    e = load_expectations("demo", project_root, livespec_root)
    assert len(e.verify.must) == 1
    assert e.verify.must[0].payload == "only-override"
