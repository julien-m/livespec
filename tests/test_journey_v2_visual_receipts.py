# LiveSpec traceability anchors
# @spec(AC-041)
# @spec(AC-042)
# @spec(AC-043)

"""`livespec journey visual-verify` checks agent receipts for compiled LLM visual contracts."""

# @spec AC-041: Strict JSON verdict with criteria, explanation, confidence, boxes
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#ac-041
# @spec AC-042: Advisory by default, blocking when configured, disabled without privacy
# — .specs/features/057-cross-feature-user-journeys-v2/spec.md#ac-042

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from tests.test_journey_v2_validation import _write_feature, _write_v2_journey
from validator.cli import app
from validator.journeys.compiler import compile_journeys

_JOURNEY = "onboarding-first-project"
_CONTRACT = f".specs/journeys/{_JOURNEY}/compiled/visual-contracts/success_card_padding.json"
_RECEIPT = f".specs/journeys/{_JOURNEY}/visual-receipts/success_card_padding.json"


def _compile(tmp_path: Path, *, blocking: bool = True, privacy: str = "") -> None:
    specs = tmp_path / ".specs"
    specs.mkdir()
    _write_feature(specs, "001-onboarding")
    _write_feature(specs, "012-projects")
    source = _write_v2_journey(specs)
    policy = privacy or "privacy:\n  llm_allowed: true\n  retention: local\n"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            "privacy:\n  llm_allowed: false\n  retention: none\n",
            "visual_checks:\n  - id: success-card-padding\n    mode: llm\n"
            "    assertion: min_margin\n    target:\n      semantic_id: success-card\n"
            "    prompt: Verify the card keeps visible padding.\n"
            f"    blocking: {'true' if blocking else 'false'}\n{policy}",
        ),
        encoding="utf-8",
    )
    result = compile_journeys(tmp_path, journey=_JOURNEY)
    assert result.error_count == 0, [issue.code for issue in result.issues]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_receipt(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    """Write the capture the agent examined and its receipt."""
    capture = tmp_path / ".specs" / "journeys" / _JOURNEY / "runs" / "visual" / "card.png"
    capture.parent.mkdir(parents=True, exist_ok=True)
    capture.write_bytes(b"\x89PNG fake capture")
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "journey_id": _JOURNEY,
        "check_id": "success-card-padding",
        "contract_sha256": _sha(tmp_path / _CONTRACT),
        "capture_path": capture.relative_to(tmp_path).as_posix(),
        "capture_sha256": _sha(capture),
        "verdict": "pass",
        "confidence": 0.9,
        "criteria_passed": ["visible padding"],
        "criteria_failed": [],
        "explanation": "The card keeps 16px padding on every side.",
        "bounding_boxes": [{"x": 10, "y": 20, "width": 300, "height": 120, "label": "card"}],
        "evaluator": {"name": "claude-code", "locality": "remote"},
        "evaluated_at": "2026-10-12T10:00:00Z",
        **overrides,
    }
    path = tmp_path / _RECEIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt


def _verify(tmp_path: Path, monkeypatch: MonkeyPatch) -> tuple[int, dict[str, Any]]:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["journey", "visual-verify", "--json"])
    return result.exit_code, json.loads(result.output)


def test_valid_pass_receipt_is_accepted(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """A schema-valid pass receipt whose hashes match verifies cleanly."""
    _compile(tmp_path)
    _write_receipt(tmp_path)

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 0
    assert [o["status"] for o in payload["outcomes"]] == ["pass"]


def test_missing_receipt_blocks_and_names_the_expected_path(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Each compiled contract needs a receipt at a predictable path."""
    _compile(tmp_path)

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 1
    assert payload["outcomes"][0]["status"] == "missing"
    assert payload["outcomes"][0]["receipt_path"] == _RECEIPT


def test_changed_capture_or_contract_makes_the_receipt_stale(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Hashes bind the verdict to the exact capture and contract evaluated."""
    _compile(tmp_path)
    receipt = _write_receipt(tmp_path)
    (tmp_path / receipt["capture_path"]).write_bytes(b"another capture")

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 1
    assert payload["outcomes"][0]["status"] == "stale"


@pytest.mark.parametrize(
    "overrides",
    [
        {"verdict": "pass", "criteria_failed": ["padding"]},
        {"verdict": "fail", "criteria_failed": []},
        {"confidence": 1.5},
        {"unexpected": True},
        {"capture_path": "../outside.png"},
    ],
)
def test_malformed_receipt_is_invalid(
    tmp_path: Path, monkeypatch: MonkeyPatch, overrides: dict[str, Any]
) -> None:
    """Strict schema: inconsistent verdicts, bad ranges, extra keys, escapes."""
    _compile(tmp_path)
    _write_receipt(tmp_path, **overrides)

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 1
    assert payload["outcomes"][0]["status"] == "invalid"


@pytest.mark.parametrize(
    ("blocking", "status", "code"), [(True, "fail", 1), (False, "advisory_fail", 0)]
)
def test_failed_verdict_blocks_only_blocking_checks(
    tmp_path: Path, monkeypatch: MonkeyPatch, blocking: bool, status: str, code: int
) -> None:
    """AC-042: a failed verdict is advisory unless the check is blocking."""
    _compile(tmp_path, blocking=blocking)
    _write_receipt(tmp_path, verdict="fail", criteria_passed=[], criteria_failed=["padding"])

    exit_code, payload = _verify(tmp_path, monkeypatch)

    assert (exit_code, payload["outcomes"][0]["status"]) == (code, status)


def test_local_only_privacy_rejects_remote_evaluator(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """AC-043: `privacy.local_only` requires a local evaluator."""
    _compile(
        tmp_path, privacy="privacy:\n  llm_allowed: true\n  retention: local\n  local_only: true\n"
    )
    _write_receipt(tmp_path)

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 1
    assert "local evaluator" in payload["outcomes"][0]["message"]


def test_retention_none_allows_a_deleted_capture(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """With `retention: none` the capture may be deleted after evaluation."""
    _compile(tmp_path, privacy="privacy:\n  llm_allowed: true\n  retention: none\n")
    receipt = _write_receipt(tmp_path)
    (tmp_path / receipt["capture_path"]).unlink()

    code, payload = _verify(tmp_path, monkeypatch)

    assert code == 0
    assert payload["outcomes"][0]["status"] == "pass"
