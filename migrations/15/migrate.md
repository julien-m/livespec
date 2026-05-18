---
version: 15
description: "Command naming normalization — hyphenated slash commands with dotted aliases"
date: 2026-05-18
---

# Migration v15: Command Naming Normalization

Feature 049 makes `/spec-*` the canonical slash-command spelling while keeping
legacy `/spec.*` aliases. Downstream projects need both symlink families so
existing workflows continue to run while new documentation and audits prefer
the hyphenated names.

## Actions

RUN migrate-command-naming.sh
SET_VERSION 15
