"""Visual feature gate for ``/spec-check``, ``/spec-fix``, ``/spec-test``,
``/spec-feature``.

# @spec FR-100: Deterministic visual-feature detection — feature TBD (visual-gate-fix cycle)
# @spec FR-101: Penflow + design-alignment aggregation — feature TBD (visual-gate-fix cycle)
# @spec FR-102: No-copy registry invariant — feature TBD (visual-gate-fix cycle)
# @spec FR-103: Runtime-under-design-screens detector — feature TBD (visual-gate-fix cycle)

The visual gate is the *single* checkpoint that the four user-facing skill
flows must call to decide whether a visual feature can be marked done. It
aggregates:

* Penflow workspace status (``penflow_contract.get_penflow_contract_status``).
* Design-alignment compare reports for any screen present in
  ``.specs/features/<slug>/design-alignment/<screen>/``.
* Canonical registry-link contract (``registry_links``): symlink-default
  with manifest fallback, no physical copy, no runtime capture under
  ``.specs/design/screens/``.
* Legacy ``baseline.manifest.yml`` staleness rows
  (``screens[].mockup_version``) when present.

The module is import-safe (no IO at import time) and exits with the codes
declared in :mod:`validator.cli_exit_codes`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from validator.design_alignment.core import compare_contract_files
from validator.design_alignment.models import AlignmentResult
from validator.penflow_contract import (
    PenflowContractStatus,
    get_penflow_contract_status,
)
from validator.registry_links import (
    BASELINES_DIRNAME,
    DESIGN_REGISTRY_DIR,
    SCREENS_DIRNAME,
    LinkViolation,
    ManifestStatus,
    detect_link_capability,
    expected_feature_local_path,
    expected_registry_baseline_path,
    expected_registry_mockup_path,
    find_runtime_misplaced_under_design_screens,
    sha256_of,
    validate_manifest,
)
from validator.visual_evidence import (
    MAX_DESIGN_FIDELITY_THRESHOLD_PERCENT,
    VisualComparison,
    VisualReceipt,
    VisualReceiptError,
    compare_visual_images,
    verify_visual_receipt,
    write_visual_receipt,
)

Classification = Literal["VISUAL", "NON_VISUAL", "CONFLICT"]
Verdict = Literal["PASS", "FAIL", "BLOCKED"]
GateCommand = Literal["spec-check", "spec-fix", "spec-test", "spec-feature"]
GateTarget = Literal["web", "ios", "android", "tauri"]


def _as_mapping(value: object) -> dict[str, object] | None:
    """Return a string-keyed mapping when dynamic JSON/YAML input is object-like."""
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


def _as_list(value: object) -> list[object] | None:
    """Return a list when dynamic JSON/YAML input is list-like."""
    if not isinstance(value, list):
        return None
    return cast(list[object], value)


@dataclass(frozen=True)
class VisualFeatureSignals:
    """Six deterministic detection signals (P0-A decision table)."""

    s1_spec_marker: bool
    s1_spec_explicit_false: bool
    s2_feature_screens: bool
    s3_penflow_workspace: bool
    s4_flow_ui_contract: bool
    s5_feature_baselines: bool
    s6_surfaces_yaml: bool

    @property
    def strong_count(self) -> int:
        return int(self.s2_feature_screens) + int(self.s3_penflow_workspace) + int(
            self.s4_flow_ui_contract
        )

    @property
    def weak_count(self) -> int:
        return int(self.s5_feature_baselines) + int(self.s6_surfaces_yaml)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation."""
        return {
            "s1_spec_marker": self.s1_spec_marker,
            "s1_spec_explicit_false": self.s1_spec_explicit_false,
            "s2_feature_screens": self.s2_feature_screens,
            "s3_penflow_workspace": self.s3_penflow_workspace,
            "s4_flow_ui_contract": self.s4_flow_ui_contract,
            "s5_feature_baselines": self.s5_feature_baselines,
            "s6_surfaces_yaml": self.s6_surfaces_yaml,
            "strong_count": self.strong_count,
            "weak_count": self.weak_count,
        }


@dataclass(frozen=True)
class VisualClassification:
    """Classification + machine-readable reason for downstream consumers."""

    classification: Classification
    signals: VisualFeatureSignals
    conflict_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "signals": self.signals.to_dict(),
            "conflict_reason": self.conflict_reason,
        }


def _alignment_results_factory() -> list[AlignmentResult]:
    return []


def _link_violations_factory() -> list[LinkViolation]:
    return []


def _path_list_factory() -> list[Path]:
    return []


def _str_list_factory() -> list[str]:
    return []


@dataclass(frozen=True)
class GateReport:
    """Complete machine-readable gate report.

    The verdict is computed deterministically from the aggregated parts:
    a non-empty ``link_violations`` or ``runtime_in_design_screens_violations``
    forces FAIL; a ``CONFLICT`` classification or missing prerequisite forces
    BLOCKED; any design-alignment FAIL forces FAIL; otherwise PASS.
    """

    feature_slug: str
    command: GateCommand
    target: GateTarget | None
    classification: Classification
    signals: VisualFeatureSignals
    verdict: Verdict
    conflict_reason: str | None
    penflow: PenflowContractStatus | None
    alignment: list[AlignmentResult] = field(default_factory=_alignment_results_factory)
    link_violations: list[LinkViolation] = field(default_factory=_link_violations_factory)
    runtime_in_design_screens_violations: list[Path] = field(default_factory=_path_list_factory)
    manifest_status: ManifestStatus | None = None
    visual_evidence: dict[str, object] | None = None
    missing_artifacts: list[str] = field(default_factory=_str_list_factory)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_slug": self.feature_slug,
            "command": self.command,
            "target": self.target,
            "classification": self.classification,
            "signals": self.signals.to_dict(),
            "verdict": self.verdict,
            "conflict_reason": self.conflict_reason,
            "penflow": self.penflow.to_dict() if self.penflow else None,
            "alignment": [r.to_dict() for r in self.alignment],
            "link_violations": [v.to_dict() for v in self.link_violations],
            "runtime_in_design_screens_violations": [
                str(p) for p in self.runtime_in_design_screens_violations
            ],
            "manifest_status": _manifest_status_to_dict(self.manifest_status),
            "visual_evidence": self.visual_evidence,
            "missing_artifacts": list(self.missing_artifacts),
        }


