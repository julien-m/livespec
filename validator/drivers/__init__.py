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

# Export the supported driver API so slash commands and tests rely on one stable surface.
__all__ = [
    "CAPABILITY_NAMES",
    "CapabilityNotImplementedError",
    "CapabilityResult",
    "DetectRule",
    "DriverCapability",
    "DriverFileExistsError",
    "DriverManifest",
    "DriverRegistry",
    "MutationResult",
    "PatchCoverageReport",
    "SurvivorRef",
    "alternative_for",
    "compute_patch_coverage",
    "evaluate_patch_gate",
    "format_degradation_message",
    "git_diff",
    "infer_stack_slug",
    "load_manifest",
    "mutation_result_to_dict",
    "normalise_cargo_mutants",
    "normalise_muter",
    "normalise_mutmut",
    "normalise_pitest",
    "normalise_stryker",
    "parse_diff",
    "parse_lcov",
    "render_report_entry",
    "run_all_capabilities",
    "run_capability",
    "run_mutation",
    "scaffold_custom_driver",
    "summarise_patch_coverage",
    "write_mutation_report",
]
