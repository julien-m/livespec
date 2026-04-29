"""Brainstorm ingestion subpackage.

Detects, validates, and ingests `project-brainstorm` artifacts
(`specs/flows/*.md`, `specs/screens/*.md`, `mockups/manifest.json`,
`mockups/*.png`, `project-profile.md`) into a fresh `.specs/` (via
`/spec.init`) or an existing one (via `/spec.refine project
--import-brainstorm`).

Implements feature 012-brainstorm-ingestion.
"""
