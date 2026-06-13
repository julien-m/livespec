"""Tests for the preflight auto-install & init engine (Feature 034)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias

import pytest

from validator import preflight_autofix as af
from validator.preflight_autofix import (
    CURL_ALLOWLIST,
    FixResult,
    PreflightItem,
    build_install_cmd,
    exit_code_for,
    filter_items,
    fix_item,
    impacted_drivers,
    impacted_runners,
    parse_preflight_manifest,
    render_guide,
    render_summary,
    run_fix,
)

RunCall: TypeAlias = tuple[Sequence[str] | str, dict[str, object]]


# --- Smart scoping ---------------------------------------------------------


def test_impacted_drivers_python_only() -> None:
    files = ["validator/cli.py", "tests/test_x.py"]
    assert impacted_drivers(files) == {"python"}
    assert impacted_runners(files) == set()


def test_impacted_drivers_swift_kotlin() -> None:
    files = ["ios/App.swift", "android/Main.kt"]
    assert impacted_drivers(files) == {"swift", "kotlin"}
    assert impacted_runners(files) == {"ios", "android"}


def test_filter_items_keeps_global_items() -> None:
    items = [
        PreflightItem("git", "git", "manual", "", driver=None, runner=None),
        PreflightItem("xcode", None, "manual", "", driver=None, runner="ios"),
        PreflightItem("python", "python", "brew", "python", driver="python"),
    ]
    kept = filter_items(items, drivers={"python"}, runners=set())
    names = {i.name for i in kept}
    assert "git" in names  # global always kept
    assert "python" in names
    assert "xcode" not in names


def test_filter_items_keeps_runner_match() -> None:
    items = [
        PreflightItem("xcode", None, "manual", "", runner="ios"),
        PreflightItem("avd", None, "manual", "", runner="android"),
    ]
    kept = filter_items(items, drivers=set(), runners={"ios"})
    assert {i.name for i in kept} == {"xcode"}


# --- Install dispatchers ---------------------------------------------------


def test_build_install_cmd_brew() -> None:
    item = PreflightItem("maestro", "maestro", "brew", "maestro")
    cmd, shell = build_install_cmd(item)
    assert cmd == ["brew", "install", "maestro"]
    assert shell is False


def test_build_install_cmd_cargo() -> None:
    item = PreflightItem("td", "tauri-driver", "cargo", "tauri-driver")
    cmd, _ = build_install_cmd(item)
    assert cmd == ["cargo", "install", "tauri-driver"]


def test_build_install_cmd_npm_prefers_pnpm(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which_pnpm(b: str) -> str | None:
        return "/usr/bin/pnpm" if b == "pnpm" else None

    monkeypatch.setattr(af, "_which", fake_which_pnpm)
    item = PreflightItem("p", "p", "npm", "playwright")
    cmd, _ = build_install_cmd(item)
    assert cmd[0] == "pnpm"


def test_build_install_cmd_npm_falls_back_to_npm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which_none(b: str) -> str | None:
        return None

    monkeypatch.setattr(af, "_which", fake_which_none)
    item = PreflightItem("p", "p", "npm", "playwright")
    cmd, _ = build_install_cmd(item)
    assert cmd[0] == "npm"


def test_build_install_cmd_curl_allowlist() -> None:
    item = PreflightItem("maestro", "maestro", "curl", "maestro")
    cmd, shell = build_install_cmd(item)
    assert shell is True
    assert "curl" in cmd
    assert CURL_ALLOWLIST["maestro"] in cmd


def test_build_install_cmd_curl_rejects_unknown() -> None:
    item = PreflightItem("evil", None, "curl", "evil-source")
    with pytest.raises(ValueError, match="Untrusted"):
        build_install_cmd(item)


def test_build_install_cmd_simctl() -> None:
    item = PreflightItem(
        "iPhone 16",
        None,
        "simctl",
        "iPhone 16|iPhone16,2|com.apple.CoreSimulator.SimRuntime.iOS-18-2",
    )
    cmd, _ = build_install_cmd(item)
    assert cmd[:3] == ["xcrun", "simctl", "create"]
    assert "iPhone 16" in cmd


def test_build_install_cmd_avdmanager() -> None:
    item = PreflightItem(
        "Pixel_8_API_35",
        None,
        "avdmanager",
        "Pixel_8_API_35|system-images;android-35;google_apis;arm64-v8a",
    )
    cmd, _ = build_install_cmd(item)
    assert cmd[:3] == ["avdmanager", "create", "avd"]
    assert "-n" in cmd and "Pixel_8_API_35" in cmd


def test_build_install_cmd_conventions_scaffold(tmp_path: Path) -> None:
    item = PreflightItem(
        "conventions scaffold",
        None,
        "conventions-scaffold",
        str(tmp_path),
    )

    cmd, shell = build_install_cmd(item)

    assert cmd == [
        "livespec",
        "conventions",
        "scaffold",
        "--repo",
        str(tmp_path),
        "--apply",
    ]
    assert shell is False


def test_conventions_preflight_items_from_gates(tmp_path: Path) -> None:
    _write_conventions_gates(tmp_path)

    items = af.conventions_preflight_items(tmp_path)

    names = {item.name for item in items}
    assert "conventions lint binary: ruff" in names
    assert "conventions lint version: ruff" in names
    assert "conventions lint config: pyproject.toml" in names
    assert "conventions scaffold" in names


def test_conventions_preflight_requires_llm_for_blocking_rulebook(tmp_path: Path) -> None:
    _write_conventions_gates(tmp_path)
    (tmp_path / ".specs" / "conventions-rulebook.yaml").write_text(
        """\
