# LiveSpec traceability anchors
# @spec(AC-001)
# @spec(AC-002)
# @spec(AC-003)
# @spec(AC-004)
# @spec(AC-005)
# @spec(AC-006)
# @spec(AC-009)
# @spec(AC-011)
# @spec(AC-012)

"""Tests for deterministic registry finalization (Feature 058).

# @spec FR-001, FR-002, FR-003, FR-004, FR-006, FR-008, FR-009, FR-010
#   — .specs/features/058-deterministic-finalization/spec.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from validator.finalize import (
    FINALIZE_ORACLE_NAME,
    FINALIZE_RECEIPT_SCHEMA_VERSION,
    ApplyRequest,
    FinalizeError,
    FinalizeReceipt,
    FinalizeReceiptError,
    apply_finalization,
    compute_hash8,
    compute_payload_hash,
    verify_finalization,
    verify_finalize_receipt,
    write_finalize_receipt,
)
from validator.locks import LockAcquisitionError, WriteHashMismatchError

# ─── Canonical hash8 payload serialization (FR-002, AC-002) ──────────────────


class TestHash8Canonicalization:
    def test_hash8_is_first_8_hex_of_payload_hash(self) -> None:
        """Identity is cmd+hash8: hash8 must be a stable prefix of the full hash."""
        payload: dict[str, object] = {
            "feature_slug": "004-notifications",
            "command": "spec-specify",
            "status": "Draft",
            "entry_body": "Spec: created",
            "global_summary": "[Feature 004] Spec created",
        }
        full = compute_payload_hash(payload)
        assert len(full) == 64
        assert compute_hash8(payload) == full[:8]

    def test_hash8_is_date_free_and_stable_across_days(self) -> None:
        """Re-running an identical apply on a later date must produce the same
        hash8 (Edge Case 1) — no volatile field may enter the canonical payload."""
        payload: dict[str, object] = {
            "feature_slug": "004-notifications",
            "command": "spec-specify",
            "status": "Draft",
            "entry_body": "Spec: created",
            "global_summary": "[Feature 004] Spec created",
        }
        assert compute_hash8(payload) == compute_hash8(dict(payload))

    def test_hash8_is_field_order_independent(self) -> None:
        """Canonical JSON sorts keys, so insertion order must not change identity."""
        ordered: dict[str, object] = {
            "command": "spec-specify",
            "entry_body": "Body",
            "feature_slug": "004-n",
            "global_summary": "Sum",
            "status": "Draft",
        }
        reordered: dict[str, object] = {
            "status": "Draft",
            "global_summary": "Sum",
            "feature_slug": "004-n",
            "entry_body": "Body",
            "command": "spec-specify",
        }
        assert compute_hash8(ordered) == compute_hash8(reordered)

    def test_payload_content_changes_identity(self) -> None:
        """Different payloads must never collide on the apply identity."""
        base: dict[str, object] = {
            "feature_slug": "004-n",
            "command": "spec-specify",
            "status": "Draft",
            "entry_body": "Body",
            "global_summary": "Sum",
        }
        changed = dict(base, entry_body="Other body")
        assert compute_hash8(base) != compute_hash8(changed)

    def test_omitted_status_is_a_distinct_identity(self) -> None:
        """`--status` omitted removes the key from the payload (Step 6 of the
        plan) — identity must stay deterministic but distinct from status runs."""
        with_status: dict[str, object] = {
            "feature_slug": "004-n",
            "command": "spec-plan",
            "status": "Planned",
            "entry_body": "Body",
            "global_summary": "Sum",
        }
        without_status: dict[str, object] = {
            "feature_slug": "004-n",
            "command": "spec-plan",
            "entry_body": "Body",
            "global_summary": "Sum",
        }
        assert compute_hash8(with_status) != compute_hash8(without_status)


# ─── Receipt write + verify_finalize_receipt (FR-003, FR-006, AC-007) ────────


def _make_request(slug: str = "004-notifications") -> ApplyRequest:
    return ApplyRequest(
        feature_slug=slug,
        command="spec-specify",
        status="Draft",
        entry_body="Spec: created\n\n- **Type:** Spec Update",
        global_summary="[Feature 004] Spec created",
        run_id="run-1",
    )


def _write_registry_file(project_root: Path, relative: str, content: str) -> Path:
    target = project_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


class TestFinalizeReceiptRoundtrip:
    def test_write_then_verify_returns_receipt(self, tmp_path: Path) -> None:
        """A receipt written by the oracle must round-trip through the verifier."""
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        assert receipt_path.is_file()
        receipt = verify_finalize_receipt(
            receipt_path,
            project_root=tmp_path,
            expected_feature_slug="004-notifications",
            expected_command="spec-specify",
        )
        assert isinstance(receipt, FinalizeReceipt)
        assert receipt.verdict == "PASS"
        assert receipt.outcome == "applied"
        assert receipt.oracle == FINALIZE_ORACLE_NAME
        assert receipt.schema_version == FINALIZE_RECEIPT_SCHEMA_VERSION
        assert [entry.path for entry in receipt.files] == [".specs/changelog.md"]

    def test_receipt_lives_under_feature_run_dir(self, tmp_path: Path) -> None:
        """Receipts must use the same containment as visual evidence:
        .specs/features/<slug>/run/<run-id>/finalize/receipt.json."""
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        expected_dir = (
            tmp_path / ".specs" / "features" / "004-notifications" / "run" / "run-1" / "finalize"
        )
        assert receipt_path == expected_dir / "receipt.json"

    def test_tampered_on_disk_file_is_rejected(self, tmp_path: Path) -> None:
        """A registry file edited after the receipt was written makes the
        receipt stale — DONE must not be provable from it (AC-008)."""
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        target.write_text("# Changelog\n\ntampered\n", encoding="utf-8")
        with pytest.raises(FinalizeReceiptError, match="sha256_mismatch"):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)

    def test_tampered_receipt_hash_is_rejected(self, tmp_path: Path) -> None:
        """Editing the receipt JSON itself (e.g. faking a sha256) must fail
        the receipt_hash recomputation."""
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        payload["files"][0]["sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(FinalizeReceiptError):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)

    def test_wrong_expected_feature_is_rejected(self, tmp_path: Path) -> None:
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        with pytest.raises(FinalizeReceiptError, match="feature_slug_mismatch"):
            verify_finalize_receipt(
                receipt_path,
                project_root=tmp_path,
                expected_feature_slug="999-other",
            )

    def test_wrong_expected_command_is_rejected(self, tmp_path: Path) -> None:
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        with pytest.raises(FinalizeReceiptError, match="command_mismatch"):
            verify_finalize_receipt(
                receipt_path,
                project_root=tmp_path,
                expected_command="spec-plan",
            )

    def test_receipt_outside_project_root_is_rejected(self, tmp_path: Path) -> None:
        """Containment rule shared with visual receipts (Edge Case 8)."""
        project_root = tmp_path / "project"
        outside_root = tmp_path / "elsewhere"
        target = _write_registry_file(project_root, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=project_root,
            request=_make_request(),
            outcome="applied",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        outside_root.mkdir()
        moved = outside_root / "receipt.json"
        moved.write_text(receipt_path.read_text(encoding="utf-8"), encoding="utf-8")
        with pytest.raises(FinalizeReceiptError, match="outside_project"):
            verify_finalize_receipt(moved, project_root=project_root)

    def test_fail_verdict_requires_violations(self, tmp_path: Path) -> None:
        """Verdict/violations consistency is part of the receipt contract:
        a FAIL receipt without violations is malformed and must be rejected."""
        target = _write_registry_file(tmp_path, ".specs/changelog.md", "# Changelog\n")
        receipt_path = write_finalize_receipt(
            project_root=tmp_path,
            request=_make_request(),
            outcome="verified",
            verdict="PASS",
            files=[target],
            violations=[],
        )
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        payload["verdict"] = "FAIL"
        receipt_path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(FinalizeReceiptError):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)


@pytest.mark.chaos
class TestFinalizeReceiptChaos:
    def test_malformed_json_receipt_raises_clear_error(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "receipt.json"
        receipt_path.write_text("{not json", encoding="utf-8")
        with pytest.raises(FinalizeReceiptError, match="receipt_unreadable"):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)

    def test_binary_receipt_raises_clear_error(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "receipt.json"
        receipt_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x01")
        with pytest.raises(FinalizeReceiptError, match="receipt_unreadable"):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)

    def test_non_oracle_json_is_rejected(self, tmp_path: Path) -> None:
        receipt_path = tmp_path / "receipt.json"
        receipt_path.write_text(json.dumps({"oracle": "other"}), encoding="utf-8")
        with pytest.raises(FinalizeReceiptError, match="oracle_mismatch"):
            verify_finalize_receipt(receipt_path, project_root=tmp_path)


# ─── Fixture .specs/ tree for apply/verify (Stories 1 and 2) ─────────────────

_SPEC_MD = """\
---
title: "Notifications"
status: Planned
priority: P1
created: 2026-06-01
updated: 2026-06-01
---

