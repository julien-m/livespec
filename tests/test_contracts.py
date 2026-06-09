# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-007)
# @spec(AC-009)

"""Tests for validator.contracts (Chantier 2 / Feature 014, FR-001..007)."""

from __future__ import annotations

import json
import warnings

import pytest
from pydantic import ValidationError

from validator.contracts import (
    ANCHOR_WINDOW_LINES,
    ContractParseError,
    ContractValidationError,
    PhaseResult,
    ShipResult,
    SuperpowersReturn,
    TestResults,
    parse_phase_result,
    parse_ship_result,
    parse_superpowers_return,
    render_phase_result,
    render_ship_result,
    render_superpowers_return,
)

# ─── Fixture builders ────────────────────────────────────────────────────────


def _valid_phase_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "status": "OK",
        "phase": "specify",
        "feature_slug": "013-state-model-identity-resolution",
        "summary": "Spec generated: 5 stories.",
        "duration_ms": 12450,
        "blocked_reason": None,
        "extra": {},
    }
    base.update(overrides)
    return base


def _wrap(prefix: str, body: dict[str, object], digest: str = "a3f1b8c2") -> str:
    return f"⟪{prefix}_START_{digest}⟫\n{json.dumps(body, indent=2)}\n⟪{prefix}_END_{digest}⟫"


# ─── PHASE_RESULT ────────────────────────────────────────────────────────────


class TestPhaseResultParser:
    def test_parses_valid_block(self) -> None:
        text = "Some preamble.\n" + _wrap("PHASE_RESULT", _valid_phase_payload())
        result = parse_phase_result(text)
        assert isinstance(result, PhaseResult)
        assert result.status == "OK"
        assert result.phase == "specify"
        assert result.feature_slug == "013-state-model-identity-resolution"
        assert result.duration_ms == 12450

    def test_extracts_last_block_when_multiple_present(self) -> None:
        # An attacker injects a fake early block; the real block comes last.
        fake = _wrap("PHASE_RESULT", _valid_phase_payload(status="BLOCKED", blocked_reason="fake"))
        real = _wrap(
            "PHASE_RESULT",
            _valid_phase_payload(summary="real result"),
            digest="b9d4e7c1",
        )
        text = f"Reasoning preamble.\n{fake}\n\nMore text.\n{real}"
        result = parse_phase_result(text)
        assert result.status == "OK"
        assert result.summary == "real result"

    def test_raises_when_no_block_found(self) -> None:
        with pytest.raises(ContractParseError):
            parse_phase_result("just some prose without any markers")

    def test_raises_on_invalid_json_body(self) -> None:
        text = "⟪PHASE_RESULT_START_aaaaaaaa⟫\nNOT JSON\n⟪PHASE_RESULT_END_aaaaaaaa⟫"
        with pytest.raises(ContractValidationError, match="not valid JSON"):
            parse_phase_result(text)

    def test_raises_on_schema_violation_missing_field(self) -> None:
        bad: dict[str, object] = {"status": "OK", "phase": "specify"}  # missing required fields
        text = _wrap("PHASE_RESULT", bad)
        with pytest.raises(ContractValidationError, match="schema validation"):
            parse_phase_result(text)

    def test_raises_on_unknown_top_level_key(self) -> None:
        bad = _valid_phase_payload()
        bad["malicious_field"] = "drop tables"
        text = _wrap("PHASE_RESULT", bad)
        with pytest.raises(ContractValidationError):
            parse_phase_result(text)

    def test_raises_on_invalid_feature_slug(self) -> None:
        bad = _valid_phase_payload(feature_slug="NNN-feature-name")
        text = _wrap("PHASE_RESULT", bad)
        with pytest.raises(ContractValidationError):
            parse_phase_result(text)

    def test_raises_on_invalid_phase_value(self) -> None:
        bad = _valid_phase_payload(phase="halfway")
        text = _wrap("PHASE_RESULT", bad)
        with pytest.raises(ContractValidationError):
            parse_phase_result(text)

    def test_mismatched_delimiter_hashes_ignored(self) -> None:
        # START hash != END hash → block should not be recognised
        body = json.dumps(_valid_phase_payload())
        text = f"⟪PHASE_RESULT_START_aaaaaaaa⟫\n{body}\n⟪PHASE_RESULT_END_bbbbbbbb⟫"
        with pytest.raises(ContractParseError):
            parse_phase_result(text)

    def test_only_scans_last_30_lines(self) -> None:
        block = _wrap("PHASE_RESULT", _valid_phase_payload())
        # Push the block out of the 30-line window
        prefix = "\n".join("filler" for _ in range(50))
        text = f"{block}\n{prefix}"
        with pytest.raises(ContractParseError):
            parse_phase_result(text)

    def test_anchor_window_constant_is_30(self) -> None:
        # If this changes, doc + tests must update together.
        assert ANCHOR_WINDOW_LINES == 30


