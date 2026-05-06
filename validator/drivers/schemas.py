"""Pydantic v2 schemas for the LiveSpec test driver subsystem."""

# @spec FR-001: YAML driver schema with 5 optional capabilities — .specs/features/016-cross-language-test-driver-architecture/spec.md#fr-001  # noqa: E501
# @spec AC-001: Exactly 5 capability fields — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-001  # noqa: E501
# @spec AC-002: Capabilities optional — .specs/features/016-cross-language-test-driver-architecture/spec.md#ac-002  # noqa: E501

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
    """File-pattern based stack detection rule."""

    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(default_factory=list)


class DriverCapability(BaseModel):
    """Single capability block (coverage / snapshots / properties / mutation)."""

    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    script: str | None = None
    report_path: str | None = None
    threshold: float | None = None
    patch_threshold: float | None = None

    @model_validator(mode="after")
    def _at_least_one_executable(self) -> DriverCapability:
        if self.command is None and self.script is None:
            raise ValueError(
                "DriverCapability requires either 'command' or 'script' (got neither)"
            )
        return self


class DriverManifest(BaseModel):
    """Parsed driver manifest from a YAML file."""

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
        if name not in CAPABILITY_NAMES:
            raise ValueError(f"Unknown capability: {name!r}")
        return getattr(self, name)

    def implemented_capabilities(self) -> list[str]:
        return [n for n in CAPABILITY_NAMES if self.get_capability(n) is not None]


class CapabilityResult(BaseModel):
    """Result of running one capability."""

    model_config = ConfigDict(extra="forbid")

    capability_name: str
    exit_code: int
    report_path: str | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class PatchCoverageReport(BaseModel):
    """Per-file patch coverage ratios computed from lcov + git diff."""

    model_config = ConfigDict(extra="forbid")

    files: dict[str, float] = Field(default_factory=dict)
    overall_ratio: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    measured_lines: int = 0
    covered_lines: int = 0


class CapabilityNotImplementedError(Exception):
    """Raised when a slash command requests a capability the driver does not implement."""

    def __init__(self, driver_name: str, capability: str) -> None:
        super().__init__(f"{capability}: not implemented for {driver_name} driver")
        self.driver_name = driver_name
        self.capability = capability
