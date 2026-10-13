"""Rust assertion identity ignores literals and comments and names its test (feature 085)."""

from __future__ import annotations

import pytest

from validator.execution_mapping import AcceptanceBinding, _assertion_span
from validator.execution_reports import ExecutedTest, cargo_test_path, resolve_test_id
from validator.execution_rust_source import rust_assertions

SOURCE = r"""//! assert!(doc_comment);
mod unix {
    /* assert!(block /* nested */ comment) */
    #[test]
    fn checks<'a>() -> Result<(), Box<dyn std::error::Error + 'a>> {
        let text = "assert!(in_string)";
        let raw = r#"assert_eq!("raw", 1)"#;
        let quote = '"';
        std::assert_eq!(
            text.len(),
            18
        );
        assert!(raw.contains('"') && quote == '"', "message with ) paren");
        Ok(())
    }

    fn helper() {
        assert_ne!(1, 2);
    }
}
"""


def test_only_real_invocations_are_found_with_their_function() -> None:
    found = [
        (item.line, item.end_line, item.function, item.text) for item in rust_assertions(SOURCE)
    ]
    assert found == [
        (9, 12, "checks", "std::assert_eq!(\n            text.len(),\n            18\n        )"),
        (
            13,
            13,
            "checks",
            "assert!(raw.contains('\"') && quote == '\"', \"message with ) paren\")",
        ),
        (18, 18, "helper", "assert_ne!(1, 2)"),
    ]


def test_columns_count_characters_and_bytes() -> None:
    [item] = rust_assertions("fn t() { let é = 1; assert!(é == 1); }\n")
    assert (item.column, item.byte_column) == (21, 22)


def _binding(start: int, end: int, test_id: str = "pkg/test/t::unix::checks") -> AcceptanceBinding:
    return AcceptanceBinding(
        requirement_id="001-x:AC-001",
        test_id=test_id,
        expected="passed",
        assertion_path="tests/t.rs",
        start_line=start,
        end_line=end,
        source_sha256="0" * 64,
        justification="fixture",
    )


def test_binding_cites_one_complete_assertion_of_its_test() -> None:
    assert _assertion_span(_binding(9, 12), SOURCE).startswith("std::assert_eq!(")
    assert _assertion_span(_binding(13, 13), SOURCE).startswith("assert!(raw")


@pytest.mark.parametrize(
    ("start", "end", "test_id"),
    [
        (9, 9, "pkg/test/t::unix::checks"),  # Partial multi-line assertion.
        (9, 13, "pkg/test/t::unix::checks"),  # Two assertions.
        (6, 6, "pkg/test/t::unix::checks"),  # A string, not an assertion.
        (18, 18, "pkg/test/t::unix::checks"),  # Assertion of another function.
    ],
)
def test_ambiguous_or_foreign_rust_bindings_are_rejected(
    start: int, end: int, test_id: str
) -> None:
    with pytest.raises(ValueError, match="one complete assertion"):
        _assertion_span(_binding(start, end, test_id), SOURCE)


def test_cargo_test_ids_resolve_bare_paths_only_when_unique() -> None:
    one = ExecutedTest(test_id="app/test/a::unix::checks", status="passed")
    other = ExecutedTest(test_id="app/lib/app::unix::checks", status="passed")
    assert cargo_test_path(one.test_id) == "unix::checks"
    assert cargo_test_path("test_app::test_add") is None
    assert resolve_test_id("unix::checks", [one]) == one.test_id
    assert resolve_test_id("unix::checks", [one, other]) == "unix::checks"
    assert resolve_test_id(other.test_id, [one, other]) == other.test_id