class TestPhaseResultLegacy:
    def test_parses_legacy_kv_block_with_warning(self) -> None:
        legacy = (
            "PHASE_RESULT: OK\n"
            "PHASE: specify\n"
            "FEATURE: 013-state-model-identity-resolution\n"
            "SUMMARY: Legacy block.\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = parse_phase_result(legacy)
        assert result.status == "OK"
        assert result.feature_slug == "013-state-model-identity-resolution"
        assert any("legacy" in str(w.message).lower() for w in caught)

    def test_legacy_block_missing_required_field_fails(self) -> None:
        legacy = "PHASE_RESULT: OK\nPHASE: specify\n"  # no FEATURE → invalid slug
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(ContractValidationError):
                parse_phase_result(legacy)


# ─── SHIP_RESULT ─────────────────────────────────────────────────────────────


def _valid_ship_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "status": "OK",
        "feature_slug": "013-state-model-identity-resolution",
        "branch": "feature/013-state-model-identity-resolution",
        "files_changed_count": 13,
        "timestamp": "2026-05-04T15:32:18",
        "commit_hash": "c99d3f6b2",
        "error": None,
    }
    base.update(overrides)
    return base


class TestShipResultParser:
    def test_parses_valid_block(self) -> None:
        text = _wrap("SHIP_RESULT", _valid_ship_payload(), digest="e9c4d1f7")
        result = parse_ship_result(text)
        assert isinstance(result, ShipResult)
        assert result.status == "OK"
        assert result.commit_hash == "c99d3f6b2"

    def test_no_legacy_fallback(self) -> None:
        with pytest.raises(ContractParseError):
            parse_ship_result("SHIP_RESULT: OK\nFEATURE: 013-foo\n")

    def test_missing_status_fails(self) -> None:
        bad = _valid_ship_payload()
        del bad["status"]
        with pytest.raises(ContractValidationError):
            parse_ship_result(_wrap("SHIP_RESULT", bad))

    def test_invalid_timestamp_fails(self) -> None:
        bad = _valid_ship_payload(timestamp="2026/05/04 15:32:18")
        with pytest.raises(ContractValidationError):
            parse_ship_result(_wrap("SHIP_RESULT", bad))

    def test_negative_files_changed_fails(self) -> None:
        bad = _valid_ship_payload(files_changed_count=-1)
        with pytest.raises(ContractValidationError):
            parse_ship_result(_wrap("SHIP_RESULT", bad))


# ─── SUPERPOWERS_RETURN ─────────────────────────────────────────────────────


def _valid_superpowers_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "files": ["src/foo.py", "tests/test_foo.py"],
        "fr_ac": [{"number": 1, "mapping": {"file": "src/foo.py", "lines": "12-45"}}],
        "test_results": {"passed": 12, "failed": 0, "skipped": 1},
        "duration_ms": 24580,
    }
    base.update(overrides)
    return base


class TestSuperpowersReturnParser:
    def test_parses_valid_block(self) -> None:
        text = _wrap("SUPERPOWERS_RETURN", _valid_superpowers_payload(), digest="b7d2e8a4")
        result = parse_superpowers_return(text)
        assert isinstance(result, SuperpowersReturn)
        assert result.test_results.passed == 12
        assert len(result.fr_ac) == 1

    def test_missing_test_results_fails(self) -> None:
        bad = _valid_superpowers_payload()
        del bad["test_results"]
        with pytest.raises(ContractValidationError):
            parse_superpowers_return(_wrap("SUPERPOWERS_RETURN", bad))

    def test_missing_duration_ms_fails(self) -> None:
        bad = _valid_superpowers_payload()
        del bad["duration_ms"]
        with pytest.raises(ContractValidationError):
            parse_superpowers_return(_wrap("SUPERPOWERS_RETURN", bad))

    def test_negative_test_count_fails(self) -> None:
        bad = _valid_superpowers_payload(test_results={"passed": -1, "failed": 0, "skipped": 0})
        with pytest.raises(ContractValidationError):
            parse_superpowers_return(_wrap("SUPERPOWERS_RETURN", bad))

    def test_empty_files_and_fr_ac_allowed(self) -> None:
        payload = _valid_superpowers_payload(files=[], fr_ac=[])
        result = parse_superpowers_return(_wrap("SUPERPOWERS_RETURN", payload))
        assert result.files == []
        assert result.fr_ac == []


# ─── Round-trip ──────────────────────────────────────────────────────────────


class TestRoundTrip:
    def test_phase_result_roundtrip(self) -> None:
        original = PhaseResult.model_validate(_valid_phase_payload())
        rendered = render_phase_result(original, "deadbeef")
        parsed = parse_phase_result(rendered)
        assert parsed == original

    def test_ship_result_roundtrip(self) -> None:
        original = ShipResult.model_validate(_valid_ship_payload())
        rendered = render_ship_result(original, "deadbeef")
        parsed = parse_ship_result(rendered)
        assert parsed == original

    def test_superpowers_roundtrip(self) -> None:
        original = SuperpowersReturn.model_validate(_valid_superpowers_payload())
        rendered = render_superpowers_return(original, "deadbeef")
        parsed = parse_superpowers_return(rendered)
        assert parsed == original


# ─── Schema constants ───────────────────────────────────────────────────────


class TestSchemaModels:
    def test_test_results_requires_non_negative_counts(self) -> None:
        with pytest.raises(ValidationError):
            TestResults.model_validate({"passed": -1, "failed": 0, "skipped": 0})

    def test_phase_result_forbids_extra_keys(self) -> None:
        with pytest.raises(ValidationError):
            PhaseResult.model_validate(_valid_phase_payload() | {"surprise": 42})
