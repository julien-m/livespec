# Design — Règle de routing LiveSpec

**Date** : 2026-05-16
**Scope** : projet `/Users/julienm/projects/livespec`
**Objectif** : router toute demande utilisateur (ajout, correction, test, etc.) vers la commande `spec.*` appropriée quand `.specs/` est présent, via une règle légère + référence chargée à la demande, avec check bloquant de synchronisation.

## Architecture

Trois artefacts :

```
.claude/
├── rules/
│   ├── livespec-routing.md       (court, chargé quand .specs/ détecté)
│   └── livespec-commands.md      (référence, chargée à la demande par le routing)
└── checks/
    └── livespec-routing-sync.md  (vérification bijection commands/ ↔ livespec-commands.md)
```

## Composants

### 1. `livespec-routing.md` (règle)

Court (< 50 lignes). Responsabilités :

- Détecter le déclencheur : `.specs/` à la racine du cwd
- Décrire la procédure de routing en 6 étapes (détection → intention → lecture référence → proposition → exécution → fallback si aucune commande)
- Renvoyer vers `livespec-commands.md` pour le détail
- Lister les exceptions (questions pures, debug rapide, mode Ask)
- Référencer la lecture préalable obligatoire de `.specs/spec-system.md`

### 2. `livespec-commands.md` (référence)

Une entrée par commande `spec.*`. Pour chaque entrée :
- Nom (`/spec.X`)
- Description courte (1 ligne, intention utilisateur typique)
- Paramètres usuels avec exemples concrets

Structure : table "intention → commande" en tête, puis sections détaillées par commande (en `### /spec.<name>`). Couvre les 20 commandes présentes dans `commands/`.

### 3. `livespec-routing-sync.md` (check)

Format identique à `migration-version.md` (existant) : `# Title / ## When / ## Verify`.

**When** : modification dans `commands/*.md` (excluding `*.expectations.md`) ou dans `.claude/rules/livespec-commands.md`.

**Verify** : bijection entre les noms de fichiers dans `commands/*.md` (filtre strict `! *.expectations.md`) et les headings `### /spec.<name>` dans `livespec-commands.md` (mapping `commands/<name>.md` ↔ `### /spec.<name>`). Tout écart bloque le commit via `/audit` (consommateur de `.claude/checks/`).

## Data flow

```
User message
  │
  ▼
Claude détecte .specs/ → charge livespec-routing.md
  │
  ▼
Identifie intention utilisateur
  │
  ▼
Read livespec-commands.md ─── (chargé à la demande, pas avant)
  │
  ▼
Propose /spec.X --params  (mode Ask: proposition seule)
  │
  ▼
Si confirmation → invoque le skill spec.* via Skill tool
```

Chaîne de check :

```
git commit
  │
  ▼
commit-via-skill rule → /git.commit
  │
  ▼
/audit lit .claude/checks/livespec-routing-sync.md
  │
  ▼
Verify bijection → PASS / FAIL bloquant
```

## Error handling

| Cas | Comportement |
|---|---|
| `.specs/` absent | Règle ne se déclenche pas, comportement par défaut |
| Intention ne matche aucune commande | Exécuter normalement + signaler absence de routage |
| `livespec-commands.md` introuvable | Procédure de routing échoue → fallback comportement par défaut + warning |
| Bijection violée au commit | `/audit` bloque, message d'erreur liste les commandes orphelines ou manquantes |
| Mode Ask actif | Proposition seule, aucune exécution même après détection |

## Testing

- **Manuel** : ajouter une commande factice `commands/dummy.md`, lancer `/audit`, vérifier que le check échoue. Supprimer, revérifier que ça passe.
- **Manuel** : supprimer une entrée dans `livespec-commands.md`, vérifier que `/audit` échoue. Restaurer.
- **Manuel** : ouvrir une nouvelle session dans ce repo, vérifier que la règle est bien chargée et propose `/spec.test` quand on dit "teste l'interface".
- Pas de test automatisé séparé — le check `/audit` EST le test continu.

## Edge cases

- **Commande renommée** : la bijection casse, force l'édition simultanée des deux côtés (`commands/` et référence). Voulu.
- **`*.expectations.md`** : exclus du filtre (sidecar, pas une commande).
- **Suppression dans CLAUDE.md** : non géré par ce check (CLAUDE.md liste les noms mais n'est pas la source ; reste un risque secondaire — voir D10 raffinée : CLAUDE.md garde la liste des noms mais routing est canonical pour params).
- **Conflit avec `commit-via-skill`** : aucun. La règle de routing ne commit pas, elle propose des commandes spec.*. Les commits restent gérés par `/git.commit`.

## Décisions raffinées (post-validation)

- D2/D3 : `.specs/` charge le routing ; le routing charge la référence à la demande (pas un chargement systématique des deux).
- D7 : bijection sur les noms uniquement (pas de hash freshness — trop de friction pour peu de valeur).
- D10 : CLAUDE.md garde la liste des noms (compat lecteurs existants) ; routing canonique pour params/exemples.
- Nouveau : protocole d'édition — manuel, message d'erreur du check pointe le diff exact (sortie shell : commandes orphelines / manquantes).
