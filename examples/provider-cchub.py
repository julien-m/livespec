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
import tempfile

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
        # `cc-hub codex --schema` only accepts a FILE PATH (unlike `cc-hub ask`,
        # which also takes inline JSON). Passing inline JSON makes cc-hub treat
        # the payload as a filename → "File name too long" (os error 63).
        schema_path = _write_schema_tempfile(_normalize_schema_for_codex(json_schema))
        cmd.extend(["--schema", schema_path])
    return _run(cmd)


def _normalize_schema_for_codex(json_schema: dict) -> dict:
    """Recursively add `additionalProperties: false` to every object node.

    OpenAI strict structured-output mode (used by Codex) rejects any object
    schema where `additionalProperties` is not explicitly false. LiveSpec
    schemas are provider-agnostic, so this adaptation lives at the codex
    boundary only.
    """
    # Unwrap the OpenRouter/OpenAI response_format envelope ({"name", "strict",
    # "schema": {...}}) — Codex expects the bare JSON Schema with a root "type".
    inner = json_schema.get("schema")
    if "type" not in json_schema and isinstance(inner, dict):
        json_schema = inner
    normalized = _normalize_schema_node(json_schema)
    return normalized if isinstance(normalized, dict) else json_schema


def _normalize_schema_node(node: object) -> object:
    if isinstance(node, dict):
        normalized = {key: _normalize_schema_node(value) for key, value in node.items()}
        if normalized.get("type") == "object" and "additionalProperties" not in normalized:
            normalized["additionalProperties"] = False
        return normalized
    if isinstance(node, list):
        return [_normalize_schema_node(item) for item in node]
    return node


def _write_schema_tempfile(json_schema: dict) -> str:
    """Persist the schema to a temp .json file and return its path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="livespec-schema-", delete=False, encoding="utf-8"
    ) as handle:
        json.dump(json_schema, handle)
        return handle.name


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
