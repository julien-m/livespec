"""Strict public C51 review data; policy and filesystem checks live in the caller."""

from typing import Annotated, Literal, Self, cast

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

# @spec FR-007: Typed reviewed source boundary
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-007

NonemptyString = Annotated[str, Field(min_length=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Category = Literal[
    "structure",
    "action",
    "permission",
    "validation",
    "transition",
    "effect",
    "persistence",
    "result",
]


def _strict_integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("Expected an integer, excluding booleans")
    return value


VersionOne = Annotated[Literal[1], BeforeValidator(_strict_integer)]
Zero = Annotated[Literal[0], BeforeValidator(_strict_integer)]


class StrictModel(BaseModel):
    """Reject extra fields and type coercion at every nested object boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class File(StrictModel):
    """A file reference whose bytes must be checked separately."""

    path: NonemptyString
    sha256: Sha256


class Scope(StrictModel):
    """Explicit project and workspace selected by the caller."""

    project_root: NonemptyString
    workspace: NonemptyString


class VerificationPolicy(StrictModel):
    """Explicit C20 applicability decisions; their authority is checked by the caller."""

    version: VersionOne
    generated_docs: Literal["required", "not_applicable"]
    native_geometry: Literal["required", "not_applicable"]
    homologous_references: Literal["required", "not_applicable"]
    native_export: Literal["required", "not_applicable"]


# @spec FR-008: Typed policy and imported source ancestry
# .specs/features/077-penflow-cumulative-verdict-consumer/spec.md#fr-008
class PolicySource(StrictModel):
    """Reviewed policy decisions bound to workflow and optional imported ancestry."""

    kind: Literal["penflow-verification-policy-source"]
    version: VersionOne
    workflow: File
    decisions: VerificationPolicy
    inherited_authority: File | None


class ImportedAuthorityFile(StrictModel):
    """Historical origin and locally copied bytes; path containment is caller policy."""

    source_path: NonemptyString
    path: NonemptyString
    sha256: Sha256


class AuthorityImport(StrictModel):
    """Locally archived Brainstorm ancestry, independent of the old source location."""

    kind: Literal["penflow-brainstorm-authority-import"]
    version: VersionOne
    origin_scope: Scope
    workspace: NonemptyString
    report: File
    files: Annotated[list[ImportedAuthorityFile], Field(min_length=1)]


class Assertion(StrictModel):
    """One typed predicate, without evaluating its applicability or result."""

    operator: Literal[
        "equals",
        "not_equals",
        "exists",
        "absent",
        "matches",
        "contains",
        "changed",
        "unchanged",
        "greater_than",
        "less_than",
    ]
    pointer: Annotated[str, Field(pattern=r"^(/.*)?$")]
    expected: JsonValue
    capability: Literal["ui", "network", "storage"]


class ExpectedOutcome(StrictModel):
    """Approved predicates for one obligation."""

    obligation_id: NonemptyString
    source_pointer: NonemptyString
    assertions: Annotated[list[Assertion], Field(min_length=1)]
    category: Category


class ApprovedBinding(StrictModel):
    """A requirement-to-obligation mapping reviewed by the workflow."""

    requirement_id: NonemptyString
    obligation_id: NonemptyString
    category: Category
    expected: ExpectedOutcome


class Requirement(StrictModel):
    """Source requirement identity; no inferred outcome category."""

    id: NonemptyString
    source_pointer: NonemptyString
    text_sha256: Sha256


class Projection(StrictModel):
    """Explicit source denominator and approved obligation bindings."""

    source_kind: Literal["livespec-fr-ac-v1", "brainstorm-product-v1"]
    sources: Annotated[list[File], Field(min_length=1)]
    requirements: Annotated[list[Requirement], Field(min_length=1)]
    bindings: list[ApprovedBinding]
    uncovered: list[NonemptyString]


class RetiredProjection(StrictModel):
    """An empty denominator, accepted only inside an entirely retired envelope."""

    source_kind: Literal["livespec-fr-ac-v1"]
    sources: Annotated[list[File], Field(max_length=0)]
    requirements: Annotated[list[Requirement], Field(max_length=0)]
    bindings: Annotated[list[ApprovedBinding], Field(max_length=0)]
    uncovered: Annotated[list[NonemptyString], Field(max_length=0)]


class ApprovedSource(StrictModel):
    """Raw and semantic identities with an immutable reviewed copy."""

    path: NonemptyString
    sha256: Sha256
    semantic_sha256: Sha256
    reviewed_snapshot: File


class ApprovalInputs(StrictModel):
    """Exact source, plan, contract, projection and selection identities."""

    sources: Annotated[list[ApprovedSource], Field(min_length=1)]
    plans: Annotated[list[ApprovedSource], Field(min_length=1)]
    contract: File
    projection_sha256: Sha256
    selection_sha256: Sha256
    verification_policy: File | None = None

    @field_validator("verification_policy", mode="before")
    @classmethod
    def reject_explicit_null_policy(cls, value: object) -> object:
        """Historical omission is allowed, but a present policy must be a file reference."""
        if value is None:
            raise ValueError("verification_policy must be omitted or a file reference")
        return value

    @model_serializer(mode="wrap")
    def preserve_historical_omission(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        """Keep old reviewed bytes stable without dropping required nulls elsewhere."""
        result = cast(dict[str, object], handler(self))
        if self.verification_policy is None:
            result.pop("verification_policy", None)
        return result


class Change(StrictModel):
    """Reviewed source reduction or binding change."""

    source_path: NonemptyString
    old_sha256: Sha256
    new_sha256: Sha256
    removed_requirement_ids: list[NonemptyString]
    changed_binding_ids: list[NonemptyString]


class ReviewFinding(StrictModel):
    """Structured reviewer finding."""

    severity: Literal["BLOCKING", "WARNING", "INFO"]
    message: NonemptyString
    requirement_ids: list[NonemptyString]


class ReviewMetadata(StrictModel):
    """Reviewer provenance and findings shared by results and approvals."""

    invocation_id: NonemptyString
    producer_id: NonemptyString
    input_sha256: Sha256
    output: File
    findings: list[ReviewFinding]


class Review(ReviewMetadata):
    """A review result; consistency of verdict and findings is caller policy."""

    verdict: Literal["PASS", "BLOCKING"]
    blocking_count: Annotated[int, Field(ge=0)]


class ApprovedReview(ReviewMetadata):
    """The public approval shape only admits PASS and zero blocking count."""

    verdict: Literal["PASS"]
    blocking_count: Zero


class SelectedEnvelope(StrictModel):
    """Governed selection; relational invariants supplement JSON Schema uniqueItems."""

    disposition: Literal["active", "retired"]
    selection: Annotated[list[NonemptyString], Field(min_length=1)]
    retired_features: list[NonemptyString]

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        """Require sorted unique selection, a retired subset and matching disposition."""
        if self.selection != sorted(set(self.selection)):
            raise ValueError("selection must be sorted and unique")
        if self.retired_features != sorted(set(self.retired_features)):
            raise ValueError("retired_features must be sorted and unique")
        if not set(self.retired_features) <= set(self.selection):
            raise ValueError("retired_features must be a subset of selection")
        active = set(self.selection) - set(self.retired_features)
        if self.disposition != ("active" if active else "retired"):
            raise ValueError("disposition must match the active selection")
        return self


class ProjectionEnvelope(SelectedEnvelope):
    """Empty projections are reserved for an entirely retired approved selection."""

    projection: Projection | RetiredProjection

    @model_validator(mode="after")
    def validate_projection_disposition(self) -> Self:
        """Enforce the same conditional projection shape as the public schema."""
        if isinstance(self.projection, RetiredProjection) != (self.disposition == "retired"):
            raise ValueError("projection must match disposition")
        return self


class ReviewSnapshot(ProjectionEnvelope):
    """Immutable pre-dispatch inputs presented to the reviewer."""

    kind: Literal["livespec-penflow-review-snapshot"]
    version: VersionOne
    command: Literal["spec-plan"]
    feature: NonemptyString
    scope: Scope
    inputs: ApprovalInputs
    prior_receipt: File | None
    changes: list[Change]


class ReviewResult(StrictModel):
    """External reviewer result bound to the requested snapshot."""

    kind: Literal["livespec-penflow-review-result"]
    version: VersionOne
    snapshot: File
    review: Review


class ReviewApproval(SelectedEnvelope):
    """Workflow-published approval after validating a bound review result."""

    kind: Literal["livespec-penflow-review-approval"]
    version: VersionOne
    command: Literal["spec-plan"]
    feature: NonemptyString
    scope: Scope
    inputs: ApprovalInputs
    review: ApprovedReview
    prior_receipt: File | None
    changes: list[Change]
    snapshot: File


class RequirementsBaseline(ProjectionEnvelope):
    """Consumer-published denominator derived from immutable approvals."""

    kind: Literal["livespec-penflow-requirements-baseline"]
    version: VersionOne
    scope: Scope
    approval_receipts: Annotated[list[File], Field(min_length=1)]
    sources: Annotated[list[ApprovedSource], Field(min_length=1)]
    contract: File
    previous: File | None
