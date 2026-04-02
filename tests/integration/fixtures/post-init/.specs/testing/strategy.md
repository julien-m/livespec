# Testing Strategy

## Unit Tests

All pure business logic functions must have unit tests. Test files colocated with source files using the `.test.ts` suffix. Target coverage: 80% line coverage on business logic modules.

Framework: Vitest with native TypeScript support. No compilation step needed for tests.

## Integration Tests

API routes tested with Supertest against a real Express instance with an in-memory PostgreSQL (via pg-mem or test container). Each test suite gets a fresh database schema. Target: every endpoint has at least one happy-path and one error-path test.

## Test Execution

- `npm test` runs unit tests only (fast, no external deps)
- `npm run test:integration` runs integration tests (requires PostgreSQL)
- CI runs both in sequence; integration tests use a PostgreSQL service container
