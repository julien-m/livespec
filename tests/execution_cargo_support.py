"""Real Cargo fixture crate and reviewed mapping for trusted Cargo runner tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from validator.execution_capture import capture_execution
from validator.execution_cargo_toolchain import CargoRunnerUnavailable, llvm_tools
from validator.execution_mapping import ingest_mapping_review, prepare_mapping_review
from validator.execution_scope import digest
from validator.semantic.review_context import PreparedReview

FEATURE = "001-add"
AC = f"{FEATURE}:AC-001"
INTEGRATION_ID = "fixture/test/integ::integration_adds"

LIB = """pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::add;

    #[test]
    fn passes() {
        assert_eq!(add(1, 2), 3);
        if add(0, 0) > 0 {
            assert!(false, "unreachable");
        }
    }

    #[test]
    fn fails() {
        assert_eq!(add(1, 1), 3, "wrong sum");
    }

    #[test]
    #[ignore = "slow"]
    fn ignored() {
        assert!(add(2, 2) == 4);
    }

    #[test]
    fn reads_caller_environment() {
        assert_eq!(std::env::var("LIVESPEC_FIXTURE_FLAG").as_deref(), Ok("1"));
    }
}

#[cfg(test)]
mod other {
    #[test]
    fn filtered_out() {
        assert!(super::add(0, 1) == 1);
    }
}
"""

INTEGRATION = """#[test]
fn integration_adds() {
    let sum = fixture::add(2, 3);
    assert_eq!(sum, 5);
}
"""


def require_cargo_runner() -> None:
    """Skip when this machine has no Cargo or no LLVM coverage tools."""
    if shutil.which("cargo") is None:
        pytest.skip("cargo is not installed")
    try:
        llvm_tools(Path.cwd(), dict(os.environ))
    except CargoRunnerUnavailable as exc:
        pytest.skip(str(exc))


@pytest.fixture
def crate(tmp_path: Path) -> Path:
    """A crate with passing, failing, ignored, filtered and integration tests."""
    require_cargo_runner()
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "Cargo.toml").write_text(
        '[package]\nname = "fixture"\nversion = "0.1.0"\nedition = "2021"\n'
    )
    (root / "src/lib.rs").write_text(LIB)
    (root / "tests/integ.rs").write_text(INTEGRATION)
    # A run must not create inputs: commit the lockfile Cargo would otherwise write.
    subprocess.run(["cargo", "generate-lockfile", "--offline"], cwd=root, check=True)
    feature = root / ".specs/features" / FEATURE
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Addition\nAC-001: Adding two and three returns five.\n")
    return root


def cargo_env(root: Path, **extra: str) -> dict[str, str]:
    """Caller environment with the build directory outside the captured project."""
    return {**os.environ, "CARGO_TARGET_DIR": str(root.parent / "cargo-target"), **extra}


def write_mapping(
    root: Path, test_id: str = INTEGRATION_ID, path: str = "tests/integ.rs", line: int = 4
) -> None:
    """Write and independently review one binding to one Rust assertion."""
    source = root / path
    mapping = {
        "schema_version": "1",
        "feature": FEATURE,
        "reviewer_model": "independent-test-review-fixture",
        "review_receipt_path": "acceptance-review.json",
        "bindings": [
            {
                "requirement_id": AC,
                "test_id": test_id,
                "expected": "Adding two and three returns five",
                "assertion_path": path,
                "start_line": line,
                "end_line": line,
                "source_sha256": digest(source.read_bytes()),
                "justification": "The assertion compares add(2, 3) to five.",
            }
        ],
    }
    (root / "mapping.json").write_text(json.dumps(mapping))
    prepared = prepare_mapping_review(root, FEATURE, root / "mapping.json")
    excerpt = source.read_text().splitlines()[line - 1].strip()
    receipt = ingest_mapping_review(
        prepared, [_review(prepared, path, excerpt)], root / "acceptance-review.json"
    )
    assert receipt.ready, receipt.errors


def _review(prepared: PreparedReview, path: str, excerpt: str) -> str:
    spec = next(section for section in prepared.sections if section.role == "spec")
    test = next(
        section
        for section in prepared.sections
        if section.source == path and excerpt in section.text
    )
    return json.dumps(
        {
            "batch_id": prepared.batches[0].batch_id,
            "reviewed_section_ids": [section.section_id for section in prepared.sections],
            "conclusions": [
                {
                    "requirement_id": AC,
                    "disposition": "covered",
                    "rationale": "The integration test compares add(2, 3) to five.",
                    "source_citations": [
                        {
                            "section_id": spec.section_id,
                            "excerpt": "AC-001: Adding two and three returns five.",
                        }
                    ],
                    "plan_citations": [{"section_id": test.section_id, "excerpt": excerpt}],
                }
            ],
            "ambiguities": [],
            "extra_scope": [],
            "findings": [],
            "confidence": 5,
        }
    )


def capture(root: Path, command: list[str], env: dict[str, str] | None = None) -> Path:
    """Capture a real Cargo run through the runner-owned capture."""
    mapping = "mapping.json" if (root / "mapping.json").exists() else None
    result = capture_execution(
        command,
        project_root=root,
        feature=FEATURE,
        adapter="junit",
        env=env or cargo_env(root),
        timeout=30,
        acceptance_mapping=mapping,
    )
    return Path(result.receipt_path)
