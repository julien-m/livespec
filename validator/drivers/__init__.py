"""LiveSpec test driver subsystem — public API."""

# @spec FR-007: Stable Python API for slash commands — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-007  # noqa: E501
# @spec AC-013: Single run_capability entry point — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-013  # noqa: E501


from .degradation import format_degradation_message, infer_stack_slug
from .loader import load_manifest
from .patch_coverage import compute_patch_coverage, git_diff, parse_diff, parse_lcov
from .registry import DriverRegistry
from .runner import run_capability
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
    "run_capability",
    "scaffold_custom_driver",
]
