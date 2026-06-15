---
name: spec-refresh-from-brainstorm
description: LiveSpec slash command /spec-refresh-from-brainstorm — sync brainstorm lifecycle events into LiveSpec specs via interactive Impact Report
---

# /spec-refresh-from-brainstorm

---
description: "Detect brainstorm lifecycle deltas and propose LiveSpec actions interactively"
argument-hint: ""
---

> **Read** [`system/anti-drift-block.md`](../../../system/anti-drift-block.md) before starting — runtime goal contract (§5), 6-field step shape (§1), ERROR/BLOCKED format (§2), finalization gate.
> **Read** [`format-contract-brainstorm-sync.md`](../../../.specs/proposals/format-contract-brainstorm-sync.md) before execution — use §2 for log hash validation, §5.2 for mutation impacts, §6 for event→action mapping, §7-8 for report/action semantics, §11 for deferral format.

## Vue d'ensemble

Lit le lifecycle Brainstorm via le symlink `./brainstorm` en essayant d'abord `brainstorm/handoff/livespec/lifecycle/`, puis le legacy `brainstorm/lifecycle/`. Valide les events postérieurs au curseur, affiche un Impact Report, puis applique uniquement les actions confirmées une par une par l'utilisateur.

**Principe absolu :** `brainstorm/` est lu en source externe. Ne jamais modifier `.specs/` sans réponse explicite `o`.

## Workflow

1. **Préconditions bloquantes**
   - Vérifier que `./brainstorm/` est un symlink.
   - Résoudre le dossier lifecycle : `./brainstorm/handoff/livespec/lifecycle/` si `log.ndjson` y est lisible, sinon legacy `./brainstorm/lifecycle/`.
   - Si les deux existent, canonical lifecycle wins : utiliser `brainstorm/handoff/livespec/lifecycle/`.
   - Inférer `<slug>` depuis la cible du symlink.
   - Si absent ou cassé : `BLOCKED at step 0 - prerequisite_unmet - symlink brainstorm ou lifecycle manquant; créer ln -s ~/projects/project-brainstorm/projects/<slug> brainstorm`.

2. **Curseur**
   - Lire `<lifecycle>/.refresh-cursor` si présent.
   - Format attendu : `{"event_id":"E-000003","ts":"2026-06-10T08:00:00Z","hash":"<sha256hex>"}` sur une ligne, sans newline final.
   - Si absent, traiter tous les events depuis `E-000001`.

3. **Deltas + intégrité**
   - Lire `<lifecycle>/log.ndjson` ligne par ligne, sélectionner les events strictement postérieurs au curseur (`ts` + `event_id`).
   - Valider la chaîne `prev_hash` selon le contrat §2 : canonicalisation JSON, SHA-256, comparaison avec l'event suivant.
   - Si divergence : `BLOCKED at step 2 - corrupted_log - event_id <E-XXXXXX>; prev_hash déclaré <x>; calculé <y>`.
   - Lire `<lifecycle>/state.yaml` pour les statuts courants.
   - Si aucun delta : afficher `Aucun nouvel event depuis le dernier refresh (curseur : <event_id>). Rien à faire.` puis terminer.

4. **Mutations**
   - Pour chaque `mutation-created`, lire `<lifecycle>/mutations/<mutation_id>/impacts.yaml`.
   - Utiliser `impacts.yaml` comme source de vérité. Ignorer `artefacts_touched`, qui n'est qu'un index rapide.

5. **Impact Report**
   - Afficher le rapport Markdown complet avant validation :
     ```markdown
     # Impact Report — spec-refresh-from-brainstorm
     **Date**: <ISO8601 UTC>
     **Période**: <ts premier delta> → <ts dernier delta>
     **Events lus**: <N>
     **Curseur précédent**: <event_id ou "aucun (première exécution)">

     ## Actions proposées
     ## Signalements (aucune action automatique)
     ## Aucun changement
     ```
   - Mapper les events avec le contrat §6. Détecter une feature présente si `.specs/features/` contient le slug exact ou `NNN-<slug>`; lire son `status` dans `spec.md`.

6. **Validation interactive**
   - Présenter chaque action applicable séparément, hors no-op et signalements :
     ```text
     Action [1/N] : <type> — <feature_id>
       Feature     : <feature_title>
       Event source: <ts> (<event_type>)
       Rationale   : <rationale>
       Action      : <description précise>
       Appliquer ? [o / n / d(iférer)]
     ```
   - `o` applique; `n` ignore définitivement cet event; `d` écrit `<lifecycle>/.refresh-deferred.yaml` au format contrat §11.
   - Aucune action groupée, aucune application implicite.

7. **Actions confirmées**
   - `feature-add` : créer `.specs/features/<NNN>-<feature_id>/spec.md` avec le prochain numéro libre et ce squelette :

```markdown
---
type: spec
title: <feature_title>
feature: <NNN>-<feature_id>
status: spec
priority: <priority ou P2 par défaut>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

# Feature Spec: <feature_title>

> Spec créée automatiquement par `/spec-refresh-from-brainstorm` depuis l'event `<event_id>` (`<ts>`).
> Origine brainstorm : `<rationale>`.
>
> **À compléter** : user stories, acceptance criteria, functional requirements.
```
   - `feature-remove` / `cancelled` : mettre `status: cancelled`, mettre `updated`, ajouter une note `Annulée` avec event et preuve.
   - `feature-remove` / `deprecated` : même procédure avec `status: deprecated` et note `Dépréciée`.

8. **Curseur final**
   - Après traitement, avancer le curseur au dernier event lu et validé, même si son action était no-op ou signalement.
   - Écrire `<lifecycle>/.refresh-cursor` en une ligne sans newline final : `{"event_id":"<id>","ts":"<ts>","hash":"<sha256hex>"}`.
   - Proposer le commit `chore: refresh brainstorm sync cursor (<event_id>)`; ne jamais committer sans confirmation.

## Garde-fous

- Lecture seule côté `brainstorm/`, sauf `.refresh-cursor` et `.refresh-deferred.yaml`.
- Aucune modification `.specs/` sans `o` explicite.
- Log corrompu ou symlink cassé = `BLOCKED` immédiat.
- Pas de cascade automatique : `pilot` ne touche jamais `.specs/`; ce skill ne touche jamais `lifecycle/` hors curseur/différé.
- `impacts.yaml` fait foi pour les mutations.