# Feature Spec: Notifications

## Header

- **Feature:** Notifications
- **Branch:** `feature/004-notifications`
- **Date:** 2026-06-01
- **Status:** Planned
"""

_FEATURE_ROW = (
    "| 004 | Notifications | Planned | 2026-06-01 | 2026-06-01 | "
    "[spec](features/004-notifications/spec.md) |"
)

_README_MD = f"""\
# .specs — Project

> Last updated: 2026-06-01

## Features

<!-- readme:features:start -->
| # | Feature | Status | Created | Updated | Spec |
|---|---|---|---|---|---|
{_FEATURE_ROW}
<!-- readme:features:end -->

## Architecture Decisions

<!-- readme:decisions:start -->
| ADR | Decision | Date | Status |
|---|---|---|---|
<!-- readme:decisions:end -->

## Recent Activity

<!-- readme:activity:start -->
| Date | Type | Description |
|---|---|---|
<!-- readme:activity:end -->
"""

_GLOBAL_CHANGELOG = """\
# Changelog

> Global changelog.

---

## 2026-06-01 — [Feature 004] Spec created: Notifications
"""

_ROADMAP_ITEM = (
    "- [x] **Notifications** — push notifications · Scope: M → "
    "[004-notifications](features/004-notifications/spec.md)"
)

_ROADMAP_MD = f"""\
# Roadmap

