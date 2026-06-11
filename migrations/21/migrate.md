---
version: 21
name: journey-fixture-bootstrap-contract
description: "Scaffold the journey fixtures bootstrap contract and recompile journeys for compiler journeys-v2-3"
date: 2026-06-11
kind: asset-sync
---

<!-- @spec FR-010: Fully automatic migration v21
     — ../../.specs/features/060-journey-fixture-bootstrap-contract/spec.md#fr-010 -->

# Migration v21: Journey Fixture Bootstrap Contract

Feature 060 introduces the project-local fixtures contract
(`.specs/journeys/fixtures.yaml`) with **blocking** validation for XCUITest
journeys that declare fixtures or mocks, derived `waitForJourneyBootstrap`
codegen, and the compiler bump to `journeys-v2-3` (with the additive
`fixtures_contract_hash` manifest field).

This migration keeps existing projects green with zero manual action:

- Agent-sync assets are refreshed so commands document the new contract.
- `livespec journey fixtures scaffold` writes a minimal valid contract from
  the fixtures/mocks already declared in v2 journeys (surfaces inferred from
  journey targets, no `expected_screen`/`required_markers`/`bootstrap` block —
  runtime behavior is unchanged until the contract is enriched). The scaffold
  never overwrites an existing `fixtures.yaml`.
- `livespec journey compile --force` regenerates every artifact and manifest,
  replacing stale `journeys-v2-2` manifests with `journeys-v2-3` ones that
  record the contract hash.

The scaffold wrapper exits 0 for all three outcomes — contract scaffolded,
contract already present, and no fixture journeys found — so neither no-op is
ever treated as a migration failure.

RUN migrate-agent-sync.sh
RUN migrate-journeys-fixtures-scaffold.sh
RUN migrate-journeys-compile.sh
SET_VERSION 21