def certify_visual_evidence(
    *,
    project_root: Path,
    feature_slug: str,
    command: GateCommand,
    target: GateTarget,
    run_id: str,
    threshold_percent: float = 5.0,
) -> dict[str, object]:
    """Produce a visual evidence receipt for mockup/runtime PNG comparisons.

    Args:
        project_root: Project root containing `.specs/`.
        feature_slug: Feature directory slug.
        command: Calling LiveSpec command.
        target: UI target.
        run_id: Runtime capture run id under the feature `run/` directory.
        threshold_percent: Design fidelity threshold.

    Returns:
        Machine-readable certification payload containing verdict and receipt.
    """
    if threshold_percent < 0 or threshold_percent > MAX_DESIGN_FIDELITY_THRESHOLD_PERCENT:
        return {
            "feature_slug": feature_slug,
            "command": command,
            "target": target,
            "run_id": run_id,
            "verdict": "BLOCKED",
            "missing_artifacts": [
                "threshold_percent must be between 0 and "
                f"{MAX_DESIGN_FIDELITY_THRESHOLD_PERCENT:g}"
            ],
            "receipt_path": None,
        }
    mockup_dir = project_root / DESIGN_REGISTRY_DIR / "screens" / feature_slug
    runtime_dir = (
        project_root
        / ".specs"
        / "features"
        / feature_slug
        / "run"
        / run_id
        / target
    )
    evidence_dir = (
        project_root
        / ".specs"
        / "features"
        / feature_slug
        / "run"
        / run_id
        / "visual-evidence"
    )
    mockups = sorted(mockup_dir.glob("*.png")) if mockup_dir.is_dir() else []
    missing: list[str] = []
    comparisons: list[VisualComparison] = []
    if not mockups:
        missing.append(str(mockup_dir))
    for mockup in mockups:
        runtime = runtime_dir / mockup.name
        if not runtime.exists():
            missing.append(str(runtime))
            continue
        screen = mockup.stem
        comparisons.append(
            compare_visual_images(
                project_root=project_root,
                feature_slug=feature_slug,
                screen=screen,
                target=target,
                comparison_kind="mockup_runtime",
                reference_path=mockup,
                actual_path=runtime,
                threshold_percent=threshold_percent,
                diff_path=evidence_dir / f"{screen}.mockup-runtime.diff.png",
            )
        )
        baseline = (
            project_root
            / DESIGN_REGISTRY_DIR
            / BASELINES_DIRNAME
            / feature_slug
            / target
            / mockup.name
        )
        if baseline.exists():
            comparisons.append(
                compare_visual_images(
                    project_root=project_root,
                    feature_slug=feature_slug,
                    screen=screen,
                    target=target,
                    comparison_kind="baseline_runtime",
                    reference_path=baseline,
                    actual_path=runtime,
                    threshold_percent=0.0,
                    diff_path=evidence_dir / f"{screen}.baseline-runtime.diff.png",
                )
            )
            comparisons.append(
                compare_visual_images(
                    project_root=project_root,
                    feature_slug=feature_slug,
                    screen=screen,
                    target=target,
                    comparison_kind="mockup_baseline",
                    reference_path=mockup,
                    actual_path=baseline,
                    threshold_percent=threshold_percent,
                    diff_path=evidence_dir / f"{screen}.mockup-baseline.diff.png",
                )
            )
    if missing:
        return {
            "feature_slug": feature_slug,
            "command": command,
            "target": target,
            "run_id": run_id,
            "verdict": "BLOCKED",
            "missing_artifacts": missing,
            "receipt_path": None,
        }
    receipt_path = write_visual_receipt(
        project_root=project_root,
        feature_slug=feature_slug,
        command=command,
        target=target,
        run_id=run_id,
        comparisons=comparisons,
        output_dir=evidence_dir,
    )
    receipt = verify_visual_receipt(receipt_path, project_root=project_root)
    return {
        "feature_slug": feature_slug,
        "command": command,
        "target": target,
        "run_id": run_id,
        "verdict": receipt.verdict,
        "receipt_path": _project_relative(project_root, receipt_path),
        "comparison_count": len(receipt.comparisons),
        "missing_artifacts": [],
    }


def _manifest_status_to_dict(status: ManifestStatus | None) -> dict[str, object] | None:
    if status is None:
        return None
    return {
        "path": str(status.path),
        "found": status.found,
        "feature_slug": status.feature_slug,
        "target": status.target,
        "parse_error": status.parse_error,
        "entries": [
            {
                "screen": e.screen,
                "kind": e.kind,
                "registry_path": str(e.registry_path),
                "feature_local_path": (
                    str(e.feature_local_path) if e.feature_local_path else None
                ),
                "sha256": e.sha256,
                "approved_at": e.approved_at,
            }
            for e in status.entries
        ],
    }


# ---------------------------------------------------------------------------
# Detection (P0-A)
# ---------------------------------------------------------------------------


def _feature_dir(project_root: Path, feature_slug: str) -> Path:
    return project_root / ".specs" / "features" / feature_slug


def _read_spec_visual_marker(spec_md: Path) -> tuple[bool, bool]:
    """Return ``(has_marker, explicit_false)`` from ``spec.md`` front-matter
    or tags.

    Looks for either ``visual:`` or ``surface:`` keys in YAML front-matter,
    or inline tags ``[visual]``/``[surface=...]``. Returns ``(False, False)``
    when no marker is present at all.
    """
    if not spec_md.exists():
        return False, False
    try:
        raw = spec_md.read_text(encoding="utf-8")
    except OSError:
        return False, False
    # Cheap parse: front-matter between leading ``---`` delimiters.
    lines = raw.splitlines()
    if not lines or not lines[0].startswith("---"):
        return _scan_inline_markers(raw)
    end_idx = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end_idx is None:
        return _scan_inline_markers(raw)
    front_matter = "\n".join(lines[1:end_idx])
    has_marker = False
    explicit_false = False
    for line in front_matter.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("visual:"):
            has_marker = True
            value = stripped.split(":", 1)[1].strip()
            if value in ("false", "no", "0"):
                explicit_false = True
        elif stripped.startswith("surface:"):
            has_marker = True
    inline_marker, inline_false = _scan_inline_markers(raw)
    return has_marker or inline_marker, explicit_false or inline_false


def _scan_inline_markers(raw: str) -> tuple[bool, bool]:
    lowered = raw.lower()
    has_marker = "[visual]" in lowered or "[surface=" in lowered or "visual:" in lowered
    explicit_false = "[visual:false]" in lowered or "visual: false" in lowered
    return has_marker, explicit_false


