# @spec FR-004: Consumers share the resolved root
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-004

"""Consumer matrix of the shared ai-ressources resolution (feature 085, AC-005, AC-007, AC-008).

Seven consumers x three situations (SC-003). Each situation builds two fake corpora with
distinct bytes, ``corpus-env`` and ``corpus-recorded``; only the expected corpus holds
``code-conventions/expected-only.md``, which the project's index routes. Each cell observes
the root a consumer actually used, through hashes, the reported root, routed files or the
rendered index, never through the resolution function itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.ai_resources_fixture import (
    ROUTED_LINE,
    file_sha256,
    provider_payload,
    write_catalog,
    write_corpus,
    write_project,
    write_rulebook,
)
from tests.test_init_profile import hybrid
from validator import init_from_code
from validator.ai_resources import INDEX_DECLARATION_RE
from validator.coherence.graph_builder import SpecGraph
from validator.coherence.rules.r7_conventions_gates import R7_3_ConventionsRulebookSourcesStale
from validator.conventions_ast.catalog import AstCatalogError, load_ast_catalog
from validator.conventions_ast.corpus import build_corpus_manifest
from validator.conventions_ast.source_decisions import build_rule_decision_manifest
from validator.conventions_rules import compile_conventions_rulebook, load_conventions_rules
from validator.init_profile import detect_profile
from validator.init_recovery import conventions_are_valid

ROUTES = f"{ROUTED_LINE}\n→ $AIRESOURCES/code-conventions/expected-only.md"


@dataclass(frozen=True)
class Scenario:
    """One project with its expected and unexpected corpora."""

    project: Path
    expected: Path
    other: Path


def _situation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, situation: str) -> Scenario:
    env_corpus = write_corpus(tmp_path / "corpus-env", "env")
    recorded = write_corpus(tmp_path / "corpus-recorded", "recorded")
    monkeypatch.delenv("AIRESOURCES", raising=False)
    if situation in {"env", "both"}:
        monkeypatch.setenv("AIRESOURCES", str(env_corpus))
    recorded_text = None if situation == "env" else str(recorded)
    project = write_project(
        tmp_path / "project",
        manifest_path=recorded_text,
        index_path=recorded_text,
        routed_line=ROUTES,
    )
    hybrid(project)
    expected, other = (recorded, env_corpus) if situation == "recorded" else (env_corpus, recorded)
    (expected / "code-conventions" / "expected-only.md").write_text("# only\n", encoding="utf-8")
    return Scenario(project=project, expected=expected, other=other)


def _matching(scenario: Scenario, predicate: Callable[[Path], bool]) -> Path | None:
    """Return the single corpus satisfying ``predicate``, or ``None`` when zero or both do."""
    matches = [corpus for corpus in (scenario.expected, scenario.other) if predicate(corpus)]
    return matches[0] if len(matches) == 1 else None


def _general_sha(corpus: Path) -> str:
    return file_sha256(corpus / "code-conventions" / "general.md")


def _catalog(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    def loads(corpus: Path) -> bool:
        catalog = write_catalog(scenario.project, corpus, name=corpus.name)
        try:
            return bool(load_ast_catalog(catalog, project_root=scenario.project).rules)
        except AstCatalogError:
            # A catalog bound to the corpus the loader did not use fails its hash check.
            return False

    return _matching(scenario, loads)


def _corpus(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    return Path(build_corpus_manifest(scenario.project)["ai_resources_root"])


def _decisions(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    manifest = build_rule_decision_manifest(scenario.project)
    hashes = {item["source_path"]: item["source_hash"] for item in manifest["decisions"]}
    observed = hashes["ai-ressources/code-conventions/general.md"]
    return _matching(scenario, lambda corpus: observed == f"sha256:{_general_sha(corpus)}")


def _compile(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    monkeypatch.setattr(
        "validator.conventions_rules.llm_provider.call_llm",
        lambda *_args, **_kwargs: provider_payload(),
    )
    rulebook = load_conventions_rules(compile_conventions_rulebook(scenario.project, force=True))
    observed = {source.path: source.sha256 for source in rulebook.sources}
    general = observed["$AIRESOURCES/code-conventions/general.md"]
    return _matching(scenario, lambda corpus: general == _general_sha(corpus))


def _r7_3(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    def fresh(corpus: Path) -> bool:
        write_rulebook(scenario.project, corpus)
        rule = R7_3_ConventionsRulebookSourcesStale()
        return rule.check(SpecGraph(), scenario.project / ".specs") == []

    return _matching(scenario, fresh)


def _validity(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    # The index routes expected-only.md, which exists only in the expected corpus.
    if not conventions_are_valid(scenario.project):
        return None
    return _matching(
        scenario, lambda corpus: (corpus / "code-conventions/expected-only.md").is_file()
    )


def _init(scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> Path | None:
    """Observe ``_prepare_documents`` on the same project with invalid conventions.

    The index is rewritten to route a source missing from every corpus, so
    ``conventions_are_valid`` is false and init renders conventions; in the
    recorded-only situation the recorded corpus still exists, so the rendered
    index names the corpus init resolved (finding 3 of the plan review).
    """
    index = scenario.project / ".conventions" / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8").replace(ROUTES, "→ $AIRESOURCES/missing/source.md"),
        encoding="utf-8",
    )
    profile = detect_profile(scenario.project)
    documents = init_from_code._prepare_documents(profile, scenario.project)
    match = INDEX_DECLARATION_RE.search(documents[".conventions/index.md"])
    rendered_manifest = documents[".conventions/manifest.yaml"]
    if match is None or f"ai_resources_path: {match.group(1)}" not in rendered_manifest:
        return None
    return Path(match.group(1))


CONSUMERS: dict[str, Callable[[Scenario, pytest.MonkeyPatch], Path | None]] = {
    "ast-catalog": _catalog,
    "corpus-manifest": _corpus,
    "rule-decisions": _decisions,
    "conventions-compile": _compile,
    "r7.3": _r7_3,
    "conventions-validity": _validity,
    "init-from-code": _init,
}


@pytest.mark.parametrize("situation", ["env", "recorded", "both"])
@pytest.mark.parametrize("consumer", list(CONSUMERS))
def test_consumer_uses_the_shared_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str, situation: str
) -> None:
    scenario = _situation(tmp_path, monkeypatch, situation)

    observed = CONSUMERS[consumer](scenario, monkeypatch)

    assert observed == scenario.expected


def test_other_machine_recorded_path_is_valid_with_local_env_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = write_corpus(tmp_path / "local-clone", "local")
    project = write_project(
        tmp_path / "project",
        manifest_path="/Users/someone-else/clones/ai-ressources",
        index_path="/home/another/ai-ressources",
    )
    monkeypatch.delenv("AIRESOURCES", raising=False)
    assert not conventions_are_valid(project)

    monkeypatch.setenv("AIRESOURCES", str(local))

    assert conventions_are_valid(project)


def test_compile_needs_no_index_declaration_with_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = write_corpus(tmp_path / "corpus-env", "env")
    project = write_project(tmp_path / "project")
    monkeypatch.setenv("AIRESOURCES", str(corpus))
    monkeypatch.setattr(
        "validator.conventions_rules.llm_provider.call_llm",
        lambda *_args, **_kwargs: provider_payload(),
    )

    rulebook = load_conventions_rules(compile_conventions_rulebook(project, force=True))

    assert {source.path for source in rulebook.sources} == {
        "$AIRESOURCES/code-conventions/general.md",
        "$AIRESOURCES/code-conventions/python.md",
    }


def test_compile_still_rejects_escaping_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = write_corpus(tmp_path / "corpus-env", "env")
    (tmp_path / "outside.md").write_text("# outside\n", encoding="utf-8")
    project = write_project(tmp_path / "project", routed_line="→ $AIRESOURCES/../outside.md")
    monkeypatch.setenv("AIRESOURCES", str(corpus))

    with pytest.raises(ValueError) as caught:
        compile_conventions_rulebook(project, force=True)

    assert (
        str(caught.value) == "conventions source escapes $AIRESOURCES: $AIRESOURCES/../outside.md"
    )


def test_r7_3_still_rejects_escaping_display_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = write_corpus(tmp_path / "corpus-env", "env")
    (tmp_path / "outside.md").write_text("# outside\n", encoding="utf-8")
    project = write_project(tmp_path / "project")
    monkeypatch.setenv("AIRESOURCES", str(corpus))
    write_rulebook(project, corpus, display_path="../outside.md")

    violations = R7_3_ConventionsRulebookSourcesStale().check(SpecGraph(), project / ".specs")

    assert [violation.message for violation in violations] == [
        "conventions rulebook source stale: $AIRESOURCES/../outside.md"
    ]
