# LiveSpec traceability anchors
# @spec(AC-007)

"""Report rendering for the verify-output engine.

Private helper module for :mod:`validator.verify_output` (rendering split out
to honor the 300-line constitution cap, as anticipated by the 039.1 plan).
The public API is re-exported from ``validator.verify_output``; import from
there, not from here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .outcome import exit_code_for

if TYPE_CHECKING:
    # Imported for typing only: verify_output imports this module at runtime,
    # so a runtime import here would be circular.
    from .verify_output import VerifyReport


def render_report(
    report: VerifyReport,
    *,
    command: str,
    artifact_path: Path | None,
    source: str | None = None,
) -> str:
    """Render the human-readable rule table (040 Section 13 demo format).

    Args:
        report: Engine output to render.
        command: Verified command name.
        artifact_path: Run artifact path, or None in preview-like contexts.
        source: Optional expectations source path shown in the header.

    Returns:
        Multi-line report text ending with the outcome and exit code footer.
    """
    lines = [f"verify-output  command={command}"]
    if source:
        lines.append(f"source         {source}")
    if artifact_path is not None:
        lines.append(f"artifact       {artifact_path.as_posix()}")
    lines.append("")
    lines.append(f"{'verb':<9} {'kind':<21} {'status':<9} detail")
    lines.append("-" * 80)
    for rule in report.rules:
        lines.append(f"{rule.verb:<9} {rule.kind:<21} {rule.status:<9} {rule.detail}")
    lines.append("")
    lines.append(f"outcome   {report.outcome}")
    lines.append(f"exit_code {exit_code_for(report.outcome)}")
    return "\n".join(lines)


def to_json_envelope(
    report: VerifyReport,
    *,
    command: str,
    artifact_path: Path | None,
) -> dict[str, Any]:
    """Return the machine-readable envelope emitted under ``--json``."""
    return {
        "command": command,
        "artifact": artifact_path.as_posix() if artifact_path is not None else None,
        "outcome": report.outcome,
        "exit_code": exit_code_for(report.outcome),
        "rules": [rule.to_dict() for rule in report.rules],
    }


__all__ = ["render_report", "to_json_envelope"]
