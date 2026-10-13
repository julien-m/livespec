# @spec FR-001: Shared resolution order, FR-002: Explicit error, FR-003: No fallback
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-001

"""Unit tests of the shared ai-ressources resolution (feature 085, AC-001 to AC-004).

Every test runs with ``HOME`` set to an empty temporary directory and ``AIRESOURCES``
removed (autouse fixture), then sets the variable explicitly with ``monkeypatch`` when
a case needs it (SC-002). Corpora are fake temporary directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ai_resources_fixture import write_catalog, write_corpus, write_project
from tests.test_init_profile import hybrid
from validator import ai_resources, init_from_code
from validator.ai_resources import resolve_ai_resources_root
from validator.conventions_ast.catalog import AstCatalogError, load_ast_catalog
from validator.conventions_ast.corpus import build_corpus_manifest
from validator.exceptions import AIRESOURCES_FIX_SENTENCE, AiResourcesResolutionError
from validator.init_profile import InitError, detect_profile

FIX = (
    "Run ./setup.sh from your ai-ressources clone, "
    "or export AIRESOURCES=<absolute path of the clone>."
)


@pytest.fixture(autouse=True)
def empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``HOME`` and ``Path.home`` to an empty directory and remove ``AIRESOURCES``."""
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("AIRESOURCES", raising=False)
    return home


def test_fix_sentence_is_exact() -> None:
    assert AIRESOURCES_FIX_SENTENCE == FIX


def test_env_wins_over_recorded_existing_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_corpus = write_corpus(tmp_path / "corpus-env", "env")
    recorded = write_corpus(tmp_path / "corpus-recorded", "recorded")
    project = write_project(
        tmp_path / "project", manifest_path=str(recorded), index_path=str(recorded)
    )
    monkeypatch.setenv("AIRESOURCES", str(env_corpus))

    resolved = resolve_ai_resources_root(project)

    assert (resolved.path, resolved.source) == (env_corpus, "env")


def test_env_is_used_without_existence_check_or_reading_conventions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_read(project_root: Path) -> list[tuple[str, str]]:
        raise AssertionError(f"recorded paths read for {project_root}")

    monkeypatch.setattr(ai_resources, "_recorded_values", fail_if_read)
    missing = tmp_path / "missing-env-corpus"
    monkeypatch.setenv("AIRESOURCES", f"  {missing}  ")

    resolved = resolve_ai_resources_root(tmp_path / "project")

    assert (resolved.path, resolved.source) == (missing.resolve(), "env")
    assert not resolved.path.exists()


def test_relative_and_tilde_env_values_become_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_home: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIRESOURCES", "relative-corpus")
    assert resolve_ai_resources_root(None).path == (tmp_path / "relative-corpus").resolve()
    monkeypatch.setenv("AIRESOURCES", "~/corpus")
    assert resolve_ai_resources_root(None).path == (empty_home / "corpus").resolve()


def test_explicit_environ_mapping_is_honoured(tmp_path: Path) -> None:
    corpus = write_corpus(tmp_path / "corpus-env", "env")

    resolved = resolve_ai_resources_root(None, environ={"AIRESOURCES": str(corpus)})

    assert resolved.path == corpus


