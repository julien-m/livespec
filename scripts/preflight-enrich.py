#!/usr/bin/env python3
"""Enrich `.specs/preflight.md` with detected driver and runner entries.

The migration scans the project for active drivers/UI runners and
appends matching preflight entries between LiveSpec section markers
(``<!-- preflight:livespec:start -->`` ... ``<!-- preflight:livespec:end -->``).
User-authored content outside the markers is preserved verbatim.

Idempotent: re-running produces no diff once the markers contain the
expected block. Custom user entries (between
``<!-- preflight:custom:start -->`` and ``<!-- preflight:custom:end -->``)
are never touched.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

LIVESPEC_START: Final[str] = "<!-- preflight:livespec:start -->"
LIVESPEC_END: Final[str] = "<!-- preflight:livespec:end -->"
LIVESPEC_SECTION_HEADING: Final[str] = "## LiveSpec-Managed (auto-generated)"

# Per-driver / per-runner preflight blocks. Sourced from features 016-033.
DRIVER_BLOCKS: dict[str, str] = {
    "python": """### python (driver)
- **binary:** `python3`
- **verify:** `python3 --version`
- **install:** `brew install python`
- **severity:** critical
- **source:** stack (driver: python)
""",
    "swift": """### swift (driver)
- **binary:** `swift`
- **verify:** `swift --version`
- **install:** human
- **severity:** critical
- **source:** stack (driver: swift)
""",
    "kotlin": """### kotlin (driver)
- **binary:** `kotlinc`
- **verify:** `kotlinc -version`
- **install:** `brew install kotlin`
- **severity:** critical
- **source:** stack (driver: kotlin)
""",
    "rust": """### rust (driver)
