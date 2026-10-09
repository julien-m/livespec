"""Force recovery updates observed registry metadata and preserves custom history."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from tests.test_init_profile import hybrid
from tests.test_init_recovery import environment, execute, tree

FEATURES = """<!-- readme:features:start -->
| # | Feature | Status | Created | Updated | Spec |
|---|---|---|---|---|---|
| 001 | custom | Draft | 2026-09-01 | 2026-09-02 | [Spec](features/001-custom/spec.md) |
<!-- readme:features:end -->"""
OLD_ADR = (
    "| [ADR-001](stacks/decisions/ADR-001-handy-app-stack.md) | "
    "Original decision | 2026-09-01 | Active |"
)


def old_readme() -> str:
    """Reproduce Handy's old generated metadata with retained user-owned content."""
    return (
        "# .specs — handy-app\n\n"
        "> Specification registry for handy-app. "
        "All artifacts produced by LiveSpec are indexed here.\n"
        "> Last updated: 2026-10-09\n\n"
        "USER HEADER WITH handy-app KEPT VERBATIM\n\n## Features\n\n"
        f"{FEATURES}\n\n## Architecture Decisions\n\n"
        "<!-- readme:decisions:start -->\n"
        "| ADR | Decision | Date | Status |\n|---|---|---|---|\n"
        f"{OLD_ADR}\n<!-- readme:decisions:end -->\n\n"
        "## Recent Activity\n\n<!-- readme:activity:start -->\n"
        "CUSTOM ACTIVITY WITH handy-app KEPT VERBATIM\n<!-- readme:activity:end -->\n"
        "USER FOOTER KEPT VERBATIM\n"
    )


def test_ac004_force_refreshes_handy_registry_and_retains_history(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    specs = project / ".specs"
    registry = specs / "README.md"
    registry.write_text(old_readme())
    old = specs / "stacks/decisions/ADR-001-handy-app-stack.md"
    old.write_text("historical decision bytes\n")
    feature = specs / "features/001-custom/spec.md"
    feature.parent.mkdir(parents=True)
    feature.write_text("feature bytes\n")
    result = execute(project, env, "--force")
    assert result.returncode == 0, result.stderr
    updated = registry.read_text()
    assert updated.startswith("# .specs — Handy\n")
    assert "> Specification registry for Handy." in updated
    assert FEATURES in updated and OLD_ADR in updated
    assert "USER HEADER WITH handy-app KEPT VERBATIM" in updated
    assert "CUSTOM ACTIVITY WITH handy-app KEPT VERBATIM" in updated
    assert updated.endswith("USER FOOTER KEPT VERBATIM\n")
    observed = next((specs / "stacks/decisions").glob("ADR-bootstrap-*.md"))
    assert f"](stacks/decisions/{observed.name})" in updated
    added = next(
        line
        for line in updated.splitlines(keepends=True)
        if f"](stacks/decisions/{observed.name})" in line
    )
    restored = updated.replace(added, "", 1)
    restored = restored.replace("# .specs — Handy\n", "# .specs — handy-app\n", 1)
    restored = restored.replace(
        "> Specification registry for Handy.", "> Specification registry for handy-app.", 1
    )
    assert restored == old_readme()
    assert old.read_text() == "historical decision bytes\n"
    assert feature.read_text() == "feature bytes\n"
    backup = next((project / ".livespec-backups").iterdir())
    assert (backup / ".specs/README.md").read_text() == old_readme()
    before = tree(project)
    verified = execute(project, env, "--verify-only")
    assert verified.returncode == 0 and tree(project) == before
    assert execute(project, env, "--force").returncode == 0
    assert registry.read_text().count(f"](stacks/decisions/{observed.name})") == 1


@pytest.mark.parametrize("defect", ["name", "adr"])
def test_ac003_verify_rejects_stale_registry_even_when_recorded_hash_matches(
    tmp_path: Path,
    defect: str,
) -> None:
    project = tmp_path / "app"
    project.mkdir()
    hybrid(project)
    env = environment(tmp_path)
    assert execute(project, env).returncode == 0
    registry = project / ".specs/README.md"
    stale = old_readme() if defect == "name" else registry.read_text()
    if defect == "adr":
        stale = "".join(
            line for line in stale.splitlines(keepends=True) if "ADR-bootstrap-" not in line
        )
    registry.write_text(stale)
    # Reproduce the old backend recording stale bytes as their own valid identity.
    manifest_path = project / ".specs/bootstrap-profile.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["documents"][".specs/README.md"] = sha256(registry.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    before = tree(project)
    result = execute(project, env, "--verify-only")
    assert result.returncode != 0 and "registry" in result.stderr.lower()
    assert tree(project) == before


def test_ac004_custom_registry_without_generated_slots_keeps_all_bytes(tmp_path: Path) -> None:
    from validator.init_profile import detect_profile
    from validator.init_recovery import refresh_registry, verify_registry

    hybrid(tmp_path)
    profile = detect_profile(tmp_path)
    custom = "# My custom project registry\n\n| feature | custom |\nUSER TEXT\n\n"
    refreshed = refresh_registry(custom, profile)
    assert refreshed.startswith(custom)
    verify_registry(refreshed, profile)
    assert refresh_registry(refreshed, profile) == refreshed
