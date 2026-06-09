# LiveSpec traceability anchors
# @spec(FR-001)

"""Pydantic v2 schemas for the LiveSpec test driver subsystem."""

# @spec FR-001: YAML driver schema with detect rules plus optional capability blocks.
# @spec AC-001: Driver manifests expose detect plus the executable capability fields.
# @spec AC-002: Capability blocks are optional and omitted ones are treated as unsupported.

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

CAPABILITY_NAMES: tuple[str, ...] = (
    "coverage",
    "snapshots",
    "properties",
    "mutation",
)


class DetectRule(BaseModel):
    """File-pattern based stack detection rule.

    Args:
        files: Top-level glob patterns used to decide whether a driver matches.
    """

    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(default_factory=list)


class DriverCapability(BaseModel):
    """Executable capability block for one driver feature.

    Args:
        command: Shell command to execute for the capability.
        script: Relative or absolute script path to execute instead of ``command``.
        report_path: Optional path to an artifact the capability must produce.
        threshold: Optional overall threshold for the capability output.
        patch_threshold: Optional threshold for changed-line coverage gating.
    """

    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    script: str | None = None
    report_path: str | None = None
    threshold: float | None = None
    patch_threshold: float | None = None

    @model_validator(mode="after")
    def _at_least_one_executable(self) -> DriverCapability:
        """Reject capability blocks that do not define any executable action."""
        if self.command is None and self.script is None:
            raise ValueError("DriverCapability requires either 'command' or 'script' (got neither)")
        return self


class DriverManifest(BaseModel):
    """Parsed driver manifest from a YAML file.

    Args:
        name: Stable driver name used for lookup and override matching.
        detect: File-pattern rules used to match the current repository.
        coverage: Optional coverage capability configuration.
        snapshots: Optional snapshot testing capability configuration.
        properties: Optional property-based testing capability configuration.
        mutation: Optional mutation testing capability configuration.
        source_path: Resolved manifest path assigned by the loader after parsing.
        is_custom: Whether the manifest came from ``.specs/drivers``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    detect: DetectRule = Field(default_factory=DetectRule)
    coverage: DriverCapability | None = None
    snapshots: DriverCapability | None = None
    properties: DriverCapability | None = None
    mutation: DriverCapability | None = None

    # Source path is set by the loader after parsing (not part of the YAML).
    source_path: Path | None = Field(default=None, exclude=True)
    is_custom: bool = Field(default=False, exclude=True)

    def get_capability(self, name: str) -> DriverCapability | None:
        """Return a named capability block.

        Args:
            name: Capability name from ``CAPABILITY_NAMES``.

        Returns:
            The configured capability block, if present.

        Raises:
            ValueError: If ``name`` is not a supported capability identifier.
        """
        if name not in CAPABILITY_NAMES:
            raise ValueError(f"Unknown capability: {name!r}")
        return getattr(self, name)

    def implemented_capabilities(self) -> list[str]:
        """List the capabilities configured on this manifest.

        Returns:
            Capability names whose blocks are present in the manifest.
        """
        return [n for n in CAPABILITY_NAMES if self.get_capability(n) is not None]


class CapabilityResult(BaseModel):
    """Result of running one capability.

    Args:
        capability_name: Name of the executed capability.
        exit_code: Process exit code or synthesized failure code.
        report_path: Optional report artifact path declared by the capability.
        stdout: Captured standard output from the subprocess.
        stderr: Captured standard error from the subprocess.
    """

    model_config = ConfigDict(extra="forbid")

    capability_name: str
    exit_code: int
    report_path: str | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        """Return whether the capability completed successfully."""
        return self.exit_code == 0


class PatchCoverageReport(BaseModel):
    """Patch coverage ratios computed from ``lcov.info`` and a unified diff.

    Args:
        files: Per-file changed-line coverage ratios.
        overall_ratio: Aggregate changed-line coverage ratio across all files.
        warnings: Non-fatal parsing or coverage data issues.
        measured_lines: Number of changed lines that had measurable coverage data.
        covered_lines: Number of measured changed lines that were covered.
    """

    model_config = ConfigDict(extra="forbid")

    files: dict[str, float] = Field(default_factory=dict)
    overall_ratio: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    measured_lines: int = 0
    covered_lines: int = 0


class CapabilityNotImplementedError(Exception):
    """Raised when a driver does not implement the requested capability.

    Args:
        driver_name: Name of the driver that lacks the capability.
        capability: Capability name requested by the caller.
    """

    def __init__(self, driver_name: str, capability: str) -> None:
        super().__init__(f"{capability}: not implemented for {driver_name} driver")
        self.driver_name = driver_name
        self.capability = capability
