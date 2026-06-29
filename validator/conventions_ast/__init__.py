"""AST convention detection layer for LiveSpec conventions."""

from .engine import run_ast_conventions

# Public surface keeps callers on the engine entry point instead of backend internals.
__all__ = ["run_ast_conventions"]
