# @spec FR-006: Catalogue support-class taxonomy (advisory/unsupported)
#   .specs/features/073-conventions-multilang-catalog/spec.md#fr-006

"""Static support-class taxonomy for the multilang conventions catalog.

Every catalog source that is NOT promoted to a blocking ``enforced_ast`` rule is
classified here as ``advisory`` (signalled, never blocking) or ``unsupported``
(no decidable detector yet, with a stated reason). Emitting these lists in the
verify receipt prevents a false "fully covered" claim: a domain that is only
heuristically detectable (SQL/design/pricing) or prose-only (legal/copy) is
declared, sourced where possible, and explicitly kept out of the blocking set.

This is deterministic, hand-maintained data — not derived from scanning. It is
the closed-form classification the release rule (final-plan.md) requires.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .corpus import build_corpus_manifest


class TaxonomyEntry(TypedDict):
    """One catalog item classified outside the blocking enforced set."""

    id: str
    support_class: str
    domain: str
    reason: str
    source_path: str


# Heuristic detectors with non-trivial false-positive/false-negative rates: they
# are catalogued and signalled but MUST NOT block (anti-PV2). Never counted as
# enforced.
_ADVISORY: tuple[TaxonomyEntry, ...] = (
    {
        "id": "db.sql.no_select_star",
        "support_class": "advisory",
        "domain": "database",
        "reason": "SELECT * detection is string/heuristic; not AST-decidable across "
        "ORMs/templates without false positives. Promote to enforced_semantic only "
        "after fixtures + measured FP rate.",
        "source_path": "ai-ressources/code-conventions/database.md",
    },
    {
        "id": "db.no_n_plus_one",
        "support_class": "advisory",
        "domain": "database",
        "reason": "N+1 access requires data-flow/runtime evidence; heuristic only.",
        "source_path": "ai-ressources/code-conventions/database.md",
    },
    {
        "id": "design.tokens.spacing_scale",
        "support_class": "advisory",
        "domain": "design",
        "reason": "Spacing/hex token conformance depends on design-token context "
        "and per-platform scales; signalled, not blocking.",
        "source_path": "ai-ressources/design/index.yaml",
    },
    {
        "id": "payment.idempotency_key",
        "support_class": "advisory",
        "domain": "payment",
        "reason": "Idempotency/webhook-signature correctness is semantic and "
        "provider-specific; heuristic only.",
        "source_path": "ai-ressources/stack-ref/payments",
    },
    {
        "id": "arch.single_responsibility",
        "support_class": "advisory",
        "domain": "architecture",
        "reason": "'One reason to change' is a judgement call, not AST-decidable.",
        "source_path": "ai-ressources/code-conventions/architecture.md",
    },
)

# No decidable detector yet (prose, visual, or pattern not named in source). Each
# carries an explicit reason and the future detector class required.
_UNSUPPORTED: tuple[TaxonomyEntry, ...] = (
    {
        "id": "kotlin.not_null_assert",
        "support_class": "unsupported",
        "domain": "kotlin",
        "reason": "'!!' not named as a forbidden pattern in source; precision not "
        "confirmed high (anti-hallucination). Candidate, not active.",
        "source_path": "ai-ressources/code-conventions/swift-kotlin.md",
    },
    {
        "id": "swift.force_unwrap",
        "support_class": "unsupported",
        "domain": "swift",
        "reason": "Bare '!' force-unwrap is broad/low-precision; source says "
        "'avoid', does not name an exact high-precision pattern. Candidate.",
        "source_path": "ai-ressources/code-conventions/swift-kotlin.md",
    },
    {
        "id": "pricing.economics_mor",
        "support_class": "unsupported",
        "domain": "pricing",
        "reason": "Pricing model / Merchant-of-Record guidance is prose/product "
        "decision, not code-decidable.",
        "source_path": "ai-ressources/pricing-models/index.yaml",
    },
    {
        "id": "legal.prose",
        "support_class": "unsupported",
        "domain": "legal",
        "reason": "ToS/RGPD/cookie legal prose has no code detector.",
        "source_path": "ai-ressources/legal/index.yaml",
    },
    {
        "id": "copywriting.prose",
        "support_class": "unsupported",
        "domain": "copywriting",
        "reason": "Landing/email copy quality is editorial, not code-decidable.",
        "source_path": "ai-ressources/copywriting/index.yaml",
    },
)


def advisory_rules() -> list[dict[str, object]]:
    """Return the advisory (signalled, non-blocking) catalog classification."""
    return [dict(entry) for entry in _ADVISORY]


def unsupported_rules() -> list[dict[str, object]]:
    """Return the unsupported (no decidable detector yet) classification."""
    return [dict(entry) for entry in _UNSUPPORTED]


def taxonomy_fields(project_root: Path | None = None) -> dict[str, object]:
    """Return receipt/verify taxonomy fields.

    Args:
        project_root: Optional LiveSpec project root. When provided, attach the
            exhaustive AI-res/ARS corpus manifest required by feature 073.
    """
    fields: dict[str, object] = {
        "advisory_rules": advisory_rules(),
        "unsupported_rules": unsupported_rules(),
    }
    if project_root is not None:
        fields["source_manifest"] = build_corpus_manifest(project_root)
    return fields
