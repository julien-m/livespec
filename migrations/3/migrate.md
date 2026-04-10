---
version: 3
description: "Retrofit visual testing infrastructure into existing projects"
date: 2026-04-10
---

# Migration v3: Visual Testing Infrastructure

Scaffolds the visual testing helper, creates required directories, installs
pixelmatch and sharp, and adds root-level test-results output to .gitignore.

After migration completes, run /spec.test to capture visual baselines for existing features.

## Actions

MKDIR tests/e2e/helpers
MKDIR .specs/design/screens
RUN scaffold-visual-testing.sh
GITIGNORE test-results/
SET_VERSION 3
