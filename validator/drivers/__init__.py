"""LiveSpec test driver subsystem — public API."""

# @spec FR-007: Slash commands consume one stable Python API for driver execution.
# @spec AC-013: The public surface exposes a single run_capability entry point.


from .degradation import format_degradation_message, infer_stack_slug
from .loader import load_manifest
from .patch_coverage import compute_patch_coverage, git_diff, parse_diff, parse_lcov
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
    "PatchCoverageReport",
    "compute_patch_coverage",
    "format_degradation_message",
    "git_diff",
    "infer_stack_slug",
    "load_manifest",
    "parse_diff",
    "parse_lcov",
    "run_all_capabilities",
    "run_capability",
    "scaffold_custom_driver",
]
