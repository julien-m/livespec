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
| Regression green | Complete | 26 targeted tests passed, including actual unknown-source BLOCKED gate. |
| Independent patch review | Complete | Read-only reviewer approved isolated ae3c185 plus scanner/tests diff; no blocking findings. |
| Native conventions | Complete | PASS, 199 classified / 0 unclassified; baseline BLOCKED and zero new violations. |
| Feature-wide readiness | Blocked | Current spec review absent; filtered selector cannot parse historical bold-list AC declarations. No certification fabricated. |
| Conventions goal | Complete | Native documentary contract c82650d2 complete 28/28; feature-wide acceptance remains unproven. |
| Selective publication | In progress | Read [scoped check](checks/2026-10-08.md) for exact publish checks and remaining gaps. |