schema_version: 1
compiled_at: now
sources: []
rules:
  - id: C001
    domain: code
    description: Must be reviewed semantically.
    check: Ask the provider.
    source_excerpt: Must be reviewed semantically.
    blocking: true
    applies_to: []
    source_paths: []
""",
        encoding="utf-8",
    )

    items = af.conventions_preflight_items(tmp_path)

    assert any(item.name == "conventions llm provider" for item in items)


# --- fix_item flow ---------------------------------------------------------


def _patch_run(
    monkeypatch: pytest.MonkeyPatch, result: subprocess.CompletedProcess[str]
) -> list[RunCall]:
    """Patch the subprocess runner and capture every invocation."""

    calls: list[RunCall] = []

    def fake_run(cmd: Sequence[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((cmd, kwargs))
        return result

    monkeypatch.setattr(af, "_run", fake_run)
    return calls


def test_fix_item_already_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(b: str) -> str:
        return "/usr/bin/" + b

    monkeypatch.setattr(af, "_which", fake_which)
    item = PreflightItem("git", "git", "brew", "git")
    res = fix_item(item)
    assert res.status == "ok"


def test_fix_item_installs_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    state: dict[str, bool] = {"installed": False}

    def fake_which_2(b: str) -> str | None:
        return "/usr/bin/" + b if state["installed"] else None

    def fake_run(cmd: Sequence[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        state["installed"] = True
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(af, "_which", fake_which_2)
    monkeypatch.setattr(af, "_run", fake_run)
    item = PreflightItem("maestro", "maestro", "brew", "maestro")
    res = fix_item(item)
    assert res.status == "installed"


def test_fix_item_dry_run_does_not_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which_3(b: str) -> str | None:
        return None

    monkeypatch.setattr(af, "_which", fake_which_3)
    calls = _patch_run(
        monkeypatch,
        subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    item = PreflightItem("maestro", "maestro", "brew", "maestro")
    res = fix_item(item, dry_run=True)
    assert res.status == "would_install"
    assert "brew install maestro" in res.command
    assert calls == []  # _run was never invoked


def test_fix_item_failed_install(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which_4(b: str) -> str | None:
        return None

    monkeypatch.setattr(af, "_which", fake_which_4)
    _patch_run(
        monkeypatch,
        subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="boom"),
    )
    item = PreflightItem("x", "x", "brew", "x")
    res = fix_item(item)
    assert res.status == "failed"
    assert "boom" in res.stderr


def test_fix_item_manual_emits_guide() -> None:
    item = PreflightItem(
        "Xcode",
        None,
        "manual",
        "",
        manual_steps=("Open the App Store", "Search Xcode", "Install"),
    )
    res = fix_item(item)
    assert res.status == "manual_required"
    assert "1. Open the App Store" in res.message


def test_fix_item_auto_skips_unsafe_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    # safe_for_auto=False but auto=True => still installs without prompting
    def fail_prompt(_msg: str) -> bool:
        raise AssertionError("prompt should not run under --auto")

    state2: dict[str, bool] = {"installed": False}

    def fake_which_5(b: str) -> str | None:
        return "/usr/bin/" + b if state2["installed"] else None

    def fake_run_2(cmd: Sequence[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        state2["installed"] = True
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(af, "_which", fake_which_5)
    monkeypatch.setattr(af, "_run", fake_run_2)

    item = PreflightItem("x", "x", "brew", "x", safe_for_auto=False)
    res = fix_item(item, auto=True, prompt=fail_prompt)
    assert res.status == "installed"


def test_fix_item_unsafe_prompt_decline(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which_6(b: str) -> str | None:
        return None

    def fake_prompt(_m: str) -> bool:
        return False

    monkeypatch.setattr(af, "_which", fake_which_6)
    item = PreflightItem("x", "x", "brew", "x", safe_for_auto=False)
    res = fix_item(item, auto=False, prompt=fake_prompt)
    assert res.status == "skipped"


# --- run_fix end-to-end ----------------------------------------------------


def test_run_fix_smart_scoping_skips_unrelated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_which_7(b: str) -> str:
        return "/usr/bin/" + b

    def fake_changed_files(repo: Path, *, base: str = "HEAD~1", head: str = "HEAD") -> list[str]:
        del repo, base, head
        return ["app.py"]

    monkeypatch.setattr(af, "_which", fake_which_7)
    monkeypatch.setattr(af, "changed_files", fake_changed_files)
    items = [
        PreflightItem("xcode", None, "manual", "", runner="ios"),
        PreflightItem("python", "python", "pip", "ruff", driver="python"),
    ]
    results = run_fix(items, repo=tmp_path, full=False)
    assert {r.item.name for r in results} == {"python"}


def test_run_fix_full_disables_smart_scoping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_which_8(b: str) -> str:
        return "/usr/bin/" + b

    def fake_changed_files_2(repo: Path, *, base: str = "HEAD~1", head: str = "HEAD") -> list[str]:
        del repo, base, head
        return ["app.py"]

    monkeypatch.setattr(af, "_which", fake_which_8)
    monkeypatch.setattr(af, "changed_files", fake_changed_files_2)
    items = [
        PreflightItem("xcode", None, "manual", "", runner="ios"),
        PreflightItem("python", "python", "pip", "ruff", driver="python"),
    ]
    results = run_fix(items, repo=tmp_path, full=True)
    assert len(results) == 2


def test_run_fix_no_changes_falls_back_to_full(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_which_9(b: str) -> str:
        return "/usr/bin/" + b

    def fake_changed_files_3(repo: Path, *, base: str = "HEAD~1", head: str = "HEAD") -> list[str]:
        del repo, base, head
        return []

    monkeypatch.setattr(af, "_which", fake_which_9)
    monkeypatch.setattr(af, "changed_files", fake_changed_files_3)
    items = [
        PreflightItem("xcode", None, "manual", "", runner="ios"),
        PreflightItem("python", "python", "pip", "ruff", driver="python"),
    ]
    results = run_fix(items, repo=tmp_path, full=False)
    # Empty diff -> EC-005: behave as --full
    assert len(results) == 2


# --- Summary & exit codes --------------------------------------------------


def test_render_summary_counts() -> None:
    item = PreflightItem("x", "x", "brew", "x")
    results = [
        FixResult(item, "ok"),
        FixResult(item, "installed"),
        FixResult(item, "manual_required"),
        FixResult(item, "failed"),
    ]
    out = render_summary(results)
    assert "Verified:        1" in out
    assert "Installed:       1" in out
    assert "Manual required: 1" in out
    assert "Failed:          1" in out


def test_exit_code_for_priority() -> None:
    item = PreflightItem("x", "x", "brew", "x")
    assert exit_code_for([FixResult(item, "ok")]) == 0
    assert exit_code_for([FixResult(item, "manual_required")]) == 2
    assert exit_code_for([FixResult(item, "failed")]) == 1
    # failed wins over manual_required
    assert exit_code_for([FixResult(item, "manual_required"), FixResult(item, "failed")]) == 1


# --- Manifest parsing ------------------------------------------------------


def test_parse_preflight_manifest_minimal() -> None:
    text = """## Tooling

