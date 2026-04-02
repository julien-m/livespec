"""Embedding computation, caching, and section extraction."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path


def cosine_distance(u: list[float], v: list[float]) -> float:
    """Compute cosine distance between two vectors. Returns 0.0 (identical) to 2.0 (opposite)."""
    if len(u) != len(v):
        raise ValueError(f"Vector dimension mismatch: {len(u)} vs {len(v)}")

    dot = sum(a * b for a, b in zip(u, v))
    norm_u = math.sqrt(sum(a * a for a in u))
    norm_v = math.sqrt(sum(b * b for b in v))

    if norm_u == 0.0 or norm_v == 0.0:
        return 1.0

    similarity = dot / (norm_u * norm_v)
    # Clamp to [-1, 1] to handle floating point errors
    similarity = max(-1.0, min(1.0, similarity))
    return 1.0 - similarity


@dataclass
class EmbeddingSection:
    """A single embedded section from a spec file."""

    section_name: str
    content_hash: str  # sha256 of section content
    embedding: list[float]
    token_count: int


@dataclass
class EmbeddingCache:
    """Persistent cache of embeddings for a spec tree."""

    version: str  # ISO date
    model: str
    sections: dict[str, EmbeddingSection] = field(default_factory=dict)


def load_cache(path: Path) -> EmbeddingCache | None:
    """Load embedding cache from a JSON file. Returns None if missing or corrupt."""
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(raw, dict) or "version" not in raw or "model" not in raw:
        return None

    sections: dict[str, EmbeddingSection] = {}
    for key, sec in raw.get("sections", {}).items():
        try:
            sections[key] = EmbeddingSection(
                section_name=sec["section_name"],
                content_hash=sec["content_hash"],
                embedding=sec["embedding"],
                token_count=sec["token_count"],
            )
        except (KeyError, TypeError):
            continue

    return EmbeddingCache(
        version=raw["version"],
        model=raw["model"],
        sections=sections,
    )


def save_cache(cache: EmbeddingCache, path: Path) -> None:
    """Persist embedding cache to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    serialized = {
        "version": cache.version,
        "model": cache.model,
        "sections": {
            key: {
                "section_name": sec.section_name,
                "content_hash": sec.content_hash,
                "embedding": sec.embedding,
                "token_count": sec.token_count,
            }
            for key, sec in cache.sections.items()
        },
    }
    path.write_text(json.dumps(serialized, indent=2))


def needs_reindex(cache: EmbeddingCache, current_model: str) -> bool:
    """Check whether the cache was built with a different model."""
    return cache.model != current_model


def compute_embedding(text: str, model: str) -> list[float]:
    """Compute an embedding vector for the given text.

    Uses the LLM provider to ask for a semantic comparison score instead of
    real vector embeddings. This is a pragmatic fallback when no embedding API
    is available — the cosine distance functions still work with cached vectors.

    For real embeddings, install the openai package and configure OPENAI_API_KEY,
    or implement a custom provider that returns vectors.
    """
    raise NotImplementedError(
        "Embedding API not configured. "
        "Real embeddings require the openai package + OPENAI_API_KEY. "
        "For semantic comparison without embeddings, use the contradiction "
        "detection module which works via the LLM provider."
    )


# Section extraction patterns
_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "user-stories": re.compile(
        r"^##\s+(?:User\s+Stories?|Histoires?\s+utilisateur)\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "acceptance-criteria": re.compile(
        r"^##\s+(?:Acceptance\s+Criteria|Crit[eè]res?\s+d['']acceptation)\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
    "functional-requirements": re.compile(
        r"^##\s+(?:Functional\s+Requirements?|Exigences?\s+fonctionnelles?)\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    ),
}


def extract_sections(spec_content: str) -> dict[str, str]:
    """Extract known sections from spec markdown content.

    Returns a dict mapping section name to its content body.
    Looks for: user-stories, acceptance-criteria, functional-requirements.
    """
    results: dict[str, str] = {}

    for name, pattern in _SECTION_PATTERNS.items():
        match = pattern.search(spec_content)
        if match:
            body = match.group(1).strip()
            if body:
                results[name] = body

    return results


def content_hash(text: str) -> str:
    """Compute SHA-256 hash of text content."""
    return hashlib.sha256(text.encode()).hexdigest()
