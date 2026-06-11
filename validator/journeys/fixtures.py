# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-008)
# @spec(FR-009)

"""Project-local journey fixtures contract: models, loader, derivation, scaffold."""

# @spec FR-001: Contract models and loader
# — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-001
# @spec FR-002: Bootstrap plan derivation
# — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-002

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]  # PyYAML has no typed metadata.
from pydantic import Field, ValidationError

from ._fixtures_helpers import render_contract_skeleton, scaffold_fixtures_contract
from .models import JourneyIssue, JourneySeverity
from .paths import fixtures_contract_path
from .schema import JourneyBaseModel, JourneySourceV2

# Shared compiler/runner constant: the generated XCUITest helper emits this prefix
# in XCTFail output so the runner can reclassify bootstrap failures without
# parsing .xcresult bundles.
BOOTSTRAP_FAILURE_PREFIX = "JOURNEY_BOOTSTRAP_FAILURE:"
# Default 15s / bounds 1-60 keep each individual wait inside the 120s XCUITest
# runner timeout, even with a ready marker, a screen, and a few markers stacked.
DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS = 15
MIN_BOOTSTRAP_TIMEOUT_SECONDS = 1
MAX_BOOTSTRAP_TIMEOUT_SECONDS = 60


class BootstrapDefaults(JourneyBaseModel):
    """App-level bootstrap contract shared by all journeys."""

    ready_marker: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(
        default=DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS,
        ge=MIN_BOOTSTRAP_TIMEOUT_SECONDS,
        le=MAX_BOOTSTRAP_TIMEOUT_SECONDS,
    )


class FixtureContract(JourneyBaseModel):
    """One declared fixture id with its per-surface bootstrap guarantees."""

    surfaces: list[str] = Field(min_length=1)
    expected_screen: dict[str, str] = Field(default_factory=dict)
    required_markers: dict[str, list[str]] = Field(default_factory=dict)


class MockContract(JourneyBaseModel):
    """One declared mock id with the surfaces it supports."""

    surfaces: list[str] = Field(min_length=1)


class FixturesContractV1(JourneyBaseModel):
    """Root of the project-local fixtures contract (.specs/journeys/fixtures.yaml)."""

    schema_version: Literal[1]
    bootstrap: BootstrapDefaults | None = None
    fixtures: dict[str, FixtureContract] = Field(default_factory=dict)
    mocks: dict[str, MockContract] = Field(default_factory=dict)


class BootstrapPlan(JourneyBaseModel):
    """Resolved single-surface bootstrap wait plan consumed by the compiler."""

    ready_marker: str | None = None
    expected_screen: str | None = None
    required_markers: list[str] = Field(default_factory=list)
    timeout_seconds: int = DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS


class BootstrapAmbiguityError(Exception):
    """Raised when fixtures derive two or more distinct expected screens."""

    def __init__(self, screens: list[str]) -> None:
        super().__init__(
            "ambiguous expected_screen derived from fixtures: "
            + ", ".join(sorted(screens))
            + " — declare preconditions.bootstrap.expected_screen to resolve"
        )
        self.screens = sorted(screens)