@pytest.mark.parametrize("value", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
def test_blank_env_falls_back_to_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    recorded = write_corpus(tmp_path / "corpus-recorded", "recorded")
    project = write_project(tmp_path / "project", manifest_path=str(recorded))
    monkeypatch.setenv("AIRESOURCES", value)

    resolved = resolve_ai_resources_root(project)

    assert (resolved.path, resolved.source) == (recorded, "manifest")


def test_index_declaration_used_when_manifest_path_missing(tmp_path: Path) -> None:
    index_corpus = write_corpus(tmp_path / "corpus-index", "index")
    project = write_project(
        tmp_path / "project",
        manifest_path=str(tmp_path / "missing-corpus"),
        index_path=str(index_corpus),
    )

    resolved = resolve_ai_resources_root(project)

    assert (resolved.path, resolved.source) == (index_corpus, "index")


def test_manifest_wins_when_manifest_and_index_disagree(tmp_path: Path) -> None:
    manifest_corpus = write_corpus(tmp_path / "corpus-manifest", "manifest")
    index_corpus = write_corpus(tmp_path / "corpus-index", "index")
    project = write_project(
        tmp_path / "project", manifest_path=str(manifest_corpus), index_path=str(index_corpus)
    )

    assert resolve_ai_resources_root(project).source == "manifest"


def test_relative_and_tilde_recorded_paths(tmp_path: Path, empty_home: Path) -> None:
    project = tmp_path / "project"
    relative = write_corpus(project / "vendor" / "corpus", "relative")
    write_project(project, manifest_path="vendor/corpus")
    assert resolve_ai_resources_root(project).path == relative

    home_corpus = write_corpus(empty_home / "clones" / "ai", "home")
    write_project(project, manifest_path="~/clones/ai")
    assert resolve_ai_resources_root(project).path == home_corpus


@pytest.mark.parametrize(
    "manifest_text",
    [
        "ai_resources_path: [unclosed\n",
        "- ai_resources_path\n",
        "project: demo\n",
        "ai_resources_path: 42\n",
        "ai_resources_path: '   '\n",
    ],
    ids=["malformed", "non-mapping", "missing-key", "non-string", "blank"],
)
def test_unusable_manifest_falls_back_to_index(tmp_path: Path, manifest_text: str) -> None:
    index_corpus = write_corpus(tmp_path / "corpus-index", "index")
    project = write_project(
        tmp_path / "project", manifest_text=manifest_text, index_path=str(index_corpus)
    )

    resolved = resolve_ai_resources_root(project)

    assert (resolved.path, resolved.source) == (index_corpus, "index")


def test_nonexistent_recorded_paths_raise_explicit_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing-corpus"
    project = write_project(tmp_path / "project", manifest_path=str(missing))

    with pytest.raises(AiResourcesResolutionError) as caught:
        resolve_ai_resources_root(project)

    message = str(caught.value)
    assert message == (
        f"ai-ressources root not resolved for project {project}: AIRESOURCES is not set; "
        f"rejected recorded paths: {missing.resolve()} (from .conventions/manifest.yaml). {FIX}"
    )
    assert caught.value.rejected == ((missing.resolve(), ".conventions/manifest.yaml"),)
    assert isinstance(caught.value, ValueError)


def test_every_rejected_path_is_listed_in_order(tmp_path: Path) -> None:
    missing = tmp_path / "missing-corpus"
    a_file = tmp_path / "not-a-directory"
    a_file.write_text("file", encoding="utf-8")
    project = write_project(
        tmp_path / "project", manifest_path=str(missing), index_path=str(a_file)
    )

    with pytest.raises(AiResourcesResolutionError) as caught:
        resolve_ai_resources_root(project)

    assert (
        f"rejected recorded paths: {missing.resolve()} (from .conventions/manifest.yaml); "
        f"{a_file.resolve()} (from .conventions/index.md). {FIX}"
    ) in str(caught.value)


def test_nothing_recorded_raises_explicit_error(tmp_path: Path) -> None:
    project = tmp_path / "bare-project"
    project.mkdir()

    with pytest.raises(AiResourcesResolutionError) as caught:
        resolve_ai_resources_root(project)

    assert str(caught.value) == (
        f"ai-ressources root not resolved for project {project.resolve()}: "
        "AIRESOURCES is not set; no path recorded in .conventions/manifest.yaml or "
        f".conventions/index.md. {FIX}"
    )


def test_without_project_root_only_environment_applies(tmp_path: Path) -> None:
    with pytest.raises(AiResourcesResolutionError) as caught:
        resolve_ai_resources_root(None)

    assert str(caught.value) == f"ai-ressources root not resolved: AIRESOURCES is not set. {FIX}"
    assert caught.value.project_root is None


def test_no_home_or_livespec_sibling_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_home: Path
) -> None:
    """D-06 / AC-004: corpora at ``~/projects`` and next to the checkout are never consulted."""
    write_corpus(empty_home / "projects" / "ai-ressources", "home")
    checkout = tmp_path / "checkout"
    write_corpus(checkout / "ai-ressources", "sibling")
    monkeypatch.setattr(init_from_code, "LIVESPEC_ROOT", checkout / "livespec")
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    catalog_corpus = write_corpus(tmp_path / "catalog-corpus", "catalog")
    catalog = write_catalog(project, catalog_corpus)

    with pytest.raises(AiResourcesResolutionError):
        resolve_ai_resources_root(project)
    manifest = build_corpus_manifest(project)
    assert manifest["ai_resources_root"] == ""
    assert FIX in manifest.get("resolution_error", "")
    with pytest.raises(AstCatalogError, match="ai-ressources root not resolved"):
        load_ast_catalog(catalog, project_root=project)
    with pytest.raises(InitError, match="ai-ressources root not resolved"):
        init_from_code._prepare_documents(detect_profile(project), project)
