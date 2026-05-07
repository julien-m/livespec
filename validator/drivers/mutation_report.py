"""On-demand mutation testing audit and report writer.

This module supports feature 025 (mutation-testing-on-demand). It does *not*
participate in per-PR CI — the orchestration entry point ``run_mutation`` is
only invoked when the user runs ``/spec.test --mutation`` explicitly.

The module wires the per-driver mutation parsers shipped with features 017
(mutmut), 018 (Stryker), 021 (cargo-mutants), 022 (pitest), and 019 (muter)
into a single ``MutationResult`` shape and renders a human-readable historical
log to ``.specs/testing/mutation-report.md``.
"""

# Spec anchors: feature 025-mutation-testing-on-demand
# @spec FR-001: --mutation flag invokes the active driver's mutation capability.
# @spec FR-002: write_mutation_report.
# @spec FR-003: MutationResult dataclass.
# @spec FR-004: SurvivorRef dataclass.

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from .jvm_detector import parse_pitest_xml
from .mutmut_parser import (
    MutmutParseResult,
    SurvivingMutant,
    parse_mutmut_results,
)
from .runner import run_capability
from .rust_detector import parse_cargo_mutants_json
from .schemas import (
    CapabilityResult,
    DriverManifest,
)
from .stryker_parser import StrykerParseResult, load_stryker_report

_DEFAULT_REPORT_PATH = Path(".specs/testing/mutation-report.md")
_MAX_SURVIVORS_DEFAULT = 20

# Best-effort regex parser for muter (Swift) — muter prints a textual summary
# such as ``Mutation score: 73.0 (killed 73, survived 27, timeout 0)``.
_SWIFT_KILLED_RE = re.compile(r"killed[^\d]*(\d+)", re.IGNORECASE)
_SWIFT_SURVIVED_RE = re.compile(r"survived[^\d]*(\d+)", re.IGNORECASE)
_SWIFT_TIMEOUT_RE = re.compile(r"timed?\s*out[^\d]*(\d+)", re.IGNORECASE)


# ----------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class SurvivorRef:
    """A surviving mutant reference for the historical mutation report.

    Attributes:
        file: Source file path (project-relative when the parser provides it).
        line: 1-indexed source line number where the mutant was applied.
        description: Optional free-form description of the mutation.
    """

    file: str
    line: int
    description: str = ""


@dataclass(frozen=True)
class MutationResult:
    """Normalised result of one mutation run.

    Attributes:
        date: ISO 8601 date string (``YYYY-MM-DD``) for when the run completed.
        driver: Driver name that produced the result (``python``, ``rust``, ...).
        kill_rate: Mutation kill rate as a percentage in ``[0, 100]``.
        killed: Number of killed mutants.
        survived: Number of surviving mutants.
        timeout: Number of mutants that triggered a timeout.
        no_coverage: Stryker-specific count of mutants in non-covered code.
        survivors: List of surviving mutant references (may be truncated by the
            renderer for readability).
        note: Optional free-form note (used by edge cases like timeouts or
            "tool not installed").
        gate_failed: True when a configured threshold was set and ``kill_rate``
            fell below it.
        threshold: Threshold value that produced ``gate_failed`` (if any).
    """

    date: str
    driver: str
    kill_rate: float
    killed: int
    survived: int
    timeout: int
    no_coverage: int = 0
    survivors: list[SurvivorRef] = field(default_factory=list[SurvivorRef])
    note: str = ""
    gate_failed: bool = False
    threshold: float | None = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _today(today: str | None) -> str:
    """Return ``today`` if provided, else the current ISO 8601 date."""
    if today is not None:
        return today
    return _dt.date.today().isoformat()


def _compute_kill_rate(killed: int, survived: int, timeout: int) -> float:
    """Compute the kill rate over killed+survived+timeout mutants.

    Timeouts are counted as kills (they imply the test suite detected the
    mutation by hanging on it). The rate is in the closed range ``[0, 100]``.
    """
    total = killed + survived + timeout
    if total == 0:
        return 0.0
    return ((killed + timeout) / total) * 100.0


def _to_survivor_refs(raw: list[SurvivingMutant]) -> list[SurvivorRef]:
    """Convert mutmut's typed-dict survivors into ``SurvivorRef`` instances."""
    out: list[SurvivorRef] = []
    for entry in raw:
        out.append(
            SurvivorRef(
                file=entry["file"],
                line=int(entry["line"]),
                description=entry["description"],
            )
        )
    return out


# ----------------------------------------------------------------------
# Per-driver normalisers
# ----------------------------------------------------------------------


