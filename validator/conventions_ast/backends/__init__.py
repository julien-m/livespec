"""AST backend adapters."""

from .ast_grep import AstGrepBackend
from .fake import FakeAstBackend

# Public backend adapters are exposed for deterministic tests and configured runtime scans.
__all__ = ["AstGrepBackend", "FakeAstBackend"]