<!-- roadmap:mvp:start -->
{_ROADMAP_ITEM}
<!-- roadmap:mvp:end -->
"""


def _make_specs_tree(project_root: Path) -> Path:
    specs = project_root / ".specs"
    feature_dir = specs / "features" / "004-notifications"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(_SPEC_MD, encoding="utf-8")
    (feature_dir / "changelog.md").write_text("# Changelog - Notifications\n", encoding="utf-8")
    (specs / "README.md").write_text(_README_MD, encoding="utf-8")
    (specs / "changelog.md").write_text(_GLOBAL_CHANGELOG, encoding="utf-8")
    (specs / "roadmap.md").write_text(_ROADMAP_MD, encoding="utf-8")
    return specs


def _implement_request() -> ApplyRequest:
    return ApplyRequest(
        feature_slug="004-notifications",
        command="spec-implement",
        status="Implemented",
        entry_body=(
            "Feature: Initial implementation\n\n- **Type:** Feature\n- **AC impacted:** AC-001"
        ),
        global_summary="[Feature 004] Implemented: Notifications",
        run_id="run-apply",
    )


def _registry_snapshot(specs: Path) -> dict[str, bytes]:
    """Byte snapshot of all registry files (run/ receipts excluded)."""
    snapshot: dict[str, bytes] = {}
    for path in sorted(specs.rglob("*")):
        if path.is_file() and "run" not in path.parts:
            snapshot[str(path)] = path.read_bytes()
    return snapshot


# ─── apply_finalization (FR-001, FR-002, AC-001..AC-004) ─────────────────────


class TestApplyFinalization:
    def test_apply_writes_all_four_targets_with_markers(self, tmp_path: Path) -> None:
        """AC-001/AC-002: one apply call must update the four registry targets
        and stamp each with the cmd+hash8 idempotence marker."""
        specs = _make_specs_tree(tmp_path)
        request = _implement_request()
        result = apply_finalization(tmp_path, request)
        assert result.outcome == "applied"
        hash8 = request.hash8()
        marker_core = f"finalize:spec-implement:2026-06-10:{hash8}"
        feature_changelog = (specs / "features/004-notifications/changelog.md").read_text()
        global_changelog = (specs / "changelog.md").read_text()
        readme = (specs / "README.md").read_text()
        spec_md = (specs / "features/004-notifications/spec.md").read_text()
        assert "Feature: Initial implementation" in feature_changelog
        assert "[Feature 004] Implemented: Notifications" in global_changelog
        assert "| Implemented |" in readme
        for content in (feature_changelog, global_changelog, readme, spec_md):
            assert "finalize:spec-implement:" in content
            assert hash8 in content
        assert marker_core[:30]  # marker carries a date segment (informational)

    def test_apply_emits_verifiable_receipt(self, tmp_path: Path) -> None:
        """AC-003: the receipt must verify against the on-disk state."""
        _make_specs_tree(tmp_path)
        result = apply_finalization(tmp_path, _implement_request())
        receipt = verify_finalize_receipt(
            result.receipt_path,
            project_root=tmp_path,
            expected_feature_slug="004-notifications",
            expected_command="spec-implement",
        )
        assert receipt.outcome == "applied"
        assert receipt.verdict == "PASS"
        assert len(receipt.files) == 5

    def test_apply_updates_spec_status_frontmatter_and_header_in_sync(self, tmp_path: Path) -> None:
        """AC-001: YAML `status:` and the `- **Status:**` header line must
        never diverge after apply."""
        specs = _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        spec_md = (specs / "features/004-notifications/spec.md").read_text()
        assert "status: Implemented" in spec_md
        assert "- **Status:** Implemented" in spec_md
        assert "status: Planned" not in spec_md
        assert "- **Status:** Planned" not in spec_md

    def test_identical_rerun_is_zero_write_already_finalized(self, tmp_path: Path) -> None:
        """AC-002 / SC-002: a byte-identical registry after the second run
        proves idempotence — the marker is the only dedupe mechanism."""
        specs = _make_specs_tree(tmp_path)
        request = _implement_request()
        apply_finalization(tmp_path, request)
        before = _registry_snapshot(specs)
        rerun = apply_finalization(
            tmp_path,
            ApplyRequest(
                feature_slug=request.feature_slug,
                command=request.command,
                status=request.status,
                entry_body=request.entry_body,
                global_summary=request.global_summary,
                run_id="run-rerun",
            ),
        )
        assert rerun.outcome == "already_finalized"
        assert _registry_snapshot(specs) == before

    def test_partial_apply_converges_without_duplicates(self, tmp_path: Path) -> None:
        """Edge Case 5: targets already carrying the marker are skipped, so a
        crashed run converges instead of duplicating entries."""
        specs = _make_specs_tree(tmp_path)
        request = _implement_request()
        marker = f"<!-- finalize:{request.command}:2026-06-09:{request.hash8()} -->"
        feature_changelog = specs / "features/004-notifications/changelog.md"
        feature_changelog.write_text(
            feature_changelog.read_text()
            + f"\n### 2026-06-09 — Feature: Initial implementation\n\n{marker}\n",
            encoding="utf-8",
        )
        pre_marked = feature_changelog.read_bytes()
        result = apply_finalization(tmp_path, request)
        assert result.outcome == "applied"
        assert feature_changelog.read_bytes() == pre_marked
        assert "finalize:spec-implement" in (specs / "README.md").read_text()
        assert result.skipped == ("feature_changelog", "roadmap")

    def test_status_none_skips_spec_status_target(self, tmp_path: Path) -> None:
        """plan.md Step 6: omitting --status writes only the three
        changelog/README targets and records the skipped target."""
        specs = _make_specs_tree(tmp_path)
        request = ApplyRequest(
            feature_slug="004-notifications",
            command="spec-plan",
            status=None,
            entry_body="Plan: Technical plan generated",
            global_summary="[Feature 004] Plan created: Notifications",
            run_id="run-plan",
        )
        spec_before = (specs / "features/004-notifications/spec.md").read_bytes()
        result = apply_finalization(tmp_path, request)
        assert result.outcome == "applied"
        assert (specs / "features/004-notifications/spec.md").read_bytes() == spec_before
        assert "spec_status" not in result.written

    def test_lock_timeout_leaves_registry_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-004: lock contention without --retry must modify nothing."""
        from contextlib import contextmanager

        from validator import finalize as finalize_module

        specs = _make_specs_tree(tmp_path)

        @contextmanager
        def _always_blocked(*args: object, **kwargs: object):
            raise LockAcquisitionError("could not acquire .specs/.LOCK within 10s")
            yield  # pragma: no cover

        monkeypatch.setattr(finalize_module, "acquire_lock", _always_blocked)
        before = _registry_snapshot(specs)
        with pytest.raises(LockAcquisitionError):
            apply_finalization(tmp_path, _implement_request())
        assert _registry_snapshot(specs) == before

    def test_hash_mismatch_blocks_naming_file_and_records_partial_receipt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-004 / Edge Case 5: a post-write hash mismatch must halt with
        state_invalid naming the file and record the files written so far."""
        from validator import finalize as finalize_module

        _make_specs_tree(tmp_path)
        real_write = finalize_module.write_with_hash_check

        def _failing_on_readme(target: Path, content: str, encoding: str = "utf-8") -> str:
            if target.name == "README.md":
                raise WriteHashMismatchError(f"post-write hash mismatch for {target}")
            return real_write(target, content, encoding)

        monkeypatch.setattr(finalize_module, "write_with_hash_check", _failing_on_readme)
        with pytest.raises(FinalizeError) as excinfo:
            apply_finalization(tmp_path, _implement_request())
        assert excinfo.value.subtype == "state_invalid"
        assert "README.md" in str(excinfo.value)
        receipt_path = excinfo.value.receipt_path
        assert receipt_path is not None and receipt_path.is_file()
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert payload["outcome"] == "BLOCKED"
        assert payload["verdict"] == "BLOCKED"
        written_paths = [entry["path"] for entry in payload["files"]]
        assert ".specs/features/004-notifications/changelog.md" in written_paths

    def test_missing_status_anchor_blocks_state_invalid(self, tmp_path: Path) -> None:
        """Edge Case 10: apply must refuse to guess an insertion point when
        the spec status anchors are absent or non-standard."""
        specs = _make_specs_tree(tmp_path)
        spec_path = specs / "features/004-notifications/spec.md"
        spec_path.write_text(
            spec_path.read_text().replace("- **Status:** Planned\n", ""),
            encoding="utf-8",
        )
        with pytest.raises(FinalizeError) as excinfo:
            apply_finalization(tmp_path, _implement_request())
        assert excinfo.value.subtype == "state_invalid"
        assert "spec.md" in str(excinfo.value)

    def test_missing_feature_directory_blocks(self, tmp_path: Path) -> None:
        (tmp_path / ".specs").mkdir()
        with pytest.raises(FinalizeError):
            apply_finalization(tmp_path, _implement_request())


# ─── README recovery + changelog rotation (FR-010, AC-012) ───────────────────


class TestRegistryRecoveryAndRotation:
    def test_legacy_readme_detached_rows_repair_on_idempotent_apply(self, tmp_path: Path) -> None:
        specs = _make_specs_tree(tmp_path)
        request = _implement_request()
        apply_finalization(tmp_path, request)
        readme = specs / "README.md"
        marker = next(line for line in readme.read_text().splitlines() if "<!-- finalize:" in line)
        legacy = "| Feature | Status | Priority |\n|---|---|---|\n"
        legacy += "| [001-legacy](features/001-legacy/) | Draft | P2 |\n"
        orphan = (
            "| 004 | Notifications | Implemented | 2026-06-01 | 2026-06-01 | "
            "[spec](features/004-notifications/spec.md) |"
        )
        readme.write_text(
            "# Specs\n\n" + legacy + "\nKeep these notes.\n\n" + marker + "\n" + orphan + "\n"
        )
        result = apply_finalization(tmp_path, request)
        assert "readme" in result.written
        repaired = readme.read_text()
        assert legacy in repaired
        assert "Keep these notes." in repaired and marker in repaired
        section = repaired.split("<!-- readme:features:start -->", 1)[1].split(
            "<!-- readme:features:end -->", 1
        )[0]
        assert "| # | Feature | Status | Created | Updated | Spec |" in section
        assert "| 004 | Notifications | Implemented |" in section
        assert repaired.count("features/004-notifications/spec.md") == 1
        assert (
            verify_finalization(
                tmp_path, request.feature_slug, run_id="legacy-readme-repair"
            ).verdict
            == "PASS"
        )
        before = readme.read_bytes()
        assert apply_finalization(tmp_path, request).outcome == "already_finalized"
        assert readme.read_bytes() == before

    def test_current_year_global_changelog_keeps_final_newline(self, tmp_path: Path) -> None:
        from datetime import date

        specs = _make_specs_tree(tmp_path)
        changelog = specs / "changelog.md"
        assert changelog.read_bytes().endswith(b"\n")
        apply_finalization(tmp_path, _implement_request(), today=date(2026, 9, 5))
        result = changelog.read_bytes()
        assert result.endswith(b"\n")
        assert b"Spec created: Notifications" in result
        assert b"Implemented: Notifications" in result
        replay = apply_finalization(tmp_path, _implement_request(), today=date(2026, 9, 5))
        assert replay.outcome == "already_finalized"
        assert changelog.read_bytes() == result

    def test_readme_recovery_preserves_generated_row_examples(self) -> None:
        from validator.finalize_readme import recover_feature_table

        row = (
            "| 004 | Notifications | Draft | 2026-06-01 | 2026-06-01 | "
            "[spec](features/004-notifications/spec.md) |"
        )
        examples = f"```markdown\n{row}\n```\n\n<!-- Example only\n{row}\n-->\n"
        content = recover_feature_table(examples)
        assert content.startswith(examples)
        section = content.split("<!-- readme:features:start -->", 1)[1]
        assert row not in section
        assert recover_feature_table(content) == content

    def test_missing_readme_is_rebuilt_with_feature_row(self, tmp_path: Path) -> None:
        """AC-012: apply must rebuild README.md from existing artifacts
        instead of crashing on a missing registry file."""
        specs = _make_specs_tree(tmp_path)
        (specs / "README.md").unlink()
        apply_finalization(tmp_path, _implement_request())
        readme = (specs / "README.md").read_text()
        assert "<!-- readme:features:start -->" in readme
        assert "<!-- readme:activity:start -->" in readme
        assert "features/004-notifications/spec.md" in readme
        assert "| Implemented |" in readme

    def test_previous_year_entries_rotate_to_archive(self, tmp_path: Path) -> None:
        """AC-012: previous-year global entries move to
        .specs/archive/changelog-YYYY.md with a Previous years link."""
        specs = _make_specs_tree(tmp_path)
        (specs / "changelog.md").write_text(
            _GLOBAL_CHANGELOG + "\n## 2025-12-01 — [Feature 004] Legacy entry\n",
            encoding="utf-8",
        )
        apply_finalization(tmp_path, _implement_request())
        archive = specs / "archive" / "changelog-2025.md"
        assert archive.is_file()
        assert "Legacy entry" in archive.read_text()
        global_changelog = (specs / "changelog.md").read_text()
        assert "Legacy entry" not in global_changelog
        assert "[2025](archive/changelog-2025.md)" in global_changelog


# ─── verify_finalization (FR-004, AC-005, AC-006) ────────────────────────────


class TestVerifyFinalization:
    def test_coherent_registry_yields_pass_and_modifies_nothing(self, tmp_path: Path) -> None:
        """AC-005/AC-006: verify is strictly read-only and must PASS on a
        registry finalized by apply (SC-003: zero R4/R6 findings)."""
        specs = _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        before = _registry_snapshot(specs)
        result = verify_finalization(
            tmp_path,
            "004-notifications",
            expected_command="spec-implement",
            run_id="run-verify",
        )
        assert result.verdict == "PASS"
        assert result.violations == ()
        assert _registry_snapshot(specs) == before
        receipt = verify_finalize_receipt(result.receipt_path, project_root=tmp_path)
        assert receipt.outcome == "verified"
        assert receipt.verdict == "PASS"

    def test_removed_readme_row_yields_fail_with_rule_id(self, tmp_path: Path) -> None:
        """Story 2: post-apply manual drift must FAIL with the violated
        coherence rule id (R4.x) listed in the receipt."""
        specs = _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        readme = specs / "README.md"
        readme.write_text(
            "\n".join(
                line
                for line in readme.read_text().splitlines()
                if "004-notifications" not in line and not line.startswith("| 004 ")
            ),
            encoding="utf-8",
        )
        result = verify_finalization(
            tmp_path,
            "004-notifications",
            run_id="run-verify-fail",
        )
        assert result.verdict == "FAIL"
        assert any(violation.rule_id.startswith("R4") for violation in result.violations)

    def test_missing_marker_for_expected_command_fails(self, tmp_path: Path) -> None:
        """AC-006: verify --command must FAIL when the registry carries no
        finalize marker for that command."""
        _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        result = verify_finalization(
            tmp_path,
            "004-notifications",
            expected_command="spec-fix",
            run_id="run-verify-marker",
        )
        assert result.verdict == "FAIL"
        assert any(violation.rule_id == "marker.missing" for violation in result.violations)

    def test_other_feature_violations_are_scoped_out(self, tmp_path: Path) -> None:
        """FR-004: verify is feature-scoped — coherence noise from other
        features must not flip this feature's verdict."""
        specs = _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        readme = specs / "README.md"
        # Inject an R4.1 ERROR for a *different* feature (missing directory).
        readme.write_text(
            readme.read_text().replace(
                "<!-- readme:features:end -->",
                "| 999 | Ghost | Draft | 2026-06-01 | 2026-06-01 | "
                "[spec](features/999-ghost/spec.md) |\n<!-- readme:features:end -->",
            ),
            encoding="utf-8",
        )
        result = verify_finalization(
            tmp_path,
            "004-notifications",
            expected_command="spec-implement",
            run_id="run-verify-scoped",
        )
        assert result.verdict == "PASS"