def normalise_mutmut(
    parsed: MutmutParseResult,
    *,
    driver: str = "python",
    today: str | None = None,
) -> MutationResult:
    """Normalise a mutmut parse result into a ``MutationResult``."""
    return MutationResult(
        date=_today(today),
        driver=driver,
        kill_rate=float(parsed.get("score", 0.0)),
        killed=int(parsed.get("killed", 0)),
        survived=int(parsed.get("survived", 0)),
        timeout=int(parsed.get("timeout", 0)),
        survivors=_to_survivor_refs(list(parsed.get("survivors", []))),
    )


def normalise_stryker(
    parsed: StrykerParseResult,
    *,
    driver: str = "typescript",
    today: str | None = None,
    survivors: list[SurvivorRef] | None = None,
) -> MutationResult:
    """Normalise a Stryker parse result into a ``MutationResult``."""
    return MutationResult(
        date=_today(today),
        driver=driver,
        kill_rate=float(parsed.get("kill_rate", 0.0)),
        killed=int(parsed.get("killed", 0)),
        survived=int(parsed.get("survived", 0)),
        timeout=int(parsed.get("timeout", 0)),
        no_coverage=int(parsed.get("no_coverage", 0)),
        survivors=list(survivors or []),
    )


def normalise_pitest(
    counts: dict[str, int],
    *,
    driver: str = "jvm",
    survivors: list[SurvivorRef] | None = None,
    today: str | None = None,
) -> MutationResult:
    """Normalise pitest mutation counts into a ``MutationResult``.

    pitest groups its statuses as KILLED, SURVIVED, TIMED_OUT, NO_COVERAGE,
    MEMORY_ERROR, RUN_ERROR. Memory and run errors are counted as kills (the
    suite reproduced an unstable behaviour) — consistent with the kill-rate
    semantics used by Stryker.
    """
    killed = int(counts.get("killed", 0)) + int(counts.get("memory_error", 0)) + int(
        counts.get("run_error", 0)
    )
    survived = int(counts.get("survived", 0))
    timeout = int(counts.get("timed_out", 0))
    no_coverage = int(counts.get("no_coverage", 0))
    return MutationResult(
        date=_today(today),
        driver=driver,
        kill_rate=_compute_kill_rate(killed, survived, timeout),
        killed=killed,
        survived=survived,
        timeout=timeout,
        no_coverage=no_coverage,
        survivors=list(survivors or []),
    )


def normalise_cargo_mutants(
    counts: dict[str, int],
    *,
    driver: str = "rust",
    survivors: list[SurvivorRef] | None = None,
    today: str | None = None,
) -> MutationResult:
    """Normalise cargo-mutants outcome counts into a ``MutationResult``.

    cargo-mutants emits ``caught`` (killed), ``missed`` (survived), ``timeout``
    and ``unviable``. Unviable mutants did not compile and are excluded from
    the kill-rate denominator (consistent with cargo-mutants' own scoring).
    """
    killed = int(counts.get("caught", 0))
    survived = int(counts.get("missed", 0))
    timeout = int(counts.get("timeout", 0))
    return MutationResult(
        date=_today(today),
        driver=driver,
        kill_rate=_compute_kill_rate(killed, survived, timeout),
        killed=killed,
        survived=survived,
        timeout=timeout,
        survivors=list(survivors or []),
    )


def normalise_muter(
    stdout: str,
    *,
    driver: str = "swift",
    today: str | None = None,
) -> MutationResult:
    """Best-effort parse of muter (Swift) stdout into a ``MutationResult``."""

    def _first_int(pattern: re.Pattern[str]) -> int:
        match = pattern.search(stdout or "")
        if match is None:
            return 0
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return 0

    killed = _first_int(_SWIFT_KILLED_RE)
    survived = _first_int(_SWIFT_SURVIVED_RE)
    timeout = _first_int(_SWIFT_TIMEOUT_RE)
    return MutationResult(
        date=_today(today),
        driver=driver,
        kill_rate=_compute_kill_rate(killed, survived, timeout),
        killed=killed,
        survived=survived,
        timeout=timeout,
    )


# ----------------------------------------------------------------------
# Report rendering / writing
# ----------------------------------------------------------------------