def resolve_bootstrap(
    source: JourneySourceV2,
    contract: FixturesContractV1 | None,
    surface: str,
) -> BootstrapPlan | None:
    """Derive the deterministic bootstrap wait plan for one journey surface.

    Args:
        source: Parsed v2 journey source.
        contract: Parsed fixtures contract, or None when absent.
        surface: The journey's target surface (only its maps are read).

    Returns:
        The resolved plan, or None when the journey declares no fixtures/mocks
        or when the resolved plan would carry zero waits (collapse rule — the
        codegen must stay byte-identical when there is nothing to wait for).

    Raises:
        BootstrapAmbiguityError: When fixtures derive >=2 distinct expected
            screens for the surface and the journey declares no override.
    """
    # @spec FR-002: resolve_bootstrap derivation rules
    # — .specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-002
    preconditions = source.preconditions
    if not preconditions.fixtures and not preconditions.mocks:
        return None
    ready_marker: str | None = None
    timeout_seconds = DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS
    screens: set[str] = set()
    markers: set[str] = set()
    if contract is not None:
        if contract.bootstrap is not None:
            ready_marker = contract.bootstrap.ready_marker.get(surface)
            timeout_seconds = contract.bootstrap.timeout_seconds
        for fixture_id in preconditions.fixtures:
            fixture = contract.fixtures.get(fixture_id)
            # Unknown ids are a validator concern (journey_fixture_unknown);
            # derivation stays pure and skips them.
            if fixture is None:
                continue
            screen = fixture.expected_screen.get(surface)
            if screen is not None:
                screens.add(screen)
            markers.update(fixture.required_markers.get(surface, []))
    override = preconditions.bootstrap
    expected_screen: str | None
    if override is not None and override.expected_screen is not None:
        # Business rule: the journey override always replaces the derived
        # screen and is the only way to resolve an ambiguous derivation.
        expected_screen = override.expected_screen
    elif len(screens) > 1:
        raise BootstrapAmbiguityError(sorted(screens))
    else:
        expected_screen = next(iter(screens), None)
    if override is not None:
        markers.update(override.required_markers)
    required_markers = sorted(markers)
    # Collapse rule (plan review finding #2): a plan with zero waits is None —
    # never an all-empty BootstrapPlan — so fixture journeys without bootstrap
    # guarantees compile byte-identically and no empty helper is emitted.
    if ready_marker is None and expected_screen is None and not required_markers:
        return None
    return BootstrapPlan(
        ready_marker=ready_marker,
        expected_screen=expected_screen,
        required_markers=required_markers,
        timeout_seconds=timeout_seconds,
    )


def read_fixtures_contract(
    project_root: Path,
) -> tuple[FixturesContractV1 | None, JourneyIssue | None]:
    """Read and validate the project fixtures contract.

    Args:
        project_root: Project root containing `.specs/`.

    Returns:
        `(contract, None)` on success, `(None, None)` when the file is absent,
        and `(None, issue)` with a `journey_fixtures_contract_invalid` issue on
        unreadable YAML, a non-mapping root, or a schema violation.
    """
    contract, _, issue = read_fixtures_contract_with_hash(project_root)
    return contract, issue


def read_fixtures_contract_with_hash(
    project_root: Path,
) -> tuple[FixturesContractV1 | None, str, JourneyIssue | None]:
    """Read the contract and its content hash from a single file read.

    The compiler needs both the parsed contract and the content hash; reading
    the bytes once keeps the hash consistent with the parsed content even if
    the file changes between calls.

    Args:
        project_root: Project root containing `.specs/`.

    Returns:
        `(contract, sha256, None)` on success, `(None, "", None)` when absent,
        and `(None, hash-or-empty, issue)` on invalid input.
    """
    path = fixtures_contract_path(project_root)
    if not path.exists():
        return None, "", None
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return None, "", _invalid_contract_issue(str(exc), path)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    try:
        data = yaml.safe_load(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, digest, _invalid_contract_issue(str(exc), path)
    if not isinstance(data, dict):
        return None, digest, _invalid_contract_issue("contract root must be a mapping", path)
    try:
        return FixturesContractV1.model_validate(data), digest, None
    except ValidationError as exc:
        return None, digest, _invalid_contract_issue(str(exc), path)


def fixtures_contract_hash(project_root: Path) -> str:
    """Return the sha256 of the contract file bytes, or "" when absent.

    Used by the runner staleness check against `CompiledManifest.fixtures_contract_hash`.
    """
    path = fixtures_contract_path(project_root)
    if not path.exists():
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        # An unreadable contract cannot match any recorded hash; "" forces the
        # same journey_compiled_stale outcome as a deleted contract.
        return ""


def _invalid_contract_issue(message: str, path: Path) -> JourneyIssue:
    """Create the blocking issue for an unparseable or invalid contract."""
    return JourneyIssue(
        code="journey_fixtures_contract_invalid",
        severity=JourneySeverity.ERROR,
        message=message,
        path=path,
    )


__all__ = [
    "BOOTSTRAP_FAILURE_PREFIX",
    "DEFAULT_BOOTSTRAP_TIMEOUT_SECONDS",
    "MAX_BOOTSTRAP_TIMEOUT_SECONDS",
    "MIN_BOOTSTRAP_TIMEOUT_SECONDS",
    "BootstrapAmbiguityError",
    "BootstrapDefaults",
    "BootstrapPlan",
    "FixtureContract",
    "FixturesContractV1",
    "MockContract",
    "fixtures_contract_hash",
    "read_fixtures_contract",
    "read_fixtures_contract_with_hash",
    "render_contract_skeleton",
    "resolve_bootstrap",
    "scaffold_fixtures_contract",
]
