"""Acceptance mapping derived from `@spec AC-xxx` test anchors (feature 087)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from tests.execution_evidence_support import AC, FEATURE, run
from validator.acceptance_anchors import derive_acceptance
from validator.cli import app
from validator.execution_evidence import verify_execution_receipt
from validator.execution_mapping import (
    AcceptanceBinding,
    AcceptanceMapping,
    prepare_mapping_review,
)

REF = f".specs/features/{FEATURE}/spec.md"
ANCHORED = (
    "from app import add\n\n\n"
    f"# @spec AC-001: Adding one and two returns three\n#   — {REF}#ac-001\n"
    "def test_add():\n    total = add(1, 2)\n    assert total > 0\n    assert total == 3\n"
)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    feature = tmp_path / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Addition\nAC-001: Adding one and two returns three.\n")
    (tmp_path / "app.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_app.py").write_text(ANCHORED)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _derive(project: Path) -> tuple[int, dict[str, object]]:
    result = CliRunner().invoke(
        app,
        ["test", "--feature", FEATURE, "--acceptance-mapping", "mapping.json", "--derive-mapping"],
    )
    return result.exit_code, json.loads(result.output.splitlines()[-1])


def _codes(project: Path) -> list[str]:
    return [issue.code for issue in derive_acceptance(project, FEATURE).blocking]


# @spec AC-001: Derive the mapping from the anchors
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-001
def test_derive_binds_last_assertion_of_anchored_test(project: Path) -> None:
    code, payload = _derive(project)
    assert code == 0, payload
    mapping = AcceptanceMapping.model_validate_json((project / "mapping.json").read_bytes())
    assert mapping.derivation == "anchors"
    assert mapping.reviewer_model == "" and mapping.review_receipt_path == ""
    [binding] = mapping.bindings
    assert (binding.requirement_id, binding.test_id) == (AC, "test_app::test_add")
    assert (binding.start_line, binding.end_line) == (9, 9)
    assert binding.justification == "Derived from the @spec anchor at test_app.py:4"
    assert payload["acceptance"] == [AC]


def test_anchor_on_an_assertion_and_in_a_test_class(project: Path) -> None:
    (project / "test_app.py").write_text(
        "from app import add\n\n\nclass TestAdd:\n    def test_add(self):\n"
        f"        # @spec AC-001: three\n        #   — {REF}#ac-001\n"
        "        assert add(1, 2) == 3\n        assert add(0, 0) == 0\n"
    )
    [binding] = derive_acceptance(project, FEATURE).bindings
    assert (binding.test_id, binding.start_line) == ("test_app.TestAdd::test_add", 8)


# @spec AC-002: Orphan ACs and unknown anchors refuse the mapping
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-002
def test_orphan_acceptance_refuses_and_writes_nothing(project: Path) -> None:
    spec = project / REF
    spec.write_text(spec.read_text() + "AC-002: Subtracting is out of scope.\n")
    code, payload = _derive(project)
    assert code == 1
    assert payload["mapping_path"] is None
    assert not (project / "mapping.json").exists()
    issues = payload["issues"]
    assert isinstance(issues, list)
    assert [issue["code"] for issue in issues] == ["orphan_acceptance"]


def test_unknown_anchor_refuses(project: Path) -> None:
    (project / "test_app.py").write_text(ANCHORED.replace("AC-001:", "AC-001, AC-009:"))
    assert _codes(project) == ["unknown_anchor"]
    assert _derive(project)[0] == 1


# @spec AC-003: Unresolved, assert-less and parametrized targets
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-003
@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("def helper():\n    return 1\n", "anchor_target_unresolved"),
        ("def test_add():\n    add(1, 2)\n", "anchor_test_without_assert"),
        (
            "import pytest\n@pytest.mark.parametrize('x', [1])\ndef test_add(x):\n    assert x\n",
            "anchor_test_parametrized",
        ),
    ],
)
def test_unbindable_anchor_targets_refuse(project: Path, body: str, code: str) -> None:
    lines = f"# @spec AC-001: three\n#   — {REF}#ac-001\n"
    if body.startswith("import"):
        head, rest = body.split("\n", 1)
        body = f"{head}\n{lines}{rest}"
    else:
        body = lines + body
    (project / "test_app.py").write_text("from app import add\n" + body)
    assert code in _codes(project)


def test_other_feature_and_unqualified_anchors_are_ignored(project: Path) -> None:
    (project / "test_other.py").write_text(
        "# @spec AC-001: other — .specs/features/002-other/spec.md#ac-001\n"
        "def test_other():\n    assert True\n\n"
        "# @spec AC-007: unqualified\ndef test_unqualified():\n    assert True\n"
    )
    derivation = derive_acceptance(project, FEATURE)
    assert [b.assertion_path for b in derivation.bindings] == ["test_app.py"]
    assert derivation.issues == []


# @spec AC-004: Certify anchored bindings without a mapping review
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-004
def test_anchored_mapping_certifies_from_a_real_run(project: Path) -> None:
    assert _derive(project)[0] == 0
    result = verify_execution_receipt(run(project), project, FEATURE, (AC,))
    assert result.valid, result.gaps
    assert result.certified_acs == [AC]
    assert not list(project.glob("*review*.json"))


def test_hand_edited_anchored_mapping_is_not_certified(project: Path) -> None:
    assert _derive(project)[0] == 0
    path = project / "mapping.json"
    data = json.loads(path.read_text())
    data["bindings"][0]["start_line"] = 8
    data["bindings"][0]["end_line"] = 8
    path.write_text(json.dumps(data))
    result = verify_execution_receipt(run(project), project, FEATURE, (AC,))
    assert not result.valid
    assert any("differs from the current test anchors" in gap for gap in result.gaps)


def test_removed_anchor_after_derivation_is_not_certified(project: Path) -> None:
    assert _derive(project)[0] == 0
    (project / "test_app.py").write_text(ANCHORED.replace("@spec AC-001", "AC-001"))
    result = verify_execution_receipt(run(project), project, FEATURE, (AC,))
    assert not result.valid
    assert any("orphan_acceptance" in gap for gap in result.gaps)


# @spec AC-005: No mapping review for an anchored mapping
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-005
def test_anchored_mapping_refuses_review_preparation(project: Path) -> None:
    assert _derive(project)[0] == 0
    with pytest.raises(ValueError, match="anchored_mapping_needs_no_review"):
        prepare_mapping_review(project, FEATURE, project / "mapping.json")
    result = CliRunner().invoke(
        app,
        [
            "test",
            "--feature",
            FEATURE,
            "--acceptance-mapping",
            "mapping.json",
            "--prepare-mapping-review",
        ],
    )
    assert result.exit_code == 1
    assert "anchored_mapping_needs_no_review" in result.output


def test_mapping_kinds_keep_their_review_fields() -> None:
    binding = AcceptanceBinding(
        requirement_id=AC,
        test_id="t::t",
        expected="e",
        assertion_path="t.py",
        start_line=1,
        end_line=1,
        source_sha256="0",
        justification="j",
    )
    with pytest.raises(ValidationError):
        AcceptanceMapping(feature=FEATURE, bindings=[binding])
    with pytest.raises(ValidationError):
        AcceptanceMapping(
            feature=FEATURE,
            bindings=[binding],
            derivation="anchors",
            reviewer_model="m",
        )


RUST_LIB = """
pub fn add(a: i32, b: i32) -> i32 {
    // @spec AC-001: production code is not a test binding
    //   — .specs/features/001-add/spec.md#ac-001
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    // @spec AC-001: Adding one and two returns three
    //   — .specs/features/001-add/spec.md#ac-001
    #[test]
    fn adds() {
        let total = add(1, 2);
        assert!(total > 0);
        assert_eq!(total, 3);
    }
}
"""


# @spec AC-006: Rust anchors and Cargo test paths
#   — .specs/features/087-anchor-derived-acceptance/spec.md#ac-006
def test_rust_anchor_binds_cargo_path(project: Path) -> None:
    (project / "test_app.py").write_text("def test_nothing():\n    assert True\n")
    (project / "crate/src/math").mkdir(parents=True)
    (project / "crate/src/math/mod.rs").write_text(RUST_LIB)
    derivation = derive_acceptance(project, FEATURE)
    assert derivation.issues == []
    [binding] = derivation.bindings
    assert binding.test_id == "math::tests::adds"
    assert (binding.start_line, binding.end_line) == (18, 18)


def test_rust_integration_anchor_without_test_refuses(project: Path) -> None:
    (project / "test_app.py").write_text("def test_nothing():\n    assert True\n")
    (project / "tests").mkdir()
    (project / "tests/add.rs").write_text(
        f"// @spec AC-001: three\n//   — {REF}#ac-001\nconst X: i32 = 3;\n"
    )
    assert "anchor_target_unresolved" in _codes(project)
    (project / "tests/add.rs").write_text(
        f"// @spec AC-001: three\n//   — {REF}#ac-001\n#[test]\nfn adds() {{ assert_eq!(3, 3); }}\n"
    )
    [binding] = derive_acceptance(project, FEATURE).bindings
    assert binding.test_id == "adds"
