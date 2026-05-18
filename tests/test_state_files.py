"""Tests for validator.state_files (Chantier 4 / Feature 013, FR-005/006)."""

from __future__ import annotations

from pathlib import Path

from validator.state_files import (
    ALLOWED_STATES,
    KNOWN_STATE_FILENAMES,
    REQUIRED_KEYS,
    discover_state_files,
    migrate_state_file,
    validate_state_file,
    validate_state_files,
)


def _write(path: Path, frontmatter_lines: list[str], body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(frontmatter_lines)
    path.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")


def _valid_feature_pipeline(tmp_path: Path, slug: str) -> Path:
    p = tmp_path / ".specs" / "features" / slug / "pipeline.md"
    _write(
        p,
        [
            "schema_version: 1",
            "owner_command: spec-feature",
            f"feature_slug: {slug}",
            "created_at: 2026-05-04",
            "updated_at: 2026-05-04",
            "current_state: InProgress",
        ],
        "# Pipeline\n",
    )
    return p


class TestDiscovery:
    def test_finds_only_known_filenames(self, tmp_path: Path) -> None:
        # Plant some valid + irrelevant files
        _valid_feature_pipeline(tmp_path, "001-foo")
        (tmp_path / ".specs" / "features" / "001-foo" / "spec.md").write_text("# spec\n")
        _write(
            tmp_path / ".specs" / "ship.md",
            [
                "schema_version: 1",
                "owner_command: spec-ship",
                'feature_slug: "-"',
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )

        found = discover_state_files(tmp_path / ".specs")
        names = sorted(p.name for p in found)
        assert names == ["pipeline.md", "ship.md"]

    def test_returns_empty_for_missing_root(self, tmp_path: Path) -> None:
        assert discover_state_files(tmp_path / "does-not-exist") == []


class TestValidateStateFile:
    def test_valid_feature_pipeline_passes(self, tmp_path: Path) -> None:
        p = _valid_feature_pipeline(tmp_path, "013-state-model-identity-resolution")
        assert validate_state_file(p) == []

    def test_missing_required_keys(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(p, ["schema_version: 1"])
        violations = validate_state_file(p)
        assert {v.rule for v in violations} == {"missing_key"}
        # Each missing key produces one violation
        assert len(violations) == len(REQUIRED_KEYS) - 1

    def test_rejects_placeholder_in_feature_slug(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-feature",
                "feature_slug: NNN-feature-name",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )
        violations = validate_state_file(p)
        rules = {v.rule for v in violations}
        assert "placeholder_leak" in rules

    def test_rejects_unknown_state_value(self, tmp_path: Path) -> None:
        p = _valid_feature_pipeline(tmp_path, "001-foo")
        # Overwrite with bad state
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-feature",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Halfway",
            ],
        )
        violations = validate_state_file(p)
        wrong_value = [v for v in violations if v.rule == "wrong_value"]
        assert wrong_value
        assert "Halfway" in wrong_value[0].message

    def test_rejects_legacy_dotted_owner_command(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec" + ".feature",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )

        violations = validate_state_file(p)

        assert any(
            v.rule == "wrong_value" and "spec-feature" in v.message
            for v in violations
        )

    def test_rejects_non_iso_date(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-feature",
                "feature_slug: 001-foo",
                "created_at: 2026/05/04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )
        violations = validate_state_file(p)
        formats = [v for v in violations if v.rule == "wrong_format"]
        assert formats
        assert "created_at" in formats[0].message

    def test_blocked_without_reason_fails(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-feature",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Blocked",
            ],
        )
        violations = validate_state_file(p)
        assert any(v.rule == "missing_reason" for v in violations)

    def test_blocked_with_reason_passes(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-feature",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Blocked",
                "reason: tests fail after 3 retries",
            ],
        )
        assert validate_state_file(p) == []

    def test_project_global_ship_md_uses_dash_sentinel(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "ship.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-ship",
                'feature_slug: "-"',
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )
        assert validate_state_file(p) == []

    def test_project_global_with_real_slug_fails(self, tmp_path: Path) -> None:
        p = tmp_path / ".specs" / "ship.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec-ship",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )
        violations = validate_state_file(p)
        assert any(v.rule == "wrong_value" for v in violations)

    def test_migrate_fixes_legacy_dotted_owner_command(self, tmp_path: Path) -> None:
        specs_root = tmp_path / ".specs"
        p = specs_root / "features" / "001-foo" / "pipeline.md"
        _write(
            p,
            [
                "schema_version: 1",
                "owner_command: spec" + ".feature",
                "feature_slug: 001-foo",
                "created_at: 2026-05-04",
                "updated_at: 2026-05-04",
                "current_state: Pending",
            ],
        )

        outcome = migrate_state_file(p, specs_root)

        assert outcome.action == "completed"
        assert "owner_command" in outcome.added_keys
        assert "owner_command: spec-feature" in p.read_text(encoding="utf-8")
        assert validate_state_file(p) == []


class TestValidateStateFiles:
    def test_aggregates_files_and_violations(self, tmp_path: Path) -> None:
        _valid_feature_pipeline(tmp_path, "001-foo")
        _valid_feature_pipeline(tmp_path, "002-bar")
        # Plant one bad file
        bad = tmp_path / ".specs" / "features" / "003-baz" / "pipeline.md"
        _write(bad, ["schema_version: 1"])

        report = validate_state_files(tmp_path / ".specs")
        assert report.files_checked == 3
        assert not report.ok
        assert all(v.path == bad for v in report.violations)

    def test_empty_report_when_clean(self, tmp_path: Path) -> None:
        _valid_feature_pipeline(tmp_path, "001-foo")
        report = validate_state_files(tmp_path / ".specs")
        assert report.ok
        assert report.files_checked == 1


class TestConstants:
    """Public constants are referenced by system/state-files-schema.md."""

    def test_known_filenames_match_doc(self) -> None:
        assert {
            "pipeline.md",
            "progress.md",
            "ship.md",
            "preflight.md",
        } == KNOWN_STATE_FILENAMES

    def test_allowed_states_match_state_machine(self) -> None:
        assert {"Pending", "InProgress", "Done", "Blocked"} == ALLOWED_STATES
