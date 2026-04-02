# Constitution

## Architecture Principles

### 1. API-First Design

Every feature must be fully usable through the REST API before any UI work begins. The web interface is a consumer of the API, never a bypass. This ensures that automation, integrations, and future mobile clients are first-class citizens.

### 2. Explicit Over Magic

Configuration, data flow, and error handling must be explicit and traceable. No hidden side effects, no implicit middleware chains, no convention-based file routing. Every behavior should be discoverable by reading the code linearly.

### 3. Minimal Viable Abstraction

Do not introduce abstractions (base classes, generic utilities, shared middleware) until at least three concrete use cases demand it. Duplication is cheaper than the wrong abstraction. When abstraction is warranted, keep it one level deep.