def _has_feature_scoped_penflow(project_root: Path, feature_slug: str) -> bool:
    """Return True only when the Penflow workspace carries evidence for this slug.

    Project-level ``penflow/`` alone is no longer sufficient — otherwise every
    feature in a Penflow-enabled project gets a free strong visual signal,
    which silently turns CONFLICT into VISUAL and hides missing artefacts.

    Accepted feature-scoped signals (any one is enough):
      * ``penflow/<slug>/`` directory exists.
      * ``penflow/features/<slug>/`` directory exists.
      * ``penflow/projects/<slug>/`` directory exists.
      * Top-level ``penflow/index.yaml`` / ``penflow/index.json`` contains the
        slug as a workspace entry id (string match against the slug).
    """
    penflow_root = project_root / "penflow"
    if not penflow_root.is_dir():
        return False
    for candidate in (
        penflow_root / feature_slug,
        penflow_root / "features" / feature_slug,
        penflow_root / "projects" / feature_slug,
    ):
        if candidate.is_dir():
            return True
    for index_name in ("index.yaml", "index.yml", "index.json"):
        idx = penflow_root / index_name
        if not idx.exists():
            continue
        try:
            raw = idx.read_text(encoding="utf-8")
        except OSError:
            continue
        if feature_slug in raw:
            return True
    return False


def _surfaces_yaml_mentions_feature(project_root: Path, feature_slug: str) -> bool:
    """Return True only when ``.specs/surfaces.yaml`` actually references the slug.

    Project-level ``surfaces.yaml`` describes every UI surface — its mere
    existence is not enough to flag a specific feature as visual. We parse it
    and accept any surface whose ``id`` / ``feature`` / ``features`` /
    declared keys reference ``feature_slug``.
    """
    surfaces_path = project_root / ".specs" / "surfaces.yaml"
    if not surfaces_path.exists():
        return False
    try:
        raw = surfaces_path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Cheap substring scan first — avoids YAML import on the negative path.
    if feature_slug not in raw:
        return False
    try:
        import yaml  # type: ignore[import-untyped]

        parsed_raw: object = yaml.safe_load(raw) or {}
    except Exception:  # pragma: no cover - bad YAML → treat as no scoped mention
        return False
    parsed = _as_mapping(parsed_raw)
    if parsed is None:
        return False
    surfaces = _as_list(parsed.get("surfaces"))
    if surfaces is not None:
        for entry_raw in surfaces:
            entry = _as_mapping(entry_raw)
            if entry is None:
                continue
            for key in ("id", "feature", "feature_slug", "slug"):
                value = entry.get(key)
                if isinstance(value, str) and feature_slug in value:
                    return True
            features = _as_list(entry.get("features"))
            if features is not None and any(
                isinstance(f, str) and feature_slug in f for f in features
            ):
                return True
    # Fallback: top-level features map keyed by slug.
    features_top = parsed.get("features")
    feature_map = _as_mapping(features_top)
    if feature_map is not None and feature_slug in feature_map:
        return True
    feature_list = _as_list(features_top)
    return feature_list is not None and any(
        isinstance(f, str) and feature_slug in f for f in feature_list
    )


def detect_visual_feature(
    *, project_root: Path, feature_slug: str
) -> VisualClassification:
    """Apply the P0-A deterministic detection table."""
    feature_dir = _feature_dir(project_root, feature_slug)
    spec_md = feature_dir / "spec.md"

    s1_present, s1_false = _read_spec_visual_marker(spec_md)
    if s1_false:
        signals = VisualFeatureSignals(
            s1_spec_marker=True,
            s1_spec_explicit_false=True,
            s2_feature_screens=False,
            s3_penflow_workspace=False,
            s4_flow_ui_contract=False,
            s5_feature_baselines=False,
            s6_surfaces_yaml=False,
        )
        return VisualClassification(
            classification="NON_VISUAL",
            signals=signals,
            conflict_reason=None,
        )

    s2_feature_screens = (
        (feature_dir / "design").is_dir()
        and any((feature_dir / "design").rglob("*.png"))
    ) or (
        (project_root / DESIGN_REGISTRY_DIR / "screens" / feature_slug).is_dir()
        and any(
            (project_root / DESIGN_REGISTRY_DIR / "screens" / feature_slug).rglob(
                "*.png"
            )
        )
    )
    s3_penflow = _has_feature_scoped_penflow(project_root, feature_slug)
    s4_flow_ui = (feature_dir / "design" / "flow-ui-contract").is_dir()
    baseline_dir = feature_dir / "baselines"
    s5_baselines = baseline_dir.is_dir() and any(baseline_dir.rglob("*.png"))
    s6_surfaces = _surfaces_yaml_mentions_feature(project_root, feature_slug)

    signals = VisualFeatureSignals(
        s1_spec_marker=s1_present,
        s1_spec_explicit_false=False,
        s2_feature_screens=s2_feature_screens,
        s3_penflow_workspace=s3_penflow,
        s4_flow_ui_contract=s4_flow_ui,
        s5_feature_baselines=s5_baselines,
        s6_surfaces_yaml=s6_surfaces,
    )

    if signals.strong_count >= 1:
        if s1_present is False and signals.s5_feature_baselines is False:
            # All strong signals come from filesystem evidence -> definitely VISUAL.
            return VisualClassification(classification="VISUAL", signals=signals)
        return VisualClassification(classification="VISUAL", signals=signals)
    if signals.strong_count == 0 and signals.weak_count >= 1:
        weak_signals = [
            name
            for flag, name in (
                (signals.s5_feature_baselines, "s5_feature_baselines"),
                (signals.s6_surfaces_yaml, "s6_surfaces_yaml"),
            )
            if flag
        ]
        return VisualClassification(
            classification="CONFLICT",
            signals=signals,
            conflict_reason=f"weak_signals_only:{','.join(weak_signals)}",
        )
    if s1_present and not s1_false:
        # Spec declares visual:true but nothing on disk → never auto-PASS.
        return VisualClassification(
            classification="CONFLICT",
            signals=signals,
            conflict_reason="spec_declares_visual_but_no_artifacts",
        )
    return VisualClassification(classification="NON_VISUAL", signals=signals)


# ---------------------------------------------------------------------------
# Validation (P1-C)
# ---------------------------------------------------------------------------


def _design_alignment_dir(project_root: Path, feature_slug: str) -> Path:
    return _feature_dir(project_root, feature_slug) / "design-alignment"


def _iter_alignment_screens(project_root: Path, feature_slug: str) -> list[Path]:
    base = _design_alignment_dir(project_root, feature_slug)
    if not base.exists():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir()])


def _resolve_manifest_source(
    raw: str, *, screen_dir: Path, project_root: Path
) -> Path | None:
    """Resolve a ``design_source``/``runtime_source`` reference from a manifest.

    Resolution order:
      * absolute path → returned as-is;
      * path starting with ``.specs/`` → resolved relative to ``project_root``;
      * any other relative path → tried first relative to ``screen_dir``,
        then relative to ``project_root``.

    Returns the first candidate that exists on disk, or ``None`` if nothing
    resolves to a readable file.
    """
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    parts = candidate.parts
    if parts and parts[0] == ".specs":
        resolved = project_root / candidate
        return resolved if resolved.exists() else None
    local = (screen_dir / candidate).resolve()
    if local.exists():
        return local
    rooted = (project_root / candidate).resolve()
    if rooted.exists():
        return rooted
    return None


