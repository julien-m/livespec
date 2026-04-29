"""Pydantic schemas for brainstorm ingestion.

Defines the shape of the brainstorm artifacts we ingest and of the
intermediate IngestionPlan JSON exchanged between the `plan` and
`apply` CLI subcommands.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# @spec FR-002: Flow frontmatter schema — .specs/features/012-brainstorm-ingestion/spec.md#fr-002
class FlowFrontmatter(BaseModel):
    """YAML frontmatter contract of a `specs/flows/<flow>.md` file."""

    flow: str
    title: str
    status: str
    priority: str | None = None  # P1 | P2 | P3 | None (defaults to Post-MVP)
    mockups: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    source: list[str] = Field(default_factory=list)
    generated_at: str | None = None

    @field_validator("generated_at", mode="before")
    @classmethod
    def _coerce_date(cls, v: object) -> object:
        # YAML often parses ISO dates into datetime.date — coerce to str.
        if v is None:
            return None
        return str(v)


class ExportEntry(BaseModel):
    """Single entry of `mockups/manifest.json` `exports[]`."""

    filename: str
    product: str | None = None
    parent: str | None = None
    subview: str | None = None
    state: str | None = None
    sourceNodeId: str | None = None
    sourceFile: str | None = None
    specFlow: str | None = None
    specScreen: str | None = None
    specStatus: str | None = None


class MockupManifest(BaseModel):
    """`mockups/manifest.json` schemaVersion 2 contract."""

    schemaVersion: Literal[2] = 2
    exports: list[ExportEntry] = Field(default_factory=list[ExportEntry])


class ProjectProfile(BaseModel):
    """Free-form `project-profile.md` shape used during seeding."""

    name: str | None = None
    vision: str | None = None
    audience: str | None = None
    constraints: str | None = None
    recommended_stack: str | None = None


# @spec FR-015: Screen annex shape — .specs/features/012-brainstorm-ingestion/spec.md#fr-015
class ScreenAnnex(BaseModel):
    """A `specs/screens/<filename>.md` annex with its parent ref."""

    parent: str | None = None
    body: str


class Violation(BaseModel):
    """A single grammar/integrity violation collected during validate."""

    file: str
    rule_id: str
    message: str
    line: int | None = None


class FlowOp(BaseModel):
    """Per-flow operations to perform during apply."""

    source_path: str
    slug: str
    nnn: str
    target_spec: str
    target_changelog: str
    mockup_refs: list[str] = Field(default_factory=list)
    priority: str | None = None
    title: str
    input_text: str = ""


class MockupOp(BaseModel):
    """Mockup PNG copy operations (bulk + per-feature)."""

    source_path: str
    global_target: str
    per_feature_targets: list[str] = Field(default_factory=list)


class ScreenOp(BaseModel):
    """Per-screen annex placement (annex or inline)."""

    source_path: str
    placement: Literal["annex", "inline"]
    target_path: str | None = None
    parent_feature: str | None = None
    body: str = ""


class ProjectOp(BaseModel):
    """Project profile / default stack seeding operation."""

    project_md_target: str
    stack_default_target: str
    fallback_interactive: bool = False
    project_md_body: str = ""
    stack_default_body: str = ""


class RoadmapOp(BaseModel):
    """Roadmap.md tier seeding operation."""

    target_path: str
    mvp: list[tuple[str, str]] = Field(default_factory=list[tuple[str, str]])
    post_mvp: list[tuple[str, str]] = Field(default_factory=list[tuple[str, str]])
    future: list[tuple[str, str]] = Field(default_factory=list[tuple[str, str]])


class IngestionPlan(BaseModel):
    """Full plan exchanged between `plan` and `apply` CLI subcommands."""

    mode: Literal["init", "refine"]
    cwd: str
    staging_dir: str
    target_dir: str
    next_nnn_start: int = 1
    flow_ops: list[FlowOp] = Field(default_factory=list[FlowOp])
    mockup_ops: list[MockupOp] = Field(default_factory=list[MockupOp])
    screen_ops: list[ScreenOp] = Field(default_factory=list[ScreenOp])
    project_op: ProjectOp | None = None
    roadmap_op: RoadmapOp | None = None
    skipped_slugs: list[str] = Field(default_factory=list)


class ApplyReport(BaseModel):
    """Outcome of an `apply` invocation."""

    written: list[str] = Field(default_factory=list)
    copied: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    mode: Literal["init", "refine"]
