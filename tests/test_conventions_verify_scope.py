# @spec(AC-007)
# @spec(FR-006)

"""Regression tests for feature-scoped conventions verification."""

# Explicit reexports preserve pytest node IDs and public fixture imports.
from tests._conventions_verify_scope_01 import (
    FEATURE,
    _commit_all,
    _convention_evidence,
    _invoke_verify,
    _violating_python,
    _write_empty_gates,
    _write_feature_scope,
    _write_project,
    runner,
    test_cli_verify_feature_scope_includes_latest_dated_mapping_only,
    test_cli_verify_feature_scope_prefers_mapping_when_implementation_exists,
    test_cli_verify_feature_scopes_violations_and_receipt_to_implementation_files,
    test_cli_verify_feature_without_implementation_uses_dirty_source_scope,
    test_cli_verify_feature_writes_fail_conventions_receipt,
    test_cli_verify_feature_writes_pass_conventions_receipt,
    test_cli_verify_invalid_feature_inputs_block_without_receipt,
    test_cli_verify_rejects_run_id_path_traversal_before_writing_receipt,
    test_cli_verify_repo_pseudo_scope_writes_repo_wide_receipt,
    test_cli_verify_unscoped_json_stays_repo_wide_with_unrelated_debt,
    test_spec_check_conventions_gate_can_use_feature_scoped_pass_receipt,
)
from tests._conventions_verify_scope_02 import (
    test_feature_scope_ignores_frontmatter_dates_when_mapping_rows_are_undated,
    test_feature_scope_ignores_legacy_artifact_links_when_current_mapping_is_clean,
    test_goal_prove_accepts_cli_generated_pass_conventions_receipt,
)

__all__ = [
    "FEATURE",
    "_commit_all",
    "_convention_evidence",
    "_invoke_verify",
    "_violating_python",
    "_write_empty_gates",
    "_write_feature_scope",
    "_write_project",
    "runner",
    "test_cli_verify_feature_scope_includes_latest_dated_mapping_only",
    "test_cli_verify_feature_scope_prefers_mapping_when_implementation_exists",
    "test_cli_verify_feature_scopes_violations_and_receipt_to_implementation_files",
    "test_cli_verify_feature_without_implementation_uses_dirty_source_scope",
    "test_cli_verify_feature_writes_fail_conventions_receipt",
    "test_cli_verify_feature_writes_pass_conventions_receipt",
    "test_cli_verify_invalid_feature_inputs_block_without_receipt",
    "test_cli_verify_rejects_run_id_path_traversal_before_writing_receipt",
    "test_cli_verify_repo_pseudo_scope_writes_repo_wide_receipt",
    "test_cli_verify_unscoped_json_stays_repo_wide_with_unrelated_debt",
    "test_feature_scope_ignores_frontmatter_dates_when_mapping_rows_are_undated",
    "test_feature_scope_ignores_legacy_artifact_links_when_current_mapping_is_clean",
    "test_goal_prove_accepts_cli_generated_pass_conventions_receipt",
    "test_spec_check_conventions_gate_can_use_feature_scoped_pass_receipt",
]
