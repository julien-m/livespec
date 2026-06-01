# FORMAT CONTRACT — Brainstorm ↔ LiveSpec Sync
<!-- version: 1.0.0 | created: 2026-05-27 | status: draft -->

> **Source de vérité** pour trois workers en aval :
> - **Worker B1** (pilot) — écrit ces fichiers depuis le repo `project-brainstorm`
> - **Worker A2** (spec-refresh-from-brainstorm) — lit ces fichiers via le symlink depuis le vrai projet
> - **Worker D** (tests E2E) — génère des fichiers de test valides depuis ces schémas

---

## 1. Topologie des fichiers

```
<project-brainstorm-root>/projects/<slug>/
├── lifecycle/
│   ├── log.ndjson               # Journal append-only (source de vérité)
│   ├── log.sha256               # Index hashes par event_id (optionnel, régénérable)
│   ├── state.yaml               # État dérivé, régénéré à la demande
│   ├── bets/
│   │   ├── B-001.yaml
│   │   ├── B-002.yaml
│   │   └── ...
│   └── mutations/
│       ├── M-001/
│       │   ├── decision.md
│       │   ├── impacts.yaml
│       │   └── rationale.md
│       └── ...
```

> Le vrai projet (ex. `~/projects/ylune`) contient un symlink  
> `brainstorm → ~/projects/project-brainstorm/projects/ylune`  
> `spec-refresh-from-brainstorm` traverse ce symlink pour lire `lifecycle/`.

---

## 2. Schéma — `lifecycle/log.ndjson`

### Règles structurelles

- Une ligne = un objet JSON valide.
- Les lignes sont en ordre chronologique strict (`ts` croissant).
- **Append-only** : aucune ligne existante ne peut être modifiée ou supprimée.
- Le champ `event` discrimine le type ; les champs listés comme _required_ **doivent** être présents.
- **Règle nullable vs omis** : les champs marqués `string \| null` (ex : `hypothesis_ref`) acceptent `null` comme valeur explicite — ils doivent toujours être présents. Les champs marqués `opt` sont **OMIS** du JSON si non applicables — jamais `null` ni chaîne vide pour les champs `opt`.

### Champs communs à tous les events

| Champ | Type | Req | Description |
|---|---|---|---|
| `event_id` | string | ✓ req non-null | Identifiant unique — format `E-XXXXXX` (6 digits, incrément strict). Premier event = `E-000001`, jamais réutilisé |
| `event` | string enum | ✓ req non-null | Type d'événement (voir table ci-dessous) |
| `schema_version` | integer | ✓ req non-null | Version du schéma de cet event (commence à `1`) |
| `ts` | ISO 8601 UTC | ✓ req non-null | Horodatage (`2026-05-27T14:32:53Z`) |
| `prev_hash` | string | ✓ req non-null¹ | SHA-256 hex de la ligne JSON canonicalisée précédente (voir §2.0) |
| `rationale` | string | ✓ req non-null | Pourquoi cet événement se produit maintenant |
| `hypothesis_ref` | string \| null | ✓ req nullable | Identifiant hypothèse liée (`"H3"`) ou `null` si non applicable |
| `expected_impact` | string | ✓ req non-null | Impact attendu ou critère de retrait (ex : `"Réduit churn onboarding de 20%"`) |
| `author` | string | ✓ req non-null | Auteur humain ou agent (`"pilot/propose"`, `"user"`) |

> ¹ `prev_hash` : omis uniquement pour `E-000001` (premier event du log — pas de précédent).

> **Garde-fou :** tout event sans les 3 champs `rationale` + `hypothesis_ref` + `expected_impact` est rejeté par le skill `pilot` à l'écriture.

### Types d'events

| `event` | Usage |
|---|---|
| `observation` | Fait empirique observé (metric, feedback, signal marché) |
| `decision` | Décision stratégique ou produit actée |
| `pivot` | Changement de direction majeur sur une hypothèse ou une feature |
| `feature-add` | Ajout d'une feature post-GO |
| `feature-remove` | Retrait d'une feature avec preuve |
| `hypothesis-update` | Mise à jour du statut d'une hypothèse (H1–H12) |
| `bet-created` | Création d'un pari B-NNN |
| `bet-resolved` | Résolution d'un pari B-NNN |
| `mutation-created` | Création d'un dossier mutation M-NNN |

---

### 2.0 Canonicalisation JSON (pour calcul `prev_hash`)