### maestro
- **binary:** `maestro`
- **verify:** `maestro --version`
- **install:** `brew install maestro`
- **severity:** critical
"""
    items = parse_preflight_manifest(text)
    assert len(items) == 1
    assert items[0].name == "maestro"
    assert items[0].installer == "brew"
    assert items[0].install_arg == "maestro"


def test_parse_preflight_manifest_yaml_style() -> None:
    text = """## Tooling

### Python 3.11+

```yaml
check: python --version
auto_resolve: pip install -e ".[dev]"
```
"""
    items = parse_preflight_manifest(text)
    # YAML style is partially supported - at minimum we do not crash.
    assert isinstance(items, list)


def test_render_guide_numbered_steps() -> None:
    item = PreflightItem(
        "Xcode",
        None,
        "manual",
        "",
        manual_steps=("Open App Store", "Install Xcode"),
    )
    g = render_guide(item)
    assert "1. Open App Store" in g
    assert "2. Install Xcode" in g


def _write_conventions_gates(repo: Path) -> None:
    from validator.visual_evidence import sha256_file

    specs = repo / ".specs"
    specs.mkdir()
    (specs / "constitution.md").write_text("line limits\n", encoding="utf-8")
    # Build the minimal gates fixture needed for preflight discovery tests; the
    # hash keeps it consistent with the generated gates schema.
    (specs / "conventions-gates.yaml").write_text(
        f"""\
schema_version: 1
generated_from:
  constitution: .specs/constitution.md
  constitution_sha256: {sha256_file(specs / "constitution.md")}
  stack: .specs/stacks/_default.md
commands:
  lint:
    - id: ruff
      run: ruff check . --output-format json
      version: ruff 0.12.0
      config: pyproject.toml
builtin: {{}}
coverage: {{}}
exclusions: []
scope: repo
""",
        encoding="utf-8",
    )
