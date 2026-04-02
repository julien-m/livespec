# ADR-001: TypeScript as Primary Language

## Status

Accepted

## Context

The team needs a single language for both backend (Express API) and shared types across the stack. JavaScript is ubiquitous but lacks compile-time type safety, leading to runtime errors that are expensive to debug in production.

## Decision

Use TypeScript 5.x for all application code (API, shared types, build scripts). Strict mode enabled. No `any` types allowed outside explicit escape hatches documented with `// eslint-disable` comments.

## Consequences

- Positive: Shared interfaces between API request/response types and database models
- Positive: Compile-time error detection reduces bug surface area
- Negative: Build step required; slightly slower development loop than plain JS
- Negative: Team members unfamiliar with TS generics will need onboarding
