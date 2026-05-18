"""Tests for feature 026 — conventions propagation by stack."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from validator.cli import app
from validator.drivers import (
    CI_WORKFLOW_PATH,
    DEFAULT_THRESHOLD,
    DriverCapability,
    DriverManifest,
    GeneratedFile,
    generate_ci_workflow,
    generate_test_config,
    go_config,
    jvm_config,
    materialize_files,
    pick_primary_driver,
    python_config,
    rust_config,
    swift_config,
    typescript_config,
    update_conventions_testing_domain,
)
from validator.drivers.schemas import DetectRule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_driver(
    name: str,
    *,
    detect_files: list[str] | None = None,
    coverage_cmd: str | None = "echo cov",
    snapshots_cmd: str | None = None,
) -> DriverManifest:
    coverage = (
        DriverCapability(command=coverage_cmd) if coverage_cmd is not None else None
    )
    snapshots = (
        DriverCapability(command=snapshots_cmd) if snapshots_cmd is not None else None
    )
    return DriverManifest(
        name=name,
        detect=DetectRule(files=detect_files or []),
        coverage=coverage,
        snapshots=snapshots,
    )


# ---------------------------------------------------------------------------
# Per-stack generators (FR-002 / AC-001 / AC-004)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn, expected_path, threshold_in_text",
    [
        (python_config, Path("pyproject.toml"), "fail_under = 70"),
        (typescript_config, Path("vitest.config.ts"), "lines: 70"),
        (swift_config, Path(".swift-coverage.yml"), "threshold: 70"),
        (go_config, Path(".go-coverage.yml"), "threshold: 70"),
        (rust_config, Path("tarpaulin.toml"), "fail-under = 70"),
        (jvm_config, Path("jacoco-livespec.gradle"), "0.70"),
    ],
)
def test_stack_generators_emit_threshold(
    fn: Callable[[float], GeneratedFile], expected_path: Path, threshold_in_text: str
) -> None:
    file = fn(70.0)
    assert file.path == expected_path
    assert threshold_in_text in file.content


def test_python_config_uses_patch_section_mode() -> None:
    file = python_config(70.0)
    assert file.mode == "patch_section"
    assert file.section_marker == "python-coverage"


def test_typescript_config_uses_patch_section_mode() -> None:
    file = typescript_config(70.0)
    assert file.mode == "patch_section"
    assert file.section_marker == "typescript-coverage"


def test_threshold_propagates_to_python_config() -> None:
    assert "fail_under = 85" in python_config(85.0).content


def test_threshold_propagates_to_jvm_config_as_decimal() -> None:
    # JaCoCo expects a 0..1 decimal — 85% becomes 0.85.
    assert "0.85" in jvm_config(85.0).content


# ---------------------------------------------------------------------------
# CI workflow (FR-003 / AC-003)
# ---------------------------------------------------------------------------


def test_generate_ci_workflow_uses_livespec_spec_test() -> None:
    driver = _make_driver("python", coverage_cmd="pytest --cov")
    file = generate_ci_workflow(driver)
    assert file.path == Path(".github/workflows/test.yml")
    assert file.mode == "skip_if_exists"
    assert "livespec spec-test" in file.content
    # AC-003: must NOT bypass the orchestration with the raw runner.
    assert "pytest --cov" not in file.content


def test_generate_ci_workflow_includes_install_step_before_test_step() -> None:
    file = generate_ci_workflow(_make_driver("python"))
    install_idx = file.content.index("pip install livespec-validator")
    test_idx = file.content.index("run: livespec spec-test")
    assert install_idx < test_idx


def test_generate_ci_workflow_yaml_is_valid() -> None:
    # SC-002: generated CI workflow is syntactically valid YAML.
    file = generate_ci_workflow(_make_driver("typescript"))
    parsed = yaml.safe_load(file.content)
    assert parsed["name"] == "tests"
    assert "test" in parsed["jobs"]


@pytest.mark.parametrize(
    "stack, expected_setup",
    [
        ("typescript", "actions/setup-node"),
        ("go", "actions/setup-go"),
        ("rust", "dtolnay/rust-toolchain"),
        ("jvm", "actions/setup-java"),
        ("swift", "swift-actions/setup-swift"),
        ("python", "actions/setup-python"),
    ],
)
def test_ci_setup_step_matches_stack(stack: str, expected_setup: str) -> None:
    file = generate_ci_workflow(_make_driver(stack))
    assert expected_setup in file.content


# ---------------------------------------------------------------------------
# generate_test_config orchestration (FR-001)
# ---------------------------------------------------------------------------


def test_generate_test_config_python_returns_coverage_and_ci(tmp_path: Path) -> None:
    plan = generate_test_config(
        _make_driver("python", coverage_cmd="pytest --cov"),
        tmp_path,
    )
    paths = [f.path for f in plan.files]
    assert Path("pyproject.toml") in paths
    assert CI_WORKFLOW_PATH in paths
    assert plan.runner == "pytest"
    assert plan.threshold == DEFAULT_THRESHOLD


def test_generate_test_config_unknown_stack_returns_only_ci(tmp_path: Path) -> None:
    plan = generate_test_config(_make_driver("haskell"), tmp_path)
    assert [f.path for f in plan.files] == [CI_WORKFLOW_PATH]


def test_generate_test_config_rejects_invalid_threshold(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        generate_test_config(_make_driver("python"), tmp_path, threshold=0)
    with pytest.raises(ValueError):
        generate_test_config(_make_driver("python"), tmp_path, threshold=150)


def test_runner_inference_picks_vitest() -> None:
    plan = generate_test_config(
        _make_driver("typescript", coverage_cmd="npx vitest run --coverage"),
        Path.cwd(),
    )
    assert plan.runner == "vitest"


def test_snapshot_lib_inference_for_pytest() -> None:
    plan = generate_test_config(
        _make_driver(
            "python",
            coverage_cmd="pytest --cov",
            snapshots_cmd="pytest --snapshot-warn-unused",
        ),
        Path.cwd(),
    )
    assert plan.snapshot_lib == "syrupy"


# ---------------------------------------------------------------------------
# Conventions update (FR-004 / AC-005 / AC-006)
# ---------------------------------------------------------------------------


def test_update_conventions_creates_block_when_absent(tmp_path: Path) -> None:
    index = tmp_path / "index.md"
    index.write_text("# Conventions\n\n## existing-domain [foo]\n", encoding="utf-8")
    plan = generate_test_config(_make_driver("python"), tmp_path)
    written = update_conventions_testing_domain(plan, _make_driver("python"), index)
    assert written is True
    text = index.read_text(encoding="utf-8")
    assert "## testing [test, coverage, snapshot, ci]" in text
    assert "<!-- livespec:testing:begin -->" in text
    assert "<!-- livespec:testing:end -->" in text
    assert "## existing-domain [foo]" in text  # original preserved


def test_update_conventions_replaces_existing_block(tmp_path: Path) -> None:
    index = tmp_path / "index.md"
    initial = (
        "# Conventions\n\n"
        "<!-- livespec:testing:begin -->\n"
        "## testing [test, coverage, snapshot, ci]\n"
        "- Stack: python\n"
        "- Coverage threshold: 50%\n"
        "<!-- livespec:testing:end -->\n"
    )
    index.write_text(initial, encoding="utf-8")
    plan = generate_test_config(
        _make_driver("typescript", coverage_cmd="npx vitest run --coverage"),
        tmp_path,
        threshold=85,
    )
    update_conventions_testing_domain(plan, _make_driver("typescript"), index)
    text = index.read_text(encoding="utf-8")
    assert text.count("<!-- livespec:testing:begin -->") == 1
    assert "Stack: typescript" in text
    assert "Coverage threshold: 85%" in text
    assert "Coverage threshold: 50%" not in text


def test_update_conventions_returns_false_when_index_missing(tmp_path: Path) -> None:
    plan = generate_test_config(_make_driver("python"), tmp_path)
    written = update_conventions_testing_domain(
        plan, _make_driver("python"), tmp_path / "missing.md"
    )
    assert written is False


# ---------------------------------------------------------------------------
# materialize_files (AC-008 / EC-001 / EC-002 / EC-004)
# ---------------------------------------------------------------------------


def test_materialize_creates_ci_workflow_in_missing_directory(tmp_path: Path) -> None:
    # EC-004: missing .github/ is created.
    plan = generate_test_config(_make_driver("python"), tmp_path)
    outcomes = materialize_files(plan.files, tmp_path)
    workflow = tmp_path / CI_WORKFLOW_PATH
    assert workflow.is_file()
    assert any(o.action == "created" and o.path == CI_WORKFLOW_PATH for o in outcomes)


def test_materialize_skips_existing_ci_workflow(tmp_path: Path) -> None:
    # EC-002: existing CI workflow is not overwritten.
    target = tmp_path / CI_WORKFLOW_PATH
    target.parent.mkdir(parents=True)
    target.write_text("name: pre-existing\n", encoding="utf-8")
    plan = generate_test_config(_make_driver("python"), tmp_path)
    outcomes = materialize_files(plan.files, tmp_path)
    assert "pre-existing" in target.read_text(encoding="utf-8")
    skipped = [o for o in outcomes if o.path == CI_WORKFLOW_PATH]
    assert skipped[0].action == "skipped"


def test_materialize_force_overwrites_skip_if_exists(tmp_path: Path) -> None:
    target = tmp_path / CI_WORKFLOW_PATH
    target.parent.mkdir(parents=True)
    target.write_text("name: pre-existing\n", encoding="utf-8")
    plan = generate_test_config(_make_driver("python"), tmp_path)
    materialize_files(plan.files, tmp_path, force=True)
    assert "pre-existing" not in target.read_text(encoding="utf-8")


def test_materialize_patches_existing_pyproject(tmp_path: Path) -> None:
    # EC-001: existing config files are patched, not overwritten.
    pyproject = tmp_path / "pyproject.toml"
    original = '[project]\nname = "demo"\nversion = "0.1.0"\n'
    pyproject.write_text(original, encoding="utf-8")
    plan = generate_test_config(_make_driver("python"), tmp_path)
    outcomes = materialize_files(plan.files, tmp_path)
    text = pyproject.read_text(encoding="utf-8")
    assert "[project]" in text  # original preserved
    assert "fail_under = 70" in text  # patched block injected
    assert "# livespec:testing:python-coverage:begin" in text
    py_outcome = next(o for o in outcomes if o.path == Path("pyproject.toml"))
    assert py_outcome.action == "patched"


def test_materialize_patch_section_idempotent(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    plan = generate_test_config(_make_driver("python"), tmp_path)
    materialize_files(plan.files, tmp_path)
    materialize_files(plan.files, tmp_path)
    text = pyproject.read_text(encoding="utf-8")
    assert text.count("# livespec:testing:python-coverage:begin") == 1


# ---------------------------------------------------------------------------
# pick_primary_driver (EC-003)
# ---------------------------------------------------------------------------


def test_pick_primary_driver_returns_none_when_empty() -> None:
    assert pick_primary_driver([], Path.cwd()) is None


def test_pick_primary_driver_returns_only_match() -> None:
    only = _make_driver("python", detect_files=["pyproject.toml"])
    assert pick_primary_driver([only], Path.cwd()) is only


def test_pick_primary_driver_prefers_highest_match_count(tmp_path: Path) -> None:
    # TS project has package.json AND pyproject.toml — TS gets one match,
    # Python gets one match, but TS has more candidate patterns matched.
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    ts = _make_driver("typescript", detect_files=["package.json", "tsconfig.json"])
    py = _make_driver("python", detect_files=["pyproject.toml"])
    primary = pick_primary_driver([py, ts], tmp_path)
    assert primary is ts


# ---------------------------------------------------------------------------
# CLI integration (FR-005 / AC-002 / AC-007)
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _seed_project(tmp_path: Path, *, marker_files: list[str]) -> Path:
    for name in marker_files:
        (tmp_path / name).write_text("", encoding="utf-8")
    return tmp_path


def test_init_test_config_python_project(runner: CliRunner, tmp_path: Path) -> None:
    _seed_project(tmp_path, marker_files=["pyproject.toml"])
    result = runner.invoke(
        app,
        ["init", "test-config", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert (tmp_path / CI_WORKFLOW_PATH).is_file()
    # AC-007: summary lists generated files.
    assert "pyproject.toml" in result.output
    assert ".github/workflows/test.yml" in result.output


def test_init_test_config_typescript_project(runner: CliRunner, tmp_path: Path) -> None:
    _seed_project(tmp_path, marker_files=["package.json"])
    result = runner.invoke(
        app,
        ["init", "test-config", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "vitest.config.ts").is_file()
    text = (tmp_path / "vitest.config.ts").read_text(encoding="utf-8")
    assert "lines: 70" in text


def test_init_test_config_unsupported_stack_skips(
    runner: CliRunner, tmp_path: Path
) -> None:
    # AC-002: no driver match -> note + exit 0, no files written.
    result = runner.invoke(
        app,
        ["init", "test-config", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert "Test config not generated" in result.output
    assert not (tmp_path / CI_WORKFLOW_PATH).exists()


def test_init_test_config_existing_vitest_is_patched(
    runner: CliRunner, tmp_path: Path
) -> None:
    # SC-004: existing vitest.config.ts is patched (not overwritten).
    _seed_project(tmp_path, marker_files=["package.json"])
    vitest = tmp_path / "vitest.config.ts"
    vitest.write_text(
        "import { defineConfig } from 'vitest/config';\n"
        "export default defineConfig({ test: { globals: true } });\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["init", "test-config", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0
    text = vitest.read_text(encoding="utf-8")
    assert "defineConfig" in text  # original preserved
    assert "# livespec:testing:typescript-coverage:begin" in text


def test_init_test_config_threshold_flag_propagates(
    runner: CliRunner, tmp_path: Path
) -> None:
    _seed_project(tmp_path, marker_files=["pyproject.toml"])
    result = runner.invoke(
        app,
        [
            "init",
            "test-config",
            "--project-root",
            str(tmp_path),
            "--threshold",
            "90",
        ],
    )
    assert result.exit_code == 0
    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "fail_under = 90" in text


def test_init_test_config_updates_conventions_index(
    runner: CliRunner, tmp_path: Path
) -> None:
    _seed_project(tmp_path, marker_files=["pyproject.toml"])
    conv_dir = tmp_path / ".conventions"
    conv_dir.mkdir()
    (conv_dir / "index.md").write_text("# Conventions\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["init", "test-config", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0
    text = (conv_dir / "index.md").read_text(encoding="utf-8")
    assert "## testing [test, coverage, snapshot, ci]" in text


def test_init_test_config_refresh_only_skips_writes(
    runner: CliRunner, tmp_path: Path
) -> None:
    # AC-006: spec-refresh-conventions reuses this surface to refresh testing
    # domain without rewriting project files.
    _seed_project(tmp_path, marker_files=["pyproject.toml"])
    conv_dir = tmp_path / ".conventions"
    conv_dir.mkdir()
    (conv_dir / "index.md").write_text("# Conventions\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "init",
            "test-config",
            "--project-root",
            str(tmp_path),
            "--refresh-conventions-only",
        ],
    )
    assert result.exit_code == 0
    assert not (tmp_path / CI_WORKFLOW_PATH).exists()
    text = (conv_dir / "index.md").read_text(encoding="utf-8")
    assert "## testing [test, coverage, snapshot, ci]" in text


def test_generated_file_dataclass_immutable() -> None:
    f = GeneratedFile(path=Path("foo"), content="bar")
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.path = Path("bad")  # type: ignore[misc]
