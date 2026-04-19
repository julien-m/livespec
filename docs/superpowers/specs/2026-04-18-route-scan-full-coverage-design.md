# Design: Route Scan + Full Coverage — migrate-visual-tests.js

**Date:** 2026-04-18
**Status:** Approved

## Problème

`migrate-visual-tests.js --generate` ne couvre que les features dans `.specs/features/`. Les pages frontend sans spec (ex: `audit.tsx`, `setup.tsx`, `tasks.tsx`, page 404) ne sont jamais testées visuellement.

Résultat: 8 vieux tests non-numérotés (`dashboard.spec.ts`, `audit.spec.ts`, etc.) coexistent avec 14 tests numérotés générés, créant des doublons et des oublis.

## Objectif

`--generate` produit une couverture **totale** : chaque page frontend a un test généré. Les anciens tests non-numérotés sont automatiquement remplacés.

## Architecture

### Deux sources de scan

```
Source 1 (existant): .specs/features/
  → Scan des spec dirs → 14 tests NNN-slug.spec.ts (spec-driven)

Source 2 (nouveau): frontend/app/routes/ (auto-détecté)
  → Scan des fichiers de routes → tests route-slug.spec.ts (route-scan)
```

### Nommage

| Source | Exemple | Préfixe |
|--------|---------|---------|
| Spec-driven | `004-real-time-dashboard.spec.ts` | `NNN-` |
| Route-scan | `route-audit.spec.ts` | `route-` |

### Couverture garantie

```
Chaque route détectée dans frontend/app/routes/ est soit:
  A) Couverte par un test numéroté (spec-driven) → skip route-scan
  B) Non couverte → génère route-{slug}.spec.ts
```

### Suppression automatique

Après génération, supprime les vieux fichiers non-numérotés et non-`route-` préfixés dont la route est maintenant couverte.

```
dashboard.spec.ts  → /dashboard  ← couvert par 004-real-time-dashboard.spec.ts → DELETE
audit.spec.ts      → /audit      ← couvert par route-audit.spec.ts             → DELETE
```

## Nouveaux composants

### `detectRoutesDir()`

```
Candidate dirs (ordered):
  frontend/app/routes
  src/app/routes
  app/routes
  src/routes
  src/pages
  pages

Return: first existing dir, or null
```

### `scanRouteFiles(routesDir)`

Pour chaque fichier `.tsx/.jsx/.vue` dans le répertoire :
- **Skip**: `__root.tsx`, fichiers `_*` (layouts), fichiers redirect-only
- **Route**: `dashboard.tsx` → `/dashboard`, `index.tsx` → `/` (si non-redirect)
- **Heading**: regex `<h[12][^>]*>([^<{]+)<\/h[12]>` → slug capitalisé fallback
- **TestPath**: `TEST_DIR/route-{slug}.spec.ts`

### `detectNotFoundFromRoot(routesDir)`

- Lit `__root.tsx` dans le même répertoire
- Cherche `notFoundComponent`
- Si trouvé → retourne `{ slug: 'not-found', route: '/nonexistent-page-404', heading: 'Not Found' }`

### `buildCoveredRoutes(specFeatures)`

Pour chaque feature spec:
- Lit son `spec.md` via `parseSpecContext`
- Extrait la route
- Aussi: normalise le slug du dir de feature → route heuristique
- Retourne `Set<string>` des routes couvertes

```
004-real-time-dashboard → parseSpecContext → /dashboard
001-authentication      → parseSpecContext → /login
```

### `deleteSupersededTests()`

Après toute génération:
1. Lister tous les fichiers dans `TEST_DIR`
2. Filtrer: non-numérotés ET non-`route-` préfixés
3. Pour chaque fichier: inférer sa route (slug depuis filename)
4. Si sa route est dans `coveredRoutes` → DELETE + log

```
Deleted (superseded):
  dashboard.spec.ts  → /dashboard  (covered by 004-real-time-dashboard.spec.ts)
  audit.spec.ts      → /audit      (covered by route-audit.spec.ts)
```

### Politique d'écrasement

| Type de fichier | Comportement |
|-----------------|-------------|
| `NNN-*.spec.ts` (numéroté) | Jamais écraser (AC-030) |
| `route-*.spec.ts` (route-scan) | Toujours écraser |
| Autres (legacy) | Supprimés après génération |

## Template route-scan

Identique à `generateE2ETemplate` mais:
- `specCtx.acRows = []` → pas d'extra tests spec-aware
- Pas d'import `existsSync` pour mockup (simplifié)
- HEADING vient du heading extrait de la route ou du slug capitalisé
- 4 tests de base: full page, empty state, header, mobile

## Flux `--generate` mis à jour

```
1. scanFeatures()          → liste des features spec-driven
2. analyzeExistingTests()  → fixtures, selectors du projet
3. buildCoveredRoutes()    → Set des routes couvertes par tests numérotés
4. detectRoutesDir()       → répertoire de routes (ou null)
5. scanRouteFiles()        → routes non couvertes
6. detectNotFoundFromRoot() → page 404 si presente
7. Pour chaque feature spec → generateTests() (AC-030)
8. Pour chaque route non couverte → generateRouteTest() (écraser)
9. deleteSupersededTests() → supprimer les anciens
10. printCompletionReport() → rapport complet
```

## Edge Cases

| Cas | Comportement |
|-----|-------------|
| Aucun répertoire de routes trouvé | Warning + continue spec-only |
| Route déjà couverte par test numéroté | Skip silencieux |
| `<h1>` dynamique `{title}` | Fallback slug capitalisé |
| `__root.tsx` absent | Skip détection 404 |
| Fichier route avec `redirect(` mais aussi `<h1>` | Inclure (a du contenu visuel) |
| `--dry-run` | Afficher ce qui serait généré/supprimé sans toucher aux fichiers |

## Impact sur les tests existants livespec

Les tests unitaires de `010-visual-testing-complete` couvrent `migrate-visual-tests.js`. Il faudra mettre à jour le fixture `migrate-visual/` pour inclure un répertoire `frontend/app/routes/` de test.