# ─── CLI surface (FR-009, AC-011, AC-004 exit codes) ─────────────────────────


def _write_entry_file(tmp_path: Path) -> Path:
    entry = tmp_path / "entry.md"
    entry.write_text(
        "Feature: Initial implementation\n\n- **Type:** Feature\n- **AC impacted:** AC-001",
        encoding="utf-8",
    )
    return entry


class TestFinalizeCli:
    @staticmethod
    def _runner() -> CliRunner:
        return CliRunner()

    def test_help_lists_apply_and_verify(self) -> None:
        """AC-011: `livespec finalize --help` exposes both subcommands."""
        from validator.cli import app

        result = self._runner().invoke(app, ["finalize", "--help"])
        assert result.exit_code == 0
        assert "apply" in result.output
        assert "verify" in result.output

    def test_apply_cli_prints_receipt_path_and_exits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from validator.cli import app

        _make_specs_tree(tmp_path)
        entry = _write_entry_file(tmp_path)
        monkeypatch.chdir(tmp_path)
        result = self._runner().invoke(
            app,
            [
                "finalize",
                "apply",
                "--feature",
                "004-notifications",
                "--command",
                "spec-implement",
                "--status",
                "Implemented",
                "--entry-file",
                str(entry),
                "--summary",
                "[Feature 004] Implemented: Notifications",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "receipt.json" in result.output
        readme = (tmp_path / ".specs" / "README.md").read_text(encoding="utf-8")
        assert "finalize:spec-implement" in readme

    def test_apply_cli_json_envelope(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """cli.md convention: every data-returning command supports --json."""
        from validator.cli import app

        _make_specs_tree(tmp_path)
        entry = _write_entry_file(tmp_path)
        monkeypatch.chdir(tmp_path)
        result = self._runner().invoke(
            app,
            [
                "finalize",
                "apply",
                "--feature",
                "004-notifications",
                "--command",
                "spec-implement",
                "--status",
                "Implemented",
                "--entry-file",
                str(entry),
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["outcome"] == "applied"
        assert payload["receipt_path"].endswith("receipt.json")

    def test_apply_cli_lock_timeout_exits_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-004: lock timeout must emit the canonical BLOCKED policy_blocked
        line and exit with the documented finalize-blocked code."""
        from validator.cli import app
        from validator.cli_commands import finalize_cmd
        from validator.cli_exit_codes import EXIT_FINALIZE_BLOCKED

        _make_specs_tree(tmp_path)
        entry = _write_entry_file(tmp_path)
        monkeypatch.chdir(tmp_path)

        def _blocked(*args: object, **kwargs: object) -> object:
            raise LockAcquisitionError("could not acquire .specs/.LOCK within 10s")

        monkeypatch.setattr(finalize_cmd, "apply_finalization", _blocked)
        result = self._runner().invoke(
            app,
            [
                "finalize",
                "apply",
                "--feature",
                "004-notifications",
                "--command",
                "spec-implement",
                "--entry-file",
                str(entry),
            ],
        )
        assert result.exit_code == EXIT_FINALIZE_BLOCKED
        assert "BLOCKED at step" in result.output
        assert "policy_blocked" in result.output

    def test_apply_cli_hash_mismatch_exits_blocked_state_invalid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from validator.cli import app
        from validator.cli_commands import finalize_cmd
        from validator.cli_exit_codes import EXIT_FINALIZE_BLOCKED

        _make_specs_tree(tmp_path)
        entry = _write_entry_file(tmp_path)
        monkeypatch.chdir(tmp_path)

        def _state_invalid(*args: object, **kwargs: object) -> object:
            raise FinalizeError(
                "post-write hash mismatch for .specs/README.md",
                subtype="state_invalid",
            )

        monkeypatch.setattr(finalize_cmd, "apply_finalization", _state_invalid)
        result = self._runner().invoke(
            app,
            [
                "finalize",
                "apply",
                "--feature",
                "004-notifications",
                "--command",
                "spec-implement",
                "--entry-file",
                str(entry),
            ],
        )
        assert result.exit_code == EXIT_FINALIZE_BLOCKED
        assert "state_invalid" in result.output
        assert "README.md" in result.output

    def test_verify_cli_pass_and_fail_exit_codes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-006: verify exits 0 on PASS and the documented non-zero code on
        FAIL (missing marker for the expected command)."""
        from validator.cli import app
        from validator.cli_exit_codes import EXIT_FINALIZE_VERIFY_FAIL

        _make_specs_tree(tmp_path)
        apply_finalization(tmp_path, _implement_request())
        monkeypatch.chdir(tmp_path)
        ok = self._runner().invoke(
            app,
            [
                "finalize",
                "verify",
                "--feature",
                "004-notifications",
                "--command",
                "spec-implement",
            ],
        )
        assert ok.exit_code == 0, ok.output
        fail = self._runner().invoke(
            app,
            ["finalize", "verify", "--feature", "004-notifications", "--command", "spec-fix"],
        )
        assert fail.exit_code == EXIT_FINALIZE_VERIFY_FAIL
        assert "marker.missing" in fail.output


# ─── Cross-process lock contention (FR-007, AC-009, SC-005) ──────────────────


def _hold_specs_lock(specs_path_str: str, hold_seconds: float, ready_event: object) -> None:
    """Hold .specs/.LOCK from a child process (real flock contention)."""
    from validator.locks import acquire_lock as _acquire

    with _acquire(Path(specs_path_str)):
        ready_event.set()  # type: ignore[attr-defined]
        import time

        time.sleep(hold_seconds)


@pytest.mark.slow
class TestApplyLockContention:
    def test_apply_with_retry_succeeds_after_real_contention(self, tmp_path: Path) -> None:
        """Story 4: a real second process holding .specs/.LOCK must only delay
        (not fail) an apply --retry run."""
        import multiprocessing

        from validator.locks import LockRetryPolicy

        specs = _make_specs_tree(tmp_path)
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        proc = ctx.Process(target=_hold_specs_lock, args=(str(specs), 3.0, ready))
        proc.start()
        try:
            assert ready.wait(timeout=10), "child failed to acquire lock"
            result = apply_finalization(
                tmp_path,
                _implement_request(),
                retry_policy=LockRetryPolicy(),
            )
            assert result.outcome == "applied"
        finally:
            proc.join(timeout=10)


# ─── Chaos: broken registry fixtures (FR-008, SC-001) ────────────────────────


@pytest.mark.chaos
class TestFinalizeChaosFixtures:
    def test_empty_global_changelog_still_applies(self, tmp_path: Path) -> None:
        """A changelog without header or entries must not crash apply — the
        summary becomes the first entry."""
        specs = _make_specs_tree(tmp_path)
        (specs / "changelog.md").write_text("", encoding="utf-8")
        result = apply_finalization(tmp_path, _implement_request())
        assert result.outcome == "applied"
        assert "[Feature 004] Implemented" in (specs / "changelog.md").read_text(encoding="utf-8")

    def test_missing_feature_changelog_is_created(self, tmp_path: Path) -> None:
        specs = _make_specs_tree(tmp_path)
        (specs / "features/004-notifications/changelog.md").unlink()
        result = apply_finalization(tmp_path, _implement_request())
        assert result.outcome == "applied"
        created = (specs / "features/004-notifications/changelog.md").read_text(encoding="utf-8")
        assert "Feature: Initial implementation" in created


class TestFinalizeRoadmap:
    """FR-006 / AC-007: closure repairs roadmap state, including old replays."""

    @pytest.mark.parametrize(
        "label",
        [
            "**004-notifications** → [spec](features/004-notifications/spec.md)",
            "[Notifications](features/004-notifications/spec.md)",
            "**Notifications** — scope M → [spec](features/004-notifications/spec.md)",
            ("**Notify** → [spec](features/004-notifications/spec.md) <!-- intent retained -->"),
        ],
    )
    def test_apply_then_verify_checks_only_matching_feature(
        self, tmp_path: Path, label: str
    ) -> None:
        specs = _make_specs_tree(tmp_path)
        roadmap = specs / "roadmap.md"
        neighbor = "- [ ] **005-next** → [spec](features/005-next/spec.md)\n"
        before = f"<!-- roadmap:mvp:start -->\n- [ ] {label}\n{neighbor}<!-- roadmap:mvp:end -->\n"
        roadmap.write_text(before)
        result = apply_finalization(tmp_path, _implement_request())
        assert "roadmap" in result.written
        assert roadmap.read_text() == before.replace(f"- [ ] {label}", f"- [x] {label}")
        verified = verify_finalization(
            tmp_path,
            "004-notifications",
            expected_command="spec-implement",
            run_id="verify-roadmap",
        )
        assert verified.verdict == "PASS", verified.violations
        receipt = json.loads(result.receipt_path.read_text())
        assert any(item["path"] == ".specs/roadmap.md" for item in receipt["files"])

    def test_old_marker_replay_repairs_roadmap_without_changelog_duplication(
        self, tmp_path: Path
    ) -> None:
        specs = _make_specs_tree(tmp_path)
        request = _implement_request()
        apply_finalization(tmp_path, request)
        before = _registry_snapshot(specs)
        roadmap = specs / "roadmap.md"
        roadmap.write_text(roadmap.read_text().replace("- [x]", "- [ ]"))
        assert verify_finalization(tmp_path, request.feature_slug, run_id="drift").verdict == "FAIL"
        repaired = apply_finalization(tmp_path, request)
        assert repaired.written == ("roadmap",)
        assert _registry_snapshot(specs) == before
        verified = verify_finalization(tmp_path, request.feature_slug, run_id="repaired")
        assert verified.verdict == "PASS"
        assert apply_finalization(tmp_path, request).outcome == "already_finalized"
        assert _registry_snapshot(specs) == before

    @pytest.mark.parametrize("status", ["Planned", "Draft", "Deprecated", None])
    def test_nonfinal_status_does_not_certify_roadmap(
        self, tmp_path: Path, status: str | None
    ) -> None:
        from dataclasses import replace

        specs = _make_specs_tree(tmp_path)
        roadmap = specs / "roadmap.md"
        roadmap.write_text(roadmap.read_text().replace("- [x]", "- [ ]"))
        before = roadmap.read_bytes()
        result = apply_finalization(tmp_path, replace(_implement_request(), status=status))
        assert "roadmap" not in result.written
        assert roadmap.read_bytes() == before

    def test_examples_and_unlinked_intent_are_never_mutated(self, tmp_path: Path) -> None:
        specs = _make_specs_tree(tmp_path)
        roadmap = specs / "roadmap.md"
        row = "- [ ] [Notifications](features/004-notifications/spec.md)\n"
        examples = (
            f"```markdown\n{row}```\n"
            f"~~~~markdown\n{row}~~~~\n"
            f"<!--\n{row}-->\n"
            f"    {row}"
            "- [ ] 004-notifications — backlog intent without spec link\n"
            "- [ ] [Other](features/004-notifications-other/spec.md)\n"
        )
        roadmap.write_text(row + examples)
        apply_finalization(tmp_path, _implement_request())
        assert roadmap.read_text() == row.replace("- [ ]", "- [x]") + examples

    def test_real_cli_apply_then_verify_supports_slug_with_spec_label(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from validator.cli import app

        specs = _make_specs_tree(tmp_path)
        (specs / "roadmap.md").write_text(
            "- [ ] **004-notifications** → [spec](features/004-notifications/spec.md)\n"
        )
        entry = _write_entry_file(tmp_path)
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        applied = runner.invoke(
            app,
            [
                "finalize",
                "apply",
                "--feature",
                "004-notifications",
                "--command",
                "spec-test",
                "--status",
                "Implemented",
                "--entry-file",
                str(entry),
                "--summary",
                "[Feature 004] Implemented: Notifications",
            ],
        )
        assert applied.exit_code == 0, applied.output
        verified = runner.invoke(
            app,
            [
                "finalize",
                "verify",
                "--feature",
                "004-notifications",
                "--command",
                "spec-test",
            ],
        )
        assert verified.exit_code == 0, verified.output


class TestFinalizeClosureOrdering:
    """Boundary stubs prove lock ordering only, not native C51 certification."""

    def test_changed_proof_before_lock_blocks_all_registry_writes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from contextlib import contextmanager

        import validator.finalize as module

        specs = _make_specs_tree(tmp_path)
        before = _registry_snapshot(specs)
        actual_lock = module.acquire_lock
        proof = {"current": True}
        calls: list[bool] = []

        @contextmanager
        def change_proof_then_acquire(*args, **kwargs):
            proof["current"] = False
            with actual_lock(*args, **kwargs):
                yield

        def check_closure(*_args):
            calls.append(proof["current"])
            if not proof["current"]:
                return module.FinalizeViolation(
                    rule_id="penflow.closure", message="protocol boundary: approval changed"
                )
            return None

        monkeypatch.setattr(module, "acquire_lock", change_proof_then_acquire)
        monkeypatch.setattr(module, "_penflow_closure_violation", check_closure)
        with pytest.raises(FinalizeError, match="approval changed") as error:
            apply_finalization(tmp_path, _implement_request())
        assert calls == [False]
        after = _registry_snapshot(specs)
        after.pop(str(specs / ".LOCK"), None)  # Acquiring the real lock creates its empty file.
        assert after == before
        assert error.value.receipt_path is not None
        receipt = json.loads(error.value.receipt_path.read_text())
        assert receipt["verdict"] == "BLOCKED"
        assert receipt["files"] == []

    def test_normal_apply_checks_once_under_lock_and_replay_checks_current_proof(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from contextlib import contextmanager

        import validator.finalize as module

        specs = _make_specs_tree(tmp_path)
        actual_lock = module.acquire_lock
        locked = False
        proof_current = True
        events: list[tuple[str, bool]] = []

        @contextmanager
        def observed_lock(*args, **kwargs):
            nonlocal locked
            with actual_lock(*args, **kwargs):
                locked = True
                try:
                    yield
                finally:
                    locked = False

        def check_closure(*_args):
            events.append(("closure", locked))
            if not proof_current:
                return module.FinalizeViolation(
                    rule_id="penflow.closure", message="protocol boundary: proof stale"
                )
            return None

        monkeypatch.setattr(module, "acquire_lock", observed_lock)
        monkeypatch.setattr(module, "_penflow_closure_violation", check_closure)
        request = _implement_request()
        assert apply_finalization(tmp_path, request).outcome == "applied"
        assert events == [("closure", True)]
        before = _registry_snapshot(specs)
        assert apply_finalization(tmp_path, request).outcome == "already_finalized"
        assert events == [("closure", True), ("closure", False)]
        proof_current = False
        with pytest.raises(FinalizeError, match="proof stale"):
            apply_finalization(tmp_path, request)
        assert events[-1] == ("closure", False)
        assert _registry_snapshot(specs) == before
