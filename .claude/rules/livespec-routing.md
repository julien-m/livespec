# LiveSpec Routing

**S'applique quand `.specs/` existe à la racine du cwd.**

Si présent : ce projet utilise [LiveSpec](https://github.com/julien-m/livespec). Toute demande d'action sur le projet (ajout, correction, test, exploration, spec, plan, vérification) doit être **routée vers la commande `/spec.*` correspondante** plutôt qu'exécutée directement.

## Procédure

1. Détecter `.specs/` dans le cwd
2. Identifier l'intention utilisateur (ajouter / corriger / tester / spécifier / planifier / vérifier / expliquer / autre)
3. **Read** [`livespec-commands.md`](livespec-commands.md) pour mapper intention → commande + paramètres usuels
4. **Proposer** la commande `/spec.*` avec les paramètres pertinents avant d'agir
5. Sur confirmation utilisateur → invoquer la commande via le Skill tool
6. Aucune commande ne couvre l'intention → exécuter normalement, signaler explicitement l'absence de routage

## Lecture préalable

Avant toute commande `spec.*`, **Read** [`.specs/spec-system.md`](../../.specs/spec-system.md) (rappel CLAUDE.md projet).

## Chargement

- `livespec-routing.md` : chargé dès que `.specs/` est détecté.
- `livespec-commands.md` : **chargé à la demande uniquement**, à l'étape 3 ci-dessus.

## Exceptions

- Question / lecture / debug rapide → pas de routage forcé
- Mode Ask actif → proposition seule, jamais d'exécution
- Commande `/spec.*` déjà demandée explicitement par l'utilisateur → pas de re-proposition

## Synchronisation

Le check `.claude/checks/livespec-routing-sync.md` (bloquant via `/audit`) garantit la bijection entre `commands/*.md` et les entrées de `livespec-commands.md`. Toute désync bloque le commit.