- **binary:** `cargo`
- **verify:** `cargo --version`
- **install:** `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **severity:** critical
- **source:** stack (driver: rust)
""",
    "go": """### go (driver)
- **binary:** `go`
- **verify:** `go version`
- **install:** `brew install go`
- **severity:** critical
- **source:** stack (driver: go)
""",
    "node": """### node (driver)
- **binary:** `node`
- **verify:** `node --version`
- **install:** `brew install node`
- **severity:** critical
- **source:** stack (driver: node)
""",
}

RUNNER_BLOCKS: dict[str, str] = {
    "ios": """### iOS Simulator runner
- **binary:** `xcrun`
- **verify:** `xcrun simctl list devices iPhone | grep -q '.'`
- **install:** human
- **severity:** critical
- **source:** stack (runner: ios)
""",
    "android": """### Android AVD runner
- **binary:** `avdmanager`
- **verify:** `avdmanager list avd | grep -q 'Name:'`
- **install:** human
- **severity:** critical
- **source:** stack (runner: android)
""",
    "tauri": """### tauri-driver
- **binary:** `tauri-driver`
- **verify:** `tauri-driver --version`
- **install:** `cargo install tauri-driver`
- **severity:** critical
- **source:** stack (runner: tauri)
""",
    "web": """### Playwright browsers
- **binary:** `npx`
- **verify:** `npx playwright --version`
- **install:** `npx playwright install`
- **severity:** warning
- **source:** stack (runner: web)
""",
}


def detect_drivers(project: Path) -> set[str]:
    """Detect active drivers from project files and explicit driver specs.

    Args:
        project: Project root to inspect.

    Returns:
        The set of detected driver identifiers.
    """

    found: set[str] = set()
    drivers_dir = project / ".specs" / "drivers"
    if drivers_dir.is_dir():
        for driver_spec in drivers_dir.glob("*.yaml"):
            found.add(driver_spec.stem)
        for driver_spec in drivers_dir.glob("*.yml"):
            found.add(driver_spec.stem)
    # Heuristic filesystem probes backfill built-in drivers when the project
    # has not declared them explicitly in `.specs/drivers/` yet.
    if (project / "pyproject.toml").exists():
        found.add("python")
    if (project / "Cargo.toml").exists():
        found.add("rust")
    if (project / "go.mod").exists():
        found.add("go")
    if (project / "package.json").exists():
        found.add("node")
    if any(project.glob("**/Package.swift")):
        found.add("swift")
    if any(project.glob("**/build.gradle*")):
        found.add("kotlin")
    return found


def detect_runners(project: Path) -> set[str]:
    """Detect active runners from project files and explicit runner specs.

    Args:
        project: Project root to inspect.

    Returns:
        The set of detected runner identifiers.
    """

    found: set[str] = set()
    runners_dir = project / ".specs" / "runners"
    if runners_dir.is_dir():
        for runner_spec in runners_dir.glob("*.yaml"):
            found.add(runner_spec.stem)
        for runner_spec in runners_dir.glob("*.yml"):
            found.add(runner_spec.stem)
    if any(project.glob("**/*.xcodeproj")):
        found.add("ios")
    if (project / "android").is_dir() or any(project.glob("**/AndroidManifest.xml")):
        found.add("android")
    if (project / "src-tauri").is_dir():
        found.add("tauri")
    if (project / "playwright.config.ts").exists() or (project / "playwright.config.js").exists():
        found.add("web")
    return found


def build_block(drivers: set[str], runners: set[str]) -> str:
    """Build the generated manifest block for detected drivers and runners.

    Args:
        drivers: Detected driver identifiers.
        runners: Detected runner identifiers.

    Returns:
        The rendered markdown block inserted between LiveSpec markers.
    """

    parts: list[str] = []
    for driver_name in sorted(drivers):
        if driver_name in DRIVER_BLOCKS:
            parts.append(DRIVER_BLOCKS[driver_name])
    for runner_name in sorted(runners):
        if runner_name in RUNNER_BLOCKS:
            parts.append(RUNNER_BLOCKS[runner_name])
    return "\n".join(parts).strip() + ("\n" if parts else "")


def enrich(text: str, block: str) -> str:
    """Insert or replace the LiveSpec-managed block in the manifest.

    Args:
        text: Existing manifest contents.
        block: Generated LiveSpec-managed markdown block.

    Returns:
        The updated manifest contents.
    """

    if not block.strip():
        return text

    section = f"\n{LIVESPEC_SECTION_HEADING}\n\n{LIVESPEC_START}\n{block}{LIVESPEC_END}\n"

    if LIVESPEC_START in text and LIVESPEC_END in text:
        # Replace only the managed slice so user-authored content outside the
        # markers survives regeneration byte-for-byte.
        return re.sub(
            re.escape(LIVESPEC_START) + r".*?" + re.escape(LIVESPEC_END),
            f"{LIVESPEC_START}\n{block}{LIVESPEC_END}",
            text,
            flags=re.DOTALL,
        )

    # No markers yet - append the section.
    if not text.endswith("\n"):
        text += "\n"
    return text + section


def run(project: Path) -> int:
    """Update the preflight manifest for one project.

    Args:
        project: Project root that owns `.specs/preflight.md`.

    Returns:
        Process exit code for the migration helper.
    """

    manifest = project / ".specs" / "preflight.md"
    if not manifest.exists():
        print(f"  WARN preflight.md not found at {manifest}; skipping", file=sys.stderr)
        return 0

    drivers = detect_drivers(project)
    runners = detect_runners(project)
    block = build_block(drivers, runners)

    original = manifest.read_text(encoding="utf-8")
    updated = enrich(original, block)

    if updated == original:
        print("  OK preflight.md already up to date")
        return 0

    manifest.write_text(updated, encoding="utf-8")
    added = sum(1 for driver_name in drivers if driver_name in DRIVER_BLOCKS)
    added += sum(1 for runner_name in runners if runner_name in RUNNER_BLOCKS)
    print(f"  OK enriched preflight.md ({added} entries)")
    return 0


def main(argv: list[str]) -> int:
    """Parse CLI arguments and run the migration helper.

    Args:
        argv: Raw command-line arguments, including the program name.

    Returns:
        Process exit code for the helper invocation.
    """

    if len(argv) < 2:
        print("Usage: preflight-enrich.py <project-dir>", file=sys.stderr)
        return 2
    project = Path(argv[1]).resolve()
    return run(project)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
