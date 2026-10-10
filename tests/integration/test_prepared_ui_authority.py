# @spec(AC-011)
# .specs/features/078-requirement-evidence-integrity/spec.md#ac-011
"""Opt-in real C51 witness uses its prepared source without inventing a LiveSpec pipeline."""

import json
import os
from pathlib import Path

import pytest

from tests.integration.helpers.witness_evaluator import evaluate_candidate, freeze_oracle


@pytest.mark.level_3a
def test_prepared_ui_c51_authority_is_independent_of_livespec_feature_pipeline():
    receipt_name = os.environ.get("LIVESPEC_PREPARED_UI_RECEIPT")
    if not receipt_name:
        pytest.skip("Requires a real current prepared UI capture receipt")
    receipt = Path(receipt_name)
    payload = json.loads(receipt.read_text())
    candidate = Path(payload["candidate"])
    assert not (candidate / ".specs/features/001-form/pipeline.md").exists()
    result = evaluate_candidate(
        freeze_oracle("ui-form"),
        candidate,
        build_manifest=Path(payload["manifest"]["path"]),
        capture_receipt=receipt,
    )
    assert result.status == "pass", result.reason
    assert result.assertions == 5 and result.authority_capture is not None
