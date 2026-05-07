"""Tests for the cross-language test driver architecture (feature 016)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.drivers import (
    CapabilityNotImplementedError,
    DriverCapability,
    DriverManifest,
    DriverRegistry,
    compute_patch_coverage,
    format_degradation_message,
    load_manifest,
    parse_diff,
    parse_lcov,
    run_capability,
    scaffold_custom_driver,
)
from validator.drivers import run_all_capabilities
from validator.drivers.scaffold import DriverFileExistsError
from validator.drivers.schemas import CAPABILITY_NAMES

# --- Schemas (FR-001 / AC-001 / AC-002) ---------------------------------------


def test_driver_manifest_all_capabilities_optional() -> None:
    manifest = DriverManifest(name="empty")
    assert manifest.implemented_capabilities() == []
    for cap in CAPABILITY_NAMES:
        assert manifest.get_capability(cap) is None


def test_driver_capability_requires_command_or_script() -> None:
    with pytest.raises(ValueError):
        DriverManifest.model_validate(
            {"name": "x", "coverage": {"report_path": "lcov.info"}}
        )


def test_driver_capability_unknown_field_rejected() -> None:
    with pytest.raises(ValueError):
        DriverManifest.model_validate(
            {"name": "x", "coverage": {"command": "true", "bogus": 1}}
        )


# --- Loader (FR-008 / AC-014) -------------------------------------------------


def test_load_manifest_valid(tmp_path: Path) -> None:
    p = tmp_path / "ruby.yaml"
    p.write_text("name: ruby\ndetect:\n  files: [Gemfile]\n")
    manifest = load_manifest(p)
    assert manifest is not None
    assert manifest.name == "ruby"
    assert manifest.detect.files == ["Gemfile"]
    assert manifest.source_path == p


def test_load_manifest_malformed_yaml_returns_none(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    p = tmp_path / "broken.yaml"
    p.write_text("name: : : invalid\n  - x\n[")
    with caplog.at_level(logging.WARNING):
        result = load_manifest(p)
    assert result is None
    assert any("malformed driver" in r.message.lower() for r in caplog.records)


def test_load_manifest_root_not_mapping(tmp_path: Path) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n")
    assert load_manifest(p) is None


def test_load_manifest_schema_violation_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    # capability with neither command nor script — invalid
    p.write_text("name: bad\ncoverage:\n  report_path: lcov.info\n")
    assert load_manifest(p) is None


# --- Registry (FR-002 / AC-003 / AC-004 / AC-005 / AC-006) --------------------


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_registry_discovers_builtin_only(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    _write(builtin / "python.yaml", "name: python\ndetect:\n  files: [pyproject.toml]\n")
    project = tmp_path / "proj"
    _write(project / "pyproject.toml", "[project]\nname='x'\n")
    reg = DriverRegistry(project, builtin_dir=builtin)
    matching = reg.discover()
    assert [m.name for m in matching] == ["python"]
    assert matching[0].is_custom is False


def test_registry_custom_overrides_builtin(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    _write(builtin / "python.yaml", "name: python\ndetect:\n  files: [pyproject.toml]\n")
    project = tmp_path / "proj"
    _write(project / "pyproject.toml", "")
    _write(
        project / ".specs/drivers/python.yaml",
        "name: python\ndetect:\n  files: [pyproject.toml]\ncoverage:\n  command: 'pytest'\n",
    )
    reg = DriverRegistry(project, builtin_dir=builtin)
    matching = reg.discover()
    assert len(matching) == 1
    assert matching[0].is_custom is True
    assert matching[0].coverage is not None


def test_registry_no_match_returns_empty(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    _write(builtin / "python.yaml", "name: python\ndetect:\n  files: [pyproject.toml]\n")
    project = tmp_path / "proj"
    _write(project / "mix.exs", "")
    reg = DriverRegistry(project, builtin_dir=builtin)
    assert reg.discover() == []


def test_registry_alphabetical_among_custom(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    _write(project / "Gemfile", "")
    _write(
        project / ".specs/drivers/zzz.yaml",
        "name: zzz\ndetect:\n  files: [Gemfile]\n",
    )
    _write(
        project / ".specs/drivers/aaa.yaml",
        "name: aaa\ndetect:\n  files: [Gemfile]\n",
    )
    reg = DriverRegistry(project, builtin_dir=tmp_path / "no-builtin")
    matching = reg.discover()
    assert [m.name for m in matching] == ["aaa", "zzz"]


def test_registry_skips_malformed_and_loads_rest(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    builtin = tmp_path / "builtin"
    _write(builtin / "broken.yaml", "[ invalid yaml")
    _write(builtin / "good.yaml", "name: good\ndetect:\n  files: [marker]\n")
    project = tmp_path / "proj"
    _write(project / "marker", "")
    reg = DriverRegistry(project, builtin_dir=builtin)
    with caplog.at_level(logging.WARNING):
        matching = reg.discover()
    assert [m.name for m in matching] == ["good"]


# --- Runner (FR-003 / AC-009 / AC-010 / AC-011) -------------------------------


def test_run_capability_command_success(tmp_path: Path) -> None:
    manifest = DriverManifest.model_validate(
        {"name": "x", "snapshots": {"command": "echo hello"}}
    )
    result = run_capability(manifest, "snapshots", project_root=tmp_path)
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_run_capability_command_failure(tmp_path: Path) -> None:
    manifest = DriverManifest.model_validate(
        {"name": "x", "snapshots": {"command": "false"}}
    )
    result = run_capability(manifest, "snapshots", project_root=tmp_path)
    assert result.exit_code != 0


def test_run_capability_script_runs(tmp_path: Path) -> None:
    script = tmp_path / "run.sh"
    script.write_text("#!/usr/bin/env bash\necho from-script\n")
    manifest = DriverManifest.model_validate(
        {"name": "x", "snapshots": {"script": "run.sh"}}
    )
    result = run_capability(manifest, "snapshots", project_root=tmp_path)
    assert result.exit_code == 0
    assert "from-script" in result.stdout


def test_run_capability_script_missing_raises(tmp_path: Path) -> None:
    manifest = DriverManifest.model_validate(
        {"name": "x", "snapshots": {"script": "no-such.sh"}}
    )
    with pytest.raises(FileNotFoundError):
        run_capability(manifest, "snapshots", project_root=tmp_path)


def test_run_capability_missing_capability_raises(tmp_path: Path) -> None:
    manifest = DriverManifest(name="x")
    with pytest.raises(CapabilityNotImplementedError):
        run_capability(manifest, "coverage", project_root=tmp_path)


def test_run_capability_missing_binary_returns_127(tmp_path: Path) -> None:
    manifest = DriverManifest.model_validate(
        {"name": "x", "snapshots": {"command": "this-binary-does-not-exist-xyz"}}
    )
    result = run_capability(manifest, "snapshots", project_root=tmp_path)
    assert result.exit_code == 127


def test_run_capability_coverage_validates_report_exists(tmp_path: Path) -> None:
    # Command succeeds but produces no report → must fail.
    manifest = DriverManifest.model_validate(
        {
            "name": "x",
            "coverage": {"command": "true", "report_path": "lcov.info"},
        }
    )
    result = run_capability(manifest, "coverage", project_root=tmp_path)
    assert result.exit_code != 0
    assert "Missing coverage report" in result.stderr


def test_run_capability_coverage_with_report_present(tmp_path: Path) -> None:
    (tmp_path / "lcov.info").write_text("TN:\nend_of_record\n")
    manifest = DriverManifest.model_validate(
        {
            "name": "x",
            "coverage": {"command": "true", "report_path": "lcov.info"},
        }
    )
    result = run_capability(manifest, "coverage", project_root=tmp_path)
    assert result.exit_code == 0


# --- Patch coverage (FR-005 / AC-012) -----------------------------------------


def test_parse_lcov_basic(tmp_path: Path) -> None:
    p = tmp_path / "lcov.info"
    p.write_text(
        "TN:\nSF:src/foo.py\nDA:1,1\nDA:2,0\nDA:3,5\nend_of_record\n"
    )
    parsed = parse_lcov(p)
    assert parsed["src/foo.py"] == {1: True, 2: False, 3: True}


def test_parse_diff_added_lines() -> None:
    diff = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,2 +1,3 @@\n"
        " line1\n"
        "+added\n"
        " line2\n"
    )
    diff_map = parse_diff(diff)
    assert diff_map["src/foo.py"] == {2}


def test_compute_patch_coverage_full_partial_missing(tmp_path: Path) -> None:
    lcov = tmp_path / "lcov.info"
    lcov.write_text(
        "SF:src/foo.py\n"
        "DA:1,1\nDA:2,1\nDA:3,0\nDA:4,1\n"
        "end_of_record\n"
    )
    diff = (
        "+++ b/src/foo.py\n"
        "@@ -0,0 +1,4 @@\n"
        "+a\n+b\n+c\n+d\n"
        "+++ b/src/new.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+x\n+y\n"
    )
    report = compute_patch_coverage(lcov, diff, project_root=tmp_path)
    assert report.files["src/foo.py"] == 0.75
    assert report.files["src/new.py"] == 0.0
    assert any("src/new.py" in w for w in report.warnings)


def test_compute_patch_coverage_empty_diff(tmp_path: Path) -> None:
    lcov = tmp_path / "lcov.info"
    lcov.write_text("SF:src/foo.py\nDA:1,1\nend_of_record\n")
    report = compute_patch_coverage(lcov, "", project_root=tmp_path)
    assert report.overall_ratio == 1.0
    assert report.files == {}


# --- Degradation (FR-004 / AC-007) --------------------------------------------


def test_format_degradation_message_elixir(tmp_path: Path) -> None:
    (tmp_path / "mix.exs").write_text("")
    msg = format_degradation_message(tmp_path)
    # AC-006: structured prefix and required sections.
    assert msg.startswith("⚠ Stack not supported")
    assert "elixir" in msg
    assert "No driver registered for this stack" in msg
    assert ".specs/drivers/elixir.yaml" in msg
    assert "livespec spec.driver --new elixir" in msg
    assert "mix.exs" in msg
    assert "spec-system.md" in msg


def test_format_degradation_message_no_signals(tmp_path: Path) -> None:
    # AC-008: fallback slug is "unknown" when no signals are detected.
    msg = format_degradation_message(tmp_path)
    assert "unknown" in msg
    assert "(none)" in msg
    assert msg.startswith("⚠ Stack not supported")


def test_format_degradation_message_ruby_inference(tmp_path: Path) -> None:
    # SC-004: stack inference for ruby via Gemfile.
    (tmp_path / "Gemfile").write_text("")
    msg = format_degradation_message(tmp_path)
    assert "ruby" in msg
    assert "livespec spec.driver --new ruby" in msg


def test_format_degradation_message_php_inference(tmp_path: Path) -> None:
    # SC-004: stack inference for php via composer.json.
    (tmp_path / "composer.json").write_text("{}")
    msg = format_degradation_message(tmp_path)
    assert "php" in msg
    assert "livespec spec.driver --new php" in msg


# --- Scaffold (FR-006 / AC-008) -----------------------------------------------


def test_scaffold_creates_yaml(tmp_path: Path) -> None:
    target = scaffold_custom_driver("elixir", project_root=tmp_path)
    assert target.exists()
    text = target.read_text()
    # AC-001: all 5 sections present (detect + 4 capabilities).
    for cap in CAPABILITY_NAMES:
        assert cap in text
    assert "detect" in text
    assert "spec-system.md" in text
    # AC-005: detect.files pre-filled for known stack.
    assert "mix.exs" in text


def test_scaffold_template_passes_schema_validation(tmp_path: Path) -> None:
    # AC-002: generated YAML passes schema validation.
    target = scaffold_custom_driver("elixir", project_root=tmp_path)
    manifest = load_manifest(target, is_custom=True)
    assert manifest is not None
    assert manifest.name == "elixir"
    assert "mix.exs" in manifest.detect.files


def test_scaffold_unknown_stack_still_validates(tmp_path: Path) -> None:
    # AC-002 + EC-003: unknown stacks emit valid YAML with empty detect.files.
    target = scaffold_custom_driver("haskell", project_root=tmp_path)
    manifest = load_manifest(target, is_custom=True)
    assert manifest is not None
    assert manifest.name == "haskell"
    assert manifest.detect.files == []


def test_scaffold_inline_documentation_present(tmp_path: Path) -> None:
    # Story 3 / SC-001: inline documentation for command vs script and report_path.
    target = scaffold_custom_driver("ruby", project_root=tmp_path)
    text = target.read_text()
    assert "command:" in text
    assert "script:" in text
    assert "report_path" in text
    assert "lcov.info" in text


def test_scaffold_refuses_overwrite(tmp_path: Path) -> None:
    scaffold_custom_driver("ruby", project_root=tmp_path)
    with pytest.raises(DriverFileExistsError):
        scaffold_custom_driver("ruby", project_root=tmp_path)


def test_scaffold_force_overwrites(tmp_path: Path) -> None:
    target = scaffold_custom_driver("ruby", project_root=tmp_path)
    target.write_text("modified\n")
    scaffold_custom_driver("ruby", project_root=tmp_path, force=True)
    assert "name: ruby" in target.read_text()


def test_scaffold_rejects_invalid_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        scaffold_custom_driver("../etc", project_root=tmp_path)


def test_scaffold_sanitizes_hyphenated_name(tmp_path: Path) -> None:
    # EC-001: hyphenated stack names become valid filenames.
    target = scaffold_custom_driver("ruby-on-rails", project_root=tmp_path)
    assert target.name == "ruby-on-rails.yaml"
    assert target.exists()


def test_scaffold_creates_specs_drivers_dir(tmp_path: Path) -> None:
    # EC-002: .specs/drivers/ created automatically.
    assert not (tmp_path / ".specs" / "drivers").exists()
    target = scaffold_custom_driver("elixir", project_root=tmp_path)
    assert target.parent.is_dir()
    assert target.parent.name == "drivers"


# --- CLI integration (FR-006 / AC-008) ----------------------------------------


def test_cli_spec_driver_new_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["spec.driver", "--new", "rust"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".specs/drivers/rust.yaml").exists()
    # AC-010: next-steps message printed.
    assert "Next steps" in result.output
    assert "spec-system.md" in result.output


def test_cli_spec_driver_new_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["spec.driver", "--new", "rust"])
    result = runner.invoke(app, ["spec.driver", "--new", "rust"])
    assert result.exit_code == 1


def test_cli_spec_driver_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["spec.driver", "--new", "rust"])
    result = runner.invoke(app, ["spec.driver", "--new", "rust", "--force"])
    assert result.exit_code == 0


def test_run_all_capabilities_partial_driver(tmp_path: Path) -> None:
    # AC-009: partial driver runs implemented capabilities and reports None for the rest.
    manifest = DriverManifest(
        name="elixir",
        snapshots=DriverCapability(command="true"),
    )
    results = run_all_capabilities(manifest, project_root=tmp_path)
    assert set(results.keys()) == set(CAPABILITY_NAMES)
    assert results["snapshots"] is not None
    assert results["snapshots"].exit_code == 0
    assert results["coverage"] is None
    assert results["properties"] is None
    assert results["mutation"] is None


def test_cli_spec_driver_legacy_alias_still_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Backward compat: pre-023 callers used `spec-driver`.
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["spec-driver", "--new", "rust"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".specs/drivers/rust.yaml").exists()


# --- Built-in driver smoke (SC-006 / AC-003) ----------------------------------


def test_builtin_drivers_load_via_default_dir() -> None:
    """All 5 built-in slots load successfully from the shipped livespec/drivers/."""
    repo_root = Path(__file__).resolve().parent.parent
    builtin = repo_root / "livespec" / "drivers"
    assert builtin.is_dir()
    files = sorted(builtin.glob("*.yaml"))
    names = {f.stem for f in files}
    assert {"python", "typescript", "swift", "go", "jvm"} <= names
    for f in files:
        m = load_manifest(f)
        assert m is not None, f"failed to load {f}"


def test_registry_default_builtin_dir_resolves(tmp_path: Path) -> None:
    """Smoke: DriverRegistry without builtin_dir override hits the shipped dir."""
    (tmp_path / "pyproject.toml").write_text("")
    reg = DriverRegistry(tmp_path)
    matching = reg.discover()
    assert any(m.name == "python" for m in matching)
