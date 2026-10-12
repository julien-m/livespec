"""Observed manifests preserve independent families and fail on contradictions."""

import json
from pathlib import Path

import pytest

from validator.init_profile import InitError, detect_profile


def hybrid(project: Path) -> None:
    """Write a hybrid fixture with corroborated Bun evidence."""
    (project / "src-tauri").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps(
            {
                "name": "handy-app",
                "dependencies": {"react": "^19"},
                "devDependencies": {"vite": "^6", "typescript": "~5", "vitest": "^3"},
                "scripts": {"test": "vitest run"},
            }
        )
    )
    (project / "bun.lock").write_text("{}")
    (project / "src-tauri/Cargo.toml").write_text(
        '[package]\nname="handy"\nversion="0.1"\n[dependencies]\ntauri={version="2",features=[]}\n'
    )
    (project / "src-tauri/tauri.conf.json").write_text(
        json.dumps(
            {
                "productName": "Handy",
                "build": {"beforeDevCommand": "bun run dev", "beforeBuildCommand": "bun run build"},
            }
        )
    )


def test_ac001_hybrid_families_and_product_name(tmp_path: Path) -> None:
    hybrid(tmp_path)
    profile = detect_profile(tmp_path)
    assert profile.product_name == "Handy"
    assert "handy-app" in profile.technical_names
    assert profile.package_manager == "bun"
    assert {"Tauri", "Rust", "React", "Vite", "TypeScript"} <= {fact.name for fact in profile.facts}
    assert next(fact.version for fact in profile.facts if fact.name == "Tauri") == "2"
    assert profile.tools == ("bun", "cargo")
    assert profile.testing_tools.count("vitest") == 1
    assert {source.path for source in profile.sources} >= {
        "package.json",
        "src-tauri/Cargo.toml",
        "bun.lock",
    }


@pytest.mark.parametrize(
    ("path", "content", "family", "tool"),
    [
        ("pyproject.toml", '[project]\nname="cli"\nversion="1"\n', "Python", "python3"),
        ("Cargo.toml", '[package]\nname="cli"\nversion="1"\n', "Rust", "cargo"),
    ],
)
def test_ac002_standalone_families(
    tmp_path: Path, path: str, content: str, family: str, tool: str
) -> None:
    (tmp_path / path).write_text(content)
    profile = detect_profile(tmp_path)
    assert {fact.name for fact in profile.facts} == {family}
    assert profile.tools == (tool,)
    assert profile.package_manager == "Unknown"


def test_ac002_missing_manager_stays_unknown(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"plain","dependencies":{"react":"19"}}')
    profile = detect_profile(tmp_path)
    assert profile.package_manager == "Unknown"
    assert "npm" not in profile.tools


@pytest.mark.parametrize("change", ["conflict", "malformed"])
def test_ac003_bad_evidence_fails_contextually(tmp_path: Path, change: str) -> None:
    hybrid(tmp_path)
    if change == "conflict":
        (tmp_path / "package-lock.json").write_text("{}")
    else:
        (tmp_path / "package.json").write_text("{")
    with pytest.raises(InitError, match=r"package"):
        detect_profile(tmp_path)


@pytest.mark.parametrize("manifest", ["go.mod", "Gemfile", "pom.xml"])
def test_ac007_unsupported_manifest_beside_supported_is_recorded(
    tmp_path: Path, manifest: str
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="cli"\nversion="1"\n')
    (tmp_path / manifest).write_text("unparsed\n")
    profile = detect_profile(tmp_path)
    assert {fact.name for fact in profile.facts} == {"Python"}
    assert profile.unsupported_manifests == (manifest,)
    assert profile.tools == ("python3",)


def test_ac007_unsupported_tauri_format_is_recorded_not_fatal(tmp_path: Path) -> None:
    hybrid(tmp_path)
    (tmp_path / "src-tauri/tauri.conf.json5").write_text("{}")
    profile = detect_profile(tmp_path)
    assert profile.unsupported_manifests == ("src-tauri/tauri.conf.json5",)
    assert {"Tauri", "Rust", "React"} <= {fact.name for fact in profile.facts}


def test_ac007_only_unsupported_manifests_fail_naming_them(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example\n")
    (tmp_path / "Gemfile").write_text("source 'x'\n")
    with pytest.raises(InitError, match=r"No supported.*Gemfile, go\.mod"):
        detect_profile(tmp_path)


def test_ac007_missing_manager_evidence_warns_without_failing(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"plain"}')
    profile = detect_profile(tmp_path)
    assert profile.package_manager == "Unknown"
    assert len(profile.warnings) == 1 and "package manager" in profile.warnings[0]
    assert "npm" not in profile.tools


def test_ac007_non_javascript_profile_has_no_manager_warning(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text('[package]\nname="cli"\nversion="1"\n')
    profile = detect_profile(tmp_path)
    assert profile.warnings == () and profile.unsupported_manifests == ()
