---
version: 6
description: "Add playwright-report/ to .gitignore"
date: 2026-04-14
---

# Migration v6: Playwright Report Gitignore

Adds playwright-report/ to .gitignore. This is Playwright's HTML reporter
output directory, distinct from test-results/ (test artifacts) which was
added in migration v3.

## Actions

GITIGNORE playwright-report/
SET_VERSION 6
