"""Causal public INIT proof regression for legacy convention routing."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.cli import app
from validator.goal_contracts import compile_command_goal

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("general.md", "python.md", "cli.md", "stack-commands.md")


def _routing(tmp_path: Path, *, legacy: bool = True) -> tuple[Path, Path]:
    project = tmp_path / "project"
    sources = tmp_path / "ai-ressources"
    (project / ".conventions").mkdir(parents=True)
    (sources / "code-conventions").mkdir(parents=True)
    for name in NAMES:
        (sources / "code-conventions" / name).write_text(
            f"# {name}\nUse explicit types and bounded subprocesses.\n", encoding="utf-8"
        )
    header = (
        "AIRESOURCES=${AIRESOURCES:-" + str(sources) + "}"
        if legacy
        else f"> `$AIRESOURCES` = `{sources}`"
    )
    directory = "conventions/code" if legacy else "code-conventions"
    (project / ".conventions/index.md").write_text(
        f"# Conventions Index\n\n{header}\n\n## code [typescript, react, vite, tests, cli]\n"
        f"→ $AIRESOURCES/{directory}/general.md, python.md, cli.md, stack-commands.md\n",
        encoding="utf-8",
    )
    return project, sources


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


# @spec FR-003: Resolve invalid routing readonly before lock
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-003
def test_public_init_render_and_lock_proof_read_existing_canonical_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, sources = _routing(tmp_path)
    controls = tmp_path / "controls"
    controls.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    before = _snapshot(project), _snapshot(sources)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "goal",
            "render",
            "spec-init",
            "--flags",
            f'--from-code --auto --force --dir "{project}"',
            "--save",
        ],
    )
    assert result.exit_code == 0, result.output
    pair_dir = controls / "livespec-goals"
    contract_path = next(pair_dir.glob("*.contract.json"))
    state_path = next(pair_dir.glob("*.state.json"))
    immutable = contract_path.read_bytes()
    contract = json.loads(immutable)
    task = next(task for task in contract["tasks"] if "Lock goal contract" in task["description"])
    paths = [(sources / "code-conventions" / name).resolve() for name in NAMES]
    actual_reads = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    proof = runner.invoke(
        app,
        [
            "goal",
            "prove",
            "--contract",
            str(contract_path),
            "--state",
            str(state_path),
            "--task",
            task["id"],
            "--evidence",
            json.dumps(
                {
                    "output": (
                        f"Rendered immutable contract {contract['goal_hash']}; read {actual_reads}"
                    ),
                    "success_criteria_met": True,
                    "convention_domains_recorded": ["code"],
                    "convention_sources_read": list(actual_reads),
                    "conventions_applied_to_output": True,
                }
            ),
        ],
    )
    assert proof.exit_code == 0, proof.output
    assert "ACCEPTED" in proof.output
    assert set(task["required_conventions"]["source_paths"]) == set(actual_reads)
    domain = contract["canonical"]["conventions"]["selected_domains"][0]
    root_resolution = contract["canonical"]["conventions"]["root_resolution"]
    assert root_resolution["kind"] == "legacy_literal_default"
    assert root_resolution["resolved_root"] == str(sources)
    assert domain["airesources_root"] == str(sources)
    for source in domain["source_files"]:
        assert Path(source["path"]).is_file()
        assert source["sha256"] == hashlib.sha256(source["content"].encode()).hexdigest()
        assert source["resolution"]["original_path"].startswith("$AIRESOURCES/conventions/code/")
    assert contract_path.read_bytes() == immutable
    assert (_snapshot(project), _snapshot(sources)) == before


@pytest.mark.parametrize("failure", ["unknown", "canonical_missing", "root_unknown"])
def test_public_init_unknown_or_missing_source_blocks_before_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    project, sources = _routing(tmp_path)
    index = project / ".conventions/index.md"
    if failure == "unknown":
        index.write_text(index.read_text().replace("general.md", "unrecognized.md"))
    elif failure == "canonical_missing":
        (sources / "code-conventions/general.md").unlink()
    else:
        index.write_text(
            index.read_text().replace("AIRESOURCES=${AIRESOURCES:-", "UNKNOWN=${OTHER:-")
        )
    controls = tmp_path / "controls"
    controls.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(controls))
    before = _snapshot(project), _snapshot(sources)
    result = CliRunner().invoke(
        app,
        [
            "goal",
            "render",
            "spec-init",
            "--flags",
            f'--from-code --auto --force --dir "{project}"',
            "--save",
        ],
    )
    assert result.exit_code == 2, result.output
    assert "init_convention_source_unresolved" in result.output
    assert not list(controls.iterdir())
    assert (_snapshot(project), _snapshot(sources)) == before


@pytest.mark.parametrize(
    "command,flags",
    [
        ("spec-init", ""),
        ("spec-init", "--from-code --auto --force"),
        ("spec-status", ""),
    ],
)
def test_valid_routing_paths_and_content_remain_unchanged(
    tmp_path: Path, command: str, flags: str
) -> None:
    project, sources = _routing(tmp_path, legacy=False)
    (project / ".specs").mkdir()
    before = _snapshot(project), _snapshot(sources)
    goal = compile_command_goal(command, project_root=project, livespec_root=ROOT, flags=flags)
    domain = goal.payload["conventions"]["selected_domains"][0]
    assert domain["paths"] == [f"$AIRESOURCES/code-conventions/{name}" for name in NAMES]
    assert all("resolution" not in source for source in domain["source_files"])
    assert (_snapshot(project), _snapshot(sources)) == before


def test_non_init_legacy_resolution_behavior_is_not_changed(tmp_path: Path) -> None:
    project, _ = _routing(tmp_path)
    (project / ".specs").mkdir()
    goal = compile_command_goal("spec-status", project_root=project, livespec_root=ROOT)
    domain = goal.payload["conventions"]["selected_domains"][0]
    assert domain["paths"] == [f"$AIRESOURCES/conventions/code/{name}" for name in NAMES]
    assert domain["airesources_root"] is None


def test_existing_valid_legacy_reference_is_preserved_exactly(tmp_path: Path) -> None:
    project, sources = _routing(tmp_path)
    legacy = sources / "conventions/code"
    legacy.mkdir(parents=True)
    for name in NAMES:
        (legacy / name).write_text(f"# Existing custom legacy {name}\n", encoding="utf-8")
    before = _snapshot(project), _snapshot(sources)
    goal = _render_init(project)
    domain = goal.payload["conventions"]["selected_domains"][0]
    assert domain["paths"] == [f"$AIRESOURCES/conventions/code/{name}" for name in NAMES]
    assert all("resolution" not in source for source in domain["source_files"])
    assert (_snapshot(project), _snapshot(sources)) == before


def _render_init(project: Path):
    return compile_command_goal("spec-init", project_root=project, livespec_root=ROOT)