def _read_alignment_manifest_sources(
    screen_dir: Path, *, project_root: Path
) -> tuple[Path | None, Path | None, str | None, dict[str, object] | None]:
    """Return ``(design_path, runtime_path, error, raw_manifest)`` from
    ``design-alignment.manifest.json`` if present.

    ``error`` is ``None`` on success and a short human-readable diagnostic
    otherwise. ``raw_manifest`` is the parsed dict (``None`` when absent or
    unreadable).
    """
    manifest_path = screen_dir / "design-alignment.manifest.json"
    if not manifest_path.exists():
        return None, None, None, None
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, None, f"{manifest_path}: unreadable ({exc})", None
    try:
        data_raw: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, None, f"{manifest_path}: malformed JSON ({exc})", None
    data = _as_mapping(data_raw)
    if data is None:
        return None, None, f"{manifest_path}: expected object at top level", None
    design_src = data.get("design_source")
    runtime_src = data.get("runtime_source")
    if not isinstance(design_src, str) or not isinstance(runtime_src, str):
        return (
            None,
            None,
            f"{manifest_path}: missing design_source / runtime_source",
            data,
        )
    design_path = _resolve_manifest_source(
        design_src, screen_dir=screen_dir, project_root=project_root
    )
    runtime_path = _resolve_manifest_source(
        runtime_src, screen_dir=screen_dir, project_root=project_root
    )
    if design_path is None or runtime_path is None:
        missing: list[str] = []
        if design_path is None:
            missing.append(f"design_source={design_src}")
        if runtime_path is None:
            missing.append(f"runtime_source={runtime_src}")
        return (
            None,
            None,
            f"{manifest_path}: unresolved {', '.join(missing)}",
            data,
        )
    return design_path, runtime_path, None, data


def _run_alignment_for_screen(
    screen_dir: Path, *, project_root: Path
) -> AlignmentResult | None:
    """Run design-alignment compare for ``screen_dir``.

    Prefer local ``design-contract.json`` / ``runtime-contract.json`` when
    present; otherwise resolve normalized sources via the screen's
    ``design-alignment.manifest.json`` (no-copy contract). Returns ``None``
    when no comparison can be run — the caller surfaces this as BLOCKED via
    :func:`_alignment_dir_incomplete_reasons`.
    """
    design_path: Path | None = screen_dir / "design-contract.json"
    runtime_path: Path | None = screen_dir / "runtime-contract.json"
    if not design_path.exists() or not runtime_path.exists():
        manifest_design, manifest_runtime, _err, _raw = (
            _read_alignment_manifest_sources(
                screen_dir, project_root=project_root
            )
        )
        if manifest_design is None or manifest_runtime is None:
            return None
        design_path = manifest_design
        runtime_path = manifest_runtime
    return compare_contract_files(
        design_path=design_path,
        runtime_path=runtime_path,
        screen=screen_dir.name,
        output_dir=screen_dir,
    )


def _alignment_dir_incomplete_reasons(
    screen_dir: Path, *, project_root: Path
) -> list[str]:
    """Return missing-file reasons for an incomplete ``design-alignment/<screen>/``.

    A "complete" screen dir must either (a) carry both ``design-contract.json``
    and ``runtime-contract.json`` locally, or (b) provide a readable
    ``design-alignment.manifest.json`` whose ``design_source`` and
    ``runtime_source`` resolve to existing files. Anything else is BLOCKING
    evidence that the skill claimed work without producing comparison inputs.
    """
    design_local = screen_dir / "design-contract.json"
    runtime_local = screen_dir / "runtime-contract.json"
    if design_local.exists() and runtime_local.exists():
        return []
    manifest_path = screen_dir / "design-alignment.manifest.json"
    if manifest_path.exists():
        _d, _r, err, _raw = _read_alignment_manifest_sources(
            screen_dir, project_root=project_root
        )
        if err is None:
            return []
        return [err]
    reasons: list[str] = []
    if not design_local.exists():
        reasons.append(f"{screen_dir}/design-contract.json")
    if not runtime_local.exists():
        reasons.append(f"{screen_dir}/runtime-contract.json")
    return reasons


def _baseline_manifest_path(project_root: Path, feature_slug: str) -> Path:
    """Return the resolved manifest path, preferring YAML and falling back to JSON.

    Symlink-mode workspaces ship ``baseline.manifest.yml``; manifest-mode
    workspaces (filesystems without symlink support) persist the same data
    as ``manifest.json``. Both must be honoured so the gate does not silently
    skip manifest validation on Windows / restricted FUSE mounts.
    """
    base = _feature_dir(project_root, feature_slug) / "baselines"
    yaml_path = base / "baseline.manifest.yml"
    if yaml_path.exists():
        return yaml_path
    json_path = base / "manifest.json"
    if json_path.exists():
        return json_path
    # No file present — return the YAML path so callers see the default name
    # in diagnostics; validate_manifest will report `found=False`.
    return yaml_path