La chaîne canonicale d'une ligne `log.ndjson` est la représentation JSON avec :

1. **Clés ordonnées alphabétiquement** à tous les niveaux.
2. **Séparateurs sans espaces** : `","` entre éléments, `":"` entre clé et valeur.
3. **Encoding UTF-8 sans BOM**.
4. **Pas de trailing newline** dans la chaîne hashée (le `\n` de fin de ligne dans le fichier est exclu du calcul).
5. **Floats** : représentation minimale (`1.5` et non `1.50`). **Integers** : sans `.0` (`2` et non `2.0`).

Exemple d'event canonicalisé (E-000001) :

```
{"author":"pilot/observe","event":"observation","event_id":"E-000001","expected_impact":"Si confirmé, simplifier le questionnaire réduit le churn onboarding IT","hypothesis_ref":"H2","rationale":"Feedback de 3 praticiennes beta IT","schema_version":1,"ts":"2026-05-27T10:00:00Z"}
```

Le SHA-256 de cette chaîne exacte devient le `prev_hash` de E-000002.

**`lifecycle/log.sha256`** (optionnel) : une ligne par event, format `<event_id> <sha256_hex>`.  
Exemple : `E-000001 a3f2c1...`.  
Régénérable à tout moment par `pilot state --recompute-hashes`. A2 utilise ce fichier comme index rapide si présent ; sinon recompute depuis `log.ndjson`.

> **Note** : les exemples JSON des sections §2.1–§2.9 ci-dessous n'incluent pas les champs communs (`event_id`, `schema_version`, `prev_hash`, `author`) pour la lisibilité. Ces champs sont **toujours requis** dans le fichier réel.

---

### 2.1 Event `observation`

