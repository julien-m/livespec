# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-017)
# @spec(FR-031)
# @spec(FR-032)
# @spec(FR-033)
# @spec(FR-035)
# @spec(FR-037)
# @spec(FR-038)
# @spec(FR-039)

"""Pydantic boundary models for User Journeys v2 YAML sources."""

# @spec FR-001, FR-005, FR-006, FR-017: v2 journey model and validation boundary
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-001
# @spec FR-031, FR-032, FR-033, FR-034: actions, targets, assertions, visuals
# @spec FR-035, FR-037, FR-038, FR-039: visual modes, strict LLM, privacy
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#fr-031

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class JourneyStatus(StrEnum):
    """Lifecycle status for a global v2 journey."""

    DRAFT = "draft"
    ACTIVE = "active"
    MANUAL = "manual"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class CoverageRefKind(StrEnum):
    """Supported requirement reference kinds covered by a journey."""

    AC = "ac"
    FR = "fr"


class RunPolicyValue(StrEnum):
    """Journey selection policy for one execution stage."""

    ALWAYS = "always"
    SMOKE = "smoke"
    IMPACTED = "impacted"
    MANUAL = "manual"
    DISABLED = "disabled"


class RunStage(StrEnum):
    """Execution stages where journey policies may differ."""

    LOCAL = "local"
    PRE_COMMIT = "pre_commit"
    PRE_PUSH = "pre_push"
    CI = "ci"
    NIGHTLY = "nightly"


class JourneyRunner(StrEnum):
    """Native test runners supported by the compiler registry."""

    PLAYWRIGHT = "playwright"
    XCUITEST = "xcuitest"
    MAESTRO = "maestro"
    PYTEST = "pytest"
    CARGO = "cargo"


class JourneyAction(StrEnum):
    """Portable user actions accepted in v2 journey steps."""

    OPEN = "open"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    WAIT = "wait"
    ASSERT = "assert"
    ASSERT_NOT = "assert_not"
    SCREENSHOT = "screenshot"
    BACK = "back"
    PRESS = "press"


class VisualCheckMode(StrEnum):
    """Visual assertion execution mode."""

    NATIVE = "native"
    LLM = "llm"
    NATIVE_THEN_LLM = "native_then_llm"


class PrivacyRetention(StrEnum):
    """Screenshot and visual-evidence retention policy."""

    NONE = "none"
    LOCAL = "local"
    CI_ARTIFACT = "ci_artifact"