def validate_gate(
    *,
    project_root: Path,
    feature_slug: str,
    command: GateCommand,
    target: GateTarget | None,
    strict_links: bool = True,
    receipt_path: Path | None = None,
) -> GateReport:
    """Run the visual gate against ``feature_slug`` and return a ``GateReport``."""
    classification = detect_visual_feature(
        project_root=project_root, feature_slug=feature_slug
    )

    if classification.classification == "NON_VISUAL":
        return GateReport(
            feature_slug=feature_slug,
            command=command,
            target=target,
            classification=classification.classification,
            signals=classification.signals,
            verdict="PASS",
            conflict_reason=classification.conflict_reason,
            penflow=None,
        )

    if classification.classification == "CONFLICT":
        return GateReport(
            feature_slug=feature_slug,
            command=command,
            target=target,
            classification=classification.classification,
            signals=classification.signals,
            verdict="BLOCKED",
            conflict_reason=classification.conflict_reason,
            penflow=None,
            missing_artifacts=_missing_artifacts_from_signals(
                classification.signals, feature_slug=feature_slug, target=target
            ),
        )

    # VISUAL → run sub-checks.
    penflow_status = get_penflow_contract_status(
        project_root,
        require_actual=False,
        require_design_registry=False,
        require_mockup_validation=False,
        feature_slug=feature_slug,
    )

    alignment_results: list[AlignmentResult] = []
    incomplete_alignment: list[str] = []
    for screen_dir in _iter_alignment_screens(project_root, feature_slug):
        result = _run_alignment_for_screen(
            screen_dir, project_root=project_root
        )
        if result is not None:
            alignment_results.append(result)
            continue
        # No result == design or runtime contract missing — that is BLOCKING
        # evidence under the strict gate (incomplete artefacts cannot
        # silently disappear, otherwise a skipped compare would PASS).
        incomplete_alignment.extend(
            _alignment_dir_incomplete_reasons(
                screen_dir, project_root=project_root
            )
        )

    runtime_misplaced = find_runtime_misplaced_under_design_screens(
        project_root=project_root, feature_slug=feature_slug
    )

    link_violations: list[LinkViolation] = []
    manifest_status: ManifestStatus | None = None
    missing: list[str] = []
    if strict_links:
        manifest_path = _baseline_manifest_path(project_root, feature_slug)
        manifest_status, violations = validate_manifest(
            manifest_path=manifest_path,
            project_root=project_root,
            feature_slug=feature_slug,
            target=target,
        )
        link_violations.extend(violations)
        legacy_missing, legacy_violations = _legacy_manifest_mockup_checks(
            manifest_path=manifest_path,
            project_root=project_root,
            feature_slug=feature_slug,
        )
        missing.extend(legacy_missing)
        link_violations.extend(legacy_violations)
        # Even when no manifest is declared, scan feature-local baselines for
        # plain-file copies that should be symlinks.
        for plain in _detect_plain_copies(project_root, feature_slug, target):
            link_violations.append(plain)

    if classification.classification == "VISUAL":
        targets_to_check = _resolve_targets_for_check(
            project_root=project_root, feature_slug=feature_slug, target=target
        )
        if not targets_to_check:
            # Caller omitted --target AND no registry / surface metadata
            # exposes a baseline target — refuse to PASS silently.
            missing.append(
                f".specs/design/baselines/{feature_slug}/<target>/ "
                "(no target registry and no derivable target from surfaces.yaml)"
            )
        for resolved_target in targets_to_check:
            registry_baselines_dir = (
                project_root
                / DESIGN_REGISTRY_DIR
                / BASELINES_DIRNAME
                / feature_slug
                / resolved_target
            )
            if not registry_baselines_dir.exists():
                missing.append(str(registry_baselines_dir))
    visual_evidence, visual_evidence_verdict, visual_evidence_missing = (
        _validate_visual_evidence_receipt(
            project_root=project_root,
            feature_slug=feature_slug,
            command=command,
            target=target,
            receipt_path=receipt_path,
        )
    )
    missing.extend(visual_evidence_missing)
    # Incomplete design-alignment dirs surface as missing artefacts so the
    # aggregated verdict goes BLOCKED instead of silently dropping the
    # broken screens on the floor.
    missing.extend(incomplete_alignment)

    verdict = _aggregate_verdict(
        penflow=penflow_status,
        alignment=alignment_results,
        link_violations=link_violations,
        runtime_misplaced=runtime_misplaced,
        missing_artifacts=missing,
        visual_evidence_verdict=visual_evidence_verdict,
    )

    return GateReport(
        feature_slug=feature_slug,
        command=command,
        target=target,
        classification=classification.classification,
        signals=classification.signals,
        verdict=verdict,
        conflict_reason=classification.conflict_reason,
        penflow=penflow_status,
        alignment=alignment_results,
        link_violations=link_violations,
        runtime_in_design_screens_violations=runtime_misplaced,
        manifest_status=manifest_status,
        visual_evidence=visual_evidence,
        missing_artifacts=missing,
    )


def _validate_visual_evidence_receipt(
    *,
    project_root: Path,
    feature_slug: str,
    command: GateCommand,
    target: GateTarget | None,
    receipt_path: Path | None,
) -> tuple[dict[str, object] | None, Verdict, list[str]]:
    """Validate an explicit oracle receipt for a visual feature."""
    expected = (
        f".specs/features/{feature_slug}/run/<run-id>/visual-evidence/receipt.json "
        "(pass it via --receipt)"
    )
    if receipt_path is None:
        return None, "BLOCKED", [expected]
    rel_receipt = _project_relative(project_root, receipt_path)
    try:
        receipt = verify_visual_receipt(
            receipt_path,
            project_root=project_root,
            expected_feature_slug=feature_slug,
            expected_command=command,
            expected_target=target,
        )
    except VisualReceiptError as exc:
        return (
            {
                "receipt_path": rel_receipt,
                "verdict": "BLOCKED",
                "error": str(exc),
            },
            "BLOCKED",
            [f"{rel_receipt}: invalid visual evidence receipt ({exc})"],
        )
    evidence = _visual_receipt_to_gate_evidence(project_root, receipt_path, receipt)
    missing = _missing_visual_receipt_requirements(
        receipt=receipt, command=command, target=target
    )
    if missing:
        evidence["verdict"] = "BLOCKED"
        return evidence, "BLOCKED", missing
    return evidence, receipt.verdict, []


def _visual_receipt_to_gate_evidence(
    project_root: Path,
    receipt_path: Path,
    receipt: VisualReceipt,
) -> dict[str, object]:
    return {
        "receipt_path": _project_relative(project_root, receipt_path),
        "verdict": receipt.verdict,
        "command": receipt.command,
        "target": receipt.target,
        "run_id": receipt.run_id,
        "comparison_count": len(receipt.comparisons),
        "comparison_kinds": sorted({c.comparison_kind for c in receipt.comparisons}),
    }


def _missing_visual_receipt_requirements(
    *,
    receipt: VisualReceipt,
    command: GateCommand,
    target: GateTarget | None,
) -> list[str]:
    missing: list[str] = []
    if receipt.command != command:
        missing.append(
            f"visual evidence receipt command={receipt.command} "
            f"does not match requested command={command}"
        )
    if target is not None and receipt.target != target:
        missing.append(
            f"visual evidence receipt target={receipt.target} "
            f"does not match requested target={target}"
        )
    kinds = {comparison.comparison_kind for comparison in receipt.comparisons}
    if "mockup_runtime" not in kinds:
        missing.append("visual evidence receipt missing mockup_runtime comparison")
    return missing


