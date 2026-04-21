# Plan: Check 0 — Filtre AI sémantique des features non-UI

**Spec:** `docs/superpowers/specs/2026-04-21-check0-ai-ui-filter-design.md`
**Fichier cible unique:** `commands/migrate.md`

## Modifications

### 1. Insérer Check 0 dans Step 4.6 (avant Check 1)

**Position exacte :** Après le paragraphe "Procedure:" (ligne 136) et avant "#### Check 1" (ligne 138).

**Contenu à insérer :**

```markdown
#### Check 0: Non-visual feature filter (AI semantic — run first)

For each `.spec.ts` file **created by Step 4.5** (not pre-existing files):

1. Extract the feature directory name from the test filename (e.g., `007-api-push.spec.ts` → `007-api-push`)
2. Read `.specs/features/{feature-dir}/spec.md`
   - If spec.md does not exist → classify as `ambiguous`
3. Classify the feature using semantic judgment:

   > Feature directory: `{feature-dir}`
   >
   > Read this feature spec. Does it describe something the end user interacts with visually in a web browser (a page, screen, dialog, component, dashboard, form)?
   >
   > A CLI tool, REST/GraphQL API endpoint, background worker, caching layer, SDK library, or infrastructure service is NOT visual — even if its spec mentions words like "response", "input", "output", "table", or "list" in a non-UI context.
   >
   > Answer: VISUAL, NON-VISUAL, or AMBIGUOUS (with one-line rationale).

4. Act on classification:
   - **VISUAL:** No action. Store `CHECK0_RESULTS[feature-dir] = visual`.
   - **NON-VISUAL:** Delete the scaffolded `.spec.ts` file. Delete baseline directories created for this feature (`baselines/mockups/{slug}/` or equivalent). Store `CHECK0_RESULTS[feature-dir] = non-visual`. Log: `Check 0: deleted {file} (non-visual feature: {rationale})`
   - **AMBIGUOUS:** Keep the file. Insert `// ⚠️ CHECK: This feature may not have a browser UI — verify before running` as the first line. Store `CHECK0_RESULTS[feature-dir] = ambiguous`. Log: `⚠ Check 0: kept {file} (ambiguous: {rationale})`

**Post-Check 0:** If all scaffolded files were deleted (0 files remaining), skip Checks 1-5 with log: `Checks 1-5: skipped (0 files remaining after Check 0)`. Store `CHECK0_RESULTS` for reuse by Step 4.7.
```

### 2. Renommer les checks existants dans la Procedure intro

**Ligne 136 actuelle :**
> Apply the 5 checks below **in order**.

**Remplacer par :**
> Apply the 6 checks below **in order** (Check 0 first, then Checks 1-5).

### 3. Mettre à jour l'early exit et les références "5 checks"

**Ligne 184 actuelle :**
> **Early exit:** If all 5 checks pass with zero findings, log `Visual test reconciliation: clean — no issues found` and skip to Step 5.

**Remplacer par :**
> **Early exit:** If all 6 checks (0-5) pass with zero findings, log `Visual test reconciliation: clean — no issues found` and skip to Step 5. If Check 0 removed all files, skip Checks 1-5 and proceed to Step 4.7.

**Convention de numérotation :** Le nouveau check est "Check 0" (zéro-indexé). Les checks existants gardent leurs numéros 1-5. Total : 6 checks numérotés 0-5. La prose dit "6 checks" et les headers markdown restent `#### Check 0:` à `#### Check 5:`.

### 4. Ajouter le filtre dans Step 4.7 Phase A

**Position exacte :** Dans la section Phase A (ligne ~198-204), après la construction de `FEATURES_TO_GENERATE`.

**Clarification importante :** "non-visual" dans Step 4.7 signifie "la feature n'a aucune interface utilisateur dans un navigateur" (CLI pur, API sans UI, worker background). Ce n'est PAS la même chose que "pas de test de regression visuelle" — une feature avec un formulaire web est visual même si elle n'a pas de mockup Figma. Les features qui ont une UI (page, écran, formulaire) doivent garder leurs tests E2E même si elles sont `ambiguous` côté visual.

**Insérer après la ligne qui construit `FEATURES_TO_GENERATE` :**

```markdown
5. **Filter non-visual features:** For each feature in `FEATURES_TO_GENERATE`:
   - If `CHECK0_RESULTS[feature-dir]` exists and equals `non-visual` → remove from list
   - If `CHECK0_RESULTS[feature-dir]` does not exist (feature not scaffolded in Step 4.5) → apply the same AI classification as Check 0. If `non-visual` → remove from list. Store the result in `CHECK0_RESULTS`.
   - `ambiguous` and `visual` features remain in the list
   - Log removed features: `E2E generation: skipped {feature-dir} (non-visual — no browser UI)`
```

### 5. Mettre à jour le report Step 5

**Position exacte :** Dans le bloc réconciliation summary (lignes 337-361).

**Remplacer le bloc "If FIXES > 0" :**

```markdown
If `FIXES > 0` or Check 0 had findings, list each action:
```
Visual test reconciliation:
  ✓ {N} non-visual feature(s) removed (Check 0)
  ⚠ {N} ambiguous feature(s) kept for review (Check 0)
  ✓ {N} duplicate(s) removed
  ��� {N} syntax fix(es)
  ✓ {N} dead stub(s) removed
  ⚠ {N} potentially orphaned route(s)
  {N} heading issue(s)
```

Omit Check 0 lines if both counts are 0 (no noise when all features are visual).
```

### 6. Mettre à jour le diagramme mermaid

**Dans le flowchart (lignes 35-39)**, remplacer :
```
AICHECK["AI reconciliation\n(5 checks)"]
```
par :
```
AICHECK["AI reconciliation\n(6 checks: UI filter + 5)"]
```

## Ordre d'exécution

Toutes les modifications sont dans le même fichier (`commands/migrate.md`), appliquées séquentiellement de haut en bas pour éviter les conflits d'offset.

## Vérification

Après implémentation :
1. Relire `commands/migrate.md` de bout en bout pour vérifier la cohérence
2. Vérifier que les numéros de checks sont cohérents (0, 1, 2, 3, 4, 5)
3. Vérifier que le diagramme mermaid reflète le nouveau flow
