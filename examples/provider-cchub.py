"""LiveSpec LLM provider using cc-hub.

Copy this file to ~/.config/livespec/provider.py

Routing logic:
- Google models (gemini) → cc-hub ask --provider poyo
- OpenAI GPT models → cc-hub codex
- Everything else → cc-hub ask (OpenRouter)

Model format: OpenRouter canonical IDs (e.g., "anthropic/claude-sonnet-4.6")
"""

from __future__ import annotations

import json
import subprocess
import sys

# Default model when none is specified
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"


def call_llm(
    prompt: str,
    json_schema: dict | None = None,
    model: str | None = None,
) -> str:
    """Route LLM calls through cc-hub based on model provider."""
    model = model or DEFAULT_MODEL

    if _is_google_model(model):
        return _call_poyo(prompt, json_schema, model)
    elif _is_openai_model(model):
        return _call_codex(prompt, json_schema, model)
    else:
        return _call_openrouter(prompt, json_schema, model)


def _is_google_model(model: str) -> bool:
    return model.startswith("google/")


def _is_openai_model(model: str) -> bool:
    return model.startswith("openai/")


def _call_openrouter(prompt: str, json_schema: dict | None, model: str) -> str:
    """Call via cc-hub ask (OpenRouter provider)."""
    cmd = ["cc-hub", "ask", prompt, "--model", model]
    if json_schema:
        cmd.extend(["--schema", json.dumps(json_schema)])
    elif _wants_json(prompt):
        cmd.append("--json")
    return _run(cmd)


def _call_poyo(prompt: str, json_schema: dict | None, model: str) -> str:
    """Call via cc-hub ask with Poyo provider for Google models."""
    cmd = ["cc-hub", "ask", prompt, "--provider", "poyo", "--model", model]
    if json_schema:
        cmd.extend(["--schema", json.dumps(json_schema)])
    elif _wants_json(prompt):
        cmd.append("--json")
    return _run(cmd)


def _call_codex(prompt: str, json_schema: dict | None, model: str) -> str:
    """Call via cc-hub codex for OpenAI models."""
    cmd = ["cc-hub", "codex", prompt, "--model", model]
    if json_schema:
        cmd.extend(["--schema", json.dumps(json_schema)])
    return _run(cmd)


def _wants_json(prompt: str) -> bool:
    """Heuristic: if the prompt asks for JSON output, add --json flag."""
    lower = prompt.lower()
    return "json" in lower and ("retourne" in lower or "return" in lower or "réponds" in lower)


def _run(cmd: list[str]) -> str:
    """Execute a cc-hub command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"cc-hub error (exit {result.returncode}): {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"cc-hub failed: {result.stderr[:200]}")
        return result.stdout.strip()
    except FileNotFoundError as exc:
        raise RuntimeError(
            "cc-hub not found in PATH. Install it first: https://github.com/julien-m/cc-hub"
        ) from exc
