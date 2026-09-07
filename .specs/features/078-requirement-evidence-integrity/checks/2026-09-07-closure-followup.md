# Spec-check qualité078 — suivi de clôture du témoin

Date :2026-09-07. Contrat neuf a0cfa9f96d4e61f72fb95c69f400909028401c7860b2848e37e08ba682b78873; flags `--quality --model=gpt-6-astra --review-max-chars=200000`.

## Résultat ciblé

Aucun finding supplémentaire dans la revue indépendante de witness_pipeline.py et test_witness_pipeline_closure.py. Les hashes courants correspondent exactement à la [revue indépendante](/Users/julienm/.codex/recovery/livespec-078-dd25/acceptance-lifecycle-fix/closure-followup-review.json).

- `_pipeline_closure` vérifie l'archive du même command/feature/policy avant de consommer ses flags modèle/budget.
- `_terminal_pipeline` fournit `--feature` (option réellement requise par Typer); exit2 n'est terminal que sans stdout/stderr, timeout ou contrôle incomplet.
- Les tests traversent le vrai CLI Typer pour terminal/pending/usageerror et refusent le contrôle incomplet.
- AGENTS candidat impose le CLI du snapshot et son interpréteur autoritatif pour les commandes certifiantes. Cette instruction n'est pas en elle-même une preuve d'utilisation; la capture runtime reste nécessaire.

Le parent indique18tests ciblés passants. Aucun test ni suite globale relancé par ce contrôle. Les observations sont documentaires, distinctes d'une capture indépendante fraîche.

## Écarts de fermeture restants

| Point | État |
|---|---|
| Suivi du faux exit2/modèle/provenance | Correction inspectée, sans finding; capture finale après ces écritures encore requise. |
| G2 —baseline076 | Toujours incomplète; huit documents authentiques ne prouvent ni inventaire initial complet ni log manquant. |
| G3 —nativev9 | Parent55/55 ne suffit pas à certifier la clôture; reprise3 de provenance en cours au moment du contrôle. Aucun native success inféré. |

## Tree Validation et Spec Quality

Système et3ADR présents, noms valides, README synchronisé, pas d'orphelin direct; artefacts078 présents. NON_VISUAL. Diagnostics structurels CLI frais stockés dans les [preuves de ce run](/Users/julienm/.codex/recovery/livespec-078-dd25/check-closure-followup) :spec80,plan100,implementation20. Ils conservent les erreurs de statut/frontmatter/titres/anchor déjà connues, sans nouveau chantier général ni PASS sémantique.

## FR table

| FR | État |
|---|---|
| FR-001 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-002 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-003 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-004 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-005 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-006 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-007 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-008 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-009 | Suivi de clôture inspecté, aucun nouveau finding; preuve native finale en attente. |
| FR-010 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-011 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-012 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-013 | Suivi de clôture inspecté, aucun nouveau finding; preuve native finale en attente. |
| FR-014 | Suivi de clôture inspecté, aucun nouveau finding; preuve native finale en attente. |
| FR-015 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |
| FR-016 | Mapping existant conservé; aucune nouvelle certification globale dans ce contrôle. |

## AC table

| AC | État |
|---|---|
| AC-001 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-002 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-003 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-004 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-005 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-006 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-007 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-008 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-009 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-010 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-011 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-012 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-013 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-014 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-015 | Partiel pour fermeture totale078; capturecourante finale/nativepipeline non certifiés par ce contrôle documentaire. |
| AC-016 | Non prouvé :baseline076 incomplète. |

## Convention Compliance

Domaine code chargé via index :general/python/javascript/cli/stack-commands. Vérifications explicites de statut, erreur et provenance inspectées. Aucun code modifié ici; aucun nouveau PASS statique global. Dette statique historique hors scope, pas d'audit général supplémentaire.

## Summary et Suggested Fixes

Le contrôle documentaire est effectué, la feature reste partielle. Capturer la preuve finale après les dernières écritures; terminer la reprise nativev9 avec son interpréteur autoritatif et vérifier archive/provenance/oracle réels. Préserver anciens contrats et échecs. Pour076, obtenir l'inventaire/log initial authentique ou une décision explicite sur la limite. Aucun Implemented/Success/10sur10 revendiqué; implementation.md inchangé (`--update` absent).
