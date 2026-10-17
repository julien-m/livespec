"""Compile Cargo proxy identities without running a compiler or inventing receipts."""

from pathlib import Path

from validator.evidence_applicability import _command_key


def test_cargo_command_identity_preserves_distinct_proxy_paths(tmp_path: Path) -> None:
    """Two executable proxies with identical arguments remain distinct declarations."""
    keys = []
    for name in ("first", "second"):
        proxy = tmp_path / name / "cargo"
        proxy.parent.mkdir()
        proxy.write_text("#!/bin/sh\nexit 1\n")
        proxy.chmod(0o755)
        keys.append(_command_key(tmp_path, [str(proxy), "test", "--", "selected"], tmp_path))
    assert keys[0] != keys[1] and all(key[-2:] == ["--", "selected"] for key in keys)
