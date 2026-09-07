# Check078 — acceptation finale du coordinateur

Date :2026-09-07. Contrat indépendant :937662620b8067eba139ad33fa02255c974d7fbb7d08b5251c15ca200cba219d. Correction inspectée :FR-009 et packaging du témoin. Aucun code/test/spec/plan modifié par ce contrôle; aucune suite relancée.

## Correction observée

Le marqueur explicite `ac-binding:reviewed-spec` est limité à une tâche finale d'exécution inconditionnelle. Il lie le coordinateur créé avant la spec à une revue actuelle de type spec, avec modèle et budget du contrat. Au moment de prouver, le vérificateur exige un inventaire courant non vide, toute l'acceptation runtime ET les AC documentaires déclarées. L'archive et sa relecture repassent par les obligations immuables. Sans ce marqueur, la comparaison avec l'inventaire figé reste inchangée : les anciens contrats v8 ne sont pas réinterprétés.

Inspecter [acceptance_evidence.py](../../../../validator/acceptance_evidence.py), [evidence_policy.py](../../../../validator/evidence_policy.py), [goal_generic_evidence.py](../../../../validator/goal_generic_evidence.py) et [goal_review_identity.py](../../../../validator/goal_review_identity.py). Les tests couvrent preuve/archive/relecture réelles, revue supprimée après archivage, revue manquante/fausse/de type plan/étrangère/périmée, preuve documentaire absente, nouvel AC non exécuté, ancien inventaire vide et métadonnées invalides. Lire les [tests coordinateur](../../../../tests/test_coordinator_acceptance.py).

Le snapshot copie et hashe les fixtures et tests déterministes référencés par les catalogues. Une dépendance absente ou non sûre invalide son identité. `_finish` convertit les erreurs de lecture d'identité en résultat `invalid`, conservé dans le rapport, au lieu de perdre le résultat du trial. Lire le [snapshot](../../../../tests/integration/helpers/witness_snapshot.py), la [finalisation du trial](../../../../tests/integration/helpers/witness_pipeline.py) et les [régressions de persistance](../../../../tests/test_witness_snapshot_integrity.py).

Aucun nouveau défaut bloquant identifié dans cette inspection ciblée. Cette conclusion documentaire ne remplace pas la revue indépendante du mapping ni la capture complète à venir.

## Validation et limites

Consulter les [observations ciblées du parent](/Users/julienm/.codex/recovery/livespec-078-dd25/acceptance-lifecycle-fix/targeted-observations.json) :56tests PASS en20.90s,3tests de snapshot PASS en0.72s, Ruff PASS et pyright0erreur/0warning sur quatre modules. Provenance explicitement déclarée : sorties exec réelles consignées par le parent, pas un receipt runner indépendant. Le test de packaging traverse réellement CLI conventions refresh, gates init et verify, puis mutation/suppression d'une dépendance.

Lire le [receipt conventions daté](../../../conventions/runs/20260907T105030Z/receipt.json) :PASS, zéro blocker, hash7ab1c44515c0e6ea2f30f21c46a6bfe4aa0cb1087163ec167c17d97c3f78ce2a. Il s'agit d'une observation à son instant, pas d'une promesse de fraîcheur après ces écritures.

## État des trois points

| Point | État réel |
|---|---|
| G1 —57bindings | Correction précédente certifiée historiquement. Cette nouvelle version FR-009 exige une revue/mapping et une capture complète fraîche après les écritures; non revendiquées ici. |
| G2 —076 | Huit documents historiques authentiques établis; inventaire initial complet et log manquants. AC-016 reste non prouvé. |
| G3 —parcours agentique | v8 :toutes phases affichées Done et oracle indépendant PASS4assertions, mais parent48/55; tâche049 rejette inventaire figé vide. `closure=false`, `pipeline_verified=false`, outcome=failure. Nouveau trial après correction encore à venir. |

Consulter le [résumé final v8](/Users/julienm/.codex/recovery/livespec-078-dd25/pipeline-v8-resume-6-summary.json) :durée de cette reprise1655.795405167s, timeout=false, raison=pipeline_closure_not_independently_verified. Les phases Done et l'oracle PASS ne suffisent pas à établir la clôture du coordinateur. Ancien contrat conservé. Consulter la [preuve076 bornée](/Users/julienm/.codex/recovery/livespec-078-dd25/076-baseline-assessment.json).

## Tree Validation et Spec Quality

Fichiers système et3ADR présents; noms valides, pas d'orphelin direct, README synchronisé;078 dispose des artefacts attendus. NON_VISUAL. Diagnostics structurels actuels conservés séparément :spec80,plan100,implementation20; erreurs de statut/frontmatter/titres/anchor déjà signalées, aucun chantier général lancé. Lire les [sorties brutes du check](/Users/julienm/.codex/recovery/livespec-078-dd25/check-coordinator).

## FR table

| FR | Résultat documentaire |
|---|---|
| FR-001 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-002 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-003 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-004 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-005 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-006 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-007 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-008 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-009 | Correction reviewed-spec inspectée; validations ciblées observées, capture complète en attente. |
| FR-010 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-011 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-012 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-013 | Packaging et persistance invalid inspectés; pas de succès agentique complet. |
| FR-014 | Packaging et persistance invalid inspectés; pas de succès agentique complet. |
| FR-015 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |
| FR-016 | Mapping existant conservé; pas de nouvelle certification complète dans ce contrôle. |

## AC table

| AC | Résultat |
|---|---|
| AC-001 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-002 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-003 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-004 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-005 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-006 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-007 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-008 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-009 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-010 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-011 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-012 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-013 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-014 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-015 | Certification actuelle à renouveler après nouvelles corrections/écritures; aucun PASS global inféré. |
| AC-016 | Non prouvé :baseline076 incomplète. |

## Convention Compliance

Domaine code résolu par index :general/python/javascript/cli/stack-commands. Typage, validation de frontière, provenance explicite et refus de succès sans preuve inspectés. Aucun code produit ici. Le receipt conventions daté et statiques ciblées sont distincts de la dette statique globale historique, exclue de ce chantier.

## Summary et Suggested Fixes

Contrôle effectué, fermeture globale partielle. Après les écritures obligatoires, compléter la revue indépendante du mapping et la capture complète courante; effectuer un nouveau trial sur le workflow corrigé. Pour076, obtenir la baseline/inventaire/log authentiques ou une décision explicite sur la limite. Ne pas réparer les anciens contrats en place ni transformer leurs phases Done en Success. Aucun Implemented/10sur10 revendiqué.
