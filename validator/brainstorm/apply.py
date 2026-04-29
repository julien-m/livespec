"""Two-phase atomic ingestion writer.

Architecture rationale (addresses plan-review Finding #2/#3):

- The 4-subcommand split (`detect / validate / plan / apply`) keeps each
  phase pure and individually testable. `validate` and `plan` perform NO
  writes. `apply` is the only phase that touches `.specs/`.
- A JSON `IngestionPlan` is the contract between `plan` and `apply`. It
  enables: dry-runs (the LLM can inspect the plan before approving),
  reproducibility (the same plan can be re-applied), and atomicity
  (the plan is fully built before any write).
- In `init` mode: writes go to a staging dir under cwd (same FS, so
  `os.replace` is atomic), then `os.replace(staging, .specs)` swaps it
  in. On any exception during apply, staging is destroyed and `.specs/`
  remains untouched (FR-003 / AC-004).
- In `refine` mode: per-file `os.replace` from staging into the existing
  `.specs/`. Atomic per file but not transactional across files — if an
  exception is raised mid-apply, the error message surfaces "partial
  apply possible in refine mode — inspect .specs/" so the operator
  knows to inspect the directory (addresses Finding #1).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Literal

from .convert import build_changelog, convert_flow_to_spec, inject_screens_section
from .grammar import FlowValidationResult, ValidationReport
from .project_seed import seed_default_stack, seed_project_md
from .roadmap import build_roadmap_op, render_roadmap
from .schemas import (
    ApplyReport,
    FlowFrontmatter,
    FlowOp,
    IngestionPlan,
    MockupOp,
    ProjectOp,
    ScreenOp,
)
from .slug import allocate_nnn, normalize_slug

INDEX_FILE = "_index.md"


def _read_index_order(cwd: Path) -> list[str] | None:
    """Read `specs/flows/_index.md` if present and return ordered slugs."""
    idx = cwd / "specs" / "flows" / INDEX_FILE
    if not idx.exists():
        return None
    out: list[str] = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*[-*]\s+(.+?)\s*$", line)
        if m:
            out.append(m.group(1).strip())
    return out or None


def _existing_features(target_dir: Path) -> list[Path]:
    """List `<.specs>/features/NNN-slug/` directories, if any."""
    fdir = target_dir / "features"
    if not fdir.exists():
        return []
    return [p for p in fdir.iterdir() if p.is_dir()]


def _resolve_screen_ops(
    cwd: Path, slug_to_nnn: dict[str, str]
) -> list[ScreenOp]:
    """Map `specs/screens/*.md` to inline-into-feature or standalone-annex."""
    sdir = cwd / "specs" / "screens"
    if not sdir.exists():
        return []
    ops: list[ScreenOp] = []
    for path in sorted(sdir.glob("*.md")):
        if path.name == INDEX_FILE:
            continue
        try:
            import frontmatter as fm_mod  # type: ignore[import-untyped]

            data = fm_mod.load(str(path))
            parent_raw = data.metadata.get("parent")
            body = data.content
        except Exception:  # pragma: no cover - defensive
            parent_raw = None
            body = path.read_text(encoding="utf-8")
        parent_slug = (
            normalize_slug(parent_raw) if isinstance(parent_raw, str) else None
        )
        if parent_slug and parent_slug in slug_to_nnn:
            nnn = slug_to_nnn[parent_slug]
            ops.append(
                ScreenOp(
                    source_path=str(path),
                    placement="inline",
                    parent_feature=f"{nnn}-{parent_slug}",
                    body=body,
                )
            )
        else:
            ops.append(
                ScreenOp(
                    source_path=str(path),
                    placement="annex",
                    target_path=f"design/screens/{path.name}",
                    body=body,
                )
            )
    return ops


def _resolve_mockup_ops(
    cwd: Path,
    flow_ops: list[FlowOp],
) -> list[MockupOp]:
    """Plan PNG copies: bulk into `design/screens/` + per-feature snapshots."""
    mockups_dir = cwd / "mockups"
    if not mockups_dir.exists():
        return []
    refs_per_png: dict[str, list[str]] = {}
    for fop in flow_ops:
        for ref in fop.mockup_refs:
            png = ref if ref.endswith(".png") else f"{ref}.png"
            refs_per_png.setdefault(png, []).append(f"{fop.nnn}-{fop.slug}")

    ops: list[MockupOp] = []
    for png in sorted(p.name for p in mockups_dir.glob("*.png")):
        targets = [
            f"design/screens/{feat}/{png}" for feat in refs_per_png.get(png, [])
        ]
        ops.append(
            MockupOp(
                source_path=str(mockups_dir / png),
                global_target=f"design/screens/{png}",
                per_feature_targets=targets,
            )
        )
    return ops


# @spec FR-001: Plan builder — .specs/features/012-brainstorm-ingestion/spec.md#fr-001
def build_plan(
    cwd: Path,
    mode: Literal["init", "refine"],
    report: ValidationReport,
) -> IngestionPlan:
    """Build a complete `IngestionPlan` (no writes performed).

    Caller must pass an already-validated `ValidationReport` whose
    `ok` is True. Build is pure: same inputs → same plan.
    """
    today = date.today().isoformat()
    target_dir = cwd / ".specs"

    valid_flows = [f for f in report.flows if f.ok and f.frontmatter is not None]
    proposed_slugs: list[str] = []
    fm_by_slug: dict[str, FlowValidationResult] = {}
    for f in valid_flows:
        assert f.frontmatter is not None
        slug = normalize_slug(f.frontmatter.flow or f.path.stem)
        proposed_slugs.append(slug)
        fm_by_slug[slug] = f

    existing = _existing_features(target_dir) if mode == "refine" else []
    index_order = _read_index_order(cwd)
    nnn_map = allocate_nnn(existing, proposed_slugs, index_order)

    skipped: list[str] = []
    for s in proposed_slugs:
        if s not in nnn_map:
            skipped.append(s)

    flow_ops: list[FlowOp] = []
    for slug, nnn in nnn_map.items():
        f = fm_by_slug[slug]
        assert f.frontmatter is not None
        input_text = ""
        m = re.search(
            r"^##\s+Input\s*\n(.+?)(?=^##\s|\Z)",
            f.body,
            re.MULTILINE | re.DOTALL,
        )
        if m:
            input_text = m.group(1).strip()
        flow_ops.append(
            FlowOp(
                source_path=str(f.path),
                slug=slug,
                nnn=nnn,
                target_spec=f"features/{nnn}-{slug}/spec.md",
                target_changelog=f"features/{nnn}-{slug}/changelog.md",
                mockup_refs=list(f.frontmatter.mockups),
                priority=f.frontmatter.priority,
                title=f.frontmatter.title,
                input_text=input_text,
            )
        )

    mockup_ops = _resolve_mockup_ops(cwd, flow_ops)
    screen_ops = _resolve_screen_ops(cwd, {op.slug: op.nnn for op in flow_ops})

    profile_path = cwd / "project-profile.md"
    project_op = ProjectOp(
        project_md_target="project.md",
        stack_default_target="stacks/_default.md",
        fallback_interactive=not profile_path.exists(),
        project_md_body=seed_project_md(profile_path if profile_path.exists() else None),
        stack_default_body=seed_default_stack(
            profile_path if profile_path.exists() else None, today
        ),
    )

    roadmap_triples: list[tuple[FlowFrontmatter, str, str]] = []
    for op in flow_ops:
        f = fm_by_slug[op.slug]
        assert f.frontmatter is not None
        roadmap_triples.append((f.frontmatter, op.nnn, op.slug))
    roadmap_op = build_roadmap_op(roadmap_triples, target_path="roadmap.md")

    staging_dir = tempfile.mkdtemp(prefix=".livespec-staging-", dir=str(cwd))

    return IngestionPlan(
        mode=mode,
        cwd=str(cwd),
        staging_dir=staging_dir,
        target_dir=str(target_dir),
        next_nnn_start=1,
        flow_ops=flow_ops,
        mockup_ops=mockup_ops,
        screen_ops=screen_ops,
        project_op=project_op,
        roadmap_op=roadmap_op,
        skipped_slugs=skipped,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _stage_flows(plan: IngestionPlan, staging: Path, today: str) -> list[str]:
    """Materialize flow specs + changelogs into the staging tree."""
    written: list[str] = []
    for fop in plan.flow_ops:
        spec_md = convert_flow_to_spec(Path(fop.source_path), fop.nnn, fop.slug, today)
        spec_md = inject_screens_section(spec_md, fop.mockup_refs, fop.nnn, fop.slug)
        target = staging / fop.target_spec
        _write(target, spec_md)
        written.append(fop.target_spec)
        cl = staging / fop.target_changelog
        _write(cl, build_changelog(fop.slug, today))
        written.append(fop.target_changelog)
    return written


def _stage_mockups(plan: IngestionPlan, staging: Path) -> list[str]:
    """Copy PNGs (bulk + per-feature) into the staging tree.

    Skips `mockups/manifest.json` per FR-008.
    """
    copied: list[str] = []
    for mop in plan.mockup_ops:
        gt = staging / mop.global_target
        gt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mop.source_path, gt)
        copied.append(mop.global_target)
        for pft in mop.per_feature_targets:
            pf = staging / pft
            pf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mop.source_path, pf)
            copied.append(pft)
    return copied


def _stage_screens(plan: IngestionPlan, staging: Path) -> list[str]:
    """Place orphan screens as standalone annexes; inline parented ones."""
    written: list[str] = []
    for sop in plan.screen_ops:
        if sop.placement == "annex" and sop.target_path:
            t = staging / sop.target_path
            _write(t, sop.body)
            written.append(sop.target_path)
        elif sop.placement == "inline" and sop.parent_feature:
            spec = staging / "features" / sop.parent_feature / "spec.md"
            if spec.exists():
                current = spec.read_text(encoding="utf-8")
                addition = (
                    "\n### Screen Annex: "
                    f"{Path(sop.source_path).stem}\n\n{sop.body}\n"
                )
                spec.write_text(current + addition, encoding="utf-8")
                written.append(f"{spec.relative_to(staging)} (annex inlined)")
    return written


def _stage_project(plan: IngestionPlan, staging: Path) -> list[str]:
    """Write `project.md` and `stacks/_default.md`."""
    if plan.project_op is None:
        return []
    written: list[str] = []
    p = staging / plan.project_op.project_md_target
    _write(p, plan.project_op.project_md_body)
    written.append(plan.project_op.project_md_target)
    s = staging / plan.project_op.stack_default_target
    _write(s, plan.project_op.stack_default_body)
    written.append(plan.project_op.stack_default_target)
    return written


def _stage_roadmap(plan: IngestionPlan, staging: Path, today: str) -> list[str]:
    """Render and write `roadmap.md`."""
    if plan.roadmap_op is None:
        return []
    body = render_roadmap(plan.roadmap_op, today)
    p = staging / plan.roadmap_op.target_path
    _write(p, body)
    return [plan.roadmap_op.target_path]


# @spec FR-007: Atomic apply — .specs/features/012-brainstorm-ingestion/spec.md#fr-007
def apply_plan(plan: IngestionPlan) -> ApplyReport:
    """Execute the plan atomically (init) or per-file (refine).

    Init mode: stage → `os.replace(staging, .specs)`.
    Refine mode: stage → walk and `os.replace` new files into `.specs/`.

    On exception during apply, staging is destroyed. In refine mode the
    error message surfaces "partial apply possible — inspect .specs/"
    so the operator knows to inspect (Finding #1).
    """
    today = date.today().isoformat()
    staging = Path(plan.staging_dir)
    target = Path(plan.target_dir)
    report = ApplyReport(mode=plan.mode)

    try:
        # Build the staged tree under staging/.specs/
        staged_specs = staging / ".specs"
        staged_specs.mkdir(parents=True, exist_ok=True)
        report.written.extend(_stage_flows(plan, staged_specs, today))
        report.copied.extend(_stage_mockups(plan, staged_specs))
        report.written.extend(_stage_screens(plan, staged_specs))
        report.written.extend(_stage_project(plan, staged_specs))
        report.written.extend(_stage_roadmap(plan, staged_specs, today))
        report.skipped.extend(plan.skipped_slugs)

        if plan.mode == "init":
            if target.exists():
                raise RuntimeError(
                    f"target {target} already exists — refuse to overwrite "
                    "(FR-012). Run `/spec.refine project --import-brainstorm` "
                    "instead."
                )
            import os

            os.replace(staged_specs, target)
            shutil.rmtree(staging, ignore_errors=True)
        else:  # refine
            try:
                _merge_into(staged_specs, target)
            except Exception as exc:
                raise RuntimeError(
                    f"refine apply failed mid-write: {exc} — "
                    "partial apply possible in refine mode — "
                    "inspect .specs/ to assess state and clean up"
                ) from exc
            shutil.rmtree(staging, ignore_errors=True)

    except Exception:
        # Init: destroy staging; .specs/ untouched.
        # Refine: best-effort destroy staging; surface partial-apply hint.
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return report


def _merge_into(staged: Path, target: Path) -> None:
    """Merge each file from `staged` into `target`, skipping pre-existing ones.

    Used in refine mode. Existing files are preserved (FR-013/FR-009).
    """
    import os

    target.mkdir(parents=True, exist_ok=True)
    for src in staged.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(staged)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # Preserve existing artifact; never overwrite.
            continue
        os.replace(src, dst)


def plan_to_json(plan: IngestionPlan) -> str:
    """Serialize an `IngestionPlan` to JSON."""
    return json.dumps(plan.model_dump(), indent=2, ensure_ascii=False)


def plan_from_json(text: str) -> IngestionPlan:
    """Deserialize an `IngestionPlan` from JSON."""
    return IngestionPlan.model_validate(json.loads(text))
