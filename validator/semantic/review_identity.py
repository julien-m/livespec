"""Pure normative identity calculation for prepared review contexts."""

from __future__ import annotations

import json
from typing import Literal

from validator.normative_identity import normative_hash


def context_identity(
    feature: str,
    kind: Literal["spec", "plan"],
    model: str,
    sources: dict[str, str],
    roles: dict[str, str],
    owners: dict[str, str],
    dependencies: dict[str, str] | None,
    max_chars: int,
    unresolved_references: tuple[str, ...],
    requirement_scope: tuple[str, ...] | None,
) -> str:
    """Fingerprint the unchanged normative identity and explicit review policy."""
    from validator.semantic import review_context as context

    identity = dict(
        feature=feature,
        kind=kind,
        model=model,
        sources={
            name: normative_hash(
                text,
                lifecycle_document=context.is_lifecycle_source(
                    name, roles.get(name, name), feature
                ),
            )
            for name, text in sorted(sources.items())
        },
        roles=roles,
        owners=owners,
        dependencies=dependencies or {},
        policy=context.POLICY_VERSION,
        schema=context.SCHEMA_VERSION,
        prompt=context.PROMPT_VERSION,
        budget=max_chars,
        unresolved=unresolved_references,
    )
    if requirement_scope is not None:
        identity["requirement_scope"] = requirement_scope
    return context.content_hash(json.dumps(identity, sort_keys=True))
