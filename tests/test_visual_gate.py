"""Unit tests for validator/visual_gate.py.

# @spec FR-100..103: Visual gate semantics — visual-gate-fix cycle
"""

import os
from pathlib import Path

# Explicit reexports preserve pytest node IDs and public fixture imports.
from tests._visual_gate_01 import (
    _png,
    _write_spec,
    test_apply_cleanup_delete_mode_removes_misplaced_files,
    test_apply_cleanup_quarantines_files_and_is_idempotent,
    test_detect_visual_feature_conflict_on_weak_signal_only,
    test_detect_visual_feature_conflict_when_spec_declares_but_no_artifacts,
    test_detect_visual_feature_returns_non_visual_when_marker_false,
    test_detect_visual_feature_returns_non_visual_without_spec_or_signals,
    test_detect_visual_feature_returns_visual_on_strong_signal_only,
    test_detect_visual_feature_surfaces_yaml_is_weak_signal,
    test_detect_visual_feature_uses_feature_scoped_penflow_index,
    test_plan_cleanup_lists_misplaced_runtime_captures,
    test_render_text_report_includes_all_diagnostic_sections,
    test_render_text_report_includes_verdict_and_classification,
    test_validate_gate_blocked_on_classification_conflict,
    test_validate_gate_fails_on_physical_copy_in_feature_baselines,
    test_validate_gate_fails_on_runtime_capture_misplaced_under_design_screens,
    test_validate_gate_passes_when_no_artifacts_required_and_no_conflicts,
    test_visual_classification_to_dict_includes_signals,
    test_write_cleanup_report_produces_json,
)
from tests._visual_gate_02 import (
    test_detect_visual_conflict_weak_only_surfaces,
    test_legacy_manifest_empty_screen_skipped,
    test_legacy_manifest_mockup_hash_helpers,
    test_legacy_manifest_mockup_path_escape_detected,
    test_legacy_manifest_mockup_version_no_sha256_prefix,
    test_legacy_manifest_mockup_version_non_string,
    test_legacy_manifest_mockup_version_short_digest,
    test_legacy_manifest_non_list_screens_returns_empty,
    test_legacy_manifest_non_mapping_entry_skipped,
    test_manifest_status_to_dict_none,
    test_penflow_index_read_oserror_skipped,
    test_penflow_index_yml_detected,
    test_promote_baseline_creates_registry_copy_and_relative_symlink,
    test_promote_baseline_manifest_mode_persists_manifest_entry,
    test_promote_baseline_raises_for_missing_run_capture,
    test_read_manifest_mapping_returns_none_for_malformed_json,
    test_read_manifest_mapping_returns_none_for_malformed_yaml,
    test_read_manifest_mapping_returns_none_for_non_mapping,
    test_read_manifest_mapping_returns_none_for_unreadable,
    test_read_spec_marker_no_closing_delimiter,
    test_read_spec_marker_unreadable_file,
    test_resolve_legacy_mockup_path_absolute_escape,
    test_resolve_legacy_mockup_path_relative_escape,
    test_surfaces_yaml_features_list_top_level,
    test_surfaces_yaml_non_mapping_entry_skipped,
    test_surfaces_yaml_non_mapping_root_returns_false,
    test_surfaces_yaml_oserror_returns_false,
)
from tests._visual_gate_03 import (
    _make_penflow,
    test_aggregate_verdict_alignment_blocked,
    test_aggregate_verdict_alignment_fail,
    test_aggregate_verdict_link_violation_blocked,
    test_aggregate_verdict_link_violation_fail,
    test_aggregate_verdict_missing_artifacts_blocked,
    test_aggregate_verdict_pass,
    test_aggregate_verdict_penflow_blocked,
    test_aggregate_verdict_penflow_fail,
    test_aggregate_verdict_visual_evidence_blocked,
    test_aggregate_verdict_visual_evidence_fail,
    test_alignment_dir_incomplete_manifest_ok,
    test_alignment_dir_incomplete_manifest_with_error,
    test_alignment_dir_incomplete_no_manifest_no_files,
    test_baseline_manifest_path_json_fallback,
    test_resolve_manifest_source_absolute_missing,
    test_resolve_manifest_source_absolute_path,
    test_resolve_manifest_source_empty_returns_none,
    test_resolve_manifest_source_local_relative,
    test_resolve_manifest_source_rooted_relative,
    test_resolve_manifest_source_specs_relative,
    test_resolve_targets_empty_when_nothing,
    test_resolve_targets_explicit_target,
    test_resolve_targets_from_baselines_registry,
    test_resolve_targets_from_surfaces_yaml,
    test_resolve_targets_surfaces_non_mapping_entry,
    test_resolve_targets_surfaces_non_mapping_root,
    test_resolve_targets_surfaces_unknown_runner,
    test_surfaces_yaml_entry_features_list,
    test_surfaces_yaml_features_map_top_level,
    test_validate_gate_strict_links_disabled,
)
from tests._visual_gate_04 import (
    test_as_list_returns_none_for_non_list,
    test_as_mapping_returns_none_for_non_dict,
    test_certify_blocked_when_no_mockups,
    test_certify_blocked_when_threshold_out_of_range,
    test_detect_plain_copies_broken_symlink,
    test_promote_baseline_manifest_mode_corrupted_json,
    test_promote_baseline_manifest_mode_replaces_same_screen,
    test_promote_baseline_manifest_mode_updates_existing,
    test_read_alignment_manifest_sources_malformed_json,
    test_read_alignment_manifest_sources_missing_fields,
    test_read_alignment_manifest_sources_non_object,
    test_read_alignment_manifest_sources_unreadable,
    test_read_alignment_manifest_sources_unresolved,
    test_validate_gate_visual_missing_registry_baselines,
    test_validate_gate_visual_no_target_no_baselines_no_surfaces,
    test_verdict_to_exit_code_all,
)
from validator.visual_gate import _detect_plain_copies