def _resolve_targets_for_check(
    *, project_root: Path, feature_slug: str, target: GateTarget | None
) -> list[str]:
    """Compute the list of baseline targets that must be present.

    * Explicit ``target`` → check just that one (caller intent wins).
    * Otherwise scan ``.specs/design/baselines/<slug>/`` for existing target
      subdirs and use them — covers projects that already promoted at least
      one target.
    * Otherwise derive targets from ``surfaces.yaml`` (per-feature mention or
      project-wide runner kinds): playwright→web, xcuitest→ios,
      maestro→android, tauri→tauri.
    * Otherwise return ``[]`` so the caller can raise BLOCKED with a clear
      "no target context" diagnostic instead of silently PASSing.
    """
    if target is not None:
        return [str(target)]
    baselines_root = (
        project_root / DESIGN_REGISTRY_DIR / BASELINES_DIRNAME / feature_slug
    )
    if baselines_root.is_dir():
        existing = sorted(
            p.name
            for p in baselines_root.iterdir()
            if p.is_dir() and p.name in ("web", "ios", "android", "tauri")
        )
        if existing:
            return existing
    # Derive from surfaces.yaml runner kinds.
    surfaces_path = project_root / ".specs" / "surfaces.yaml"
    if not surfaces_path.exists():
        return []
    try:
        import yaml  # type: ignore[import-untyped]

        parsed_raw: object = yaml.safe_load(
            surfaces_path.read_text(encoding="utf-8")
        ) or {}
    except Exception:  # pragma: no cover - bad YAML
        return []
    parsed = _as_mapping(parsed_raw)
    if parsed is None:
        return []
    runner_to_target = {
        "playwright": "web",
        "xcuitest": "ios",
        "maestro": "android",
        "tauri": "tauri",
    }
    derived: list[str] = []
    surfaces = _as_list(parsed.get("surfaces"))
    if surfaces is not None:
        for entry_raw in surfaces:
            entry = _as_mapping(entry_raw)
            if entry is None:
                continue
            runner_value = entry.get("runner")
            runner = runner_value.lower() if isinstance(runner_value, str) else ""
            if runner in runner_to_target:
                t = runner_to_target[runner]
                if t not in derived:
                    derived.append(t)
    return derived


def _missing_artifacts_from_signals(
    signals: VisualFeatureSignals, *, feature_slug: str, target: GateTarget | None
) -> list[str]:
    missing: list[str] = []
    if not signals.s2_feature_screens:
        missing.append(
            f".specs/design/screens/{feature_slug}/ or "
            f".specs/features/{feature_slug}/design/ (no PNG present)"
        )
    if not signals.s3_penflow_workspace:
        missing.append("penflow/ workspace at project root")
    if not signals.s4_flow_ui_contract:
        missing.append(
            f".specs/features/{feature_slug}/design/flow-ui-contract/"
        )
    if target is not None:
        missing.append(
            f".specs/design/baselines/{feature_slug}/{target}/ "
            f"(approved baseline registry)"
        )
    return missing


def _detect_plain_copies(
    project_root: Path, feature_slug: str, target: GateTarget | None
) -> list[LinkViolation]:
    out: list[LinkViolation] = []
    baselines_dir = (
        project_root / ".specs" / "features" / feature_slug / "baselines"
    )
    if not baselines_dir.exists():
        return out
    # Use scandir-style iteration so broken symlinks are surfaced
    # (Path.rglob with a glob pattern skips broken symlinks silently).
    for entry in baselines_dir.iterdir():
        if not entry.name.endswith(".png"):
            continue
        screen = entry.stem
        target_dir = target or "unknown"
        expected = expected_registry_baseline_path(
            feature_slug=feature_slug, target=target_dir, screen=screen
        )
        if entry.is_symlink():
            # Broken symlink → anti-false-positive: missing registry baseline
            # MUST surface as a violation, not silently disappear.
            try:
                _ = entry.resolve(strict=True)
            except (FileNotFoundError, OSError):
                out.append(
                    LinkViolation(
                        kind="broken_symlink",
                        feature_slug=feature_slug,
                        target=target,
                        screen=screen,
                        path=entry,
                        message=(
                            f"{entry} is a broken symlink. Expected target "
                            f"{expected} does not exist. Restore the baseline "
                            f"via `livespec visual-gate promote --feature "
                            f"{feature_slug} --target {target_dir} --screen "
                            f"{screen} --run-id <ts>` or remove the dead "
                            "link."
                        ),
                    )
                )
                continue
            # Healthy symlink → verify it actually points to the expected
            # registry baseline path (a symlink that resolves to *some*
            # file is not enough; it must resolve to the right registry
            # entry, otherwise the gate silently accepts cross-feature or
            # stale targets).
            from validator.registry_links import check_link

            link_violation = check_link(
                feature_local_path=entry,
                expected_registry_path=expected,
                project_root=project_root,
                feature_slug=feature_slug,
                target=target,
                screen=screen,
            )
            if link_violation is not None:
                out.append(link_violation)
            continue
        # Plain file under feature/baselines → must be a symlink under the
        # strict-links contract.
        out.append(
            LinkViolation(
                kind="physical_copy_where_link_required",
                feature_slug=feature_slug,
                target=target,
                screen=screen,
                path=entry,
                message=(
                    f"{entry} is a plain PNG. Expected a relative "
                    f"symlink to {expected}. Run "
                    f"`livespec visual-gate cleanup --feature {feature_slug} "
                    f"--dry-run` then `--apply`, then "
                    f"`livespec visual-gate promote --feature {feature_slug} "
                    f"--target {target_dir} --screen {screen} --run-id <ts>`."
                ),
            )
        )
    return out


def _legacy_manifest_mockup_checks(
    *,
    manifest_path: Path,
    project_root: Path,
    feature_slug: str,
) -> tuple[list[str], list[LinkViolation]]:
    """Validate legacy staleness rows against canonical design-screen PNGs."""
    if not manifest_path.exists():
        return [], []
    payload = _read_manifest_mapping(manifest_path)
    if payload is None:
        return [], []
    raw_screens = _as_list(payload.get("screens"))
    if raw_screens is None:
        return [], []

    missing: list[str] = []
    violations: list[LinkViolation] = []
    for raw_item in raw_screens:
        raw = _as_mapping(raw_item)
        if raw is None:
            continue
        screen = str(raw.get("screen", "")).strip()
        if not screen:
            continue
        mockup_path, mockup_error = _resolve_legacy_mockup_path(
            raw,
            project_root=project_root,
            feature_slug=feature_slug,
            screen=screen,
        )
        if mockup_error is not None:
            violations.append(
                LinkViolation(
                    kind="manifest_unreadable",
                    feature_slug=feature_slug,
                    target=None,
                    screen=screen,
                    path=manifest_path,
                    message=mockup_error,
                )
            )
            continue
        if not mockup_path.exists():
            missing.append(
                f"{manifest_path}: mockup for screen '{screen}' not found at "
                f"{mockup_path}"
            )
            continue
        expected_hash = _legacy_mockup_hash(raw)
        if expected_hash is None:
            missing.append(f"{manifest_path}: screens[{screen}].mockup_version")
            continue
        actual_hash = sha256_of(mockup_path)
        if actual_hash.lower() != expected_hash.lower():
            violations.append(
                LinkViolation(
                    kind="manifest_mockup_sha_mismatch",
                    feature_slug=feature_slug,
                    target=None,
                    screen=screen,
                    path=mockup_path,
                    message=(
                        f"Legacy manifest mockup hash mismatch for screen "
                        f"'{screen}': manifest={expected_hash[:12]}…, "
                        f"actual={actual_hash[:12]}…. Refresh "
                        f"`mockup_version` from {mockup_path}."
                    ),
                )
            )
    return missing, violations


