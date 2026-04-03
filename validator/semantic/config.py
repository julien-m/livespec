"""Semantic validation configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SemanticConfig:
    """Configuration for Layer 4 semantic validation.

    Attributes:
        drift_info_threshold: Cosine distance threshold for info-level drift.
        drift_warning_threshold: Cosine distance threshold for warning-level drift.
        drift_blocking_threshold: Cosine distance threshold for blocking drift.
        confidence_threshold: Minimum confidence to report a contradiction.
        suspicion_threshold: Minimum confidence for potential contradictions.
        embedding_model: Embedding model name for semantic analysis.
        embedding_dimension: Dimension of embedding vectors.
        mutation_acceptable_score: Minimum mutation kill score (0.0-1.0).
        multi_model_divergence_threshold: Maximum divergence allowed in multi-model consensus.
        review_confidence_threshold: Minimum reviewer confidence (1-5 scale) to skip cascade retry.
    """

    # Embedding thresholds (cosine distance)
    drift_info_threshold: float = 0.05
    drift_warning_threshold: float = 0.15
    drift_blocking_threshold: float = 0.30

    # Contradiction detection
    confidence_threshold: float = 0.75
    suspicion_threshold: float = 0.50

    # Embedding model
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Mutation testing
    mutation_acceptable_score: float = 0.80

    # Multi-model
    multi_model_divergence_threshold: float = 0.25

    # Plan review
    review_reviewers: list[str] = field(default_factory=list)
    review_confidence_threshold: float = 3.0


def load_semantic_config(specs_root: Path) -> SemanticConfig:
    """Load from .specs/semantic/config.yaml if present, else defaults.

    Args:
        specs_root: Path to the .specs directory.

    Returns:
        Populated config if config.yaml exists and is valid, else defaults.
    """
    config_path = specs_root / "semantic" / "config.yaml"
    if not config_path.exists():
        return SemanticConfig()

    raw = yaml.safe_load(config_path.read_text())
    if not isinstance(raw, dict):
        return SemanticConfig()

    field_names = {f.name for f in SemanticConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in raw.items() if k in field_names}
    return SemanticConfig(**filtered)
