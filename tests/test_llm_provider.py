"""Tests for the LLM provider loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from validator.llm_provider import (
    LLMProviderNotConfigured,
    call_llm,
    is_available,
    reset,
)


class TestProviderNotConfigured:
    """When no provider file exists."""

    def setup_method(self):
        reset()

    def test_is_available_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            "validator.llm_provider.PROVIDER_PATH",
            Path("/nonexistent/provider.py"),
        )
        reset()
        assert not is_available()

    def test_call_llm_raises(self, monkeypatch):
        monkeypatch.setattr(
            "validator.llm_provider.PROVIDER_PATH",
            Path("/nonexistent/provider.py"),
        )
        reset()
        with pytest.raises(LLMProviderNotConfigured):
            call_llm("test prompt")


class TestProviderLoaded:
    """When a valid provider file exists."""

    def setup_method(self):
        reset()

    def test_loads_and_calls(self, tmp_path, monkeypatch):
        provider_file = tmp_path / "provider.py"
        provider_file.write_text(
            "def call_llm(prompt, json_schema=None, model=None):\n"
            '    return f"echo:{prompt}:{model}"\n'
        )
        monkeypatch.setattr("validator.llm_provider.PROVIDER_PATH", provider_file)
        reset()

        assert is_available()
        result = call_llm("hello", model="anthropic/claude-sonnet-4.6")
        assert result == "echo:hello:anthropic/claude-sonnet-4.6"

    def test_json_schema_passed(self, tmp_path, monkeypatch):
        provider_file = tmp_path / "provider.py"
        provider_file.write_text(
            "import json\n"
            "def call_llm(prompt, json_schema=None, model=None):\n"
            '    return json.dumps({"has_schema": json_schema is not None})\n'
        )
        monkeypatch.setattr("validator.llm_provider.PROVIDER_PATH", provider_file)
        reset()

        import json

        result = json.loads(call_llm("test", json_schema={"type": "object"}))
        assert result["has_schema"] is True


class TestProviderInvalid:
    """When the provider file is broken."""

    def setup_method(self):
        reset()

    def test_missing_call_llm_function(self, tmp_path, monkeypatch):
        provider_file = tmp_path / "provider.py"
        provider_file.write_text("# no call_llm function\nx = 1\n")
        monkeypatch.setattr("validator.llm_provider.PROVIDER_PATH", provider_file)
        reset()

        assert not is_available()

    def test_syntax_error_in_provider(self, tmp_path, monkeypatch):
        provider_file = tmp_path / "provider.py"
        provider_file.write_text("def call_llm(:\n")
        monkeypatch.setattr("validator.llm_provider.PROVIDER_PATH", provider_file)
        reset()

        assert not is_available()