__all__ = [
    "_make_penflow",
    "_png",
    "_write_spec",
    "test_aggregate_verdict_alignment_blocked",
    "test_aggregate_verdict_alignment_fail",
    "test_aggregate_verdict_link_violation_blocked",
    "test_aggregate_verdict_link_violation_fail",
    "test_aggregate_verdict_missing_artifacts_blocked",
    "test_aggregate_verdict_pass",
    "test_aggregate_verdict_penflow_blocked",
    "test_aggregate_verdict_penflow_fail",
    "test_aggregate_verdict_visual_evidence_blocked",
    "test_aggregate_verdict_visual_evidence_fail",
    "test_alignment_dir_incomplete_manifest_ok",
    "test_alignment_dir_incomplete_manifest_with_error",
    "test_alignment_dir_incomplete_no_manifest_no_files",
    "test_apply_cleanup_delete_mode_removes_misplaced_files",
    "test_apply_cleanup_quarantines_files_and_is_idempotent",
    "test_as_list_returns_none_for_non_list",
    "test_as_mapping_returns_none_for_non_dict",
    "test_baseline_manifest_path_json_fallback",
    "test_certify_blocked_when_no_mockups",
    "test_certify_blocked_when_threshold_out_of_range",
    "test_detect_plain_copies_broken_symlink",
    "test_detect_visual_conflict_weak_only_surfaces",
    "test_detect_visual_feature_conflict_on_weak_signal_only",
    "test_detect_visual_feature_conflict_when_spec_declares_but_no_artifacts",
    "test_detect_visual_feature_returns_non_visual_when_marker_false",
    "test_detect_visual_feature_returns_non_visual_without_spec_or_signals",
    "test_detect_visual_feature_returns_visual_on_strong_signal_only",
    "test_detect_visual_feature_surfaces_yaml_is_weak_signal",
    "test_detect_visual_feature_uses_feature_scoped_penflow_index",
    "test_legacy_manifest_empty_screen_skipped",
    "test_legacy_manifest_mockup_hash_helpers",
    "test_legacy_manifest_mockup_path_escape_detected",
    "test_legacy_manifest_mockup_version_no_sha256_prefix",
    "test_legacy_manifest_mockup_version_non_string",
    "test_legacy_manifest_mockup_version_short_digest",
    "test_legacy_manifest_non_list_screens_returns_empty",
    "test_legacy_manifest_non_mapping_entry_skipped",
    "test_manifest_status_to_dict_none",
    "test_penflow_index_read_oserror_skipped",
    "test_penflow_index_yml_detected",
    "test_plan_cleanup_lists_misplaced_runtime_captures",
    "test_promote_baseline_creates_registry_copy_and_relative_symlink",
    "test_promote_baseline_manifest_mode_corrupted_json",
    "test_promote_baseline_manifest_mode_persists_manifest_entry",
    "test_promote_baseline_manifest_mode_replaces_same_screen",
    "test_promote_baseline_manifest_mode_updates_existing",
    "test_promote_baseline_raises_for_missing_run_capture",
    "test_read_alignment_manifest_sources_malformed_json",
    "test_read_alignment_manifest_sources_missing_fields",
    "test_read_alignment_manifest_sources_non_object",
    "test_read_alignment_manifest_sources_unreadable",
    "test_read_alignment_manifest_sources_unresolved",
    "test_read_manifest_mapping_returns_none_for_malformed_json",
    "test_read_manifest_mapping_returns_none_for_malformed_yaml",
    "test_read_manifest_mapping_returns_none_for_non_mapping",
    "test_read_manifest_mapping_returns_none_for_unreadable",
    "test_read_spec_marker_no_closing_delimiter",
    "test_read_spec_marker_unreadable_file",
    "test_render_text_report_includes_all_diagnostic_sections",
    "test_render_text_report_includes_verdict_and_classification",
    "test_resolve_legacy_mockup_path_absolute_escape",
    "test_resolve_legacy_mockup_path_relative_escape",
    "test_resolve_manifest_source_absolute_missing",
    "test_resolve_manifest_source_absolute_path",
    "test_resolve_manifest_source_empty_returns_none",
    "test_resolve_manifest_source_local_relative",
    "test_resolve_manifest_source_rooted_relative",
    "test_resolve_manifest_source_specs_relative",
    "test_resolve_targets_empty_when_nothing",
    "test_resolve_targets_explicit_target",
    "test_resolve_targets_from_baselines_registry",
    "test_resolve_targets_from_surfaces_yaml",
    "test_resolve_targets_surfaces_non_mapping_entry",
    "test_resolve_targets_surfaces_non_mapping_root",
    "test_resolve_targets_surfaces_unknown_runner",
    "test_surfaces_yaml_entry_features_list",
    "test_surfaces_yaml_features_list_top_level",
    "test_surfaces_yaml_features_map_top_level",
    "test_surfaces_yaml_non_mapping_entry_skipped",
    "test_surfaces_yaml_non_mapping_root_returns_false",
    "test_surfaces_yaml_oserror_returns_false",
    "test_validate_gate_blocked_on_classification_conflict",
    "test_validate_gate_fails_on_physical_copy_in_feature_baselines",
    "test_validate_gate_fails_on_runtime_capture_misplaced_under_design_screens",
    "test_validate_gate_passes_when_no_artifacts_required_and_no_conflicts",
    "test_validate_gate_strict_links_disabled",
    "test_validate_gate_visual_missing_registry_baselines",
    "test_validate_gate_visual_no_target_no_baselines_no_surfaces",
    "test_verdict_to_exit_code_all",
    "test_visual_classification_to_dict_includes_signals",
    "test_write_cleanup_report_produces_json",
]


# @spec FR-004: Reject foreign healthy baseline links without flagging valid links.
def test_detect_plain_copies_checks_healthy_symlink_targets(tmp_path: Path) -> None:
    from validator.registry_links import expected_registry_baseline_path

    slug = "079-baseline-links"
    expected = tmp_path / expected_registry_baseline_path(
        feature_slug=slug, target="web", screen="dashboard"
    )
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"registry-baseline")
    local = tmp_path / ".specs/features" / slug / "baselines/dashboard.png"
    local.parent.mkdir(parents=True)
    local.symlink_to(os.path.relpath(expected, local.parent))
    assert _detect_plain_copies(tmp_path, slug, "web") == []

    foreign = tmp_path / "foreign.png"
    foreign.write_bytes(expected.read_bytes())
    local.unlink()
    local.symlink_to(os.path.relpath(foreign, local.parent))
    violations = _detect_plain_copies(tmp_path, slug, "web")
    assert len(violations) == 1
    assert violations[0].kind == "broken_symlink"
    assert violations[0].path == local
    assert str(expected) in violations[0].message
