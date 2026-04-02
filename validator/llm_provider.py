"""LLM provider loader — loads call_llm() from ~/.config/livespec/provider.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

PROVIDER_PATH = Path.home() / ".config" / "livespec" / "provider.py"

_provider_module: Any = None
_load_attempted: bool = False


class LLMProviderNotConfigured(Exception):
    """Raised when no LLM provider is available."""

    def __init__(self) -> None:
        super().__init__(
            f"No LLM provider configured.\n"
            f"Create {PROVIDER_PATH} with a call_llm(prompt, json_schema, model) function.\n"
            f"See examples/provider-cchub.py for a template."
        )


def _load_provider() -> Any:
    """Dynamically load the provider module from disk."""
    global _provider_module, _load_attempted

    if _load_attempted:
        return _provider_module

    _load_attempted = True

    if not PROVIDER_PATH.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location("livespec_provider", PROVIDER_PATH)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["livespec_provider"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "call_llm"):
            raise AttributeError(
                f"{PROVIDER_PATH} must define a call_llm(prompt, json_schema, model) function"
            )

        _provider_module = module
        return module
    except Exception as e:
        print(f"Warning: failed to load LLM provider from {PROVIDER_PATH}: {e}", file=sys.stderr)
        return None


def is_available() -> bool:
    """Check if an LLM provider is configured and loadable."""
    return _load_provider() is not None


def call_llm(
    prompt: str,
    json_schema: dict | None = None,
    model: str | None = None,
) -> str:
    """Call the configured LLM provider.

    Args:
        prompt: The prompt text to send.
        json_schema: Optional JSON schema to constrain output format.
        model: Optional model ID in OpenRouter format (e.g., "anthropic/claude-sonnet-4.6").
               If None, the provider uses its own default.

    Returns:
        The LLM response as a string.

    Raises:
        LLMProviderNotConfigured: If no provider is installed.
    """
    provider = _load_provider()
    if provider is None:
        raise LLMProviderNotConfigured()

    return provider.call_llm(prompt, json_schema=json_schema, model=model)


def reset() -> None:
    """Reset the provider cache (useful for testing)."""
    global _provider_module, _load_attempted
    _provider_module = None
    _load_attempted = False
