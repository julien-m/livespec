"""Read-only current profile and generated-content verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .init_profile import InitError, ObservedProfile, detect_profile
from .init_recovery import guard_path, observed_adr_path, validate_destinations, verify_registry

MANIFEST = ".specs/bootstrap-profile.json"


def render_manifest(profile: ObservedProfile, documents: dict[str, str]) -> str:
    """Record current observed inputs and every owned document content identity."""
    content = {
        "schema_version": 1,
        "profile": asdict(profile),
        "documents": {
            path: hashlib.sha256(text.encode()).hexdigest() for path, text in documents.items()
        },
    }
    return json.dumps(content, indent=2, sort_keys=True) + "\n"


# @spec FR-002: Read-only current artifact verification
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-002
def verify_current_profile(project: Path) -> ObservedProfile:
    """Re-detect source identities and verify owned contents without writing anything.

    Args:
        project: Selected initialized project directory.
    Returns:
        Current profile only when observed inputs and artifact bytes agree.
    Raises:
        InitError: Missing, malformed, escaping or changed evidence/artifacts.
    """
    root = project.resolve()
    validate_destinations(root)
    profile = detect_profile(root)
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise InitError(f"{MANIFEST}: missing or malformed current profile: {error}") from error
    current = json.loads(json.dumps(asdict(profile)))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("profile") != current
    ):
        raise InitError(f"{MANIFEST}: current source/profile identity drift")
    documents = manifest.get("documents")
    if not isinstance(documents, dict) or not documents:
        raise InitError(f"{MANIFEST}: document identities missing")
    for relative, expected in documents.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise InitError(f"{MANIFEST}: invalid document identity")
        path = root / relative
        guard_path(root, path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise InitError(f"{relative}: generated content drift")
    verify_registry((root / ".specs/README.md").read_text(encoding="utf-8"), profile)
    if not (root / ".specs" / observed_adr_path(profile)).is_file():
        raise InitError("README registry: observed stack ADR artifact missing")
    recap = (root / ".specs/bootstrap-recap.md").read_text(encoding="utf-8")
    if not recap.startswith("---\nstatus: completed\n"):
        raise InitError("bootstrap-recap.md: backend completion missing")
    return profile
