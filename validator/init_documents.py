"""Render source-backed bootstrap documents with explicit unknown business facts."""

from __future__ import annotations

from datetime import date

from .init_probes import ProbeResult
from .init_profile import ObservedProfile

UNKNOWN_FIELDS = ("Roles", "Growth", "Geography", "Budget", "Deployment", "Authentication")


def _table(header: str, rows: list[str]) -> str:
    return header + "\n" + "\n".join(rows) + "\n"


# @spec FR-002: Evidence-based project artifacts
#   — .specs/features/080-autonomous-from-code-recovery/spec.md#fr-002
def render_documents(
    profile: ObservedProfile, *, generated_on: str | None = None
) -> dict[str, str]:
    """Return generated relative paths and document bytes without filesystem writes.

    Args:
        profile: Independently observed manifest facts.
        generated_on: Stable generation date for repeat verification.
    Returns:
        Project-specific documents; no product or deployment assumptions.
    """
    today = generated_on or date.today().isoformat()
    name = profile.product_name
    facts = _table(
        "| Layer | Choice | Version | Evidence |\n|---|---|---|---|",
        [
            f"| {fact.name} | {fact.name} | {fact.version} | {fact.evidence} |"
            for fact in profile.facts
        ],
    )
    unknowns = "\n".join(
        f"- **{field}:** Unknown (not observed in supported manifests)." for field in UNKNOWN_FIELDS
    )
    evidence = "\n".join(f"- {source.path}: SHA256 {source.sha256}" for source in profile.sources)
    # Documents deliberately separate observed code identity from unobserved product decisions.
    project = f"""# Project Profile: {name}

## Vision

Observed technical packages: {", ".join(profile.technical_names) or "Unknown"}.
Product intent and business vision: Unknown.

## Users

{unknowns}

## Constraints

Package manager: {profile.package_manager}.

## Stack Reference

Read [observed stack](stacks/_default.md).

## Testing Reference

Read [testing strategy](testing/strategy.md).

## Source Evidence

{evidence}
"""
    constitution = f"""# Constitution — {name}

## Project Identity

Retain observed packages {", ".join(profile.technical_names) or "Unknown"}.
Independent families:

{facts}

## Architecture Principles

- Preserve the existing source and native/frontend boundaries.
- Derive stack and manager choices from manifests; unsupported business decisions remain Unknown.
- Tool version availability certifies tooling only;
  application build, UI and runtime require separate execution evidence.
- Specify changed behavior before implementing it;
  require meaningful tests and current source verification.

## Testing Standards

Read [testing strategy](testing/strategy.md).
"""
    stack = f"""---
updated: {today}
---

# Stack — {name}

## Core Stack

{facts}

Package manager: {profile.package_manager}.

## Rationale

Retain every independently observed family without inferring deployment.

{unknowns}
"""
    tests = (
        "\n".join(f"- {tool}" for tool in profile.testing_tools)
        or "- Unknown: no supported testing dependency observed."
    )
    commands = (
        "\n".join(f"- `{command}`" for command in profile.test_commands)
        or "- Unknown: no supported test command observed."
    )
    testing = f"""# Testing Strategy: {name}

## Observed Tools

{tests}

## Observed Commands

{commands}

## Evidence Boundary

Commands above are observed and deduplicated; they were not executed during initialization.
Run relevant unit, integration and native/frontend tests before claiming application success.
"""
    tools = (
        "\n".join(f"- `{tool} --version` — required observed tooling" for tool in profile.tools)
        or "- Unknown: no package manager evidence establishes a required tooling probe."
    )
    preflight = f"""# Preflight — {name}

## Tooling

{tools}

## Authentication

Unknown. No application authentication or deployment inferred.

<!-- preflight:custom:start -->
<!-- preflight:custom:end -->
"""
    adr = f"""# ADR — Observed stack retention

- **Date:** {today}
- **Status:** Accepted (observed existing implementation)

## Context

{facts}

## Decision

Retain independent observed stack families and package manager {profile.package_manager}.
This records existing code rather than selecting a new stack.

## Consequences

Unobserved business/deployment choices remain Unknown; future changes require an explicit decision.
"""
    return {
        "project.md": project,
        "constitution.md": constitution,
        "stacks/_default.md": stack,
        "testing/strategy.md": testing,
        "preflight.md": preflight,
        "stacks/decisions/ADR-bootstrap-observed.md": adr,
        "roadmap.md": _roadmap(name),
    }


def render_preflight(results: tuple[ProbeResult, ...]) -> str:
    """Render actual probe output and a tooling-only verdict."""
    verdict = "READY" if all(result.passed for result in results) else "BLOCKED"
    rows = [
        f"| {' '.join(result.argv)} | {result.exit_code} | {result.duration:.3f}s | "
        f"{result.timed_out} | {result.stdout.strip().replace('|', '/')} | "
        f"{result.stderr.strip().replace('|', '/')} |"
        for result in results
    ]
    return (
        f"# Preflight Report\n\nVerdict: {verdict}\n\n"
        "Tooling availability only; application build/UI/runtime was not executed.\n\n"
        + _table(
            "| Argv | Exit | Duration | Timeout | Stdout | Stderr |\n|---|---|---|---|---|---|",
            rows,
        )
    )


def _roadmap(name: str) -> str:
    tiers = ("mvp", "postmvp", "future", "deferred")
    markers = "\n".join(
        f"<!-- roadmap:{tier}:{edge} -->" for tier in tiers for edge in ("start", "end")
    )
    return f"# Roadmap — {name}\n\n{markers}\n\nNo business backlog inferred from manifests.\n"
