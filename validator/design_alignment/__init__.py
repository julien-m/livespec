"""Design alignment gate API."""

# @spec FR-003: Design alignment module
#   — .specs/features/047-design-alignment-gate/spec.md#fr-003

from .core import compare_contract_files
from .models import AlignmentIssue, AlignmentResult, NormalizedContract

__all__ = [
    "AlignmentIssue",
    "AlignmentResult",
    "NormalizedContract",
    "compare_contract_files",
]
