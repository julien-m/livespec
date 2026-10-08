---
title: "Progress: Root governance corpus correction"
feature: 073-conventions-multilang-catalog
type: progress
created: 2026-10-08
updated: 2026-10-08
---

# Progress: Corpus prerequisite repair

| Step | Status | Evidence / limitation |
|---|---|---|
| Scoped gap | Complete | Root notices incorrectly unclassified; existing FR-008/FR-009 exclusion contract applies. |
| Regression red | Complete | 1 failed, 2 passed before scanner change; missing SECURITY exclusion. |
| Scanner correction | Complete | Exact root-relative paths, existing reason and counts retained. |
| Regression green | Complete | 26 targeted tests on original local base; 11 taxonomy tests on publication base; root regression also fails on original remote scanner. |
| Independent patch review | Complete | Read-only reviewer approved original and final origin/main-based scanner/tests diffs; no blocking findings or remote changes lost. |
| Native conventions | Complete | PASS, 199 classified / 0 unclassified; baseline BLOCKED and zero new violations. |
| Feature-wide readiness | Blocked | Current spec review absent; filtered selector cannot parse historical bold-list AC declarations. No certification fabricated. |
| Conventions goal | Complete | Native documentary contract c82650d2 complete 28/28; feature-wide acceptance remains unproven. |
| Publication checks | Complete with limits | 98/102 expanded conventions tests pass; same four fixture failures reproduce on parent; full suite 3628 passed, 87 failed, 29 skipped. |
| Selective publication candidate | Prepared | Read [scoped check](checks/2026-10-08.md) for exact publish checks and remaining gaps. |
