"""LiveSpec test driver subsystem — public API."""

# @spec FR-007: Slash commands consume one stable Python API for driver execution.
# @spec AC-013: The public surface exposes a single run_capability entry point.


from .degradation import format_degradation_message, infer_stack_slug
from .loader import load_manifest
from .mutation_report import (
    MutationResult,
    SurvivorRef,
    alternative_for,
    mutation_result_to_dict,
    normalise_cargo_mutants,
    normalise_muter,
    normalise_mutmut,
    normalise_pitest,
    normalise_stryker,
    render_report_entry,
    run_mutation,
    write_mutation_report,
)
from .patch_coverage import (
    compute_patch_coverage,
    evaluate_patch_gate,
    git_diff,
    parse_diff,
    parse_lcov,
    summarise_patch_coverage,
)
from .registry import DriverRegistry
from .runner import run_all_capabilities, run_capability
from .scaffold import DriverFileExistsError, scaffold_custom_driver
from .schemas import (
    CAPABILITY_NAMES,
    CapabilityNotImplementedError,
    CapabilityResult,
    DetectRule,
    DriverCapability,
    DriverManifest,
    PatchCoverageReport,
)
from .test_config import (
    CI_WORKFLOW_PATH,
    DEFAULT_THRESHOLD,
    GeneratedFile,
    TestConfigPlan,
    WriteOutcome,
    generate_ci_workflow,
    generate_test_config,
    go_config,
    jvm_config,
    materialize_files,
    pick_primary_driver,
    python_config,
    rust_config,
    swift_config,
    typescript_config,
    update_conventions_testing_domain,
)

# Export the supported driver API so slash commands and tests rely on one stable surface.
# The __all__ list defines the compatibility contract that downstream imports rely on.
__all__ = [
    "CAPABILITY_NAMES",
    "CI_WORKFLOW_PATH",
    "DEFAULT_THRESHOLD",
    "CapabilityNotImplementedError",
    "CapabilityResult",
    "DetectRule",
    "DriverCapability",
    "DriverFileExistsError",
    "DriverManifest",
    "DriverRegistry",
    "GeneratedFile",
    "MutationResult",
    "PatchCoverageReport",
    "SurvivorRef",
    "TestConfigPlan",
    "WriteOutcome",
    "alternative_for",
    "compute_patch_coverage",
    "evaluate_patch_gate",
    "format_degradation_message",
    "generate_ci_workflow",
    "generate_test_config",
    "git_diff",
    "go_config",
    "infer_stack_slug",
    "jvm_config",
    "load_manifest",
    "materialize_files",
    "mutation_result_to_dict",
    "normalise_cargo_mutants",
    "normalise_muter",
    "normalise_mutmut",
    "normalise_pitest",
    "normalise_stryker",
    "parse_diff",
    "parse_lcov",
    "pick_primary_driver",
    "python_config",
    "render_report_entry",
    "run_all_capabilities",
    "run_capability",
    "run_mutation",
    "rust_config",
    "scaffold_custom_driver",
    "summarise_patch_coverage",
    "swift_config",
    "typescript_config",
    "update_conventions_testing_domain",
    "write_mutation_report",
]
