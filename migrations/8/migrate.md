---
version: 8
description: "Multi-surface model — generates .specs/surfaces.yaml for test directory resolution"
date: 2026-04-22
---

# Migration v8: Multi-Surface Model

Introduces `.specs/surfaces.yaml` for explicit surface configuration.
Detects project surfaces from filesystem structure and generates the config file.
Test scripts now iterate over declared surfaces instead of hardcoded paths.

## Actions

SET_VERSION 8
RUN_SCRIPT scripts/generate-surfaces.js
