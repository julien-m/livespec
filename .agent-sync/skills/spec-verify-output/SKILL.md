---
name: spec-verify-output
description: LiveSpec slash command /spec-verify-output
---

# /spec-verify-output

---
description: "Verify a command run artifact against its expectations"
argument-hint: "<command-name>"
---

> **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md) before starting — runtime goal contract (§5), 6-field step shape (§1), ERROR/BLOCKED format (§2), finalization gate.

## STEP 0 — Goal Lock (ABSOLU — aucun flag ne bypasse cette étape)

La toute première action lors de `/spec-verify-output` est de poser le goal durable avec un contrat machine, puis de laisser `livespec goal prove` valider chaque tâche.

1. Résoudre command, feature éventuelle et flags à partir des arguments de la commande (lecture seule).
2. Vérifier qu'aucun goal n'est actif. Si actif → `BLOCKED at step 0 - prerequisite_unmet - active goal exists — run /goal clear first` et stop.
3. Rendre et sauvegarder le contrat immuable et l'état mutable :
   ```bash
   livespec goal render spec-verify-output --feature <feature-slug> --flags "<active-flags>" --save
   ```
   Si aucune feature fournie, omettre `--feature`. Si aucun flag actif, passer `--flags ""`.
   Le stdout affiche : `hash:<hash> | contract-file:$TMPDIR/livespec-goals/goal-spec-verify-output-<hash8>.contract.json | state-file:$TMPDIR/livespec-goals/goal-spec-verify-output-<hash8>.state.json`
4. Lire le `contract-file` et le `state-file`. Le contrat contient la liste authoritative des tâches, preuves requises, substitutions interdites, et actions de réparation. Le state contient uniquement les statuts `pending`/`complete`.
5. Émettre la commande slash `/goal` avec hash et références machine :
   ```
   /goal hash:<hash> | spec-verify-output for <feature> — contract-file:$TMPDIR/livespec-goals/goal-spec-verify-output-<hash8>.contract.json — state-file:$TMPDIR/livespec-goals/goal-spec-verify-output-<hash8>.state.json — mode:enforced
   ```
6. Exécuter les tâches dans l'ordre du `contract-file`. Après chaque tâche, soumettre une preuve :
   ```bash
   livespec goal prove --contract <contract-file> --state <state-file> --task <task-id> --evidence '<json>'
   ```
   Seul `goal prove` peut marquer une tâche `complete`. Si le résultat est `REJECTED_NEEDS_ACTION`, effectuer les actions `repair_if_missing`, produire la preuve manquante, puis resoumettre. Ne jamais cocher, simuler, ou marquer manuellement une tâche.
7. Avant `DONE`, exécuter `livespec goal status --state <state-file>` et vérifier que toutes les tâches requises sont `complete`, ou émettre un `BLOCKED` canonique avec la tâche et la preuve manquante.

Si le rendu échoue → `BLOCKED at step 0 - dependency_unmet - livespec goal render failed` et stop.
Si l'environnement courant n'accepte pas `/goal` → `BLOCKED at step 0 - dependency_unmet - /goal slash command unavailable` et stop.

# Command: /spec-verify-output

Verify a LiveSpec command output artifact against the command's `expectations.md` contract.

---

## Internal Command Invocations

_(none — this command calls the `livespec verify-output` CLI, not nested `/spec-*` commands.)_

## Usage

```bash
/spec-verify-output <command>
/spec-verify-output <command> --scenario "<flags>"
/spec-verify-output <command> --run <path>
/spec-verify-output <command> --json
/spec-verify-output <command> --feature <name>
/spec-verify-output <command> --preview --save
```

## Execution Tasks

> Machine-readable task inventory parsed by `livespec goal render`.
> Format: `- [branch] task description`

- [always] Resolve target command name and normalize active scenario flags
- [always] Locate builtin or project override expectations for the target command
- [always] Locate the latest `.specs/.runs/<command>-*.json` artifact, unless `--run` or `--preview` is provided
- [always] Execute `livespec verify-output <command>` with the resolved flags/run/preview options
- [always] Surface outcome `success`, `drift`, `error`, or `blocked` exactly as reported by the CLI
- [always] If `--json` is active, return the JSON envelope without prose rewriting
- [always] If `--preview --save` is active, report the `.specs/.previews/<command>-*.md` path

## Definition of Done (Command-Level)

`/spec-verify-output` is complete only if all are true:

- [ ] Target command expectations were resolved or canonical BLOCKED was emitted
- [ ] Run artifact was resolved, or preview mode was explicitly active
- [ ] `livespec verify-output` executed with the requested flags
- [ ] Outcome was reported exactly
- [ ] No source, spec, or expectation files were modified
