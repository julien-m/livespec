# TypeScript create API witness

Implement `app.ts` using Node standard library. Export `createApp(storePath)`
returning a Node HTTP server. POST /items requires `Authorization: Bearer witness`;
otherwise return 403 without changing any persisted bytes. A valid JSON object
with a nonempty string `name` returns 201 and persists that same item in a JSON
array at storePath. Reject invalid authorized input with 400 and no mutation.
Importing the module must not start a server. Node runs TypeScript natively.