class JourneyBaseModel(BaseModel):
    """Base model that rejects unknown YAML keys by default."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CoverageRef(JourneyBaseModel):
    """Qualified feature requirement reference covered by a journey."""

    feature: str = Field(min_length=1)
    kind: CoverageRefKind
    ref: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @field_validator("feature")
    @classmethod
    def validate_feature_slug(cls, value: str) -> str:
        """Validate that refs are feature-qualified, not bare AC/FR IDs."""
        if value.startswith(("AC-", "FR-")):
            raise ValueError("coverage refs require a feature slug, not a requirement id")
        return value

    @field_validator("ref")
    @classmethod
    def validate_ref_prefix(cls, value: str, info: ValidationInfo) -> str:
        """Validate that the reference prefix matches the declared kind."""
        kind = info.data.get("kind")
        if kind is CoverageRefKind.AC and not value.startswith("AC-"):
            raise ValueError("AC coverage refs must start with AC-")
        if kind is CoverageRefKind.FR and not value.startswith("FR-"):
            raise ValueError("FR coverage refs must start with FR-")
        return value


class JourneyTargetRef(JourneyBaseModel):
    """Stable UI target reference used by actions and visual assertions."""

    semantic_id: str | None = None
    test_id: str | None = None
    i18n_key: str | None = None
    role: str | None = None
    name: str | None = None
    accessibility_label: str | None = None
    text: str | None = None
    product_contract: bool = False
    route: str | None = None
    label: str | None = None

    @model_validator(mode="after")
    def validate_stable_target(self) -> JourneyTargetRef:
        """Require stable selectors and explicitly mark product-contract text."""
        has_any_target = any(
            [
                self.semantic_id,
                self.test_id,
                self.i18n_key,
                self.role,
                self.accessibility_label,
                self.text,
                self.route,
                self.label,
            ]
        )
        if not has_any_target:
            raise ValueError("target requires at least one stable locator")
        if self.text and not self.product_contract:
            raise ValueError("text targets require product_contract: true")
        return self


class JourneyViewport(JourneyBaseModel):
    """Viewport dimensions for browser-like journey targets."""

    width: int = Field(gt=0)
    height: int = Field(gt=0)


class JourneyTarget(JourneyBaseModel):
    """Target surface and native runner for a journey."""

    surface: str = Field(min_length=1)
    runner: JourneyRunner
    device: str | None = None
    viewport: JourneyViewport | None = None

    @field_validator("surface")
    @classmethod
    def validate_surface(cls, value: str) -> str:
        """Validate known UI surfaces while keeping runner separate."""
        if value not in {"web", "ios", "watchos", "android", "maestro"}:
            raise ValueError(f"journey_target_unsupported: {value}")
        return value


class BootstrapOverride(JourneyBaseModel):
    """Journey-level bootstrap override under `preconditions.bootstrap`."""

    # @spec FR-003: Optional preconditions.bootstrap override
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-003
    expected_screen: str | None = None
    required_markers: list[str] = Field(default_factory=list)


class Preconditions(JourneyBaseModel):
    """Project state required before running a journey."""

    auth: str | None = None
    fixtures: list[str] = Field(default_factory=list)
    feature_flags: list[str] = Field(default_factory=list)
    mocks: list[str] = Field(default_factory=list)
    bootstrap: BootstrapOverride | None = None


class JourneyStep(JourneyBaseModel):
    """One portable journey action."""

    action: JourneyAction
    target: JourneyTargetRef | None = None
    value: str | None = None
    seconds: int | None = Field(default=None, gt=0)
    key: str | None = None


class VisualCheck(JourneyBaseModel):
    """Deterministic or LLM-backed visual assertion contract."""

    id: str = Field(min_length=1)
    mode: VisualCheckMode
    assertion: str = Field(min_length=1)
    target: JourneyTargetRef
    min_px: int | None = Field(default=None, ge=0)
    prompt: str | None = None
    blocking: bool = False

    @model_validator(mode="after")
    def validate_llm_contract(self) -> VisualCheck:
        """Require a prompt when a visual check needs LLM evaluation."""
        if self.mode in {VisualCheckMode.LLM, VisualCheckMode.NATIVE_THEN_LLM} and not self.prompt:
            raise ValueError("LLM visual checks require prompt")
        return self


class PrivacyPolicy(JourneyBaseModel):
    """Privacy policy for screenshots and LLM visual evaluation."""

    llm_allowed: bool = False
    retention: PrivacyRetention = PrivacyRetention.NONE
    masking: list[str] = Field(default_factory=list)
    local_only: bool = False


class JourneySourceV2(JourneyBaseModel):
    """Canonical User Journeys v2 YAML source document."""

    schema_version: Literal[2]
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: JourneyStatus = JourneyStatus.ACTIVE
    description: str = Field(min_length=1)
    covers: list[CoverageRef] = Field(min_length=1)
    run_policy: dict[RunStage, RunPolicyValue]
    targets: list[JourneyTarget] = Field(min_length=1)
    preconditions: Preconditions = Field(default_factory=Preconditions)
    steps: list[JourneyStep] = Field(min_length=1)
    visual_checks: list[VisualCheck] = Field(default_factory=list)
    privacy: PrivacyPolicy = Field(default_factory=PrivacyPolicy)

    @model_validator(mode="after")
    def validate_privacy_for_visual_checks(self) -> JourneySourceV2:
        """Block LLM visual checks unless the source explicitly opts in."""
        has_llm_check = any(
            check.mode in {VisualCheckMode.LLM, VisualCheckMode.NATIVE_THEN_LLM}
            for check in self.visual_checks
        )
        if has_llm_check and not self.privacy.llm_allowed:
            raise ValueError("LLM visual checks require privacy.llm_allowed: true")
        return self


__all__ = [
    "BootstrapOverride",
    "CoverageRef",
    "CoverageRefKind",
    "JourneyAction",
    "JourneyRunner",
    "JourneySourceV2",
    "JourneyStatus",
    "JourneyStep",
    "JourneyTarget",
    "JourneyTargetRef",
    "Preconditions",
    "PrivacyPolicy",
    "PrivacyRetention",
    "RunPolicyValue",
    "RunStage",
    "VisualCheck",
    "VisualCheckMode",
]
