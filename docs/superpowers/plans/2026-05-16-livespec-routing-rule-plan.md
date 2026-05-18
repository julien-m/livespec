# Plan — Règle de routing LiveSpec

**Spec** : `docs/superpowers/specs/2026-05-16-livespec-routing-rule-design.md`
**Exécution** : Subagent-Driven (auto-sélectionné)

## Tâches

### T1. Lire toutes les commandes pour extraire params usuels

> **Note importante** : les fichiers dans `commands/` sont nommés **sans préfixe `spec.`** (ex : `commands/spec-test.md`, `commands/spec-feature.md`). Le préfixe `/spec.` n'est que la forme d'invocation utilisateur. La bijection du check (T4) doit donc mapper `commands/<name>.md` ↔ `### /spec.<name>` dans la référence.

Les 20 commandes uniques (vérifiées via `find commands -maxdepth 1 -name '*.md' -not -name '*.expectations.md'`) :

`check`, `explain`, `feature`, `fix`, `hooks`, `implement`, `init`, `migrate`, `plan`, `play-coverage`, `preflight`, `propose`, `refine`, `refresh-conventions`, `ship`, `specify`, `stack`, `status`, `test`, `verify-output`.

- Pour chaque : lire `commands/<name>.md`, extraire section `## Usage` ou bloc `/spec.<name> ...` du body, retenir 3-5 exemples représentatifs.

**Success** : liste des 20 commandes avec params usuels en mémoire pour T3.

### T2. Écrire `.claude/rules/livespec-routing.md`

Contenu attendu (< 60 lignes) :

```
# LiveSpec Routing

S'applique quand `.specs/` existe à la racine du cwd.

Si présent : ce projet utilise LiveSpec. Toute demande d'action
(ajout, correction, test, exploration, spec, plan) doit être
routée vers la commande `/spec.*` correspondante.

## Procédure

1. Détecter `.specs/` dans le cwd
2. Identifier l'intention utilisateur
3. **Read** [`livespec-commands.md`](livespec-commands.md)
4. Proposer la commande `/spec.*` avec les paramètres pertinents
5. Sur confirmation → invoquer via le Skill tool
6. Si aucune commande ne couvre l'intention → exécuter normalement, signaler

## Lecture préalable

Avant toute commande `spec.*`, **Read** `.specs/spec-system.md`.

## Exceptions

- Question / lecture / debug rapide → pas de routage forcé
- Mode Ask actif → proposition uniquement, pas d'exécution
- Commande déjà demandée explicitement par l'utilisateur → pas de re-proposition
```

**Success** : fichier créé, < 60 lignes, mentionne `.specs/` comme trigger, pointe vers `livespec-commands.md`.

### T3. Écrire `.claude/rules/livespec-commands.md`

Structure :

1. En-tête : "Chargé à la demande par `livespec-routing.md`"
2. Table "Intention → Commande" (15-20 lignes) couvrant les cas usuels
3. Sections par commande (une par `/spec.X`, en heading H3) :
   ```
   ### /spec.X
   <description 1 ligne>
   **Usage** :
   - `/spec.X ...` — <quand>
   - `/spec.X --flag` — <quand>
   ```

Couvre les 20 commandes identifiées en T1.

**Success** : fichier créé, 20 sections présentes (une par commande), table de routage en tête.

### T4. Écrire `.claude/checks/livespec-routing-sync.md`

Format identique à `migration-version.md` (prose + one-liner, lu par `/audit` qui est LLM — pas un script exécutable) :

```
# LiveSpec Routing Sync

## When
Staged files match `commands/*.md` (excluding `*.expectations.md`) or `.claude/rules/livespec-commands.md`.

## Verify
The set of command names in `commands/` must match exactly the set of `### /spec.X` headings in `.claude/rules/livespec-commands.md`. Command filenames in `commands/` do NOT carry the `spec.` prefix (e.g. `commands/spec-test.md` ↔ `### /spec.test`).

Compare:
- Files: `find commands -maxdepth 1 -name '*.md' -not -name '*.expectations.md' | sed 's|.*/||;s|\.md$||' | sort`
- Headings: `grep -E '^### /spec\.' .claude/rules/livespec-commands.md | sed 's|^### /spec\.||' | sort`

The two lists must be identical. Any orphan (in routing, not in `commands/`) or missing entry (in `commands/`, not in routing) blocks the commit. The error report must list both sets of diffs explicitly.
```

**Success** : fichier créé, format aligné sur `migration-version.md` (prose + one-liners, pas un script).

### T5. Vérification manuelle bout-en-bout

1. `ls .claude/rules/livespec-routing.md .claude/rules/livespec-commands.md .claude/checks/livespec-routing-sync.md` → tous présents
2. Compter les sections `^### /spec\.` dans `livespec-commands.md` → doit être 20
3. Lister `find commands -maxdepth 1 -name '*.md' -not -name '*.expectations.md'` → doit être 20
4. Vérifier bijection :
   `diff <(find commands -maxdepth 1 -name '*.md' -not -name '*.expectations.md' | sed 's|.*/||;s|\.md$||' | sort) <(grep -E '^### /spec\.' .claude/rules/livespec-commands.md | sed 's|^### /spec\.||' | sort)` → vide

**Success** : 4 vérifications passent.

### T6. (Optionnel) Mention dans CLAUDE.md

Confirmer que la liste de noms dans CLAUDE.md reste cohérente — pas de modif requise si elle l'est déjà (D10 raffinée : CLAUDE.md garde les noms, routing porte les params).

**Success** : décision documentée dans le rapport final ; pas de modif silencieuse.

## Verification

- Lint/typecheck : N/A (markdown)
- Manual : bijection vérifiée bash (T5)
- Re-read : Read sur les 3 fichiers créés pour confirmer contenu
- Audit : `/audit.fix` en step 9 du workflow auto-brainstorm

## Out of scope

- Mise à jour de la commande `/spec.refresh-conventions` pour générer automatiquement `livespec-commands.md` (cool to have, hors scope)
- Hook pre-commit dédié — `/audit` via `/git.commit` suffit