def render_report_entry(
    result: MutationResult,
    *,
    max_survivors: int = _MAX_SURVIVORS_DEFAULT,
) -> str:
    """Render a single mutation run entry as a Markdown section.

    The first line is a ``## YYYY-MM-DD — <driver>`` heading so that
    ``write_mutation_report`` can split the file on this marker when prepending
    new entries (AC-004).

    Survivor lists exceeding ``max_survivors`` are truncated and a "more
    survivors" note is appended (EC-002).
    """
    lines: list[str] = []
    lines.append(f"## {result.date} — {result.driver}")
    lines.append("")
    lines.append(f"- Driver: {result.driver}")
    lines.append(f"- Kill rate: {result.kill_rate:.1f} %")
    lines.append(f"- Killed: {result.killed}")
    lines.append(f"- Survived: {result.survived}")
    lines.append(f"- Timeout: {result.timeout}")
    if result.no_coverage:
        lines.append(f"- No coverage: {result.no_coverage}")
    if result.threshold is not None:
        gate = "FAIL" if result.gate_failed else "PASS"
        lines.append(f"- Threshold: {result.threshold:.1f} % ({gate})")
    if result.note:
        lines.append(f"- Note: {result.note}")

    survivors = result.survivors
    if survivors:
        shown = list(survivors[:max_survivors])
        lines.append("")
        lines.append(
            f"- Survivors (showing {len(shown)} of {len(survivors)}):"
        )
        for surv in shown:
            descr = f" — {surv.description}" if surv.description else ""
            lines.append(f"  - `{surv.file}:{surv.line}`{descr}")
        if len(survivors) > max_survivors:
            extra = len(survivors) - max_survivors
            lines.append(
                f"  - … {extra} more survivors — run tool directly for full list"
            )
    else:
        lines.append("")
        lines.append("- Survivors: 0")

    lines.append("")
    return "\n".join(lines)


def _split_existing_entries(text: str) -> tuple[str, str]:
    """Return ``(header, entries)`` from the existing report file content.

    The header is the prefix preceding the first ``## `` heading. The entries
    are the rest of the file (newest first, by convention). When no entries
    exist, the returned ``entries`` string is empty.
    """
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("## "):
            header = "".join(lines[:index])
            body = "".join(lines[index:])
            return header, body
    return text, ""


def _default_header(project_name: str) -> str:
    """Build the default report header used when the file is created."""
    return (
        f"# Mutation Report — {project_name}\n"
        "\n"
        "<!-- Auto-generated by /spec.test --mutation. Newest entry first. -->\n"
        "\n"
    )


def write_mutation_report(
    result: MutationResult,
    report_path: Path = _DEFAULT_REPORT_PATH,
    *,
    project_name: str | None = None,
    max_survivors: int = _MAX_SURVIVORS_DEFAULT,
) -> Path:
    """Create or prepend a mutation run entry to the historical report.

    Args:
        result: Mutation run result to append.
        report_path: Target Markdown file (defaults to
            ``.specs/testing/mutation-report.md``).
        project_name: Title used in the file header when the file is being
            created. Defaults to the ``report_path`` parent's parent directory
            name (i.e. the project root) which is good enough for a v1.
        max_survivors: Maximum number of survivors rendered per entry.

    Returns:
        The resolved ``report_path``.
    """
    # EC-003 — create the parent directory if missing.
    report_path.parent.mkdir(parents=True, exist_ok=True)

    new_entry = render_report_entry(result, max_survivors=max_survivors)

    if report_path.exists():
        existing = report_path.read_text(encoding="utf-8")
        header, prior_entries = _split_existing_entries(existing)
        if not header.strip():
            header = _default_header(project_name or report_path.parent.name)
        body = new_entry + ("\n" + prior_entries if prior_entries else "")
        report_path.write_text(header + body, encoding="utf-8")
    else:
        header = _default_header(project_name or report_path.parent.name)
        report_path.write_text(header + new_entry, encoding="utf-8")

    return report_path


# ----------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------


def _apply_threshold(result: MutationResult, threshold: float | None) -> MutationResult:
    """Return ``result`` with ``threshold`` and ``gate_failed`` populated."""
    if threshold is None:
        return result
    return replace(
        result,
        threshold=float(threshold),
        gate_failed=result.kill_rate < float(threshold),
    )


def _dispatch_parser(
    driver: DriverManifest, capability_result: CapabilityResult
) -> MutationResult:
    """Dispatch the capability output to the matching per-driver parser.

    Args:
        driver: The active driver manifest.
        capability_result: The raw subprocess result from ``run_capability``.

    Returns:
        A normalised :class:`MutationResult`.
    """
    name = driver.name.lower()
    stdout = capability_result.stdout or ""

    if name == "python":
        # mutmut's structured payload is parsed from stdout; we keep that
        # contract from feature 017 (the parser falls back to running mutmut
        # again when the input is empty, which is the expected behaviour).
        parsed = parse_mutmut_results(stdout if stdout else None)
        return normalise_mutmut(parsed)

    if name in {"typescript", "javascript"}:
        # Stryker writes its JSON report next to the project root by default.
        report_path = (
            Path(capability_result.report_path)
            if capability_result.report_path
            else Path("reports/mutation/mutation.json")
        )
        parsed = load_stryker_report(report_path)
        return normalise_stryker(parsed, driver=name)

    if name == "jvm":
        counts = parse_pitest_xml(stdout)
        return normalise_pitest(counts)

    if name == "rust":
        counts = parse_cargo_mutants_json(stdout)
        return normalise_cargo_mutants(counts)

    if name == "swift":
        return normalise_muter(stdout)

    # Fallback: unknown driver — surface what we have without parsing.
    return MutationResult(
        date=_today(None),
        driver=driver.name,
        kill_rate=0.0,
        killed=0,
        survived=0,
        timeout=0,
        note=f"no parser for driver '{driver.name}' — capability ran but output not interpreted",
    )


