# @spec FR-006: Fake corpora for resolution and consumer tests
#   .specs/features/085-localiser-ai-ressources-sans-chemin-en-dur/spec.md#fr-006

"""Fake ai-ressources corpora, projects and catalogs for feature 085 tests.

Every corpus is a temporary directory whose files carry a distinct marker, so a
consumer's observable output (hashes, routed files, rendered index) shows which
root it used. No test needs a real ai-ressources checkout.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

CONVENTION_SOURCES = ("general.md", "python.md", "javascript.md", "cli.md", "stack-commands.md")
"""The five code-convention files routed by ``init --from-code`` and the fixtures."""

ROUTED_LINE = "→ $AIRESOURCES/code-conventions/general.md, python.md"
"""Default source line of fixture indexes (directory prefix shared by both files)."""


def write_corpus(root: Path, marker: str) -> Path:
    """Write a fake corpus whose five code-convention files mention ``marker``.

    Args:
        root: Directory to create.
        marker: Text that makes this corpus's bytes distinct from any other corpus.

    Returns:
        The resolved corpus root.
    """
    for name in CONVENTION_SOURCES:
        source = root / "code-conventions" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"# {name}\n\n- {marker} convention source.\n", encoding="utf-8")
    return root.resolve()


def write_project(
    project: Path,
    *,
    manifest_path: str | None = None,
    index_path: str | None = None,
    manifest_text: str | None = None,
    routed_line: str = ROUTED_LINE,
) -> Path:
    """Write a project whose ``.conventions/`` files record the given paths.

    Args:
        project: Project directory to create.
        manifest_path: ``ai_resources_path`` value of the manifest, omitted when ``None``.
        index_path: ``$AIRESOURCES`` declaration of ``index.md``, omitted when ``None``.
        manifest_text: Raw manifest content overriding ``manifest_path``.
        routed_line: Source line written in ``index.md``.

    Returns:
        The resolved project root.
    """
    conventions = project / ".conventions"
    conventions.mkdir(parents=True, exist_ok=True)
    (project / ".specs").mkdir(exist_ok=True)
    if manifest_text is None:
        recorded = f"ai_resources_path: {manifest_path}\n" if manifest_path is not None else ""
        manifest_text = f"{recorded}project: demo\n"
    (conventions / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
    declaration = f"> `$AIRESOURCES` = `{index_path}`\n\n" if index_path is not None else ""
    (conventions / "index.md").write_text(
        f"# Conventions — demo\n\n{declaration}## code [code]\n{routed_line}\n",
        encoding="utf-8",
    )
    return project.resolve()


def file_sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 of a file's bytes."""
    return sha256(path.read_bytes()).hexdigest()


def write_catalog(project: Path, corpus: Path, name: str = "ast_fixture") -> Path:
    """Write one AST catalog inside ``project`` bound to ``corpus``'s ``general.md``.

    The rule uses the logical ``ai-ressources/`` source path, so loading it resolves
    the corpus through the shared resolution and checks the hash of that file.

    Args:
        project: Project that owns the catalog, fixtures and deterministic test.
        corpus: Corpus whose ``code-conventions/general.md`` bytes the hash pins.
        name: Catalog file stem, so one project can hold catalogs bound to several corpora.

    Returns:
        The catalog path.
    """
    fixtures = project / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    (fixtures / "pass.ts").write_text("const value = input as unknown;\n", encoding="utf-8")
    (fixtures / "fail.ts").write_text("const value = input as any;\n", encoding="utf-8")
    (project / "tests" / "test_fixture_contract.py").write_text(
        "def test_fixture_contract():\n    assert True\n", encoding="utf-8"
    )
    source_hash = file_sha256(corpus / "code-conventions" / "general.md")
    rule = {
        "id": "ts.no_as_any",
        "title": "No as any",
        "language": "typescript",
        "domain": "code",
        "decision_kind": "executable",
        "decidability": "ast",
        "precision": "high",
        "severity": "error",
        "source_path": "ai-ressources/code-conventions/general.md",
        "source_anchor": "#general",
        "source_hash": f"sha256:{source_hash}",
        "backend": "ast-grep",
        "detector": "ts.no_as_any",
        "patterns": [{"kind": "sg_yaml", "value": "rule: { pattern: '$A as any' }"}],
        "fixtures": {"pass": "tests/fixtures/pass.ts", "fail": "tests/fixtures/fail.ts"},
        "deterministic_test_evidence": [
            {
                "test": "tests/test_fixture_contract.py",
                "pass_fixture": "tests/fixtures/pass.ts",
                "fail_fixture": "tests/fixtures/fail.ts",
            }
        ],
    }
    catalog = project / "catalogs" / f"{name}.yaml"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML and keeps the fixture free of quoting pitfalls.
    catalog.write_text(json.dumps({"rules": [rule]}, indent=2), encoding="utf-8")
    return catalog


def provider_payload() -> str:
    """Return a minimal valid provider response for ``conventions compile``."""
    return json.dumps(
        {
            "rules": [
                {
                    "id": "code-docs",
                    "domain": "code-semantic",
                    "description": "Public functions document side effects.",
                    "check": "Flag public functions missing side-effect documentation.",
                    "source_excerpt": "convention source",
                    "blocking": True,
                    "applies_to": [],
                    "source_paths": ["$AIRESOURCES/code-conventions/general.md"],
                }
            ],
            "unenforceable": [],
            "waivers": [],
        }
    )


def write_rulebook(
    project: Path, corpus: Path, display_path: str = "code-conventions/general.md"
) -> None:
    """Write a compiled rulebook whose single source hash matches ``corpus``.

    Args:
        project: Project whose ``.specs/conventions-rulebook.yaml`` is written.
        corpus: Corpus whose file bytes the recorded hash pins.
        display_path: Path below ``$AIRESOURCES/`` recorded in the rulebook.
    """
    source = (corpus / display_path).resolve()
    digest = file_sha256(source) if source.is_file() else "0" * 64
    (project / ".specs").mkdir(parents=True, exist_ok=True)
    (project / ".specs" / "conventions-rulebook.yaml").write_text(
        "schema_version: 1\n"
        'compiled_at: "2026-10-13T00:00:00+00:00"\n'
        "sources:\n"
        f"  - path: $AIRESOURCES/{display_path}\n"
        f'    sha256: "{digest}"\n'
        "rules: []\nunenforceable: []\nwaivers: []\n",
        encoding="utf-8",
    )
