# Design: Check 0 — Filtre AI sémantique des features non-UI

**Date:** 2026-04-21
**Scope:** `commands/migrate.md` (Steps 4.6, 4.7, 5)

## Problème

Le script `migrate-visual-tests.js` (Step 4.5) utilise une heuristique par mots-clés (`UI_KEYWORDS`) pour détecter si une feature a un frontend. Cette heuristique produit des faux positifs — des mots comme "page", "list", "table", "input" apparaissent dans des specs purement backend (API, CLI, caching). Résultat : des tests visuels sont scaffoldés pour des features sans interface navigateur.

Exemples concrets observés sur artifact-lab : `007-api-push`, `012-sdk-runtime`, `014-dedicated-cli`, `017-r2-artifact-caching` ont tous reçu des tests visuels inutiles.

Le même problème affecte Step 4.7 (E2E generation) qui génère des tests interactifs pour des features backend.

## Solution

Ajouter un **Check 0** en tête de Step 4.6 (avant les 5 checks existants) où l'AI lit le `spec.md` de chaque feature scaffoldée et classifie sémantiquement si la feature a réellement un composant UI visible dans un navigateur.

Appliquer le même filtre dans Step 4.7 Phase A pour exclure les features non-visuelles de la génération E2E.

## Architecture

### Check 0 dans Step 4.6

**Position :** Premier check, avant Check 1 (duplicates). Réduit le nombre de fichiers à traiter par les checks suivants.

**Scope :** Uniquement les fichiers scaffoldés par Step 4.5 (pas les fichiers pré-existants).

**Procédure par fichier scaffoldé :**

1. Identifier la feature correspondante (extraire le numéro/slug du nom de fichier)
2. Lire `.specs/features/{NNN-slug}/spec.md`
3. Classifier la feature via jugement sémantique AI :
   - **`visual`** — La feature décrit une page, écran, composant, modal, formulaire que l'utilisateur voit dans un navigateur → **Garder le fichier**
   - **`non-visual`** — La feature décrit un CLI, une API REST/GraphQL, un worker background, un système de cache, une lib/SDK sans UI propre → **Supprimer le fichier scaffoldé + ses dossiers baseline**
   - **`ambiguous`** — Features mixtes (ex: API avec dashboard d'admin) → **Garder + ajouter un warning**

**Prompt de classification :**
> Feature directory: `{NNN-slug}`
>
> Read this feature spec. Does it describe something the end user interacts with visually in a web browser (a page, screen, dialog, component, dashboard, form)?
>
> A CLI tool, REST/GraphQL API endpoint, background worker, caching layer, SDK library, or infrastructure service is NOT visual — even if its spec mentions words like "response", "input", "output", "table", or "list" in a non-UI context.
>
> Answer: VISUAL, NON-VISUAL, or AMBIGUOUS (with one-line rationale).

Le nom du répertoire de la feature est inclus dans le prompt comme signal supplémentaire (ex: `014-dedicated-cli` est un indice fort de non-visual).

**Actions :**
- `non-visual` : supprimer le `.spec.ts` scaffoldé + les dossiers baseline créés pour cette feature. Log : `Check 0: deleted {file} (non-visual feature: {rationale})`
- `ambiguous` : garder le fichier mais ajouter un commentaire `// ⚠️ CHECK: This feature may not have a browser UI — verify before running` en tête. Log : `⚠ Check 0: kept {file} (ambiguous: {rationale})`
- `visual` : aucune action. Log optionnel en mode verbose.

**Post-Check 0 flow :** Si Check 0 supprime TOUS les fichiers scaffoldés (toutes les features sont non-visual), les Checks 1-5 sont skippés avec le log : `Checks 1-5: skipped (0 files remaining after Check 0)`. Les compteurs `FIXES` et `WARNINGS` incluent les résultats de Check 0.

**Classification caching :** Check 0 stocke ses résultats dans une map `CHECK0_RESULTS = { featureDir → classification }` qui sera réutilisée par Step 4.7 pour éviter de re-classifier les mêmes features.

### Filtre dans Step 4.7 Phase A

Réutiliser `CHECK0_RESULTS` de Step 4.6 si disponible. Pour les features non couvertes par Check 0 (features avec Gherkin mais non scaffoldées en visual par Step 4.5), appliquer la même classification AI avant de les ajouter à `FEATURES_TO_GENERATE`.

Exclure les features `non-visual`. Les features `ambiguous` sont incluses (conservatisme — mieux vaut générer un test E2E de trop).

### Comportement en `--dry-run`

En mode dry-run, Check 0 exécute la classification et affiche ce qui serait supprimé/gardé, sans modifier de fichiers. Log : `[DRY RUN] Check 0 would delete {file} (non-visual: {rationale})`.

### Impact sur le Report Step 5

Intégrer au résumé de réconciliation existant :
```
Visual test reconciliation:
  ✓ {N} non-visual feature(s) removed (Check 0)
  ⚠ {N} ambiguous feature(s) kept for review (Check 0)
  ✓ {N} duplicate(s) removed
  ✓ {N} syntax fix(es)
  ✓ {N} dead stub(s) removed
  ⚠ {N} potentially orphaned route(s)
  {N} heading issue(s)
```

Si Check 0 n'a trouvé aucun non-visual/ambiguous, omettre les lignes Check 0 (pas de bruit).

## Décisions de design

| Décision | Choix | Justification |
|----------|-------|---------------|
| Classification | Tri-state | Évite les faux négatifs sur les features mixtes |
| Action sur ambiguous | Keep + warn | Conservateur — pas de suppression silencieuse |
| Scope | Fichiers scaffoldés uniquement | Les pré-existants sont déjà validés |
| Position | Check 0 (premier) | Réduit le travail des checks suivants |
| Impact 4.7 | Même filtre | Même problème, même solution |

## Edge cases

- **Spec.md absent** : si le fichier spec n'existe pas, classifier comme `ambiguous` (ne pas supprimer sans info)
- **Feature hybride** (API + admin dashboard) : classifier comme `ambiguous` → warning
- **Idempotence** : si Check 0 re-tourne sur des fichiers déjà filtrés, les `visual` restent, les `non-visual` ont déjà été supprimés → noop
- **Dossiers baseline orphelins** : quand un fichier est supprimé, nettoyer aussi `baselines/mockups/{slug}/` s'il a été créé

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `commands/migrate.md` | Check 0 dans Step 4.6, filtre dans Step 4.7 Phase A, résumé dans Step 5 |
