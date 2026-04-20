# Plan: Migration 7 — E2E Test Generation

**Date:** 2026-04-20
**Design:** `docs/superpowers/specs/2026-04-20-migration-7-e2e-test-generation-design.md`

---

## Tasks

### Task 1: Créer `migrations/7/migrate.md`

**Fichier:** `migrations/7/migrate.md`
**Action:** Créer

```markdown
---
version: 7
description: "E2E interactive test generation from feature specs"
date: 2026-04-20
---

# Migration v7: E2E Test Generation

Bumps version to enable Step 4.7 (E2E test generation from Gherkin specs).
The actual generation runs unconditionally in commands/migrate.md Step 4.7.

## Actions

SET_VERSION 7
```

**Critère de done:** Fichier existe, parseable par `migrate.sh`.

---

### Task 2: Créer `scripts/generate-e2e-tests.js`

**Fichier:** `scripts/generate-e2e-tests.js`
**Action:** Créer (~300-400 lignes)

**Structure du script:**

```
1. Shebang + imports (fs, path)
2. Constants (SPECS_DIR, frontend detection indicators)
3. Frontend detection (same 9 indicators as migrate-visual-tests.js)
4. Spec parser:
   - extractGherkinBlocks(content) → [{feature, scenarios: [{name, steps}]}]
   - extractRoutes(content) → ['/route1', '/route2']
   - extractFeatureTitle(content) → string
5. Test existence checker:
   - hasExistingTest(testDir, featureNum, slug) → boolean
6. Gherkin-to-Playwright translator:
   - translateStep(step) → {code: string, matched: boolean}
   - translateScenario(scenario, route) → string (full test block or test.todo)
7. File generator:
   - generateTestFile(feature, scenarios, route, testDir, fixtures) → string
8. Main:
   - Parse args (--generate, --scan, --dry-run)
   - Detect frontend, find test dir
   - Detect fixtures (fixtures.ts, mock-server.ts)
   - For each feature: parse → check existing → generate
   - Emit sentinel: E2E_GENERATE_RESULT: files=N skipped=M [reason=...]
```

**Heuristiques de traduction (translateStep):**

```javascript
const PATTERNS = [
  { regex: /navigates? to (\S+)/i, code: (m) => `await page.goto('${m[1]}');` },
  { regex: /(?:is on|visits?) (?:the )?(\S+) page/i, code: (m) => `await page.goto('/${m[1]}');` },
  { regex: /clicks? (?:the |on )?(.+)/i, code: (m) => `await page.locator('[data-testid="TODO-${slugify(m[1])}"]').click();` },
  { regex: /enters? (.+) in (?:the )?(.+)/i, code: (m) => `await page.locator('[data-testid="TODO-${slugify(m[2])}"]').fill('${m[1]}');` },
  { regex: /submits? (?:the )?form/i, code: () => `await page.locator('[type="submit"]').click();` },
  { regex: /displays? (.+)/i, code: (m) => `await expect(page.locator('text=${m[1]}')).toBeVisible();` },
  { regex: /redirects? to (\S+)/i, code: (m) => `await page.waitForURL('**${m[1]}**');` },
  { regex: /(?:is|are) (?:not )?visible/i, code: (m) => `await expect(...).not.toBeVisible(); // TODO: specify locator` },
  { regex: /shows? (?:an? )?error/i, code: () => `await expect(page.locator('[role="alert"]')).toBeVisible();` },
  { regex: /does not/i, code: (m) => `// TODO: negate assertion — ${m.input}` },
];
```

**Critère de done:** Script exécutable, retourne sentinel, génère des fichiers qui compilent.

---

### Task 3: Modifier `commands/migrate.md` — ajouter Step 4.7

**Fichier:** `commands/migrate.md`
**Action:** Modifier

**Insertions:**

1. **Flowchart (ligne ~33):** Ajouter noeud E2E entre RECONCILE et DONE :
   ```
   AICHECK --> E2EGEN["E2E test generation\n(generate-e2e-tests.js)"]
   E2EGEN --> DONE
   ```
   Et sur le path "no" de RECONCILE :
   ```
   RECONCILE -->|"no"| E2EGEN
   ```

2. **Step 4.7 (après Step 4.6, ~ligne 189):** Insérer le bloc complet (guards, run, parse sentinel)

3. **Step 4.6 extension (~ligne 135):** Ajouter mention des `e2e-*.spec.ts` dans le glob des checks

4. **Step 5 rapport (~ligne 211):** Ajouter section E2E au template de sortie

**Critère de done:** Le command flow décrit correctement les 3 mécanismes (visual + reconciliation + E2E).

---

### Task 4: Modifier `VERSION`

**Fichier:** `VERSION`
**Action:** Modifier `6` → `7`

**Critère de done:** `cat VERSION` retourne `7`.

---

### Task 5: Test d'intégration

**Pas un fichier à créer** — vérification manuelle sur claude-pilot :
1. Remettre `.specs/livespec-version` à `6`
2. Lancer `/spec.migrate`
3. Vérifier que les `e2e-*.spec.ts` sont générés
4. Vérifier que les tests existants (`route-*.spec.ts`) ne sont pas touchés
5. Vérifier idempotence (relancer = 0 files created)

---

## Ordre d'exécution

```
Task 1 (migration file) ──┐
Task 2 (script)          ──┼── Parallélisables
Task 4 (VERSION)         ──┘
         │
         ▼
Task 3 (commands/migrate.md) ── Dépend de Task 2 (pour référencer le bon sentinel)
         │
         ▼
Task 5 (test intégration) ── Dépend de tout
```

**Tasks 1, 2, 4** sont indépendantes → parallélisables en subagents.
**Task 3** dépend de la structure finale du script (sentinel format).
**Task 5** est un test post-implémentation.

---

## Risques

| Risque | Mitigation |
|--------|-----------|
| Parser Gherkin trop fragile | Fallback `test.todo()` pour tout scénario non-parseable |
| Fichiers générés ne compilent pas | Utiliser uniquement des patterns syntaxiquement valides + test.todo |
| Collision avec tests visuels existants | Préfixe `e2e-` distinct |
| Script trop lent (beaucoup de features) | Pas de I/O réseau, juste du parsing de fichiers — rapide |
