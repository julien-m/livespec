# Design Spec: Phase de réconciliation IA post-migration visuelle

**Date:** 2026-04-20  
**Status:** Approved (auto-brainstorm)  
**Branch:** main

---

## Problème

Le script `migrate-visual-tests.js` génère, supprime et merge des fichiers de test mécaniquement. Mais il produit des artefacts incorrects que seul un jugement IA peut détecter :

1. **Doublons fonctionnels** — `not-found.spec.ts` et `route-not-found.spec.ts` testent la même page 404
2. **Erreurs de syntaxe** — double `});` en fin de fichier quand le merge legacy ajoute un bloc
3. **Code mort préservé** — `test("placeholder")` copié depuis des stubs `.skip` vides
4. **Fichiers orphelins** — test pour une route qui n'existe plus après refactoring
5. **Incohérence slug/route/heading** — slug `not-found` mais route `/nonexistent-page-404`

**Cas réel :** Migration de claude-pilot — 5 des 6 fichiers `route-*.spec.ts` générés avaient le problème 2+3, et `not-found.spec.ts` n'a pas été supprimé (problème 1).

---

## Solution

### Nouveau Step 4.6 dans `commands/migrate.md`

Ajouter une phase de réconciliation IA entre Step 4.5 (Visual Scaffolding) et Step 5 (Report). L'agent qui exécute `/spec.migrate` analyse les fichiers de test générés et corrige les incohérences.

**Condition de déclenchement :** Le sentinel de Step 4.5 indique `files > 0` OU `routes > 0`. Si `files == 0 AND routes == 0`, skip la réconciliation.

**Mécanisme de rollback :** Avant toute modification, l'agent stage les fichiers générés par Step 4.5 (`git add <test-dir>/`). Les corrections de Step 4.6 restent unstaged, permettant un `git checkout -- <test-dir>/` pour rollback.

### Les 5 checks

#### Check 1 : Doublons fonctionnels
Lister tous les fichiers `.spec.ts` dans TEST_DIR. Pour chaque paire, vérifier si deux fichiers testent la même route (comparer les constantes `ROUTE` dans le code). Si doublon trouvé :
- Garder le fichier le plus complet (plus de tests, plus de couverture)
- Supprimer le doublon
- Reporter : `Doublon supprimé : {file} (même route que {other})`

#### Check 2 : Erreurs de syntaxe
Pour chaque fichier `.spec.ts` créé ou modifié par Step 4.5 :
- Vérifier que le nombre de `{` et `}` est équilibré
- Vérifier qu'il n'y a pas de double `});` consécutif (signe d'un merge raté)
- Si trouvé : supprimer le `});` orphelin
- Reporter : `Syntaxe corrigée : {file} (double fermeture de bloc supprimée)`

#### Check 3 : Code mort préservé
Pour chaque fichier contenant une section `// ── Preserved from`:
- **RÈGLE : ne JAMAIS supprimer le contenu qui a une logique réelle** (page.goto, expect, assertions)
- Supprimer uniquement les tests qui sont des stubs vides : `test("placeholder", async () => {});` ou `test.describe.skip(...)` sans vrai contenu
- Reporter : `Code mort supprimé : {file} (stub placeholder dans section Preserved)`

#### Check 4 : Fichiers orphelins
Cross-référencer les fichiers `route-*.spec.ts` avec les routes réelles du projet :
- Lire `frontend/app/routes/` (ou équivalent) pour lister les routes existantes
- Si un `route-*.spec.ts` cible une route qui n'existe pas → reporter mais NE PAS supprimer (la route peut être en cours de développement)
- Reporter : `⚠️ Route potentiellement orpheline : {file} (route {route} non trouvée)`

#### Check 5 : Cohérence slug/route/heading
Pour chaque fichier de test :
- Vérifier que `ROUTE` correspond à un pattern plausible pour le slug du fichier
- Vérifier que `HEADING` est renseigné (pas un placeholder générique comme "Page Title")
- Reporter les incohérences : `⚠️ Vérifier heading : {file} (HEADING = "{heading}" semble générique)`

### Mise à jour Step 4.5 point 6

Parser les 3 champs du sentinel : `files=N dirs=M routes=R` (actuellement seuls `files` et `dirs` sont documentés).

---

## Rapport de réconciliation (intégré au Step 5)

```
Visual test reconciliation:
  ✓ 1 duplicate removed (not-found.spec.ts → covered by route-not-found.spec.ts)
  ✓ 5 syntax fixes (double }); in route-*.spec.ts)
  ✓ 5 dead stubs removed (placeholder tests in Preserved sections)
  ⚠ 1 potentially orphaned route (route-legacy.spec.ts → /legacy not found)
  0 heading issues
```

Si aucune correction nécessaire :
```
Visual test reconciliation: 0 issues found
```

---

## Edge Cases

| Scénario | Comportement |
|---|---|
| Aucun fichier dans TEST_DIR | Skip réconciliation |
| Test file avec syntaxe complexe (nested describes) | Check 2 utilise le comptage de braces, pas regex |
| "Preserved from" contient du vrai code | Check 3 ne supprime que les stubs vides, jamais le code avec des assertions |
| Route `route-not-found.spec.ts` vs `not-found.spec.ts` | Check 1 compare les constantes ROUTE, pas les noms de fichiers |
| Pas de dossier routes (projet non-Remix/Next) | Check 4 skip si aucun dossier routes trouvé |

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `commands/migrate.md` | Mise à jour Step 4.5 point 6 (parser `routes=R`) + nouveau Step 4.6 (réconciliation IA) |

---

## Hors périmètre

- Pas de modification de `migrate-visual-tests.js` — les checks déterministes (syntaxe, doublons) sont suffisamment simples pour être décrits en prose agent
- Pas de tests automatisés — c'est de la prose agent, pas du code testable
- Pas de modification de `spec.test.md` — la réconciliation est spécifique à la migration, pas au workflow de test
