"""Rust anchors of the anchor-derived acceptance mapping (feature 087 AC-006)."""

from __future__ import annotations

from pathlib import Path

from tests.execution_evidence_support import FEATURE
from tests.test_acceptance_anchors import REF, _codes, project
from validator.acceptance_anchors import derive_acceptance

__all__ = ["project"]


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


def test_rust_assertion_in_production_code_is_not_bound(project: Path) -> None:
    (project / "src").mkdir()
    (project / "src/calc.rs").write_text(
        "pub fn compute(x: i32) -> i32 {\n"
        f"    // @spec AC-001: see #[test]\n    //   — {REF}#ac-001\n"
        "    assert!(x > 0);\n    x\n}\n"
    )
    derivation = derive_acceptance(project, FEATURE)
    assert all(b.assertion_path != "src/calc.rs" for b in derivation.bindings)


def test_rust_custom_attribute_ending_in_test_is_not_a_test(project: Path) -> None:
    (project / "test_app.py").write_text("def test_nothing():\n    assert True\n")
    (project / "tests").mkdir()
    (project / "tests/add.rs").write_text(
        f"// @spec AC-001: three\n//   — {REF}#ac-001\n"
        "#[my_test]\nfn adds() { assert_eq!(3, 3); }\n"
    )
    assert _codes(project) == ["orphan_acceptance"]
