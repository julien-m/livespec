"""Bind the shipped AST catalogs to a fixture corpus, without vendoring private sources.

The shipped catalogs pin ``source_hash`` to the private normative corpus. Manifest tests
that classify a synthetic corpus copy those catalogs and rebind each rule's hash to the
fixture bytes it names; every other rule field is unchanged and the loader still verifies
``source_path`` and ``source_hash``. Binding to the real corpus stays covered by the
catalog tests that run against the pinned corpus.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from validator.conventions_ast import source_decisions
from validator.conventions_ast.corpus import ai_resources_root
from validator.conventions_gates import DEFAULT_AST_CATALOGS

REPO = Path(__file__).resolve().parents[1]


def bind_default_catalogs_to_corpus(
    project: Path, catalogs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, ...]:
    """Activate copies of the default catalogs whose hashes match the project's corpus.

    Args:
        project: Project whose ``.conventions/manifest.yaml`` names the fixture corpus.
        catalogs_dir: Directory outside ``project`` (rule fixtures resolve from the repo).
        monkeypatch: Scopes the AIRESOURCES removal and the catalog selection to the test.

    Returns:
        The absolute catalog paths now used by the rule decision manifest.
    """
    # A caller's AIRESOURCES would otherwise redirect source checks to a private corpus.
    monkeypatch.delenv("AIRESOURCES", raising=False)
    corpus = ai_resources_root(project)
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for relative in DEFAULT_AST_CATALOGS:
        data = cast(dict[str, Any], yaml.safe_load((REPO / relative).read_text(encoding="utf-8")))
        for rule in cast(list[dict[str, Any]], data["rules"]):
            source = corpus / str(rule["source_path"]).removeprefix("ai-ressources/")
            rule["source_hash"] = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        target = catalogs_dir / Path(relative).name
        target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        paths.append(str(target))
    monkeypatch.setattr(source_decisions, "DEFAULT_AST_CATALOGS", tuple(paths))
    return tuple(paths)
