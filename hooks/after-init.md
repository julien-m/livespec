# After Init — Generate Conventions

After `/spec.init` completes and `.specs/stacks/_default.md` has been created, generate the project's coding conventions.

## Instructions

1. Check if `.conventions/conventions.md` already exists
   - If it exists → skip (conventions already initialized)
   - If it does not exist → continue

2. Run `/conventions.init`
   - The skill will automatically detect `.specs/stacks/_default.md` and use it as a stack source
   - This generates `.conventions/conventions.md` with the correct conventions for the declared stack

3. Report briefly:
   ```
   Conventions generated from stack in .specs/stacks/_default.md
   ```