```json
{
  "event": "observation",
  "ts": "2026-05-27T10:00:00Z",
  "rationale": "Feedback de 3 praticiennes beta IT sur la complexité du questionnaire pré-séance",
  "hypothesis_ref": "H2",
  "expected_impact": "Si confirmé, simplifier le questionnaire réduit le churn onboarding IT",
  "body": "Les praticiennes IT demandent max 3 champs au questionnaire ; 7 champs perçus comme trop intrusifs.",
  "source": "beta-feedback",
  "geo": "IT"
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `body` | string | ✓ | Contenu factuel de l'observation |
| `source` | string | opt | Origine (`"beta-feedback"`, `"analytics"`, `"user-interview"`, `"market-research"`) |
| `geo` | string | opt | Marché concerné (`"FR"`, `"IT"`, `"DE"`, `"ES"`, `"UK"`, `"US"`) |

---

### 2.2 Event `decision`

```json
{
  "event": "decision",
  "ts": "2026-05-27T11:00:00Z",
  "rationale": "Break-even praticienne IT confirmé à €380/mois ; le pricing €19/mo est validé par 3 pre-pays IT",
  "hypothesis_ref": "H1",
  "expected_impact": "Déblocage Sprint 1 — onboarding IT+FR activé",
  "title": "Vague 1 activée : IT + FR simultané",
  "supersedes": null
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `title` | string | ✓ | Intitulé court de la décision |
| `supersedes` | string \| null | opt | ID d'un event précédent remplacé (`"decision-2026-04-23T..."`) ou `null` |

---

### 2.3 Event `pivot`

```json
{
  "event": "pivot",
  "ts": "2026-05-28T09:00:00Z",
  "rationale": "Résistance au double prélèvement (sub + commission) confirmée sur DE après 5 entretiens",
  "hypothesis_ref": "H3",
  "expected_impact": "Passage au modèle merchant-of-record DE pour éliminer la commission visible praticienne",
  "from": "Stripe Connect pur — commission 10% Starter / 5% Pro visible",
  "to": "Paddle merchant-of-record sur DE — commission masquée dans le prix praticienne",
  "hypothesis_new_status": "pivoting"
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `from` | string | ✓ | État avant le pivot |
| `to` | string | ✓ | État après le pivot |
| `hypothesis_new_status` | string enum | ✓ | Nouveau statut hypothèse liée : `"open"`, `"validated"`, `"invalidated"`, `"pivoting"` |

---

### 2.4 Event `feature-add`

```json
{
  "event": "feature-add",
  "ts": "2026-05-29T14:00:00Z",
  "rationale": "Les praticiennes DE attendent un modèle reseller ; Bizum quasi-obligatoire en ES",
  "hypothesis_ref": "H6",
  "expected_impact": "Déblocage vague 2 DE+ES, +15% conversion praticienne sur ces marchés",
  "feature_id": "multi-psp-routing",
  "feature_title": "Routage PSP par géo (Stripe Connect + Paddle + Bizum)",
  "origin": "added",
  "priority": "P1",
  "target_geo": ["DE", "ES"]
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `feature_id` | string | ✓ | Slug technique (`kebab-case`) |
| `feature_title` | string | ✓ | Titre lisible |
| `origin` | `"initial"` \| `"added"` | ✓ | `"initial"` = existait au brainstorm ; `"added"` = post-GO |
| `priority` | string | opt | `"P0"`, `"P1"`, `"P2"` |
| `target_geo` | string[] | opt | Marchés cibles |

---

### 2.5 Event `feature-remove`

```json
{
  "event": "feature-remove",
  "ts": "2026-06-01T10:00:00Z",
  "rationale": "Mode communauté (groupes de praticiennes) ne convertit pas — 0 demande sur 40 beta",
  "hypothesis_ref": null,
  "expected_impact": "Allège le périmètre MVP, focus praticienne individuelle uniquement",
  "feature_id": "community-mode",
  "feature_title": "Mode communauté — groupes de praticiennes",
  "new_status": "cancelled",
  "evidence": "40 beta interviewées, 0 mention du besoin de groupes. Scope creep confirmé."
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `feature_id` | string | ✓ | Slug technique |
| `feature_title` | string | ✓ | Titre lisible |
| `new_status` | `"removed"` \| `"cancelled"` \| `"deprecated"` | ✓ | `"removed"` = retiré avec preuve, `"cancelled"` = jamais implémenté, `"deprecated"` = retiré après implémentation |
| `evidence` | string | ✓ | Preuve justifiant le retrait |

---

### 2.6 Event `hypothesis-update`

```json
{
  "event": "hypothesis-update",
  "ts": "2026-06-10T08:00:00Z",
  "rationale": "10 pre-pays €19 reçus en 14j sur FR+IT — seuil GO/NO-GO atteint",
  "hypothesis_ref": "H1",
  "expected_impact": "Libère Sprint 1 — validation WTP multi-langues actée",
  "new_status": "validated",
  "evidence_summary": "10 paiements Stripe : 6 FR, 4 IT. Panier moyen premier mois €19. 0 refus."
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `new_status` | `"open"` \| `"validated"` \| `"invalidated"` \| `"pivoting"` | ✓ | Nouveau statut |
| `evidence_summary` | string | ✓ | Résumé factuel des preuves |

---

### 2.7 Event `bet-created`

```json
{
  "event": "bet-created",
  "ts": "2026-05-27T15:00:00Z",
  "rationale": "H1 non encore validée — pari sur le WTP IT avant de débloquer Sprint 1",
  "hypothesis_ref": "H1",
  "expected_impact": "Si B-001 résolu positivement, onboarding IT activé",
  "bet_id": "B-001",
  "bet_title": "WTP praticienne IT validé à €19/mois"
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `bet_id` | string | ✓ | Identifiant (`B-NNN`) |
| `bet_title` | string | ✓ | Titre court |

---

### 2.8 Event `bet-resolved`

```json
{
  "event": "bet-resolved",
  "ts": "2026-06-10T08:00:00Z",
  "rationale": "4 pre-pays IT reçus avant la deadline — seuil 2/langue atteint",
  "hypothesis_ref": "H1",
  "expected_impact": "Décision de lancer la vague 1 IT+FR actée",
  "bet_id": "B-001",
  "resolution": "won",
  "resolution_note": "4 paiements IT confirmés Stripe avant expiration B-001."
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `bet_id` | string | ✓ | Identifiant (`B-NNN`) |
| `resolution` | `"won"` \| `"lost"` \| `"expired"` | ✓ | Résultat |
| `resolution_note` | string | ✓ | Explication factuelle |

---

### 2.9 Event `mutation-created`

```json
{
  "event": "mutation-created",
  "ts": "2026-06-15T11:00:00Z",
  "rationale": "Retrait du mode communauté décidé post-beta — mutation majeure nécessite artefacts dédiés",
  "hypothesis_ref": null,
  "expected_impact": "Périmètre MVP allégé, focus praticienne individuelle uniquement",
  "mutation_id": "M-001",
  "mutation_title": "Retrait mode communauté",
  "artefacts_touched": ["features/community-mode", "04-identity.md"]
}
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `mutation_id` | string | ✓ | Identifiant (`M-NNN`) |
| `mutation_title` | string | ✓ | Titre court |
| `artefacts_touched` | string[] | ✓ | Index rapide des chemins relatifs impactés |

> **`artefacts_touched` vs `impacts.yaml`** : `artefacts_touched` dans l'event est un **index rapide** (string[]) permettant à A2 de détecter rapidement si une mutation concerne des artefacts `.specs/`. La **source de vérité structurée** (path + action + section + note) est dans `lifecycle/mutations/M-NNN/impacts.yaml`. A2 lit **toujours** `impacts.yaml`, pas le champ event, pour exécuter les actions.

---

## 3. Schéma — `lifecycle/state.yaml`

> **Dérivé** de `log.ndjson`, régénéré par `pilot state` à la demande.  
> Ne jamais éditer manuellement.

```yaml
# GÉNÉRÉ AUTOMATIQUEMENT par `pilot state`
# Source : lifecycle/log.ndjson
# Ne pas éditer manuellement.
project_slug: ylune
last_event_at: "2026-06-10T08:00:00Z"

hypotheses:
  H1:
    text: "Les praticiennes ressentent suffisamment la friction des outils actuels pour payer"
    status: validated          # open | validated | invalidated | pivoting
    last_updated_at: "2026-06-10T08:00:00Z"
    evidence_summary: "10 pre-pays €19 (6 FR, 4 IT) reçus en 14j."
  H2:
    text: "Le questionnaire pré-séance est perçu comme un différenciateur, pas une contrainte"
    status: open
    last_updated_at: null
    evidence_summary: null
  H3:
    text: "Le tier commission-only (10%) convertit des praticiennes qui refusaient un abonnement"
    status: pivoting
    last_updated_at: "2026-05-28T09:00:00Z"
    evidence_summary: "Résistance double prélèvement confirmée DE — pivot merchant-of-record."
  # H4–H12 omis pour concision ; même structure

features:
  questionnaire-pre-seance:
    title: "Questionnaire pré-séance configurable"
    origin: initial            # initial | added
    status: initial            # initial | added | removed | cancelled | deprecated
    priority: P0
    hypothesis_refs: ["H2"]
    last_updated_at: "2026-05-27T14:32:53Z"
  multi-psp-routing:
    title: "Routage PSP par géo (Stripe Connect + Paddle + Bizum)"
    origin: added
    status: added
    priority: P1
    hypothesis_refs: ["H6"]
    last_updated_at: "2026-05-29T14:00:00Z"
    target_geo: ["DE", "ES"]
  community-mode:
    title: "Mode communauté — groupes de praticiennes"
    origin: initial
    status: cancelled
    priority: null
    hypothesis_refs: []
    last_updated_at: "2026-06-01T10:00:00Z"
    removal_evidence: "40 beta interviewées, 0 mention du besoin."

bets:
  B-001:
    title: "WTP praticienne IT validé à €19/mois"
    status: resolved           # open | resolved | expired
    resolution: won            # won | lost | expired | null
    resolved_at: "2026-06-10T08:00:00Z"
    expires_at: "2026-06-15T23:59:00Z"
  B-002:
    title: "Taux de no-show sans acompte > 15% sur FR"
    status: open
    resolution: null
    resolved_at: null
    expires_at: "2026-07-01T23:59:00Z"

mutations:
  M-001:
    title: "Retrait mode communauté"
    created_at: "2026-06-15T11:00:00Z"
    artefacts_touched:
      - "features/community-mode"
      - "04-identity.md"
```

### Top-level keys obligatoires

| Clé | Type | Description |
|---|---|---|
| `project_slug` | string | Slug du projet (ex : `ylune`) |
| `last_event_at` | ISO 8601 UTC | Horodatage du dernier event dans `log.ndjson` |
| `hypotheses` | map\<H-key, HypothesisEntry\> | Une entrée par hypothèse connue |
| `features` | map\<slug, FeatureEntry\> | Une entrée par feature trackée |
| `bets` | map\<B-NNN, BetEntry\> | Une entrée par pari créé |
| `mutations` | map\<M-NNN, MutationEntry\> | Une entrée par mutation majeure |

---

## 4. Schéma — `lifecycle/bets/B-NNN.yaml`

> Format d'ID : `B-001`, `B-002`, … (zéro-paddé sur 3 chiffres).

```yaml
id: B-001
title: "WTP praticienne IT validé à €19/mois"
rationale: >
  H1 non encore validée sur le marché IT. Le plan d'activation vague 1 (IT+FR)
  est bloquant — sans preuve de WTP IT, Sprint 1 ne peut pas démarrer.
hypothesis_ref: H1
success_criteria:
  metric: "Nombre de pre-pays IT reçus"
  threshold: 2
  unit: "paiements Stripe"
  deadline: "2026-06-15T23:59:00Z"
signals:
  - "Stripe Dashboard — filtrer par pays IT sur la période [created_at, expires_at]"
  - "Email praticienne beta IT confirmant l'abonnement"
created_at: "2026-05-27T15:00:00Z"
expires_at: "2026-06-15T23:59:00Z"
status: resolved              # open | resolved | expired
resolved_at: "2026-06-10T08:00:00Z"
resolution: won               # won | lost | expired
resolution_note: "4 paiements IT confirmés Stripe avant expiration."
```

### Champs obligatoires / optionnels

| Champ | Type | Req | Contrainte |
|---|---|---|---|
| `id` | string | ✓ | Format `B-NNN` |
| `title` | string | ✓ | — |
| `rationale` | string | ✓ | — |
| `hypothesis_ref` | string | ✓ | Doit référencer une hypothèse connue (H1–H12 pour Ylune) |
| `success_criteria.metric` | string | ✓ | Nom de la métrique mesurée |
| `success_criteria.threshold` | number | ✓ | Seuil chiffré |
| `success_criteria.unit` | string | ✓ | Unité de mesure |
| `success_criteria.deadline` | ISO 8601 | ✓ | Équivalent à `expires_at` — doit être cohérent |
| `signals` | string[] | ✓ | Min 1 signal observable (comment mesurer concrètement) |
| `created_at` | ISO 8601 | ✓ | — |
| `expires_at` | ISO 8601 | ✓ | — |
| `status` | `"open"` \| `"resolved"` \| `"expired"` | ✓ | — |
| `resolved_at` | ISO 8601 \| null | ✓ | `null` si `status == "open"` |
| `resolution` | `"won"` \| `"lost"` \| `"expired"` \| null | ✓ | `null` si `status == "open"` |
| `resolution_note` | string \| null | opt | Requis si `status != "open"` |

> **Expiration automatique** : quand `expires_at` est atteint sans qu'un event `bet-resolved` existe dans `log.ndjson`, `pilot state` **génère automatiquement** un event `bet-resolved` avec `resolution: "expired"` et l'ajoute au log. A2 ne calcule **jamais** d'expiration — il lit uniquement le log. Tout bet en statut `open` passé son `expires_at` **sans** event `bet-resolved` correspondant indique un log corrompu (invariant E2E §10).

---

## 5. Schéma — `lifecycle/mutations/M-NNN/`

> Format d'ID : `M-001`, `M-002`, … (zéro-paddé sur 3 chiffres).

### Structure du dossier

```
lifecycle/mutations/M-001/
├── decision.md      # Narration de la décision (Markdown libre)
├── impacts.yaml     # Artefacts touchés, avec action requise
└── rationale.md     # Preuves factuelles justifiant la mutation
```

---

### 5.1 `decision.md`

```markdown
# M-001 — Retrait du mode communauté

**Date** : 2026-06-15  
**Auteur** : pilot/decide  
**Mutation** : Retrait de la feature "mode communauté — groupes de praticiennes"

## Contexte

Pendant le brainstorm initial, un mode communauté (groupes de praticiennes partageant
un espace client) avait été envisagé comme feature V2. Suite aux 40 entretiens beta
(FR + IT + DE), 0 praticienne n'a mentionné ce besoin spontanément.

## Décision

La feature `community-mode` est annulée (statut `cancelled`). Elle n'a jamais été
implémentée. Aucune donnée de production n'est concernée.

## Conséquences

- `04-identity.md` : retirer la mention du mode communauté dans la section Features V2
- Aucune migration de données requise
- Le catalogue d'offres reste 100% praticienne individuelle au MVP
```

---

### 5.2 `impacts.yaml`

```yaml
mutation_id: M-001
artefacts:
  - path: "04-identity.md"
    section: "Features > V2"
    action: remove_mention
    note: "Retirer la ligne 'Mode communauté' de la table V2."
  - path: "features/community-mode"
    section: null
    action: mark_cancelled
    note: "Si la feature existe dans .specs/, passer le statut à 'cancelled'."
```

| Champ | Type | Req | Description |
|---|---|---|---|
| `mutation_id` | string | ✓ | Identifiant `M-NNN` |
| `artefacts[].path` | string | ✓ | Chemin relatif depuis la racine du projet brainstorm |
| `artefacts[].section` | string \| null | opt | Section précise concernée |
| `artefacts[].action` | string enum | ✓ | `remove_mention`, `mark_cancelled`, `mark_deprecated`, `update_content`, `create`, `delete` |
| `artefacts[].note` | string | opt | Instruction précise pour l'éditeur |

> **`impacts.yaml` est la source de vérité structurée** pour toute mutation. Le champ `mutation-created.artefacts_touched` dans `log.ndjson` est un index rapide (string[]) destiné à la détection préliminaire ; il peut être incomplet. A2 lit **toujours** `impacts.yaml` pour déterminer les actions réelles à proposer dans l'Impact Report.

---

### 5.3 `rationale.md`

```markdown
# M-001 — Preuves

## Données empiriques

- 40 entretiens beta (FR : 18, IT : 14, DE : 8)
- Question ouverte : "Qu'est-ce qui vous manque le plus dans votre setup actuel ?"
- 0 réponse mentionnant des groupes ou une communauté de praticiennes

## Analyse

Le besoin était une projection du fondateur. Les praticiennes opèrent en solo
et perçoivent leur base clientèle comme exclusive. Un espace communautaire
est antagoniste avec l'image de "praticienne personnelle et unique".

## Décision

Annulation sans regret. Périmètre MVP plus focalisé.
```

---

## 6. Mapping events brainstorm → actions LiveSpec

> Cette table est consommée par `spec-refresh-from-brainstorm` pour générer l'Impact Report.

| `event_type` | Feature status in `.specs/` | Action proposée dans l'Impact Report |
|---|---|---|
| `feature-add` (`origin: "added"`) | feature absente | **Créer** une spec vide (`status: spec`) pour la feature |
| `feature-add` (`origin: "added"`) | feature présente, n'importe quel statut | **No-op** — feature déjà connue de LiveSpec |
| `feature-remove` (`new_status: "cancelled"`) | feature absente | **No-op** — jamais connue |
| `feature-remove` (`new_status: "cancelled"`) | feature présente, `status: spec\|plan\|implementing` | **Annuler** : passer le statut à `cancelled` |
| `feature-remove` (`new_status: "deprecated"`) | feature présente, `status: implemented` | **Déprécier** : passer le statut à `deprecated` |
| `feature-remove` (`new_status: "removed"`) | feature présente | **Déprécier ou annuler** selon statut courant dans `.specs/` |
| `hypothesis-update` (`new_status: "invalidated"`) | features liées via `hypothesis_refs` | **Signaler** : lister les features à risque dans le rapport (action humaine) |
| `pivot` | features liées à `hypothesis_ref` | **Signaler** : avertissement dans le rapport — vérification humaine requise |
| `decision` | — | **Aucune action automatique** — documenté dans le rapport uniquement |
| `observation` | — | **Aucune action automatique** — documenté dans le rapport uniquement |
| `mutation-created` | artefacts dans `impacts.yaml` | **Signaler** : liste les artefacts `.specs/` potentiellement affectés |
| `bet-resolved` (`resolution: "lost"`) | features liées à `hypothesis_ref` | **Signaler** : hypothèse non validée — action humaine requise |
| `bet-resolved` (`resolution: "won"`) | — | **Aucune action automatique** — succès loggé dans le rapport |
| `bet-created` | — | **Aucune action automatique** — rappel dans le rapport si le bet est ouvert |

> **Principe** : seuls `feature-add` et `feature-remove` génèrent des actions automatiques sur `.specs/`.  
> Tout le reste produit des signalements pour validation humaine.

---

## 7. Workflow `spec-refresh-from-brainstorm`

> Ce workflow est exécuté **côté vrai projet** (ex. `~/projects/ylune`), en mode interactif.

### Étape 0 — Détection du symlink

```
<project-root>/brainstorm/  →  ~/projects/project-brainstorm/projects/<slug>/
```

- Le skill vérifie que `brainstorm/lifecycle/log.ndjson` est accessible.
- Si le symlink est absent ou cassé → **BLOCKED** : symlink brainstorm manquant.
- Le slug est inféré depuis `brainstorm/` → répertoire cible → nom du dossier.

### Étape 1 — Lecture du curseur

- Fichier de curseur : `brainstorm/lifecycle/.refresh-cursor`
- Format JSON sur une seule ligne : `{"event_id":"E-000003","ts":"2026-06-10T08:00:00Z","hash":"a3f2c1..."}`.
- Si absent → traiter **tous** les events depuis le début du log (pas de curseur précédent).

### Étape 2 — Lecture des deltas + vérification de la chaîne

- Lire `log.ndjson` depuis le curseur (ou depuis le début).
- **Vérification de la chaîne `prev_hash`** : pour chaque event lu, recomputer le SHA-256 canonicalisé de la ligne précédente et le comparer au `prev_hash` déclaré. Si une divergence est détectée → **BLOCKED** : log corrompu à `event_id` E-XXXXXX (afficher l'event_id et les deux hashes). A2 ne continue pas sur un log corrompu.
- Collecter les events valides non encore traités, dans l'ordre chronologique.
- Charger `state.yaml` pour connaître le statut courant des features et hypothèses.

### Étape 3 — Génération de l'Impact Report

Format du rapport (Markdown, affiché interactivement) :

```markdown
# Impact Report — spec-refresh-from-brainstorm
**Date** : 2026-06-16T10:00:00Z  
**Période** : 2026-05-27T15:00:00Z → 2026-06-15T11:00:00Z  
**Events lus** : 9

## Actions proposées

### ✅ feature-add → Créer spec
- **Feature** : `multi-psp-routing` — "Routage PSP par géo"
- **Event source** : `2026-05-29T14:00:00Z` (feature-add)
- **Rationale** : Déblocage vague 2 DE+ES
- **Action** : Créer `.specs/features/multi-psp-routing/spec.md` avec `status: spec`
- **Confirmation requise** : [o/n]

### ⚠️ feature-remove → Annuler spec
- **Feature** : `community-mode` — "Mode communauté"
- **Event source** : `2026-06-01T10:00:00Z` (feature-remove, status: cancelled)
- **Statut actuel dans .specs/** : `spec` (non implémentée)
- **Action** : Passer le statut à `cancelled`
- **Confirmation requise** : [o/n]

## Signalements (aucune action automatique)

### 🔴 hypothesis-update — H3 pivoting
- Hypothèse H3 en statut `pivoting` depuis 2026-05-28
- Features liées dans .specs/ : aucune (H3 non référencée)
- Action recommandée : vérifier si le pivot DE affecte des specs en cours

### 📌 bet-resolved — B-001 won
- Pari B-001 résolu positivement (WTP IT validé)
- Aucune action sur .specs/ requise

## Aucun changement
- 3 events `observation` et 1 event `decision` — documentés seulement
```

### Étape 4 — Validation action par action (mode interactif)

- Chaque action est présentée **une par une**.
- L'utilisateur répond `o` (appliquer), `n` (ignorer), ou `d` (différer).
- Une action différée est enregistrée dans `brainstorm/lifecycle/.refresh-deferred.yaml`.
- Aucune action n'est appliquée en masse sans confirmation.

### Étape 5 — Application des actions validées

- Créations : générer le fichier spec minimal (template standard LiveSpec).
- Annulations / dépréciations : mettre à jour le champ `status` dans la spec existante.
- Aucune modification des artefacts brainstorm (lecture seule).

### Étape 6 — Mise à jour du curseur

- Écrire le `ts` du dernier event traité dans `brainstorm/lifecycle/.refresh-cursor`.
- Commit automatique proposé : `chore: refresh brainstorm sync cursor`.

---

## 8. Garde-fous

### 8.1 Trois champs obligatoires sur tout event

Tout event dans `log.ndjson` **doit** porter :

| Champ | Rôle |
|---|---|
| `rationale` | Pourquoi maintenant — discipline de justification |
| `hypothesis_ref` | Lien avec une hypothèse trackée ou `null` explicite |
| `expected_impact` | Impact attendu ou critère de retrait — mesurable ou observable |

Le skill `pilot` rejette à l'écriture tout event manquant un de ces trois champs.

### 8.2 Append-only enforcement

- `log.ndjson` : **aucune modification, aucune suppression** de ligne existante.
- Seul l'ajout en fin de fichier est autorisé.
- En cas de désaccord avec un event passé : écrire un event correctif (ex : `decision` supersedant une `decision` antérieure).
- Le skill `pilot` vérifie l'intégrité append-only avant chaque écriture (comparaison du hash SHA-256 des N premières lignes).

### 8.3 Validation humaine cascade

- Aucun artefact brainstorm (`03-challenge.md`, `04-identity.md`, etc.) n'est modifié automatiquement.
- `spec-refresh-from-brainstorm` est **lecture seule** côté brainstorm.
- Toute propagation vers `.specs/` passe par l'Impact Report interactif.
- Aucune cascade automatique sans `o` explicite de l'utilisateur.

### 8.4 Pilot ne touche jamais `.specs/`

- Le skill `pilot` opère exclusivement dans `lifecycle/` (côté brainstorm).
- Il n'a pas connaissance de la structure `.specs/` du vrai projet.
- Le pont est unidirectionnel : brainstorm → LiveSpec via `spec-refresh-from-brainstorm`.

---

## 9. Conventions de nommage et types enum

### Feature statuses (lifecycle/state.yaml)

| Valeur | Signification |
|---|---|
| `initial` | Existait au brainstorm (avant GO) |
| `added` | Ajoutée post-GO |
| `removed` | Retirée avec preuve (était listée, jamais implémentée côté LiveSpec) |
| `cancelled` | Jamais implémentée, annulée |
| `deprecated` | Implémentée, puis retirée |

### Feature statuses (LiveSpec .specs/)

| Valeur | Signification |
|---|---|
| `spec` | Spec créée, plan pas encore produit |
| `plan` | Plan technique produit |
| `implementing` | En cours de développement |
| `implemented` | Implémentée et testée |
| `deprecated` | Retirée après implémentation |
| `cancelled` | Annulée avant implémentation |

### Hypothesis statuses

| Valeur | Signification |
|---|---|
| `open` | Ni validée ni invalidée |
| `validated` | Preuve suffisante recueillie |
| `invalidated` | Réfutée par les faits |
| `pivoting` | En cours de reformulation suite à un pivot |

---

## 10. Invariants inter-fichiers

Les contraintes suivantes doivent être vérifiées par les tests E2E :

1. Tout `bet_id` référencé dans `log.ndjson` doit avoir un fichier `bets/B-NNN.yaml` correspondant.
2. Tout `mutation_id` référencé dans `log.ndjson` doit avoir un dossier `mutations/M-NNN/` avec les 3 fichiers (`decision.md`, `impacts.yaml`, `rationale.md`).
3. Tout `hypothesis_ref` non-null dans `log.ndjson` doit être une clé présente dans `state.yaml > hypotheses`.
4. Le `last_event_at` dans `state.yaml` doit correspondre au `ts` de la dernière ligne de `log.ndjson`.
5. Un event `feature-remove` avec `new_status: "deprecated"` ne peut référencer que des features dont `origin == "initial"` ou `status == "added"` dans `state.yaml` (preuve d'implémentation requise).
6. Le `status` d'un bet dans `state.yaml` doit être cohérent avec les events `bet-created` / `bet-resolved` dans `log.ndjson`.

---

## 11. Fichiers annexes

| Fichier | Créé par | Consommé par | Description |
|---|---|---|---|
| `lifecycle/log.sha256` | `pilot state --recompute-hashes` | `spec-refresh-from-brainstorm` | Index optionnel : une ligne `<event_id> <sha256_hex>` par event |
| `lifecycle/.refresh-cursor` | `spec-refresh-from-brainstorm` | `spec-refresh-from-brainstorm` | Curseur du dernier event traité (`{event_id, ts, hash}`) |
| `lifecycle/.refresh-deferred.yaml` | `spec-refresh-from-brainstorm` | `spec-refresh-from-brainstorm` | Actions différées par l'utilisateur |

### Format `log.sha256`

```
E-000001 a3f2c1d8e4b2...64hexchars
E-000002 9b1f3a7c5d0e...64hexchars
```

Une ligne par event, ordre chronologique, format `<event_id> <sha256_hex_64>`. Régénérable à tout moment par `pilot state --recompute-hashes`.

### Format `.refresh-cursor`

```json
{"event_id":"E-000003","ts":"2026-06-10T08:00:00Z","hash":"a3f2c1d8e4b2...64hexchars"}
```

JSON sur une seule ligne, sans retour chariot final.

### Format `.refresh-deferred.yaml`

```yaml
deferred:
  - ts: "2026-05-29T14:00:00Z"
    event: feature-add
    feature_id: multi-psp-routing
    deferred_at: "2026-06-16T10:05:00Z"
    reason: "Pas encore décidé si Paddle est retenu pour DE"
```
