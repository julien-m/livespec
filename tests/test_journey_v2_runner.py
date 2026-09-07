# @spec(AC-015)

# LiveSpec traceability anchors
# @spec(AC-016)
# @spec(AC-025)
# @spec(AC-027)
# @spec(AC-028)
# @spec(AC-031)

"""Tests for compiled-only User Journeys v2 run semantics."""

# Explicit reexports preserve pytest node IDs and public fixture imports.
from tests._journey_v2_runner_01 import (
    _install_simctl_fake,
    _JsonValue,
    _RunKwargs,
    _setup_compiled,
    _setup_watch_xcuitest_compiled_project,
    _setup_xcuitest_compiled_project,
    test_run_journeys_emits_native_runner_progress_to_stderr,
    test_run_journeys_executes_manifest_artifacts_without_compiling,
    test_run_journeys_executes_playwright_artifact,
    test_run_journeys_fails_old_compiler_manifest_without_recompiling,
    test_run_journeys_fails_stale_manifest_without_recompiling,
    test_run_journeys_preserves_native_runner_stdout_and_stderr_on_failure,
    test_run_journeys_records_playwright_run_without_udid,
    test_run_journeys_records_run_even_when_native_run_fails,
    test_run_journeys_reports_manual_and_disabled_without_execution,
    test_run_journeys_reports_native_runner_failure,
    test_run_journeys_reports_timeout_with_captured_native_output,
)
from tests._journey_v2_runner_02 import (
    test_run_journeys_executes_xcuitest_with_only_testing,
    test_run_journeys_prefers_iphone_family_before_shutdown_ipad,
    test_run_journeys_prefers_shutdown_iphone_over_newer_booted_iphone,
    test_run_journeys_prefers_shutdown_simulator_over_booted_stale_device,
    test_run_journeys_records_xcuitest_destination_and_udid,
    test_run_journeys_uses_bounded_xcuitest_timeout,
    test_run_journeys_uses_surfaces_yaml_for_shared_watch_xcuitest_artifact,
    test_run_journeys_writes_last_run_receipt,
)
from tests._journey_v2_runner_03 import (
    test_run_journeys_executes_watch_xcuitest_on_available_watch_simulator,
    test_run_journeys_keeps_native_run_failed_without_prefix,
    test_run_journeys_prefers_shutdown_watch_over_newer_booted_watch,
    test_run_journeys_reclassifies_bootstrap_failure_prefix,
    test_run_journeys_rejects_missing_compiled_artifact,
    test_run_journeys_rejects_unsupported_manifest_runner,
    test_run_journeys_reports_no_available_simulator_for_matching_platform,
    test_run_journeys_reports_simulator_discovery_errors,
    test_run_journeys_supports_injected_executor,
)
from tests._journey_v2_runner_04 import (
    test_run_journeys_fails_stale_contract_hash_without_recompiling,
    test_run_journeys_fails_when_contract_deleted_after_compile,
    test_run_journeys_ignores_prefix_on_passing_run,
    test_run_journeys_reports_compiler_stale_before_contract_hash,
)

__all__ = [
    "_JsonValue",
    "_RunKwargs",
    "_install_simctl_fake",
    "_setup_compiled",
    "_setup_watch_xcuitest_compiled_project",
    "_setup_xcuitest_compiled_project",
    "test_run_journeys_emits_native_runner_progress_to_stderr",
    "test_run_journeys_executes_manifest_artifacts_without_compiling",
    "test_run_journeys_executes_playwright_artifact",
    "test_run_journeys_executes_watch_xcuitest_on_available_watch_simulator",
    "test_run_journeys_executes_xcuitest_with_only_testing",
    "test_run_journeys_fails_old_compiler_manifest_without_recompiling",
    "test_run_journeys_fails_stale_contract_hash_without_recompiling",
    "test_run_journeys_fails_stale_manifest_without_recompiling",
    "test_run_journeys_fails_when_contract_deleted_after_compile",
    "test_run_journeys_ignores_prefix_on_passing_run",
    "test_run_journeys_keeps_native_run_failed_without_prefix",
    "test_run_journeys_prefers_iphone_family_before_shutdown_ipad",
    "test_run_journeys_prefers_shutdown_iphone_over_newer_booted_iphone",
    "test_run_journeys_prefers_shutdown_simulator_over_booted_stale_device",
    "test_run_journeys_prefers_shutdown_watch_over_newer_booted_watch",
    "test_run_journeys_preserves_native_runner_stdout_and_stderr_on_failure",
    "test_run_journeys_reclassifies_bootstrap_failure_prefix",
    "test_run_journeys_records_playwright_run_without_udid",
    "test_run_journeys_records_run_even_when_native_run_fails",
    "test_run_journeys_records_xcuitest_destination_and_udid",
    "test_run_journeys_rejects_missing_compiled_artifact",
    "test_run_journeys_rejects_unsupported_manifest_runner",
    "test_run_journeys_reports_compiler_stale_before_contract_hash",
    "test_run_journeys_reports_manual_and_disabled_without_execution",
    "test_run_journeys_reports_native_runner_failure",
    "test_run_journeys_reports_no_available_simulator_for_matching_platform",
    "test_run_journeys_reports_simulator_discovery_errors",
    "test_run_journeys_reports_timeout_with_captured_native_output",
    "test_run_journeys_supports_injected_executor",
    "test_run_journeys_uses_bounded_xcuitest_timeout",
    "test_run_journeys_uses_surfaces_yaml_for_shared_watch_xcuitest_artifact",
    "test_run_journeys_writes_last_run_receipt",
]
