# @spec FR-006: Fake corpora for resolution and consumer tests
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-006

"""Feature 085 tests need no real ai-ressources checkout (AC-011).

The resolution, consumer and failure modules are re-run in a child pytest whose
environment has no ``AIRESOURCES`` and an empty ``HOME``: they must still pass, so every
corpus they observe is one they built themselves. The real-corpus AST modules keep
reading the corpus that CI provides and never import the feature's fake-corpus helpers.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FEATURE_MODULES = (
    "tests/test_ai_resources.py",
    "tests/test_ai_resources_consumers.py",
    "tests/test_ai_resources_failures.py",
)
REAL_CORPUS_MODULES = (
    "tests/test_conventions_ast_catalog.py",
    "tests/test_conventions_ast_engine.py",
    "tests/test_conventions_ast_multilang.py",
    "tests/test_conventions_gate_signal.py",
    "tests/test_conventions_verify.py",
    "tests/test_conventions_verify_scope.py",
    "tests/test_conventions_baseline.py",
    "tests/test_conventions_diffguard.py",
)
FAKE_CORPUS_HELPERS = ("ai_resources_fixture", "without_airesources")


def test_feature_tests_pass_without_any_real_corpus(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {key: value for key, value in os.environ.items() if key != "AIRESOURCES"}
    env["HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *FEATURE_MODULES],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


def test_real_corpus_ast_tests_do_not_use_fake_corpora() -> None:
    offenders = [
        f"{module}: {helper}"
        for module in REAL_CORPUS_MODULES
        for helper in FAKE_CORPUS_HELPERS
        if helper in (REPO / module).read_text(encoding="utf-8")
    ]

    assert offenders == []