def _read_manifest_mapping(manifest_path: Path) -> dict[str, object] | None:
    """Parse a JSON/YAML manifest and return a mapping when possible."""
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        if manifest_path.suffix.lower() == ".json":
            payload_raw: object = json.loads(raw_text)
        else:
            import yaml  # type: ignore[import-untyped]

            payload_raw = yaml.safe_load(raw_text)
    except Exception:
        return None
    return _as_mapping(payload_raw)


def _resolve_legacy_mockup_path(
    raw: dict[str, object],
    *,
    project_root: Path,
    feature_slug: str,
    screen: str,
) -> tuple[Path, str | None]:
    """Resolve optional ``mockup_path`` or the default screen-named mockup."""
    raw_path = raw.get("mockup_path")
    allowed_root = (
        project_root / DESIGN_REGISTRY_DIR / SCREENS_DIRNAME / feature_slug
    ).resolve()
    if isinstance(raw_path, str) and raw_path.strip():
        candidate = Path(raw_path)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (project_root / candidate).resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError:
            return (
                resolved,
                "Legacy manifest mockup_path escapes "
                f".specs/design/screens/{feature_slug}/.",
            )
        return resolved, None
    return project_root / expected_registry_mockup_path(
        feature_slug=feature_slug,
        screen=screen,
    ), None


def _legacy_mockup_hash(raw: dict[str, object]) -> str | None:
    """Return the lowercase sha256 value from ``mockup_version``."""
    version = raw.get("mockup_version")
    if not isinstance(version, str):
        return None
    prefix = "sha256:"
    value = version.strip()
    if not value.startswith(prefix):
        return None
    digest = value[len(prefix) :].lower()
    return digest if len(digest) == 64 else None


def _aggregate_verdict(
    *,
    penflow: PenflowContractStatus,
    alignment: list[AlignmentResult],
    link_violations: list[LinkViolation],
    runtime_misplaced: list[Path],
    missing_artifacts: list[str],
    visual_evidence_verdict: Verdict | None,
) -> Verdict:
    if runtime_misplaced:
        return "FAIL"
    if visual_evidence_verdict == "FAIL":
        return "FAIL"
    fail_violation_kinds = {
        "physical_copy_where_link_required",
        "broken_symlink",
        "manifest_mockup_sha_mismatch",
        "manifest_sha_mismatch",
        "runtime_under_design_screens",
    }
    if any(v.kind in fail_violation_kinds for v in link_violations):
        return "FAIL"
    if any(r.verdict == "FAIL" for r in alignment):
        return "FAIL"
    if penflow.runtime_comparison == "FAIL":
        return "FAIL"
    if visual_evidence_verdict == "BLOCKED":
        return "BLOCKED"
    block_violation_kinds = {
        "manifest_missing_registry_path",
        "manifest_unreadable",
        "registry_path_missing",
        "feature_local_path_missing",
    }
    if any(v.kind in block_violation_kinds for v in link_violations):
        return "BLOCKED"
    if any(r.verdict == "BLOCKED" for r in alignment):
        return "BLOCKED"
    if penflow.runtime_comparison == "BLOCKED":
        return "BLOCKED"
    if missing_artifacts:
        return "BLOCKED"
    return "PASS"


def render_text_report(report: GateReport) -> str:
    """Render a concise human-readable report (used by CLI without ``--json``)."""
    lines: list[str] = []
    lines.append(f"Visual Gate Verdict: {report.verdict}")
    lines.append(
        f"feature={report.feature_slug} command={report.command} "
        f"target={report.target or 'auto'} classification={report.classification}"
    )
    if report.conflict_reason:
        lines.append(f"conflict_reason: {report.conflict_reason}")
    if report.missing_artifacts:
        lines.append("missing artifacts:")
        for item in report.missing_artifacts:
            lines.append(f"  - {item}")
    if report.link_violations:
        lines.append("link violations:")
        for violation in report.link_violations:
            lines.append(f"  [{violation.kind}] {violation.message}")
    if report.runtime_in_design_screens_violations:
        lines.append("runtime captures misplaced under .specs/design/screens/:")
        for path in report.runtime_in_design_screens_violations:
            lines.append(f"  - {path}")
    if report.visual_evidence is not None:
        lines.append(
            "visual evidence: "
            f"verdict={report.visual_evidence.get('verdict')} "
            f"receipt={report.visual_evidence.get('receipt_path')}"
        )
    if report.alignment:
        lines.append("design-alignment screens:")
        for result in report.alignment:
            lines.append(f"  - {result.screen}: {result.verdict}")
    if report.penflow is not None:
        lines.append(
            f"penflow: state={report.penflow.state} "
            f"runtime_comparison={report.penflow.runtime_comparison}"
        )
    return "\n".join(lines)


def verdict_to_exit_code(verdict: Verdict) -> int:
    """Map a verdict to the gate-specific exit code constants."""
    from validator.cli_exit_codes import (
        EXIT_OK,
        EXIT_VISUAL_GATE_BLOCKED,
        EXIT_VISUAL_GATE_FAIL,
    )

    if verdict == "PASS":
        return EXIT_OK
    if verdict == "FAIL":
        return EXIT_VISUAL_GATE_FAIL
    return EXIT_VISUAL_GATE_BLOCKED


# ---------------------------------------------------------------------------
# Cleanup (P0-D)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CleanupAction:
    """One planned cleanup move/delete."""

    source: Path
    quarantine_target: Path | None
    kind: Literal["archive", "delete"]
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "quarantine_target": (
                str(self.quarantine_target) if self.quarantine_target else None
            ),
            "kind": self.kind,
            "reason": self.reason,
        }


def _cleanup_actions_factory() -> list[CleanupAction]:
    return []


@dataclass(frozen=True)
class CleanupPlan:
    """Result of ``visual-gate cleanup --dry-run``."""

    feature_slug: str
    actions: list[CleanupAction] = field(default_factory=_cleanup_actions_factory)
    quarantine_root: Path | None = None

    @property
    def has_drift(self) -> bool:
        return bool(self.actions)

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_slug": self.feature_slug,
            "quarantine_root": (
                str(self.quarantine_root) if self.quarantine_root else None
            ),
            "actions": [a.to_dict() for a in self.actions],
            "has_drift": self.has_drift,
        }