def run_mutation(
    driver: DriverManifest,
    *,
    project_root: Path | None = None,
    report_path: Path | None = _DEFAULT_REPORT_PATH,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> MutationResult | None:
    """Run the active driver's mutation capability on demand.

    Returns ``None`` when the driver does not declare a ``mutation`` capability
    (Story 1, Scenario 2 — the caller is expected to print the canonical
    "not implemented" message and exit 0). When the capability ran, the result
    is parsed via the matching per-driver parser, optional threshold gating
    is applied, and a Markdown report is appended to ``report_path``.

    Args:
        driver: Resolved driver manifest for the active stack.
        project_root: Working directory for the subprocess invocation.
        report_path: Target Markdown report. Pass ``None`` to skip writing.
        timeout: Subprocess timeout passed through to ``run_capability``.
        env: Environment overrides forwarded to ``run_capability``.

    Returns:
        The normalised :class:`MutationResult`, or ``None`` when the active
        driver has no ``mutation`` capability.
    """
    if driver.get_capability("mutation") is None:
        return None

    capability_result = run_capability(
        driver,
        "mutation",
        project_root=project_root,
        env=env,
        timeout=timeout,
    )

    if capability_result.exit_code == 127:
        # AC-007 — tool not installed: emit an install hint and exit 0.
        return MutationResult(
            date=_today(None),
            driver=driver.name,
            kill_rate=0.0,
            killed=0,
            survived=0,
            timeout=0,
            note=(
                "tool not installed — install the mutation tool for this stack "
                f"({_install_hint(driver.name)})"
            ),
        )

    result = _dispatch_parser(driver, capability_result)

    threshold = driver.mutation.threshold if driver.mutation else None
    result = _apply_threshold(result, threshold)

    if report_path is not None:
        write_mutation_report(result, report_path)

    return result


def _install_hint(driver_name: str) -> str:
    """Return a human-readable install hint for the named driver."""
    hints: dict[str, str] = {
        "python": "pip install mutmut",
        "typescript": "npm install --save-dev @stryker-mutator/core",
        "javascript": "npm install --save-dev @stryker-mutator/core",
        "rust": "cargo install cargo-mutants",
        "jvm": "add the pitest plugin to your build (Gradle/Maven)",
        "swift": "brew install muter-mutation-testing/formulae/muter",
    }
    return hints.get(driver_name.lower(), "see the tool's documentation")


def alternative_for(driver_name: str) -> str:
    """Return a short alternative-capability suggestion for "not implemented".

    Used when the active driver has no ``mutation`` capability — Story 1
    Scenario 2 expects a hint pointing at a nearby technique.
    """
    suggestions: dict[str, str] = {
        "go": "Consider gopter (property-based testing) as a richer alternative",
    }
    return suggestions.get(
        driver_name.lower(),
        "Consider property-based testing as a complementary safety net",
    )


# Public surface -------------------------------------------------------

__all__ = [
    "MutationResult",
    "SurvivorRef",
    "alternative_for",
    "mutation_result_to_dict",
    "normalise_cargo_mutants",
    "normalise_muter",
    "normalise_mutmut",
    "normalise_pitest",
    "normalise_stryker",
    "render_report_entry",
    "run_mutation",
    "write_mutation_report",
]


# Public helper kept at module scope so callers can serialise results.
def mutation_result_to_dict(result: MutationResult) -> dict[str, object]:
    """Render a ``MutationResult`` as a serialisable dict."""
    return {
        "date": result.date,
        "driver": result.driver,
        "kill_rate": result.kill_rate,
        "killed": result.killed,
        "survived": result.survived,
        "timeout": result.timeout,
        "no_coverage": result.no_coverage,
        "survivors": [
            {"file": s.file, "line": s.line, "description": s.description}
            for s in result.survivors
        ],
        "note": result.note,
        "gate_failed": result.gate_failed,
        "threshold": result.threshold,
    }
