"""Regression tests for selecting a fresh ``spec-init`` goal root."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.goal_bootstrap_support import archive_pair as _archive_pair
from tests.goal_bootstrap_support import mark_all_tasks_complete as _mark_all_tasks_complete
from tests.goal_bootstrap_support import prove_relative_artifact as _prove_relative_artifact
from tests.goal_bootstrap_support import render_saved_bootstrap as _render_saved_bootstrap
from validator.cli import app
from validator.exceptions import SpecsRootNotFoundError
from validator.goal_bootstrap import GoalBootstrapError, select_goal_render_context
from validator.goal_contracts import compile_command_goal

runner = CliRunner()


@pytest.mark.parametrize(
    ("flags", "expected_suffix"),
    [
        ("", "caller"),
        ("--dir target", "caller/target"),
        ("-D=target", "caller/target"),
        ("--dir target -D target", "caller/target"),
        ("prefix--dir ../other", "caller"),
        ("--directory ../other", "caller"),
        ("-- --dir ../other", "caller"),
    ],
)
def test_spec_init_root_grammar(tmp_path: Path, flags: str, expected_suffix: str) -> None:
    caller = tmp_path / "caller"
    target = caller / "target"
    other = tmp_path / "other"
    target.mkdir(parents=True)
    other.mkdir()

    context = select_goal_render_context("spec-init", flags, caller)

    assert context.project_root.as_posix().endswith(expected_suffix)
    assert sum(token.startswith("--dir=") for token in context.normalized_flags) <= 1


@pytest.mark.parametrize(
    "flags",
    ["--dir", "-D=", "--dir missing", "--dir target -D ../other"],
)
def test_invalid_spec_init_root_fails_without_writes(tmp_path: Path, flags: str) -> None:
    caller = tmp_path / "caller"
    (caller / "target").mkdir(parents=True)
    (tmp_path / "other").mkdir()
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    with pytest.raises(GoalBootstrapError):
        select_goal_render_context("spec-init", flags, caller)

    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_non_init_uses_strict_specs_root(tmp_path: Path) -> None:
    with pytest.raises(SpecsRootNotFoundError):
        select_goal_render_context("spec-plan", "--dir elsewhere", tmp_path)


def test_render_spec_init_from_fresh_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["goal", "render", "spec-init", "--flags", "--auto", "--save"],
    )

    assert result.exit_code == 0, result.output
    match = re.fullmatch(
        r"hash:([a-f0-9]{64}) \| contract-file:(\S+) \| state-file:(\S+)\n?",
        result.output,
    )
    assert match is not None
    output_hash, contract_path, state_path = match.groups()
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    assert output_hash == contract["goal_hash"] == state["goal_hash"]
    assert hashlib.sha256(contract["canonical_json"].encode("utf-8")).hexdigest() == output_hash
    assert json.loads(contract["canonical_json"]) == contract["canonical"]
    assert contract["project_root"] == tmp_path.resolve().as_posix()
    assert contract["canonical"]["project_root"] == tmp_path.resolve().as_posix()
    assert state["command"] == "spec-init"
    assert state["status"] == "active"
    assert state["tasks"]
    assert not (tmp_path / ".specs").exists()


def test_rendered_symlink_root_remains_bound_after_retarget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = tmp_path / "caller"
    original = tmp_path / "original"
    foreign = tmp_path / "foreign"
    selected = tmp_path / "selected"
    caller.mkdir()
    original.mkdir()
    foreign.mkdir()
    selected.symlink_to(original, target_is_directory=True)
    monkeypatch.chdir(caller)
    contract_file, state_file, contract = _render_saved_bootstrap(selected)
    assert contract["project_root"] == original.resolve().as_posix()
    (original / "proof.txt").write_text("proof", encoding="utf-8")
    (original / ".specs").mkdir()
    (foreign / ".specs").mkdir()
    selected.unlink()
    selected.symlink_to(foreign, target_is_directory=True)

    task_id = contract["tasks"][0]["id"]
    _prove_relative_artifact(contract_file, state_file, task_id)
    _mark_all_tasks_complete(state_file)
    artifact_path = _archive_pair(contract_file, state_file)
    assert artifact_path.parent == (original / ".specs" / ".runs").resolve()
    assert not (foreign / ".specs" / ".runs").exists()


def test_explicit_target_controls_root_and_conventions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = tmp_path / "caller"
    target = tmp_path / "target"
    caller.mkdir()
    target.mkdir()
    (caller / ".conventions").mkdir()
    (caller / ".conventions" / "index.md").write_text("# caller", encoding="utf-8")
    monkeypatch.chdir(caller)

    result = runner.invoke(
        app,
        [
            "goal",
            "render",
            "spec-init",
            "--flags",
            f"--auto --dir {target}",
            "--save",
        ],
    )

    assert result.exit_code == 0, result.output
    contract_path = Path(re.search(r"contract-file:(\S+)", result.output).group(1))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert contract["project_root"] == target.resolve().as_posix()
    assert contract["normalized_flags"] == ["--auto", f"--dir={target.resolve()}"]
    assert contract["canonical"]["conventions"]["selected_domains"] == []
    assert not (target / ".specs").exists()


@pytest.mark.parametrize("flag", ["--dir", "-D", "--dir=", "-D="])
@pytest.mark.parametrize("through_symlink", [False, True])
def test_absolute_directory_forms_are_canonicalized(
    tmp_path: Path, flag: str, through_symlink: bool
) -> None:
    caller = tmp_path / "caller"
    target = tmp_path / "target"
    caller.mkdir()
    target.mkdir()
    selected = tmp_path / "target-link" if through_symlink else target
    if through_symlink:
        selected.symlink_to(target, target_is_directory=True)
    flags = f"{flag}{selected}" if flag.endswith("=") else f"{flag} {selected}"

    context = select_goal_render_context("spec-init", flags, caller)

    assert context.project_root == target.resolve()
    assert context.normalized_flags == (f"--dir={target.resolve()}",)


def test_initialized_ancestor_is_not_borrowed_for_spec_init(tmp_path: Path) -> None:
    child = tmp_path / "nested" / "fresh"
    child.mkdir(parents=True)
    (tmp_path / ".specs").mkdir()

    context = select_goal_render_context("spec-init", "", child)

    assert context.project_root == child.resolve()
    assert not (child / ".specs").exists()


@pytest.mark.parametrize("kind", ["file", "unreadable", "loop", "conflict", "grammar"])
def test_invalid_render_cli_is_actionable_and_write_free(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    if kind == "file":
        selected = tmp_path / "target.txt"
        selected.write_text("file", encoding="utf-8")
        flags = f"--dir {selected}"
    elif kind == "unreadable":
        target.chmod(0)
        flags = f"--dir {target}"
    elif kind == "loop":
        selected = tmp_path / "loop"
        selected.symlink_to(selected)
        flags = f"--dir {selected}"
    elif kind == "conflict":
        other = tmp_path / "other"
        other.mkdir()
        flags = f"--dir {target} -D {other}"
    else:
        flags = "--dir 'unterminated"
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["goal", "render", "spec-init", "--flags", flags, "--save"])
    if kind == "unreadable":
        target.chmod(0o700)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("goal blocked:")
    assert "correct --dir and rerender the goal" in result.stderr
    assert "Traceback" not in result.output
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_project_root_is_the_only_root_specific_hash_input(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    livespec_root = Path(__file__).resolve().parents[1]

    goal_a = compile_command_goal("spec-init", project_root=first, livespec_root=livespec_root)
    goal_b = compile_command_goal("spec-init", project_root=first, livespec_root=livespec_root)
    goal_c = compile_command_goal("spec-init", project_root=second, livespec_root=livespec_root)

    assert goal_a.goal_hash == goal_b.goal_hash
    assert goal_a.goal_hash != goal_c.goal_hash
