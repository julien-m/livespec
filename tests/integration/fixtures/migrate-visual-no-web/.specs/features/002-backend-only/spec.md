---
feature: API Rate Limiter
title: "API Rate Limiter"
status: Implemented
---

# Feature Spec: API Rate Limiter

- **Feature:** API Rate Limiter
- **Status:** Implemented

## User Scenarios

### Story 1 — Rate limiting on API endpoints

The system enforces rate limits per API key.
Requests exceeding the limit receive a 429 status code.
The limiter uses a sliding window algorithm with Redis storage.