def plan_cleanup(
    *,
    project_root: Path,
    feature_slug: str,
    timestamp: str,
    mode: Literal["archive", "delete"] = "archive",
) -> CleanupPlan:
    """Compute the cleanup plan without touching the filesystem."""
    misplaced = find_runtime_misplaced_under_design_screens(
        project_root=project_root, feature_slug=feature_slug
    )
    quarantine_root = (
        project_root
        / DESIGN_REGISTRY_DIR
        / "_quarantine"
        / timestamp
    )
    actions: list[CleanupAction] = []
    for source in misplaced:
        rel = source.relative_to(project_root)
        target = quarantine_root / rel if mode == "archive" else None
        actions.append(
            CleanupAction(
                source=source,
                quarantine_target=target,
                kind=mode,
                reason="runtime_under_design_screens",
            )
        )
    return CleanupPlan(
        feature_slug=feature_slug,
        actions=actions,
        quarantine_root=quarantine_root if mode == "archive" else None,
    )


def apply_cleanup(plan: CleanupPlan) -> list[CleanupAction]:
    """Execute ``plan`` and return the list of applied actions.

    Idempotent: a second run on a clean state returns ``[]``.
    """
    applied: list[CleanupAction] = []
    for action in plan.actions:
        if not action.source.exists():
            continue
        if action.kind == "archive" and action.quarantine_target is not None:
            action.quarantine_target.parent.mkdir(parents=True, exist_ok=True)
            action.source.replace(action.quarantine_target)
        elif action.kind == "delete":
            action.source.unlink()
        applied.append(action)
    return applied


def write_cleanup_report(
    *,
    project_root: Path,
    plan: CleanupPlan,
    applied: list[CleanupAction],
    timestamp: str,
) -> Path:
    """Persist a ``cleanup-report.json`` under ``.specs/visual-gate/runs/<ts>``."""
    run_dir = project_root / ".specs" / "visual-gate" / "runs" / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": timestamp,
        "feature_slug": plan.feature_slug,
        "planned": [a.to_dict() for a in plan.actions],
        "applied": [a.to_dict() for a in applied],
        "quarantine_root": (
            str(plan.quarantine_root) if plan.quarantine_root else None
        ),
        "has_drift": plan.has_drift,
    }
    target = run_dir / "cleanup-report.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Promote (P0-D follow-up)
# ---------------------------------------------------------------------------


def promote_baseline(
    *,
    project_root: Path,
    feature_slug: str,
    target: GateTarget,
    screen: str,
    run_id: str,
) -> tuple[Path, Path | None]:
    """Promote a run capture into the registry + create a feature-local symlink.

    Returns the resolved registry path and (when symlink mode is active) the
    feature-local symlink path created.
    """
    safe_screen = screen if screen.endswith(".png") else f"{screen}.png"
    run_capture = (
        project_root
        / ".specs"
        / "features"
        / feature_slug
        / "run"
        / run_id
        / target
        / safe_screen
    )
    if not run_capture.exists():
        raise FileNotFoundError(f"Run capture not found: {run_capture}")
    registry_rel = expected_registry_baseline_path(
        feature_slug=feature_slug, target=target, screen=safe_screen
    )
    registry_abs = project_root / registry_rel
    registry_abs.parent.mkdir(parents=True, exist_ok=True)
    # Copy bytes once into the registry — this is the *only* canonical copy.
    registry_abs.write_bytes(run_capture.read_bytes())
    mode = detect_link_capability(project_root)
    feature_local_path: Path | None = None
    if mode == "symlink":
        feature_local_path = expected_feature_local_path(
            feature_slug=feature_slug,
            screen=safe_screen,
            project_root=project_root,
        )
        feature_local_path.parent.mkdir(parents=True, exist_ok=True)
        if feature_local_path.is_symlink() or feature_local_path.exists():
            feature_local_path.unlink()
        # Compute the relative path from the symlink dir to the registry file.
        rel_target = Path(
            *([".."] * (len(feature_local_path.parent.relative_to(project_root).parts)))
        ) / registry_rel
        _safe_symlink(rel_target, feature_local_path)
    else:
        # manifest mode: symlink unsupported → persist a manifest.json entry
        # under the feature baselines dir so downstream gate runs still find
        # the canonical registry reference. Without this the registry copy
        # exists but the gate cannot link it back to the feature.
        _persist_manifest_entry(
            project_root=project_root,
            feature_slug=feature_slug,
            target=target,
            screen=safe_screen,
            registry_rel=registry_rel,
        )
    return registry_abs, feature_local_path


def _persist_manifest_entry(
    *,
    project_root: Path,
    feature_slug: str,
    target: GateTarget,
    screen: str,
    registry_rel: Path,
) -> Path:
    """Create or update ``manifest.json`` for the feature baselines dir."""
    from validator.registry_links import sha256_of

    manifest_path = (
        project_root / ".specs" / "features" / feature_slug / "baselines" / "manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object]
    if manifest_path.exists():
        try:
            payload_raw: object = json.loads(
                manifest_path.read_text(encoding="utf-8")
            ) or {}
        except (json.JSONDecodeError, ValueError):
            payload = {}
        else:
            payload = _as_mapping(payload_raw) or {}
    else:
        payload = {}
    payload.setdefault("feature_slug", feature_slug)
    payload.setdefault("target", target)
    raw_entries = _as_list(payload.get("entries"))
    entries: list[dict[str, object]] = []
    if raw_entries is not None:
        for entry_raw in raw_entries:
            entry = _as_mapping(entry_raw)
            if entry is not None:
                entries.append(entry)
    registry_abs = project_root / registry_rel
    sha = sha256_of(registry_abs) if registry_abs.exists() else None
    new_entry: dict[str, object] = {
        "screen": screen.rsplit(".", 1)[0],
        "kind": "ref",
        "registry_path": str(registry_rel),
        "sha256": sha,
    }
    entries = [
        e for e in entries if str(e.get("screen", "")) != new_entry["screen"]
    ]
    entries.append(new_entry)
    payload["entries"] = entries
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest_path


def _safe_symlink(target: Path, link_path: Path) -> None:
    """Best-effort relative-symlink creation; raises ``OSError`` on failure."""
    import os as _os

    _os.symlink(target, link_path)


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = [
    "Classification",
    "CleanupAction",
    "CleanupPlan",
    "GateCommand",
    "GateReport",
    "GateTarget",
    "Verdict",
    "VisualClassification",
    "VisualFeatureSignals",
    "apply_cleanup",
    "certify_visual_evidence",
    "detect_visual_feature",
    "plan_cleanup",
    "promote_baseline",
    "render_text_report",
    "validate_gate",
    "verdict_to_exit_code",
    "write_cleanup_report",
]
