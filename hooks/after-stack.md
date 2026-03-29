# After Stack — Refresh Conventions

After `/spec.stack` completes and the stack has changed, refresh coding conventions to match the new stack.

## Instructions

1. Check if `.conventions/conventions.md` exists
   - If it does not exist → run `/conventions.init` instead and stop
   - If it exists → continue

2. Run `/conventions.refresh --full`
   - Full mode re-detects domains from scratch (new stack components may add/remove entire convention categories)
   - The skill will automatically detect `.specs/stacks/_default.md` and use the updated stack

3. Report briefly:
   ```
   Conventions refreshed after stack change
   ```
